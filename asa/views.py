import calendar
from collections import OrderedDict
import datetime
import json
import logging
import uuid
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.contrib.auth import get_user_model
from django.db.models import  Q
from django.db import transaction
from asa import models
from asa import serializers
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import User, Sendmail, SRRSDepartment
from asa.utils import shared_fxns
from django.db.models import Sum
from django.core.mail import send_mail

from rest_framework.pagination import PageNumberPagination

# Get an instance of a logger
logger = logging.getLogger(__name__)

class ASAViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="access-request",
            url_name="access-request")
    def access_request(self, request):
        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data
            employee = payload['employee']
            doctor_info = payload['doctor_info']
            system_access = payload['system_access']
            module_access = payload['module_access']

           

            # serialize employee payload
            employee_serializer = serializers.EmployeeSerializer(
                    data=employee, many=False)
            if not employee_serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            # serialize system access payload
            # system_access_serializer = serializers.SystemAccessSerializer(
            #         data=system_access, many=False)
            # if not system_access_serializer.is_valid():
            #     return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            # serialize doctor payload
            if employee['is_doctor'] == 'YES':
                employee['is_doctor'] = True
                is_doctor = True
                doctor_info_serializer = serializers.DoctorsSerializer(
                        data=doctor_info, many=False)
                if not doctor_info_serializer.is_valid():
                    return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            else:
                employee['is_doctor'] = False
                is_doctor = False
            
           
            department = employee['department']
            try:
                department = SRRSDepartment.objects.get(id=department)
                employee['department'] = department
            except Exception as e:
                return Response({"details": "Unknown department"}, status=status.HTTP_400_BAD_REQUEST)
            
            system = system_access['system']
            try:
                system = models.System.objects.get(id=system)
                system_access['system'] = system
            except Exception as e:
                return Response({"details": "Unknown selected system "}, status=status.HTTP_400_BAD_REQUEST)

    
            with transaction.atomic():
                employee_no = employee['employee_no']
                # check if employee exists
                employeeInstance = models.Employee.objects.filter(
                    Q(employee_no=employee_no)
                ).first()
                if employeeInstance:
                    models.Employee.objects.filter(
                        Q(employee_no=employee_no)
                    ).update(employee)
                    employee_exists = True
                else:
                    employeeInstance = models.Employee.objects.create(
                        **employee
                    )
                    employee_exists = False

                # create system access
                system_access.update({
                    "employee" : employeeInstance
                })
                is_existing = models.SystemAccess.objects.filter(
                    Q(employee=employeeInstance) & Q(system=system)
                ).exists()
                if not is_existing:
                    system_access = models.SystemAccess.objects.create(
                        **system_access
                    )

                # module access
                if module_access.get('modules'):
                    module_access.update({
                        "employee" : employeeInstance
                    })
                    # check if is existing
                    is_existing = models.ModuleAccess.objects.filter(
                        employee=employeeInstance, system=system
                    ).exists()
                    if is_existing:
                        models.ModuleAccess.objects.filter(
                           Q(employee=employeeInstance) & Q(system=system)
                        ).update(module_access)
                        # modules = is_existing.modules
                        # modules += module_access['modules']
                        # is_existing.save()
                    else:
                        module_access = models.ModuleAccess.objects.create(
                            **module_access
                        )

                # create doctor info
                if is_doctor:
                    doctor_info.update({
                        "employee" : employeeInstance
                    })
                    # check if is existing
                    is_existing = models.DoctorInfo.objects.filter(
                        Q(employee=employeeInstance)
                    ).exists()
                    if is_existing:
                        models.DoctorInfo.objects.filter(
                           Q(employee=employeeInstance)
                        ).update(doctor_info)
                    else:
                        doctor_info = models.DoctorInfo.objects.create(
                            **doctor_info
                        )

                # create access instance
                if not employee_exists:
                    access = {
                        "employee": employeeInstance
                    }
                    access = models.Access.objects.create(
                        **access
                    )

                # create track status change
                raw = {
                    "access": access,
                    "status": "REQUESTED",
                    "status_for": '/'.join(roles),
                    "action_by": authenticated_user
                }

                models.StatusChange.objects.create(**raw)


                # Notify ICT
                subject = f"New Access Request Received [ASA-AKHK]"
                message = f"Hello, \n\nA new access request from department: {department.name},\nhas been submitted by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending your action.\n\nRegards\nASA-AKHK"
                
                try:
                    mail = {
                        "email" : [department.hod.email], 
                        "subject" : subject,
                        "message" : message,
                    }

                    Sendmail.objects.create(**mail)

                except Exception as e:
                    logger.error(e)
                    # send_mail(subject, message, 'notification@akhskenya.org', managers_emails)

            user_util.log_account_activity(
                authenticated_user, authenticated_user, "Access Request created", f"Employee Id: {employeeInstance.id}")
            
            return Response('success', status=status.HTTP_200_OK)
            

        if request.method == "PUT":
            payload = request.data

            payload = json.loads(request.data['payload'])
            job_description_file = request.FILES.get('job_description', None)


            serializer = serializers.PutRecruitSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['record_id']
                department = payload['department']
                position_title = payload['position_title']
                position_type = payload['position_type']
                qualifications = payload['qualifications']
                nature_of_hiring = payload['nature_of_hiring']
                existing_staff_same_title = payload['existing_staff_same_title']
                reasons_for_not_sharing_tasks = payload['reasons_for_not_sharing_tasks']
                period_from = payload['period_from']
                period_to = payload['period_to']
                filling_date = payload['filling_date']
                temporary_task_assignment_to = payload['temporary_task_assignment_to']

                # Check temporary hire period
                if position_type == 'Temporary':
                    if not period_from or not period_to:
                        return Response({"details": "Period From and Period To required"},
                                status=status.HTTP_400_BAD_REQUEST)
                    
                    years = shared_fxns.find_date_difference(period_from,period_to,'years')
                    if years > 1:
                        return Response({"details": "Temporary hire period cannot be more than one year"},
                                status=status.HTTP_400_BAD_REQUEST)

                try:
                    recruit = models.Recruit.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Recruit Request !"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    department = SRRSDepartment.objects.get(id=department)
                except Exception as e:
                    print(e)
                    return Response({"details": "Unknown Department!"}, status=status.HTTP_400_BAD_REQUEST)

                if not qualifications:
                    return Response({"details": "Qualifications Required !"}, status=status.HTTP_400_BAD_REQUEST)
                
                # keep history before editing
                try:
                    history = serializers.SuperSlimFetchRecruitSerializer(recruit, many=False).data
                    for key, value in history.items():
                        try:
                            if isinstance(value, uuid.UUID):
                                history[key] = str(value)
                        except Exception as e:
                            print(e)
                    raw = {
                        "uid" : recruit.uid,
                        "data" : dict(history),
                        "triggered_by": authenticated_user
                    }
                    models.RecruitHistory.objects.create(**raw)
                except Exception as e:
                    print(e)       
                
                with transaction.atomic():
                    raw = {
                        "department": department,
                        "created_by": authenticated_user,
                        "position_title": position_title,
                        "position_type": position_type,
                        "qualifications": qualifications,
                        "nature_of_hiring": nature_of_hiring,
                        "existing_staff_same_title": existing_staff_same_title,
                        "reasons_for_not_sharing_tasks": reasons_for_not_sharing_tasks,
                        "period_from": period_from,
                        "period_to": period_to,
                        "filling_date": filling_date,
                        "temporary_task_assignment_to": temporary_task_assignment_to,
                    }  

                    models.Recruit.objects.filter(Q(id=request_id)).update(**raw)

                    if job_description_file:
                        recruit.job_description = job_description_file
                        recruit.save()

                    # create track status change
                    raw = {
                        "recruit": recruit,
                        "status": "EDITED",
                        "status_for": '/'.join(roles),
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)


                    # Notify creator
                    subject = f"Recruitment Request {recruit.uid} Edited [SRRS-AKHK]"
                    message = f"Hello, \n\nYour recruit request of id: {recruit.uid} for position: {recruit.position_title},\nhas been edited by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nVisit SRRS to review.\n\nRegards\nSRRS-AKHK"

                    try:
                        mail = {
                            "email" : [recruit.created_by.email], 
                            "subject" : subject,
                            "message" : message,
                        }

                        Sendmail.objects.create(**mail)

                    except Exception as e:
                        print(e)

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Recruitment Request edited", f"Recruitment Request Id: {recruit.id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
  
        elif request.method == "PATCH":
            payload = request.data
            serializer = serializers.PatchRecruitSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                recruit_id = payload['recruit_id']
                recruit_status = payload['status'].upper()
                reason = payload.get('comments', None) 

                try:
                    recruit = models.Recruit.objects.get(id=recruit_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Recruit !"}, status=status.HTTP_400_BAD_REQUEST)
            
                
                with transaction.atomic():

                    if recruit_status in  ['DECLINED','CANCELED', 'ONHOLD']:
                        recruit.rejected_by = authenticated_user
                        if not reason:
                            return Response({"details": f"Reason for {recruit_status} status required !"}, status=status.HTTP_400_BAD_REQUEST)

                    if recruit_status == "REACTIVATED":
                        # find last status before on hold
                        selected_status = ""
                        unwanted = ['ONHOLD', 'REACTIVATED']
                        recent_statuses = list(models.StatusChange.objects.filter(Q(recruit=recruit)).order_by('-date_created').values_list('status', flat=True))

                        for recent_status in recent_statuses:
                            if recent_status not in unwanted:
                                selected_status = recent_status
                                break

                        recruit.status = selected_status

                    else:
                        recruit.status = recruit_status

                    if reason:
                        current_reason = recruit.rejection_reasons

                        if current_reason:
                            current_reason.append(
                                {
                                    "status": recruit_status,
                                    "reason": reason,
                                    "date": str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))
                                }
                            )
                            recruit.rejection_reasons = current_reason
                        else:
                            recruit.rejection_reasons =  [
                                {
                                    "status": recruit_status,
                                    "reason": reason,
                                    "date": str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))
                                }
                            ]

                    recruit.save()

                    # track status change
                    raw = {
                        "recruit": recruit,
                        "status": recruit_status,
                        "status_for": '/'.join(roles),
                        "action_by": authenticated_user,
                    }
                    models.StatusChange.objects.create(**raw)

                    emails = []
                    target = []

                    if recruit.is_slt_approved:
                        emails.append(recruit.department.slt.email)

                    if recruit.is_hhr_approved:
                       target += ["HR","HHR"]

                    if recruit.is_hof_approved:
                       target += ["HOF","FINANCE"]

                    if recruit.is_ceo_approved:
                       target += ["CEO"]

                    # Notify targets
                    targets_emails = list(get_user_model().objects.filter(Q(groups__name__in=target)).values_list('email', flat=True))
                    
                    # Notify requestor
                    emails.append(recruit.created_by.email)

                    # combine emails
                    emails += targets_emails

                    subject = f"Staff Recruitment Request: {recruit.uid} Progress Update [SRRS-AKHK]"
                    message = f"Hello. \n\nThe requisition request of id:{recruit.uid} for position: {recruit.position_title} has been marked as {recruit_status}\nby {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\n\nRegards\nSRRS-AKHK"

                    try:
                        mail = {
                            "email" : emails, 
                            "subject" : subject,
                            "message" : message,
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        logger.error(e)
                                                

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, f"Recruitment Request Update Status: {recruit_status}", f"Recruitment Request: {recruit_id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            query = request.query_params.get('q')
            slim = request.query_params.get('slim')

            if request_id:
                try:
                    resp = models.Recruit.objects.get(Q(id=request_id))
                    if slim:
                        resp = serializers.SlimFetchRecruitSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.FetchRecruitSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request!"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:

                    if "HOD" in roles:

                        if query == 'pending':
                            resp = models.Recruit.objects.filter(Q(department=request.user.srrs_department) | Q(created_by=request.user), is_ceo_approved=False, is_deleted=False).order_by('-date_created')

                        else:
                            resp = models.Recruit.objects.filter(Q(department=request.user.srrs_department) | Q(created_by=request.user), is_deleted=False).order_by('-date_created')

                    elif "USER_MANAGER" in roles:
                        resp = models.Recruit.objects.filter(Q(is_deleted=False) ).order_by('-date_created')

                    elif "SLT" in roles:
                        resp = []
                        if "HOF" in roles:

                            if query == 'pending':
                                resp = models.Recruit.objects.filter((Q(department__slt=authenticated_user) & Q(is_slt_approved=False)) |(Q(is_hof_approved=False) & Q(is_hhr_approved=True)), is_deleted=False).order_by('-date_created')

                            else:
                                resp = models.Recruit.objects.filter((Q(department__slt=authenticated_user) & Q(is_slt_approved=False)) |(Q(is_hof_approved=False) & Q(is_hhr_approved=True)), is_deleted=False).order_by('-date_created')

                        else:
                            resp = models.Recruit.objects.filter(Q(is_deleted=False) & Q(department__slt=authenticated_user) & Q(is_slt_approved=False)).order_by('-date_created')

                    elif "HR" in roles:
                        if not query:
                            resp = models.Recruit.objects.filter((Q(is_slt_approved=True)),is_deleted=False).order_by('-date_created')

                        elif query == 'pending':
                            resp = models.Recruit.objects.filter((Q(is_slt_approved=True) & Q(is_hhr_approved=False)),is_deleted=False).order_by('-date_created')

                    elif "HOF" in roles:
                        if not query:
                            resp = models.Recruit.objects.filter((Q(is_hof_approved=False) & Q(is_hhr_approved=True)),is_deleted=False).order_by('-date_created')

                        elif query == 'pending':
                            resp = models.Recruit.objects.filter((Q(is_hof_approved=False) & Q(is_hhr_approved=True)),is_deleted=False).order_by('-date_created')
                    
                    elif "CEO" in roles:
                        if not query:
                            resp = models.Recruit.objects.filter((Q(is_hof_approved=True) & Q(is_hhr_approved=True) & Q(is_ceo_approved=False)),is_deleted=False).order_by('-date_created')

                        elif query == 'pending':
                            resp = models.Recruit.objects.filter((Q(is_hof_approved=True) & Q(is_hhr_approved=True) & Q(is_ceo_approved=False)),is_deleted=False).order_by('-date_created')

                    elif "USER" in roles:
                        resp = []


                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resp, request)
                    serializer = serializers.SlimFetchRecruitSerializer(
                        result_page, many=True, context={"user_id":request.user.id})
                    return paginator.get_paginated_response(serializer.data)
                
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request !"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:

                    raw = {"is_deleted" : True}
                    models.Recruit.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)    
                 
                except Exception as e:
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)    

    
    @action(methods=["POST"],
            detail=False,
            url_path="approve-request",
            url_name="approve-request")
    def approval(self, request):

        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        allowed = ["HOF","SLT","HHR","CEO"]

        if not any(role in allowed for role in roles):
            return Response({"details": "Permission Denied !"}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "POST":

            payload = request.data
            roles = user_util.fetchusergroups(request.user.id) 

            serializer = serializers.ApprovalSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                recruit_id = payload['recruit_id']
                comments = payload.get('comments')
                replacement = payload.get('replacement', None)

                try:
                    recruit = models.Recruit.objects.get(Q(id=recruit_id))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Recruit !"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():

                    new_status = "APPROVED"
                    forward_to = []
                    previous_office = []

                    if 'SLT' in roles:
                        if recruit.department.slt == authenticated_user and not recruit.is_slt_approved:
                            recruit.is_slt_approved = True
                            new_status = "SLT APPROVED"
                            forward_to = ["HR","HHR"]
                            previous_office = []

                            if comments:
                                recruit.slt_comments = comments

                    if 'HHR' in roles:
                        if recruit.is_slt_approved:
                            recruit.is_hhr_approved = True
                            new_status = "HR APPROVED"
                            forward_to = ["HOF","FINANCE"]
                            previous_office = ["SLT"]

                            if comments:
                                recruit.hhr_comments = comments
                            
                            if recruit.nature_of_hiring == 'Replacement':
                                if not replacement:
                                    return Response({"details": "Staff Replacement Details Required"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                                
                                recruit.replacement_details = replacement

                    if 'HOF' in roles:
                        if recruit.is_hhr_approved:
                            recruit.is_hof_approved = True
                            new_status = "FINANCE APPROVED"
                            forward_to = ["CEO"]
                            previous_office = ["SLT","HR","HHR"]
                            if comments:
                                recruit.hof_comments = comments

                    if 'CEO' in roles:
                        if recruit.is_hof_approved:
                            recruit.is_ceo_approved = True
                            new_status = "CEO APPROVED"
                            forward_to = []
                            previous_office = ["SLT","HR","HHR","HOF","FINANCE"]
                            if comments:
                                recruit.ceo_comments = comments

                    
                    recruit.status = new_status
                    recruit.save()

                    # track status change
                    raw = {
                        "recruit": recruit,
                        "status": new_status,
                        "status_for": '/'.join(roles),
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)

                    # Notify the requestor & previous offices
                    emails = list(get_user_model().objects.filter(Q(groups__name__in=previous_office)).values_list('email', flat=True))
                    emails.append(recruit.created_by.email)
                    subject = f"Recruitment Request: {recruit.uid} Status  [SRRS-AKHK]"
                    message = f"Hello, \nStaff Recruitment Request of id: {recruit.uid} for position: {recruit.position_title} has been {new_status}\nby {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.\n\nRegards\nSRRS-AKHK"
                    
                    try:
                        mail = {
                            "email" : [recruit.created_by.email], 
                            "subject" : subject,
                            "message" : message,
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        logger.error(e)

                    # Notify next office
                    emails = list(get_user_model().objects.filter(Q(groups__name__in=forward_to)).values_list('email', flat=True))
                    subject = f"Recruitment Request: {recruit.uid} Pending Your Action.  [SRRS-AKHK]"
                    message = f"Hello. \nRecruitment Request: {recruit.uid} from department: {recruit.department.name}, for position: {recruit.position_title} is {new_status},\nby {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}, and is now pending your action\n\nRegards\nSRRS-AKHK"

                    try:
                        if emails:
                            mail = {
                                "email" : emails, 
                                "subject" : subject,
                                "message" : message,
                            }
                            
                            Sendmail.objects.create(**mail)
                    except Exception as e:
                        logger.error(e)


                user_util.log_account_activity(
                    authenticated_user, recruit.created_by, "Recruitment Request approval", 
                    f"Approval Executed UID: {str(recruit.id)}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, 
                                status=status.HTTP_400_BAD_REQUEST)
            

    @action(methods=["POST","PUT"],
            detail=False,
            url_path="hr-details-update",
            url_name="hr-details-update")
    def hr_details_update(self, request):

        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        allowed = ["HOF","HR","HHR","FINANCE"]

        if not any(item in allowed for item in roles):
            return Response({"details": "Permission Denied !"}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "POST":

            payload = request.data

            serializer = serializers.PatchHRDetailsSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                recruit_id = payload['recruit_id']
                proposed_salary = payload['proposed_salary']
                replacement_details = payload.get('replacement_details', None)
                comments = payload.get('comments', None)

                try:
                    recruit = models.Recruit.objects.get(id=recruit_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Recruitment Request !"}, status=status.HTTP_400_BAD_REQUEST)
                
                if recruit.nature_of_hiring == 'Replacement' and not replacement_details:
                    return Response({"details": "Replacement details required !"}, status=status.HTTP_400_BAD_REQUEST)
                
                # keep history before editing
                try:
                    history = serializers.SlimFetchRecruitSerializer(recruit, many=False).data
                    raw = {
                        "uid" : recruit.uid,
                        "data" : history,
                        "triggered_by": authenticated_user
                    }
                    models.RecruitHistory.objects.create(**raw)
                except Exception as e:
                    print(e)
                
                with transaction.atomic():

                    recruit.proposed_salary = proposed_salary
                    recruit.replacement_details = replacement_details
                    recruit.hhr_comments = comments
                    recruit.save()

                user_util.log_account_activity(
                    authenticated_user, recruit.created_by, "HR Details Added", f"Recruitment ID : {str(recruit.id)}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
                 
    @action(methods=["POST"],
            detail=False,
            url_path="attach-budget-approval",
            url_name="attach-budget-approval")
    def attach_budget_approval(self, request):

        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        allowed = ["HOF","HR","HHR","FINANCE"]

        if not any(item in allowed for item in roles):
            return Response({"details": "Permission Denied !"}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "POST":

            payload = json.loads(request.data['payload'])
            budget_approval_file = request.FILES.get('budget_approval', None)

            if not budget_approval_file:
                return Response({"details": "No file attached"}, status=status.HTTP_400_BAD_REQUEST)


            serializer = serializers.ApprovalSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                recruit_id = payload['recruit_id']

                try:
                    recruit = models.Recruit.objects.get(id=recruit_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Recruit !"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    recruit.budget_approval_file = budget_approval_file
                    recruit.save()

                    # update status
                    raw = {
                        "recruit": recruit,
                        "status": "BUDGET APPROVAL UPLOADED",
                        "status_for": '/'.join(roles),
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)

                    # Notify the HR / FINANCE
                    recipients = list(get_user_model().objects.filter(
                        Q(groups__name__in=['HR','HOF'])).values_list('email', flat=True))
                    subject = f"Recruitment Request {recruit.uid} Budget  [SRRS-AKHK]"
                    message = f"Hello. \nBudget approval for requisition position: {recruit.position_title},\nhas been uploaded by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\n\nRegards\nSRRS-AKHK"

                    try:
                        mail = {
                            "email" : recipients, 
                            "subject" : subject,
                            "message" : message,
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        logger.error(e)

                user_util.log_account_activity(
                    authenticated_user, recruit.created_by, "SRRS budget approval", f"UID: {str(recruit.id)}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)



    @action(methods=["POST","PUT"],
            detail=False,
            url_path="employee",
            url_name="employee")
    def employee(self, request):

        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        allowed = ["HOF","HR","HHR","FINANCE"]

        if not any(item in allowed for item in roles):
            return Response({"details": "Permission Denied !"}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "POST":

            payload = request.data

            employees = payload.get('employees', None) 
            if not employees:
                return Response({"details": "Staff details required"}, status=status.HTTP_400_BAD_REQUEST)
            
            recruit_id = payload.get('recruit_id', None) 
            if not recruit_id:
                return Response({"details": "Request id required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                recruit = models.Recruit.objects.get(id=recruit_id)
            except (ValidationError, ObjectDoesNotExist):
                return Response({"details": "Unknown Recruit !"}, status=status.HTTP_400_BAD_REQUEST)
            
            for employee in employees:
                serializer = serializers.EmployeeSerializer(
                    data=employee, many=False)
                if not serializer.is_valid():
                    return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            
            for employee in employees:
                reporting_date = employee.get('reporting_date', None) 
                reporting_station = employee.get('reporting_station', None) 
                working_station = employee.get('working_station', None) 
                employee_no = employee.get('employee_no', None) 
                name = employee.get('name', None) 
                email = employee.get('email', None) 

                if reporting_station == 'OUTREACH CENTRES':
                    if not working_station:
                        return Response({"details": "Working station required "}, status=status.HTTP_400_BAD_REQUEST)

                is_existing = models.Employee.objects.filter(Q(employee_no=employee_no)).exists()
                if is_existing:
                    return Response({"details": f"Employee {employee_no} already exists "}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    raw = {
                        "name" : name,
                        "email" : email,
                        "recruit" : recruit,
                        "employee_no" : employee_no, 
                        "reporting_date" : reporting_date, 
                        "working_station" : working_station,
                        "action_by" : authenticated_user
                    }

                    models.Employee.objects.create(**raw)

                    # Notify the HR / FINANCE
                    recipients = list(get_user_model().objects.filter(
                        Q(groups__name__in=['HR','HOF', 'CEO'])).values_list('email', flat=True))
                    recipients.append(recruit.created_by.email)
                    recipients.append(recruit.department.slt.email)
                    subject = f"Candidate hired [SRRS-AKHK]"
                    message = f"Hello. \n\nThe position: {recruit.position_title},\nhas been filled. Candidate name: {name},\nas updated by{authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\n\nRegards\nSRRS-AKHK"

                    try:
                        mail = {
                            "email" : recipients, 
                            "subject" : subject,
                            "message" : message,
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        logger.error(e)


            recruit.status = "HIRED"
            recruit.save()

            # update status
            raw = {
                "recruit": recruit,
                "status": "HIRED",
                "status_for": '/'.join(roles),
                "action_by": authenticated_user
            }

            models.StatusChange.objects.create(**raw)

            user_util.log_account_activity(
                authenticated_user, recruit.created_by, "SRRS Employee added", f"UID: {str(recruit.id)}")
            
            return Response('success', status=status.HTTP_200_OK)
        
        if request.method == "PUT":

            payload = request.data

            serializer = serializers.PutEmployeeSerializer(
                data=payload, many=False)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            request_id = payload.get('request_id', None) 
            reporting_date = payload.get('reporting_date', None) 
            reporting_station = payload.get('reporting_station', None) 
            working_station = payload.get('working_station', None) 
            employee_no = payload.get('employee_no', None) 
            name = payload.get('name', None) 
            email = payload.get('email', None) 

            try:
                employee = models.Employee.objects.get(id=request_id)
            except (ValidationError, ObjectDoesNotExist):
                return Response({"details": "Unknown Employee "}, status=status.HTTP_400_BAD_REQUEST)

            if reporting_station == 'OUTREACH CENTRES':
                if not working_station:
                    return Response({"details": "Working station required "}, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                raw = {
                    "name" : name,
                    "email" : email,
                    "employee_no" : employee_no, 
                    "reporting_date" : reporting_date, 
                    "working_station" : working_station,
                }

                models.Employee.objects.filter(Q(id=request_id)).update(**raw)


            user_util.log_account_activity(
                authenticated_user, authenticated_user, "SRRS Employee edited", f"UID: {str(request_id)}")
            
            return Response('success', status=status.HTTP_200_OK) 


class LocumViewSet(viewsets.ViewSet):

    def get_queryset(self):
        return []

    @action(methods=["GET",],
            detail=False,
            url_path="locum",
            url_name="locum")
    def locums(self, request):
                    
        department = request.query_params.get('department')
        position_type = request.query_params.get('position_type')
        nature_of_hiring = request.query_params.get('nature_of_hiring')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        r_status = request.query_params.get('status')
        date = False

        if date_to and date_from:
            date = True

        def create_date_range(date_from,date_to):
            # Convert the string dates to datetime objects
            date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d')
            date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d')

            q_filters = Q(date_created__gte=date_from) & Q(date_created__lte=date_to)

            return q_filters

        q_filters = Q()

        if department:
            q_filters &= Q(department=department)

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)
            
        if r_status:
            q_filters &= Q(status=r_status)

        if position_type:
            q_filters &= Q(position_type=position_type)

        if nature_of_hiring:
            q_filters &= Q(nature_of_hiring=nature_of_hiring)


        if q_filters:

            resp = models.Recruit.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
            
        else:
            roles = user_util.fetchusergroups(request.user.id)  

            if "HOD" in roles:
                resp = models.Employee.objects.filter(Q(recruit__department=request.user.srrs_department) | Q(created_by=request.user), recruit__position_type='Temporary', is_deleted=False).order_by('-date_created')

            else:
                resp = models.Employee.objects.filter(Q(recruit__position_type='Temporary') & Q(is_deleted=False)).order_by('-date_created')
   
        paginator = PageNumberPagination()
        paginator.page_size = 50
        result_page = paginator.paginate_queryset(resp, request)
        serializer = serializers.SlimFetchEmployeeSerializer(
            result_page, many=True, context={"user_id":request.user.id})
        return paginator.get_paginated_response(serializer.data)


    @action(methods=["POST","GET","DELETE"],
            detail=False,
            url_path="attendance",
            url_name="attendance")
    def attendance(self, request):
        authenticated_user = request.user
        if request.method == "POST":
            payload = request.data

            serializer = serializers.AttendanceSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                month = payload['month']
                year = payload['year']
                day = payload['day']
                hours_worked = payload['hours_worked']
                overtime_hours = payload['overtime_hours']

                try:
                    employee = models.Employee.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Requisition"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Invalid Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                # check if date is within hire period
                end_period_date = employee.recruit.period_to
                selected_date =  f"{year}-{month}-{day}"
                period = shared_fxns.find_date_difference(selected_date, str(end_period_date.strftime('%Y-%m-%d')),'days')

                if period < 0:
                    return Response({"details": "Attendance date is beyond locum period"}, status=status.HTTP_400_BAD_REQUEST)
                
                begin_period_date = employee.recruit.period_from
                period = shared_fxns.find_date_difference(str(begin_period_date.strftime('%Y-%m-%d')),selected_date, 'days')

                if period < 0:
                    return Response({"details": "Attendance date not within locum period"}, status=status.HTTP_400_BAD_REQUEST)


                is_existing =  models.LocumAttendance.objects.filter(
                    Q(month=month) & Q(year=year) & Q(employee=employee)
                ).order_by('-date_created').first()


                with transaction.atomic():
                    data = {
                        "id" : str(uuid.uuid4()),
                        "month": month,
                        "year": year,
                        "day": day,
                        "hours_worked": hours_worked,
                        "overtime_hours": overtime_hours
                    }
                    raw = {
                        "employee": employee,
                        "month": month,
                        "year": year,
                        "action_by": authenticated_user,
                        "data": [data]
                    }

                    if is_existing:
                        attendance = is_existing.data
                        for item in attendance:
                            if int(item['day']) == int(day):
                                return Response({"details": f"Attendance for {day} of {calendar.month_name[month]}  has been recorded"}, status=status.HTTP_400_BAD_REQUEST)
                        attendance.append(data)
                        is_existing.data = attendance
                        is_existing.save()
                    else:
                        models.LocumAttendance.objects.create(**raw)
                    
                    return Response(200, status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, 
                                status=status.HTTP_400_BAD_REQUEST)


        elif request.method == "GET":

            request_id = request.query_params.get('request_id')
            month = request.query_params.get('month', 0) or 0
            year = request.query_params.get('year', 0) or 0

            year = int(year)
            month = int(month)

            try:
                targetInstance = models.Employee.objects.get(Q(id=request_id))
            except (ValidationError, ObjectDoesNotExist):
                return Response({"details": "Unknown Staff"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(e)
                return Response({"details": "Invalid Request"}, status=status.HTTP_400_BAD_REQUEST)

            def is_reporting_month_fn(targetInstance):
                reporting_date = targetInstance.reporting_date
                month = reporting_date.month
                year = reporting_date.year
                return [year,month]
            
            def current_month_fn():
                current_date = datetime.datetime.now().date()
                month = current_date.month
                year = current_date.year
                return [year,month]
            
            def check_if_hiring_month_fn():
                hiring_month, hiring_year = is_reporting_month_fn(targetInstance)
                current_month, current_year = current_month_fn()

                if current_month == hiring_month and current_year == hiring_year:
                    return True
                return False

            def reporting_date_fn(targetInstance):
                reporting_date = targetInstance.reporting_date

                if reporting_date:
                    # Extract the month
                    month = reporting_date.month
                    # Extract day
                    start_day = reporting_date.day

                    # Determine the number of days in the month
                    year = reporting_date.year
                    _, num_days = calendar.monthrange(year, month)

                    # Print the month and the number of days
                    month_name = calendar.month_name[month]

                    days = []
                    for i in range(start_day, num_days + 1):
                        days.append(i)

                    attendance = models.LocumAttendance.objects.filter(Q(employee=request_id), year=year, month=month)
                    serialized_attendance = serializers.SlimFetchLocumAttendanceSerializer(
                            attendance, many=True).data
                    
                    employee = serializers.SuperSlimFetchEmployeeSerializer(
                            targetInstance, many=False).data


                    resp = {
                        "days": days,
                        "month": month,
                        "month_name" : month_name,
                        "year" : year,
                        "attendance" : serialized_attendance,
                        "employee": employee
                    }

                return resp

            def current_month_days_fn(request_id):

                current_date = datetime.now().date()
                month = current_date.month
                start_day = current_date.day
                year = current_date.year
                _, num_days = calendar.monthrange(year, month)

                # Get the month name
                month_name = calendar.month_name[month]

                days = []
                for i in range(start_day, num_days + 1):
                    days.append(i)

                attendance = models.LocumAttendance.objects.filter(Q(recruit=request_id), year=year, month=month)
                serialized_attendance = serializers.SlimFetchLocumAttendanceSerializer(
                        attendance, many=True).data
                
                employee = serializers.SuperSlimFetchEmployeeSerializer(
                            targetInstance, many=False).data

                resp = {
                    "days": days,
                    "month": month,
                    "month_name" : month_name,
                    "year" : year,
                    "attendance" : serialized_attendance,
                    "employee" : employee
                }

                return Response(resp, status=status.HTTP_200_OK)
            
            def selected_period_fn(request_id,month,year):
                start_day = 1
                _, num_days = calendar.monthrange(int(year), int(month))

                # Get the month name
                month_name = calendar.month_name[month]

                days = []
                for i in range(start_day, num_days + 1):
                    days.append(i)

                attendance = models.LocumAttendance.objects.filter(Q(employee=request_id), year=year, month=month)
                serialized_attendance = serializers.SlimFetchLocumAttendanceSerializer(
                        attendance, many=True).data
                
                employee = serializers.SuperSlimFetchEmployeeSerializer(
                            targetInstance, many=False).data

                resp = {
                    "days": days,
                    "month": month,
                    "month_name" : month_name,
                    "year" : year,
                    "attendance" : serialized_attendance,
                    "employee": employee
                }
                
                return resp
            

            if month or year:
                if not year:
                    year = datetime.datetime.now().date().year
                resp = selected_period_fn(request_id,month,year)
            elif check_if_hiring_month_fn():
                resp = reporting_date_fn(targetInstance)
            else:
                resp = current_month_days_fn(request_id)

            return Response(resp, status=status.HTTP_200_OK)

        elif request.method == "DELETE":

            employee_id = request.query_params.get('employee_id')
            record_id = request.query_params.get('record_id')

            try:
                targetInstance = models.Employee.objects.get(Q(id=employee_id))
            except (ValidationError, ObjectDoesNotExist):
                return Response({"details": "Unknown Staff"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(e)
                return Response({"details": "Invalid Request"}, status=status.HTTP_400_BAD_REQUEST)
            
            attendances = models.LocumAttendance.objects.filter(Q(employee=employee_id))
            for attendance in attendances:
                for data in attendance.data:
                    if data['id']  == record_id:
                        attendance.data.remove(data)
                        attendance.save()
                        break
            return Response(200, status=status.HTTP_200_OK)
            

   
class SRRSReportsViewSet(viewsets.ViewSet):
    # search_fields = ['id', ]

    def get_queryset(self):
        return []

    @action(methods=["GET",],
            detail=False,
            url_path="requisitions",
            url_name="requisitions")
    def requisitions(self, request):
                    
        department = request.query_params.get('department')
        position_type = request.query_params.get('position_type')
        nature_of_hiring = request.query_params.get('nature_of_hiring')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        r_status = request.query_params.get('status')
        date = False

        if date_to and date_from:
            date = True

        def create_date_range(date_from,date_to):
            # Convert the string dates to datetime objects
            date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d')
            date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d')

            q_filters = Q(date_created__gte=date_from) & Q(date_created__lte=date_to)

            return q_filters

        # try:
        q_filters = Q()

        if department:
            q_filters &= Q(department=department)

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)
            
        if r_status:
            q_filters &= Q(status=r_status)

        if position_type:
            q_filters &= Q(position_type=position_type)

        if nature_of_hiring:
            q_filters &= Q(nature_of_hiring=nature_of_hiring)


        if q_filters:

            resp = models.Recruit.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
            
        else:
            roles = user_util.fetchusergroups(request.user.id)  

            if "HOD" in roles:
                resp = models.Recruit.objects.filter(Q(is_deleted=False) & Q(created_by=request.user)).order_by('-date_created')[:50]

            else:
                resp = models.Recruit.objects.filter(Q(is_deleted=False)).order_by('-date_created')[:50]

        resp = serializers.FetchRecruitSerializer(resp, many=True, context={"user_id":request.user.id}).data

        return Response(resp, status=status.HTTP_200_OK)
        
    @action(methods=["GET",],
            detail=False,
            url_path="replacements",
            url_name="replacements")
    def replacements(self, request):
                    
        department = request.query_params.get('department')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        # quote_status = request.query_params.get('status')
        date = False

        if date_to and date_from:
            date = True

        def create_date_range(date_from,date_to):
            # Convert the string dates to datetime objects
            date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d')
            date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d')

            q_filters = Q(date_created__gte=date_from) & Q(date_created__lte=date_to)

            return q_filters

        q_filters = Q(nature_of_hiring='Replacement')

        if department:
            q_filters &= Q(department=department)

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)
            
        # if quote_status:
        #     q_filters &= Q(status=quote_status)


        if q_filters:

            resp = models.Recruit.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
            
        else:
            roles = user_util.fetchusergroups(request.user.id)  

            resp = models.Recruit.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')[:50]

        resp = serializers.FetchRecruitSerializer(resp, many=True, context={"user_id":request.user.id}).data

        return Response(resp, status=status.HTTP_200_OK)
    
    @action(methods=["GET",],
            detail=False,
            url_path="hires",
            url_name="hires")
    def hires(self, request):
                    
        department = request.query_params.get('department')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        type = request.query_params.get('type')
        date = False

        if date_to and date_from:
            date = True

        def create_date_range(date_from,date_to):
            # Convert the string dates to datetime objects
            date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d')
            date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d')

            q_filters = Q(date_created__gte=date_from) & Q(date_created__lte=date_to)

            return q_filters

        q_filters = Q(status='ACTIVE')
        q_filters &= Q(recruit__status='HIRED')

        if department:
            q_filters &= Q(recruit__department=department)

        if type:
            q_filters &= Q(recruit__position_type=type)

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)


        resp = models.Employee.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
            
        resp = serializers.FullFetchEmployeeSerializer(resp, many=True, context={"user_id":request.user.id}).data

        return Response(resp, status=status.HTTP_200_OK)
        
        
class SRRSAnalyticsViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return []

    @action(methods=["GET",],
            detail=False,
            url_path="general",
            url_name="general")
    def general(self, request):
        roles = user_util.fetchusergroups(request.user.id)
        active_status = ['REQUESTED','CEO APPROVED','HR APPROVED','SLT APPROVED','CLOSED']

        if 'HOD' in roles:
            requests = models.Recruit.objects.filter(Q(department=request.user.srrs_department) | Q(created_by=request.user), is_deleted=False).count()
            canceled = models.Recruit.objects.filter(Q(department=request.user.srrs_department) |  Q(created_by=request.user), status="CANCELED", is_deleted=False).count()
            declined = models.Recruit.objects.filter(Q(department=request.user.srrs_department) |  Q(created_by=request.user), status="DECLINED", is_deleted=False).count()
            pending = models.Recruit.objects.filter(Q(department=request.user.srrs_department) |  Q(created_by=request.user), status__in=active_status, is_ceo_approved=False, is_deleted=False).count()
        else:
            requests = models.Recruit.objects.filter(Q(is_deleted=False)).count()
            canceled = models.Recruit.objects.filter(Q(status="CANCELED"), is_deleted=False).count()
            declined = models.Recruit.objects.filter(Q(created_by=request.user), status="DECLINED", is_deleted=False).count()
            pending = models.Recruit.objects.filter(Q(status__in=active_status), is_ceo_approved=False, is_deleted=False).count()

        resp = {
            "requests": requests,
            "canceled": canceled,
            "declined": declined,
            "pending": pending,
        }

        return Response(resp, status=status.HTTP_200_OK)