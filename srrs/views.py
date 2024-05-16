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
from srrs import models
from srrs import serializers
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import User, Department, Sendmail
from srrs.utils import shared_fxns
from django.db.models import Sum
from django.core.mail import send_mail

from rest_framework.pagination import PageNumberPagination

# Get an instance of a logger
logger = logging.getLogger(__name__)

class TrsViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="recruit",
            url_name="recruit")
    def recruit(self, request):
        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.RecruitSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                position_title = payload['position_title']
                position_type = payload['position_type']
                qualifications = payload['qualifications']
                job_description = payload['job_description']
                nature_of_hiring = payload['nature_of_hiring']
                existing_staff_same_title = payload['existing_staff_same_title']
                reasons_for_not_sharing_tasks = payload['reasons_for_not_sharing_tasks']
                filling_period_from = payload['filling_period_from']
                filling_period_to = payload['filling_period_to']
                temporary_task_assignment_to = payload['temporary_task_assignment_to']

                uid = shared_fxns.generate_unique_identifier()

                department = authenticated_user.department
                if not department:
                    return Response({"details": "Department Required !"}, status=status.HTTP_400_BAD_REQUEST)

                if not qualifications:
                    return Response({"details": "Qualifications Required !"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    raw = {
                        "department": department,
                        "created_by": authenticated_user,
                        "position_title": position_title,
                        "position_type": position_type,
                        "qualifications": qualifications,
                        "job_description": job_description,
                        "nature_of_hiring": nature_of_hiring,
                        "existing_staff_same_title": existing_staff_same_title,
                        "reasons_for_not_sharing_tasks": reasons_for_not_sharing_tasks,
                        "filling_period_from": filling_period_from,
                        "filling_period_to": filling_period_to,
                        "temporary_task_assignment_to": temporary_task_assignment_to,
                        "uid": uid
                    }  

                    recruit = models.Recruit.objects.create(
                        **raw
                    )

                    # create track status change
                    raw = {
                        "recruit": recruit,
                        "status": "REQUESTED",
                        "status_for": "HOD",
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)


                    if department.slt:
                        managers_emails = [department.slt.lead.email]
                    else:
                        return Response({"details": "Your Department has no SLT assigned !"}, status=status.HTTP_400_BAD_REQUEST)
                        
                        

                    # Notify SLT
                    subject = f"New Recruitment Request {uid} Received [SRRS-AKHK]"
                    message = f"Hello, \n\nA new recruit request of id: {uid}, from department: {department.name}\nhas been submitted by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending your action.\n\nRegards\SRRS-AKHK"

                    try:
                        mail = {
                            "email" : managers_emails, 
                            "subject" : subject,
                            "message" : message,
                        }

                        Sendmail.objects.create(**mail)

                    except Exception as e:
                        send_mail(subject, message, 'notification@akhskenya.org', managers_emails)

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Recruitment Request created", f"Recruitment Request Id: {recruit.id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "PUT":
            payload = request.data

            serializer = serializers.PutRecruitSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                position_title = payload['position_title']
                position_type = payload['position_type']
                qualifications = payload['qualifications']
                job_description = payload['job_description']
                nature_of_hiring = payload['nature_of_hiring']
                existing_staff_same_title = payload['existing_staff_same_title']
                reasons_for_not_sharing_tasks = payload['reasons_for_not_sharing_tasks']
                filling_period_from = payload['filling_period_from']
                filling_period_to = payload['filling_period_to']
                temporary_task_assignment_to = payload['temporary_task_assignment_to']

                try:
                    recruit = models.Recruit.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Recruit Request !"}, status=status.HTTP_400_BAD_REQUEST)
                
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


                department = authenticated_user.department
                if not department:
                    return Response({"details": "Department Required !"}, status=status.HTTP_400_BAD_REQUEST)

                if not qualifications:
                    return Response({"details": "Qualifications Required !"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    raw = {
                        "department": department,
                        "created_by": authenticated_user,
                        "position_title": position_title,
                        "position_type": position_type,
                        "qualifications": qualifications,
                        "job_description": job_description,
                        "nature_of_hiring": nature_of_hiring,
                        "existing_staff_same_title": existing_staff_same_title,
                        "reasons_for_not_sharing_tasks": reasons_for_not_sharing_tasks,
                        "filling_period_from": filling_period_from,
                        "filling_period_to": filling_period_to,
                        "temporary_task_assignment_to": temporary_task_assignment_to,
                    }  

                    models.Recruit.objects.filter(Q(id=request_id)).update(**raw)

                    # create track status change
                    raw = {
                        "recruit": recruit,
                        "status": "UPDATED",
                        "status_for": '/'.join(roles),
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)


                    # Notify creator
                    subject = f"Recruitment Request {recruit.uid} Edited [SRRS-AKHK]"
                    message = f"Hello, \n\nYour recruit request of id: {recruit.uid},\nhas been edited by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nVisit SRRS to review.\n\nRegards\SRRS-AKHK"

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
            serializer = serializers.PatchTravelerSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                traveler_id = payload['traveler_id']
                traveler_status = payload['status'].upper()
                # roles = user_util.fetchusergroups(request.user.id)  

                try:
                    traveler = models.Traveler.objects.get(id=traveler_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Travel !"}, status=status.HTTP_400_BAD_REQUEST)
            
                
                with transaction.atomic():

                    if traveler_status == 'REJECTED':
                        traveler.rejected_by = authenticated_user

                    traveler.status = traveler_status
                    traveler.save()

                    # update advance travel request
                    try:
                        salaryRequest = models.AdvanceSalaryRequests.objects.get(
                            traveler=traveler)
                        salaryRequest.status = traveler_status
                        salaryRequest.approved_by = authenticated_user
                        salaryRequest.save()
                    except (ValidationError, ObjectDoesNotExist):
                        pass

                    raw = {
                        "traveler": traveler,
                        "status": traveler_status,
                        "status_for": '/'.join(roles),
                        "action_by": authenticated_user,
                    }

                    models.StatusChange.objects.create(**raw)

                    # Notify requestor
                    emails = [traveler.created_by.email]

                    subject = f"Travel Request: {traveler.tid} Progress Update [TRS-AKHK]"
                    message = f"Hello, \nThe Request:{traveler.tid} has been marked as {traveler_status} by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\n\nRegards\nTRS-AKHK"

                    # try:
                    #     send_mail(subject, message, 'notification@akhskenya.org', emails)
                    # except Exception as e:
                    #     pass
                    try:
                        mail = {
                            "email" : emails, 
                            "subject" : subject,
                            "message" : message,
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        send_mail(subject, message, 'notification@akhskenya.org', emails)
                                                

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, f"Travel Request Status: {traveler_status}", f"Travel Request: {traveler_id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            query = request.query_params.get('q')

            if request_id:
                try:
                    resp = models.Recruit.objects.get(Q(id=request_id))
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
                            resp = models.Recruit.objects.filter(Q(department=request.user.department) | Q(created_by=request.user), is_ceo_approved=False, is_deleted=False).order_by('-date_created')

                        else:
                            resp = models.Recruit.objects.filter(Q(department=request.user.department) | Q(created_by=request.user), is_deleted=False).order_by('-date_created')

                    elif "USER_MANAGER" in roles:
                        resp = models.Recruit.objects.filter(Q(is_deleted=False) ).order_by('-date_created')

                    elif "SLT" in roles:
                        resp = []
                        if "HOF" in roles:

                            if query == 'pending':
                                resp = models.Recruit.objects.filter((Q(department__slt__lead=authenticated_user) & Q(is_slt_approved=False)) |(Q(is_hof_approved=False) & Q(is_hhr_approved=True)), is_deleted=False).order_by('-date_created')

                            else:
                                resp = models.Recruit.objects.filter((Q(department__slt__lead=authenticated_user) & Q(is_slt_approved=False)) |(Q(is_hof_approved=False) & Q(is_hhr_approved=True)), is_deleted=False).order_by('-date_created')

                        else:
                            resp = models.Recruit.objects.filter(Q(is_deleted=False) & Q(department__slt__lead=authenticated_user) & Q(is_slt_approved=False)).order_by('-date_created')

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

    
    @action(methods=["POST", "GET", "PUT", "DELETE"],
            detail=False,
            url_path="approve-request",
            url_name="approve-request")
    def approval(self, request):

        authenticated_user = request.user

        if request.method == "POST":

            payload = request.data
            roles = user_util.fetchusergroups(request.user.id) 

            serializer = serializers.ApprovalSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                recruit_id = payload['recruit_id']
                recruit_status = payload['status']
                budget_code = payload.get('budget_code')

                try:
                    recruit = models.Recruit.objects.get(Q(id=recruit_id))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Recruit !"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():

                    new_status = "APPROVED"
                    forward_to = ""

                    if 'SLT' in roles:
                        if recruit.department.slt.lead == authenticated_user:
                            recruit.is_slt_approved = True
                            new_status = "SLT APPROVED"
                            forward_to = ["HR","HHR"]

                    if 'HHR' in roles:
                        if recruit.is_slt_approved:
                            recruit.is_hhr_approved = True
                            new_status = "HR APPROVED"
                            forward_to = ["HOF","FINANCE"]

                    if 'HOF' in roles:
                        if recruit.is_hhr_approved:
                            recruit.is_hof_approved = True
                            new_status = "FINANCE APPROVED"
                            forward_to = ["CEO"]

                    if 'CEO' in roles:
                        if recruit.is_hof_approved:
                            recruit.is_ceo_approved = True
                            new_status = "CEO APPROVED"
                            forward_to = []

                    
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

                    # Notify the requestor
                    subject = f"Recruitment Request: {recruit.uid} Status  [SRRS-AKHK]"
                    message = f"Dear {recruit.created_by.first_name}, \n\nYour Recruitment Request has been {new_status}\nby {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.\n\nRegards\nSRRS-AKHK"
                    
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
                    message = f"Hello. \n\Recruitment Request: {recruit.uid} from department: {recruit.department.name} has been is {new_status},\nby {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}, and is now pending your action\n\nRegards\SRRS-AKHK"

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
            
            
    @action(methods=["POST", "GET", "PUT", "DELETE"],
            detail=False,
            url_path="forward-request",
            url_name="forward-request")
    def forward(self, request):

        authenticated_user = request.user

        if request.method == "POST":

            payload = request.data
            roles = user_util.fetchusergroups(request.user.id) 

            serializer = serializers.TravelForwardingSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                traveler = payload['traveler']
                send_to = payload['send_to']

                try:
                    traveler = models.Traveler.objects.get(Q(id=traveler))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Travel Request !"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():

                    if send_to == 'HOD':
                        traveler.requires_hod_approval = True
                        emails = list(get_user_model().objects.filter(Q(groups__name='HOD') & Q(department=traveler.department)).values_list('email', flat=True))
                        
                    elif send_to == "SLT":
                        traveler.requires_slt_approval = True
                        if traveler.department.slt:
                            emails = [traveler.department.slt.lead.email]
                        else:
                            return Response({"details": "Department has no SLT assigned !"}, status=status.HTTP_400_BAD_REQUEST)

                    elif send_to == "HOF" :
                        traveler.requires_hof_approval = True
                        emails = list(get_user_model().objects.filter(Q(groups__name='HOF')).values_list('email', flat=True))
                        
                    elif send_to == "CEO":
                        traveler.requires_ceo_approval = True
                        emails = list(get_user_model().objects.filter(Q(groups__name='CEO')).values_list('email', flat=True))

                    elif send_to == "TRANSPORT":
                        traveler.requires_transport_approval = True
                        emails = list(get_user_model().objects.filter(Q(groups__name='TRANSPORT')).values_list('email', flat=True))

                    elif send_to == "CASH_OFFICE":
                        traveler.requires_cash_office_approval = True
                        emails = list(get_user_model().objects.filter(Q(groups__name='CASH_OFFICE')).values_list('email', flat=True))

                    elif send_to == "ADMINISTRATOR":
                        traveler.requires_administrator_approval = True
                        emails = list(get_user_model().objects.filter(Q(groups__name='ADMINISTRATOR')).values_list('email', flat=True))

                    # update travel
                    traveler.save()


                    # create forwarding instance
                    previous_forwarder = models.TravelForwarding.objects.filter(
                        Q(traveler=traveler)).order_by('-date_created').first()
                    if previous_forwarder:
                        previous_forwarder = previous_forwarder.forward_to
                    else:
                        previous_forwarder = "CREATOR"

                    raw = {
                        "traveler": traveler,
                        "forward_to": send_to,
                        "forward_from": previous_forwarder,
                        "forward_by": authenticated_user,
                    }
                    models.TravelForwarding.objects.create(**raw)

                    # Notify recipient
                    subject = f"Travel Request Received [{traveler.tid}]"
                    message = f"Hello. \n\nTravel Request: of ID {traveler.tid}\nhas been forwarded to you by {authenticated_user.first_name} {authenticated_user.last_name},\npending your action.\n\nRegards\nTRS-AKHK"

                    # try:
                    #     send_mail(subject, message, 'notification@akhskenya.org', emails)
                    # except Exception as e:
                    #     pass

                    try:
                        mail = {
                            "email" : emails, 
                            "subject" : subject,
                            "message" : message,
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        send_mail(subject, message, 'notification@akhskenya.org', emails)


                user_util.log_account_activity(
                    authenticated_user, traveler.created_by, f"Travel Request forwarded to {send_to}", f"Approval Executed TID: {str(traveler.id)}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

    @action(methods=["POST",],
            detail=False,
            url_path="update-salary-request",
            url_name="update-salary-request")
    def salary_request(self, request):

        authenticated_user = request.user

        if request.method == "POST":

            payload = request.data
            roles = user_util.fetchusergroups(request.user.id) 

            serializer = serializers.PatchAdvanceSalaryRequestsSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                update_status = payload['status'].upper()
                request_id = payload.get('request_id')

                try:
                    salaryRequest = models.AdvanceSalaryRequests.objects.get(Q(id=request_id))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Salary Request !"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():

                    if "CEO" in roles or "HOF" in roles:
                        salaryRequest.status = update_status
                        salaryRequest.approved_by = authenticated_user
                        salaryRequest.save()
                    else:
                        return Response({"details": "Not Permitted !"}, status=status.HTTP_400_BAD_REQUEST)

                    # Notify the requestor
                    subject = f"Travel Advance Request {update_status.capitalize()}  [TRS-AKHK]"
                    message = f"Hello, \nYour Advance Travel Request for travel:{salaryRequest.traveler.tid} has been {update_status.capitalize()} by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\n\nRegards\nTRS-AKHK"

                    # try:
                    #     send_mail(subject, message, 'notification@akhskenya.org', [salaryRequest.traveler.traveler.email])
                    # except Exception as e:
                    #     pass

                    try:
                        mail = {
                            "email" : [salaryRequest.traveler.traveler.email], 
                            "subject" : subject,
                            "message" : message,
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        send_mail(subject, message, 'notification@akhskenya.org', [salaryRequest.traveler.traveler.email])

                user_util.log_account_activity(
                    authenticated_user, salaryRequest.traveler.created_by, "Travel Request approval", f"Approval Executed instance ID: {str(salaryRequest.id)}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

    @action(methods=["POST",],
            detail=False,
            url_path="update-budget-code",
            url_name="update-budget-code")
    def budget_code(self, request):

        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        allowed = ["HOF","CEO", "FINANCE"]

        if not any(item in allowed for item in roles):
            return Response({"details": "Permission Denied !"}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "POST":

            payload = request.data
            roles = user_util.fetchusergroups(request.user.id) 

            serializer = serializers.PatchBudgetCodeSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                code = payload['budget_code']
                request_id = payload.get('request_id')

                try:
                    traveler = models.Traveler.objects.get(Q(id=request_id))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Travel Request !"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():

                    traveler.budget_code = code
                    traveler.save()

                user_util.log_account_activity(
                    authenticated_user, traveler.created_by, "Budget Code", f"Travel Budget Code Updated. ID : {str(traveler.id)}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            
    @action(methods=["POST", "GET", "PUT", "DELETE"],
            detail=False,
            url_path="process-travel-request",
            url_name="process-travel-request")
    def process_travel_request(self, request):

        authenticated_user = request.user

        if request.method == "POST":

            # payload = request.data
            roles = user_util.fetchusergroups(request.user.id) 

            payload = json.loads(request.data['payload'])
            air_ticket_file = request.FILES.get('ticket', None)

            if "ADMINISTRATOR" not in roles:
                return Response({"details": "Permission Denied !"}, status=status.HTTP_400_BAD_REQUEST)

            serializer = serializers.CostingSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                traveler = payload['traveler']
                bill_settlement_by = payload['bill_settlement_by']
                accommodation = payload.get('accommodation')
                cost = payload.get('cost')

                traveler_status = 'APPROVED'

                try:
                    traveler = models.Traveler.objects.get(Q(id=traveler))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Trip !"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():

                    raw = {
                        "traveler": traveler,
                        "bill_settlement_by": bill_settlement_by,
                        "accommodation": accommodation,
                        "cost": cost,
                        "air_ticket": air_ticket_file,
                        "created_by": authenticated_user
                    }  

                    is_existing = models.Costing.objects.filter(Q(traveler=traveler)).exists()

                    if is_existing:
                        models.Costing.objects.filter(Q(traveler=traveler)).update(**raw)
                    else:
                        models.Costing.objects.create(
                            **raw
                        )

                    if traveler.is_ceo_approved and traveler.is_hof_approved and traveler.is_cash_office_approved:
                        traveler_status = 'CLOSED'
                        traveler.status = traveler_status
                        traveler.closed_by = authenticated_user
                        traveler.date_closed = datetime.datetime.now()

                    traveler.is_administrator_approved = True
                    traveler.save()

                    is_existing = models.Approval.objects.filter(Q(traveler=traveler) & 
                                                                 Q(approval_for='ADMINISTRATOR')).first()

                    raw = {
                        "traveler": traveler,
                        "approval_for": 'ADMINISTRATOR',
                        "approved_by": authenticated_user,
                    }  

                    models.Approval.objects.create(
                            **raw
                        )
                    
                    raw = {
                        "traveler": traveler,
                        "status": traveler_status,
                        "status_for": 'ADMINISTRATOR',
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)

                    # Notify the requestor
                    subject = f"Travel Request {traveler.tid} Closed  [TRS-AKHK]"
                    message = f"Dear {traveler.created_by.first_name}, \nYour Travel Request: {traveler.tid}, \nhas been fully processed by administrator.\nThank you for your patience.\n\nRegards\nTRS-AKHK"

                    # try:
                    #     send_mail(subject, message, 'notification@akhskenya.org', [traveler.created_by.email])
                    # except Exception as e:
                    #     pass

                    try:
                        mail = {
                            "email" : [traveler.created_by.email], 
                            "subject" : subject,
                            "message" : message,
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        send_mail(subject, message, 'notification@akhskenya.org', [traveler.created_by.email])

                user_util.log_account_activity(
                    authenticated_user, traveler.created_by, "Travel Request closed", f"TID: {str(traveler.id)}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

                
    
   
class TRSReportsViewSet(viewsets.ViewSet):
    # search_fields = ['id', ]

    def get_queryset(self):
        return []

    @action(methods=["GET",],
            detail=False,
            url_path="requests",
            url_name="requests")
    def requests(self, request):
                    
        department = request.query_params.get('department')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        quote_status = request.query_params.get('status')
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
            
        if quote_status:
            q_filters &= Q(status=quote_status)


        if q_filters:

            resp = models.Traveler.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
            
        else:
            roles = user_util.fetchusergroups(request.user.id)  

            if "HOD" in roles:
                resp = models.Traveler.objects.filter(Q(is_deleted=False) & Q(created_by=request.user)).order_by('-date_created')[:50]

            else:
                resp = models.Traveler.objects.filter(Q(is_deleted=False)).order_by('-date_created')[:50]

        resp = serializers.FetchTravelerSerializer(resp, many=True, context={"user_id":request.user.id}).data

        return Response(resp, status=status.HTTP_200_OK)
        
    @action(methods=["GET",],
            detail=False,
            url_path="transport",
            url_name="transport")
    def transport(self, request):
                    
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

        q_filters = Q(approval_for='TRANSPORT')

        if department:
            q_filters &= Q(department=department)

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)
            
        # if quote_status:
        #     q_filters &= Q(status=quote_status)


        if q_filters:

            resp = models.Approval.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
            
        else:
            roles = user_util.fetchusergroups(request.user.id)  

            resp = models.Approval.objects.filter(Q(is_deleted=False)).order_by('-date_created')[:50]

        resp = serializers.FullFetchApprovalSerializer(resp, many=True, context={"user_id":request.user.id}).data

        return Response(resp, status=status.HTTP_200_OK)
        

    @action(methods=["GET",],
            detail=False,
            url_path="flights",
            url_name="flights")
    def flight(self, request):
                    
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

        q_filters = Q(approval_for='ADMINISTRATOR')

        if department:
            q_filters &= Q(department=department)

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)
            
        if type:
            q_filters &= Q(traveler__type_of_travel=type)


        if q_filters:

            resp = models.Approval.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
            
        else:
            roles = user_util.fetchusergroups(request.user.id)  

            resp = models.Approval.objects.filter(Q(is_deleted=False)).order_by('-date_created')[:50]

        resp = serializers.FullFetchApprovalSerializer(resp, many=True, context={"user_id":request.user.id}).data

        return Response(resp, status=status.HTTP_200_OK)
    

    @action(methods=["GET",],
            detail=False,
            url_path="journeys",
            url_name="journeys")
    def journeys(self, request):
                    
        employee_no = request.query_params.get('employee_no')
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

        q_filters = Q()

        if employee_no:
            q_filters &= (Q(employee_no=employee_no) | Q(employees__contains=[{"employee_no": employee_no}]))

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)
            
        if type:
            q_filters &= Q(type_of_travel=type)


        if q_filters:

            resp = models.Traveler.objects.filter(Q(is_deleted=False) & q_filters).order_by('date_created')
            
        else:
            roles = user_util.fetchusergroups(request.user.id)  

            resp = []

        resp = serializers.FetchTravelerSerializer(resp, many=True, context={"user_id":request.user.id}).data

        return Response(resp, status=status.HTTP_200_OK)
    


        
class TRSAnalyticsViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return []

    @action(methods=["GET",],
            detail=False,
            url_path="general",
            url_name="general")
    def general(self, request):
        roles = user_util.fetchusergroups(request.user.id)

        if 'USER' in roles:
            requests = models.Traveler.objects.filter(Q(is_deleted=False) & Q(traveler=request.user)).count()
            # requested = models.Traveler.objects.filter(Q(status="REQUESTED") & Q(is_deleted=False) & Q(traveler=request.user)).count()
            requested = models.Traveler.objects.filter(Q(status="REQUESTED") | Q(status="RESUBMITTED") & Q(traveler=request.user), is_deleted=False).count()

            closed = models.Traveler.objects.filter(Q(status="CLOSED") & Q(is_deleted=False) & Q(traveler=request.user)).count()
            # assigned = models.Traveler.objects.filter(Q(status="ASSIGNED") & Q(is_deleted=False) & Q(traveler=request.user)).count()
            incomplete = models.Traveler.objects.filter(Q(status="INCOMPLETE") & Q(is_deleted=False) & Q(traveler=request.user)).count()
        else:
            requests = models.Traveler.objects.filter(Q(is_deleted=False)).count()
            requested = models.Traveler.objects.filter(Q(status="REQUESTED") | Q(status="RESUBMITTED"), is_deleted=False).count()
            closed = models.Traveler.objects.filter(Q(status="CLOSED") & Q(is_deleted=False)).count()
            assigned = models.Traveler.objects.filter(Q(status="ASSIGNED") & Q(is_deleted=False)).count()
            incomplete = models.Traveler.objects.filter(Q(status="INCOMPLETE") & Q(is_deleted=False)).count()

        if 'CEO' in roles or 'HOF' in roles:
            requested = models.Traveler.objects.filter(Q(status="APPROVED"), is_ceo_approved=False, is_deleted=False).count()

        resp = {
            "requests": requests,
            "requested": requested,
            "closed": closed,
            # "assigned": assigned,
            "incomplete": incomplete,
        }

        return Response(resp, status=status.HTTP_200_OK)