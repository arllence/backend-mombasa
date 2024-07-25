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
                return Response({"details": employee_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
      
            # serialize doctor payload
            if employee['is_doctor'] == 'YES':
                employee['is_doctor'] = True
                is_doctor = True
                doctor_info_serializer = serializers.DoctorsSerializer(
                        data=doctor_info, many=False)
                if not doctor_info_serializer.is_valid():
                    return Response({"details": doctor_info_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            else:
                employee['is_doctor'] = False
                is_doctor = False
            
           
            department = employee['department']
            try:
                department = SRRSDepartment.objects.get(id=department)
                employee['department'] = department
            except Exception as e:
                return Response({"details": "Unknown department"}, status=status.HTTP_400_BAD_REQUEST)
            
            systems = system_access['systems']
            try:
                systems = models.System.objects.filter(id__in=systems)
                # system_access['systems'] = systems
            except Exception as e:
                return Response({"details": "Unknown selected system "}, status=status.HTTP_400_BAD_REQUEST)

    
            with transaction.atomic():
                record_id = None if payload.get('record_id') == '' else payload.get('record_id')
                employee_no = None if payload.get('employee_no') == '' else payload.get('employee_no')
                # employee_no = employee['employee_no']
                # check if employee exists
                employeeInstance = models.Employee.objects.filter(
                    Q(employee_no=employee_no) | Q(id=record_id)
                ).first()
                if employeeInstance:
                    models.Employee.objects.filter(
                        Q(employee_no=employee_no) | Q(id=record_id)
                    ).update(**employee)
                    employee_exists = True
                else:
                    employeeInstance = models.Employee.objects.create(
                        **employee
                    )
                    employee_exists = False

                # keep history before editing
                if employee_exists:
                    try:
                        history = serializers.FetchRequestSerializer(employeeInstance, many=False, context={"user_id":request.user.id}).data
                        history = shared_fxns.convert_to_json_serializable(history)
                        raw = {
                            "employee" : employeeInstance,
                            "data" : history,
                            "triggered_by": authenticated_user
                        }
                        models.RequestHistory.objects.create(**raw)
                    except Exception as e:
                        print(e) 
                        return

                # create system access
                models.SystemAccess.objects.filter(
                        Q(employee=employeeInstance)
                    ).delete()
                for system in systems:
                    models.SystemAccess.objects.create(
                        employee=employeeInstance, system=system
                    )

                # module access
                modules = module_access.get('modules')
                if modules:
                    module_access.update({
                        "employee" : employeeInstance
                    })
                    # check if is existing
                    is_existing = models.ModuleAccess.objects.filter(
                        employee=employeeInstance
                    ).first()
                    if is_existing:
                        # current_modules = is_existing.modules
                        # current_modules += modules
                        is_existing.modules = modules
                        is_existing.save()
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
                        ).update(**doctor_info)
                    else:
                        doctor_info = models.DoctorInfo.objects.create(
                            **doctor_info
                        )

                # create access instance
                if not employee_exists:
                    access = {
                        "employee": employeeInstance,
                        "created_by": authenticated_user
                    }
                    try:
                        accessInstance = models.Access.objects.create(
                            **access
                        )
                    except Exception as e:
                        print(e)
                    track_status = "REQUESTED"
                else:
                    accessInstance = models.Access.objects.get(employee=employeeInstance)
                    track_status = "UPDATED"

                # create track status change
                try:
                    raw = {
                        "access": accessInstance,
                        "status": track_status,
                        "status_for": '/'.join(roles),
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)
                except Exception as e:
                    print(e)


                # Notify HOD
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
                    print("mail error: ", e)

            user_util.log_account_activity(
                authenticated_user, authenticated_user, "Access Request created", f"Employee Id: {employeeInstance.id}")
            
            return Response('success', status=status.HTTP_200_OK)
            

        elif request.method == "PUT":
            # endpoint approves / alters requests status
            payload = request.data

            # serialize payload
            serializer = serializers.UpdateRequestSerializer(
                    data=payload, many=False)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            # extrapolate
            request_id = payload['request_id']
            request_status = payload['status']
            
            try:
                accessInstance = models.Access.objects.get(Q(id=request_id) | Q(employee=request_id))
            except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                print(e)
                return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            
            if 'HOD' in roles:
                if request_status == 'APPROVED':
                    accessInstance.is_hod_approved = True
                    request_status = 'HOD APPROVED'
                    accessInstance.status = request_status
                else:
                    accessInstance.status = request_status

                status_for = 'HOD'

            elif 'ICT' in roles:
                if request_status == 'APPROVED':
                    accessInstance.is_ict_approved = True
                    request_status = 'ICT APPROVED'
                    accessInstance.status = request_status
                    accessInstance.granted_by = authenticated_user
                    accessInstance.employee.status = 'ACTIVE'
                else:
                    accessInstance.status = request_status

                status_for = 'ICT'

            else:
                return Response({"details": "Permission denied"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            # update instance
            accessInstance.save()
            accessInstance.employee.save()
            
            # Notify ICT
            if status_for == 'HOD' and request_status == 'HOD APPROVED':
                subject = f"New Access Request Received [ASA-AKHK]"
                message = f"Hello, \n\nA new access request from department: {accessInstance.employee.department.name},\nhas been approved by {authenticated_user.first_name} {authenticated_user.last_name} for HOD on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending your action.\n\nRegards\nASA-AKHK"
                # get emails
                emails = list(models.RequestApprover.objects.all().values_list('approver__email', flat=True))
                
                try:
                    mail = {
                        "email" : emails, 
                        "subject" : subject,
                        "message" : message
                    }
                    Sendmail.objects.create(**mail)
                except Exception as e:
                    logger.error(e)
                    print("mail error: ", e)

            # Notify requestor
            emails = [accessInstance.employee.email]

            subject = f"Access Request Progress Update"
            message = f"Hello, \nYour Access request has been marked as {request_status}\nby {authenticated_user.first_name} {authenticated_user.last_name} for {status_for} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\n\nRegards\nASA-AKHK"

            try:
                mail = {
                    "email" : emails, 
                    "subject" : subject,
                    "message" : message,
                }
                Sendmail.objects.create(**mail)
            except Exception as e:
                logger.error(e)


            # create track status change
            try:
                raw = {
                    "access": accessInstance,
                    "status": request_status,
                    "status_for": status_for,
                    "action_by": authenticated_user
                }
                models.StatusChange.objects.create(**raw)
            except Exception as e:
                print(e)

            return Response('success', status=status.HTTP_200_OK)
     
  
        elif request.method == "PATCH":
            payload = request.data
            serializer = serializers.PatchRecruitSerializer(
                data=payload, many=False)
            
            return
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            employee_no = request.query_params.get('employee_no')
            query = request.query_params.get('q')
            slim = request.query_params.get('slim')

            if request_id:
                try:
                    resp = models.Employee.objects.get(Q(id=request_id))

                    if slim:
                        resp = serializers.SlimFetchEmployeeSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.FetchRequestSerializer(resp, many=False, context={"user_id":request.user.id}).data

                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request!"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
                
            elif employee_no:
                try:
                    resp = models.Employee.objects.get(Q(employee_no=employee_no))

                    if slim:
                        resp = serializers.SlimFetchEmployeeSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.FetchRequestSerializer(resp, many=False, context={"user_id":request.user.id}).data

                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request!"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
                
            else:
                try:

                    if any(role in ['HOD','SLT'] for role in roles):

                        if query == 'pending':
                            resp = models.Access.objects.filter(Q(employee__department=request.user.srrs_department) | Q(created_by=request.user), is_hod_approved=False, is_deleted=False).order_by('-date_created')

                        else:
                            resp = models.Access.objects.filter(Q(employee__department=request.user.srrs_department) | Q(created_by=request.user), is_deleted=False).order_by('-date_created')

                        resp = [x.employee for x in resp]

                    elif any(role in ['SUPERUSER','ICT'] for role in roles):
                        resp = models.Access.objects.filter(Q(is_deleted=False) ).order_by('-date_created')
                        resp = [x.employee for x in resp]

                    else:
                        if query == 'pending':
                            resp = models.Access.objects.filter(Q(created_by=request.user), is_hod_approved=False, is_deleted=False).order_by('-date_created')

                        else:
                            resp = models.Access.objects.filter(Q(created_by=request.user), is_deleted=False).order_by('-date_created')

                        resp = [x.employee for x in resp]


                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resp, request)
                    serializer = serializers.FetchRequestSerializer(
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
                    models.Access.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)    
                except Exception as e:
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)    

    @action(methods=["POST", "GET", "PUT"],
            detail=False,
            url_path="systems",
            url_name="systems")
    def systems(self, request):
        # roles = user_util.fetchusergroups(request.user.id)
        if request.method == "POST":
            payload = request.data
            serializer = serializers.GeneralNameSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                name = payload['name']

                with transaction.atomic():
                    raw = {
                        "name": name
                    }

                    models.System.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":
            payload = request.data

            serializer = serializers.UpdateGeneralNameSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                name = payload['name']

                try:
                    system = models.System.objects.get(id=request_id)
                except Exception as e:
                    logger.error(e)
                    return Response({"details": "Unknown System"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():

                    system.name = name
                    system.save()

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    system = models.System.objects.get(Q(id=request_id))
                    system = serializers.SlimFetchSystemsSerializer(system, many=False).data
                    return Response(system, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown system"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:

                    systems = models.System.objects.filter(Q(is_deleted=False)).order_by('name')
                    systems = serializers.SlimFetchSystemsSerializer(systems, many=True).data
                    return Response(systems, status=status.HTTP_200_OK)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)


    @action(methods=["POST", "GET", "PUT", "DELETE"],
            detail=False,
            url_path="request-approver",
            url_name="request-approver")
    def request_approver(self, request):
        # roles = user_util.fetchusergroups(request.user.id)
        if request.method == "POST":
            payload = request.data
            serializer = serializers.ApproverSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                approver = payload['approver']

                try:
                    approver = User.objects.get(id=approver)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown User"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Invalid Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                # assign ICT role
                assign_role = user_util.award_role('ICT', str(approver.id))
                if not assign_role:
                    return Response({"details": "Unable to assign role ICT"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    raw = {
                        "approver": approver,
                        "created_by": request.user
                    }

                    models.RequestApprover.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":
            payload = request.data

            serializer = serializers.UpdateApproverSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                approver = payload['approver']

                try:
                    request = models.RequestApprover.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Invalid Request"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():

                    request.approver = approver
                    request.created_by = request.user
                    request.save()

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    request = models.RequestApprover.objects.get(Q(id=request_id))
                    request = serializers.FetchRequestApproverSerializer(request, many=False).data
                    return Response(request, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:

                    request = models.RequestApprover.objects.filter(Q(is_deleted=False)).order_by('approver')
                    request = serializers.FetchRequestApproverSerializer(request, many=True).data
                    return Response(request, status=status.HTTP_200_OK)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                
        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    user = models.RequestApprover.objects.get(id=request_id)
                    user_util.revoke_role('ICT', str(user.approver.id))
                    user.delete()
                    return Response('200', status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request "}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"details": "Request incomplete"}, status=status.HTTP_400_BAD_REQUEST)


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
            

   
class ReportsViewSet(viewsets.ViewSet):
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
        access = request.query_params.get('access')
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
            q_filters &= Q(employee__department=department)

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)
            
        if r_status:
            q_filters &= Q(status=r_status)

        if position_type:
            q_filters &= Q(employee__employee_type=position_type)

        if access:
            q_filters &= Q(employee__status=access)


        if q_filters:

            resp = models.Access.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
            resp = [x.employee for x in resp]
            
        else:
            roles = user_util.fetchusergroups(request.user.id)  

            if "HOD" in roles:
                resp = models.Access.objects.filter(Q(is_deleted=False) & Q(created_by=request.user)).order_by('-date_created')[:50]

            else:
                resp = models.Access.objects.filter(Q(is_deleted=False)).order_by('-date_created')[:50]

            resp = [x.employee for x in resp]

        resp = serializers.FetchRequestSerializer(resp, many=True, context={"user_id":request.user.id}).data

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
        
        
class ASAAnalyticsViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return []

    @action(methods=["GET",],
            detail=False,
            url_path="general",
            url_name="general")
    def general(self, request):
        roles = user_util.fetchusergroups(request.user.id)
        active_status = ['REQUESTED','HOD APPROVED','CLOSED']

        if 'HOD' in roles:
            requests = models.Access.objects.filter(Q(employee__department=request.user.srrs_department) | Q(created_by=request.user), is_deleted=False).count()
            approved = models.Access.objects.filter(Q(employee__department=request.user.srrs_department) |  Q(created_by=request.user), status="ICT APPROVED", is_deleted=False).count()
            rejected = models.Access.objects.filter(Q(employee__department=request.user.srrs_department) |  Q(created_by=request.user), status="REJECTED", is_deleted=False).count()
            pending = models.Access.objects.filter(Q(employee__department=request.user.srrs_department) |  Q(created_by=request.user), status__in=active_status, is_deleted=False).count()
        elif 'ICT' in roles or 'SUPERUSER' in roles:
            requests = models.Access.objects.filter(is_deleted=False).count()
            approved = models.Access.objects.filter(status="ICT APPROVED", is_deleted=False).count()
            rejected = models.Access.objects.filter(status="REJECTED", is_deleted=False).count()
            pending = models.Access.objects.filter(status__in=active_status, is_deleted=False).count()
        else:
            requests = models.Access.objects.filter(Q(created_by=request.user) & Q(is_deleted=False)).count()
            approved = models.Access.objects.filter(Q(created_by=request.user) & Q(status="ICT APPROVED"), is_deleted=False).count()
            rejected = models.Access.objects.filter(Q(created_by=request.user) & Q(status="REJECTED"), is_deleted=False).count()
            pending = models.Access.objects.filter(Q(created_by=request.user) & Q(status__in=active_status), is_deleted=False).count()

        resp = {
            "requests": requests,
            "rejected": rejected,
            "approved": approved,
            "pending": pending,
        }

        return Response(resp, status=status.HTTP_200_OK)