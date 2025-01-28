import calendar
from collections import OrderedDict
import datetime
import json
import logging
import uuid
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, JSONParser
from django.contrib.auth.hashers import make_password
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
from django.conf import settings
from django.contrib.auth.models import Group

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
        

        if request.method == "POST":
            acl_roles = user_util.fetchusergroups(request.user.id) 

            payload = request.data

            employee = payload['employee']
            doctor_info = payload['doctor_info']
            system_access = payload['system_access']

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
                        
            
            # if str(department.id) != str(authenticated_user.srrs_department.id):
            #     return Response({"details": "Request Must be within your department"}, status=status.HTTP_400_BAD_REQUEST)
            
            user_exists = get_user_model().objects.filter(email=employee['email']).exists()
            # if user_exists:
            #     return Response({'details': 'User With Credentials Already Exist'}, status=status.HTTP_400_BAD_REQUEST)

    
            with transaction.atomic():
                record_id = None if payload.get('record_id') == '' else payload.get('record_id')
                employee_no = None if payload.get('employee_no') == '' else payload.get('employee_no')

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
                # models.SystemAccess.objects.filter(
                #         Q(employee=employeeInstance)
                #     ).delete()
                

                # get system forms attribute
                systems = system_access['systems']
                remarks = system_access['remarks']                

                
                for item in systems:
                    system = item['system']
                    modules = item['modules']
                    roles = item['roles']
                    
                    try:
                        systemInstance = models.System.objects.get(id=system)
                    except Exception as e:
                        return Response({"details": "Unknown selected system "}, status=status.HTTP_400_BAD_REQUEST)
                    
                    is_existing = models.SystemAccess.objects.filter(
                            employee=employeeInstance, system=systemInstance
                        ).exists()

                    if not is_existing:
                        models.SystemAccess.objects.create(
                            employee=employeeInstance, system=systemInstance
                        )

                    # store roles
                    if roles:
                        r_raw = {
                            "employee" : employeeInstance,
                            "roles" : roles
                        }
                        # check if is existing
                        is_existing = models.RoleAccess.objects.filter(
                            employee=employeeInstance
                        ).first()
                        if is_existing:
                            current_roles = is_existing.roles
                            roles += current_roles
                            is_existing.roles = roles
                            is_existing.save()
                        else:
                            models.RoleAccess.objects.create(
                                **r_raw
                            )

                    # module access
                    if modules:
                        m_raw = {
                            "employee" : employeeInstance,
                            "modules" : modules,
                            "remarks" : remarks
                        }
                        # check if is existing
                        is_existing = models.ModuleAccess.objects.filter(
                            employee=employeeInstance
                        ).first()
                        if is_existing:
                            current_modules = is_existing.modules
                            modules += current_modules
                            is_existing.modules = modules
                            is_existing.remarks = remarks
                            is_existing.save()
                        else:
                            models.ModuleAccess.objects.create(
                                **m_raw
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

                
                # create user
                if not user_exists:
                    name = employeeInstance.name.split()
                    password = 'welcome@123'
                    hashed_pwd = make_password(password)
                    newuser = {
                        "email": employeeInstance.email,
                        "first_name": name[0],
                        "last_name": name[-1],
                        "srrs_department": department,
                        "is_active": True,
                        "password": hashed_pwd,
                        "is_defaultpassword": True
                    }
                    created_user = get_user_model().objects.create(**newuser)

                    try:
                        group_details = Group.objects.get(name='USER')
                    except (ValidationError, ObjectDoesNotExist):
                        return Response({'details': 'Role User does not exist'}, status=status.HTTP_400_BAD_REQUEST)
                    
                    group_details.user_set.add(created_user)
                    user_util.log_account_activity(
                        created_user, created_user, "Account Creation",
                        "USER CREATED")
                         

                # create access instance
                if not employee_exists:
                    access = {
                        "employee": employeeInstance,
                        "created_by": authenticated_user,
                        "created_for": created_user,
                        "is_hod_approved" : True
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
                    track_status = "EDITED"
                
                # create track status change
                try:
                    raw = {
                        "access": accessInstance,
                        "status": track_status,
                        "status_for": '/'.join(acl_roles),
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)
                except Exception as e:
                    print(e)


                # Notify New User
                if not user_exists:
                    subject = f"Access Service Agreement [ASA-AKHK]"
                    message = f"Hello, \n\nA new access request has been created for you by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending your action. Kindly login to accept the agreement.\nYour password is: {password}\nPlatform link is: {settings.PLATFORM_LINK}\n\nRegards\nASA-AKHK"
                    
                    try:
                        mail = {
                            "email" : [created_user.email], 
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
            roles = user_util.fetchusergroups(request.user.id) 
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
                    request_status = 'ICT AUTHORIZED'
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
            acl_roles = user_util.fetchusergroups(request.user.id) 
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

                    if any(role in ['HOD','SLT'] for role in acl_roles):

                        if query == 'pending':
                            resp = models.Access.objects.filter(Q(employee__department=request.user.srrs_department) | Q(created_by=request.user), agreement_accepted=False, is_deleted=False).order_by('-date_created')

                        else:
                            resp = models.Access.objects.filter(Q(employee__department=request.user.srrs_department) | Q(created_by=request.user), is_deleted=False).order_by('-date_created')

                        resp = [x.employee for x in resp]

                    elif any(role in ['ICT'] for role in acl_roles):
                        resp = models.Access.objects.filter(Q(is_deleted=False) & (Q(agreement_accepted=True)) ).order_by('-date_created')
                        resp = [x.employee for x in resp]
                    elif any(role in ['SUPERUSER'] for role in acl_roles):
                        resp = models.Access.objects.filter(Q(is_deleted=False) ).order_by('-date_created')
                        resp = [x.employee for x in resp]
                    else:
                        if query == 'pending':
                            resp = models.Access.objects.filter(Q(created_by=request.user) | Q(created_for=request.user), agreement_accepted=False, is_deleted=False).order_by('-date_created')

                        else:
                            resp = models.Access.objects.filter(Q(created_by=request.user) | Q(created_for=request.user), is_deleted=False).order_by('-date_created')

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
                
    
    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="additional-access-rights",
            url_name="additional-access-rights")
    def additional_access_rights(self, request):
        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            try:
                record_id = payload['record_id']
                employeeInstance = models.Employee.objects.get(id=record_id)
            except:
                return Response({"details": "Unknown staff"}, status=status.HTTP_400_BAD_REQUEST)
            
            system_access = payload['system_access']
            module_access = payload['module_access']

            systems = system_access['systems']
            try:
                systems = models.System.objects.filter(id__in=systems)
            except Exception as e:
                return Response({"details": "Unknown selected system "}, status=status.HTTP_400_BAD_REQUEST)
 

            with transaction.atomic():
                # create system access
                for system in systems:
                    is_exists = models.SystemAccess.objects.filter(
                        employee=employeeInstance, system=system).exists()
                    if not is_exists:
                        models.AdditionalSystemAccess.objects.create(
                            employee=employeeInstance, system=system
                        )

                # module access
                modules = module_access.get('modules')
                if modules:
                    module_access.update({
                        "employee" : employeeInstance
                    })

                    module_access = models.AdditionalModuleAccess.objects.create(
                        **module_access
                    )



                # Notify ICT
                subject = f"New Additional Access Request Received [ASA-AKHK]"
                message = f"Hello, \n\nA new access request from department: {employeeInstance.department.name},\nhas been submitted by {request.user.first_name} {request.user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending your action.\n\nRegards\nASA-AKHK"
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

            user_util.log_account_activity(
                authenticated_user, authenticated_user, "Additional Access Request created", f"Employee Id: {employeeInstance.id}")
            
            return Response('success', status=status.HTTP_200_OK)
            

        elif request.method == "PUT":
            # endpoint approves / alters requests status
            payload = request.data

            # serialize payload
            serializer = serializers.UpdateAdditionalRequestSerializer(
                    data=payload, many=False)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            # extrapolate
            request_id = payload['request_id']
            request_status = payload['status']
            option = payload['option']
            
            if option == 'SYSTEM':
                try:
                    accessInstance = models.AdditionalSystemAccess.objects.get(Q(id=request_id))
                except (ValidationError, ObjectDoesNotExist):
                        return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
                
                raw = {
                    "employee": accessInstance.employee,
                    "system": accessInstance.system
                }
                if request_status == 'APPROVED':
                    models.SystemAccess.objects.create(**raw)
                accessInstance.status = request_status
                accessInstance.save()
            
            elif option == 'MODULE':
                try:
                    accessInstance = models.AdditionalModuleAccess.objects.get(Q(id=request_id))
                except (ValidationError, ObjectDoesNotExist):
                        return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
                
                raw = {
                    "employee": accessInstance.employee,
                    "modules": accessInstance.modules,
                    "remarks": accessInstance.remarks
                }
                if request_status == 'APPROVED':
                    existing_modules = []
                    current_modules = accessInstance.modules
                    existing_module_access = models.ModuleAccess.objects.filter(employee=accessInstance.employee).first()

                    if existing_module_access:
                        # Collect existing modules and rights
                        existing_modules = existing_module_access.modules

                        for current_module in current_modules:
                            current_module_id = current_module['module']
                            current_rights = set(current_module['rights'])

                            # Check if the current module exists in the employee's modules
                            module_exists = False
                            for existing_module in existing_modules:
                                if existing_module['module'] == current_module_id:
                                    # Merge rights if the module already exists
                                    existing_module['rights'] = list(set(existing_module['rights']) | current_rights)
                                    module_exists = True
                                    break

                            # Add new module if it doesn't exist
                            if not module_exists:
                                existing_modules.append(current_module)

                        # Update the modules and save the instance
                        existing_module_access.modules = existing_modules
                        existing_module_access.save()
                    else:
                        # Create new ModuleAccess entry if none exists
                        models.ModuleAccess.objects.create(employee=accessInstance.employee, modules=current_modules)

                accessInstance.status = request_status
                accessInstance.save()
            

            # Notify ICT
            # if status_for == 'HOD' and request_status == 'HOD APPROVED':
            #     subject = f"New Access Request Received [ASA-AKHK]"
            #     message = f"Hello, \n\nA new access request from department: {accessInstance.employee.department.name},\nhas been approved by {authenticated_user.first_name} {authenticated_user.last_name} for HOD on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending your action.\n\nRegards\nASA-AKHK"
            #     # get emails
            #     emails = list(models.RequestApprover.objects.all().values_list('approver__email', flat=True))
                
            #     try:
            #         mail = {
            #             "email" : emails, 
            #             "subject" : subject,
            #             "message" : message
            #         }
            #         Sendmail.objects.create(**mail)
            #     except Exception as e:
            #         logger.error(e)
            #         print("mail error: ", e)

            


            # create track status change
            # try:
            #     raw = {
            #         "access": accessInstance,
            #         "status": request_status,
            #         "status_for": status_for,
            #         "action_by": authenticated_user
            #     }
            #     models.StatusChange.objects.create(**raw)
            # except Exception as e:
            #     print(e)

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
                            resp = models.Access.objects.filter(Q(employee__department=request.user.srrs_department) | Q(created_by=request.user), agreement_accepted=False, is_deleted=False).order_by('-date_created')

                        else:
                            resp = models.Access.objects.filter(Q(employee__department=request.user.srrs_department) | Q(created_by=request.user), is_deleted=False).order_by('-date_created')

                        resp = [x.employee for x in resp]

                    elif any(role in ['ICT'] for role in roles):
                        resp = models.Access.objects.filter(Q(is_deleted=False) & (Q(agreement_accepted=True)) ).order_by('-date_created')
                        resp = [x.employee for x in resp]
                    elif any(role in ['SUPERUSER'] for role in roles):
                        resp = models.Access.objects.filter(Q(is_deleted=False) ).order_by('-date_created')
                        resp = [x.employee for x in resp]
                    else:
                        if query == 'pending':
                            resp = models.Access.objects.filter(Q(created_by=request.user) | Q(created_for=request.user), agreement_accepted=False, is_deleted=False).order_by('-date_created')

                        else:
                            resp = models.Access.objects.filter(Q(created_by=request.user) | Q(created_for=request.user), is_deleted=False).order_by('-date_created')

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
            url_path="agreement",
            url_name="agreement")
    def agreement(self, request):
        # roles = user_util.fetchusergroups(request.user.id)
        if request.method == "POST":
            payload = request.data
            serializer = serializers.IdNumberSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                id_number = payload['id_number']
                request_id = payload['request_id']

                try:
                    accessInstance = models.Access.objects.get(employee=request_id)
                except Exception as e:
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    details = {
                        "id_number": id_number,
                        "date_signed": str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))
                    }

                    accessInstance.agreement_accepted = True
                    accessInstance.agreement_details = details
                    accessInstance.status = 'STAFF SIGNED'
                    accessInstance.save()

                    # Notify ICT
                    subject = f"New Access Request Received [ASA-AKHK]"
                    message = f"Hello, \n\nA new access request from department: {accessInstance.employee.department.name},\nhas been reviewed and accepted by {request.user.first_name} {request.user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending your action.\n\nRegards\nASA-AKHK"
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

                    # create track status change
                    try:
                        raw = {
                            "access": accessInstance,
                            "status": 'STAFF SIGNED',
                            "status_for": 'USER',
                            "action_by": request.user
                        }
                        models.StatusChange.objects.create(**raw)
                    except Exception as e:
                        print(e)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

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


    @action(methods=["POST", "GET", "PUT"],
            detail=False,
            url_path="modules",
            url_name="modules")
    def modules(self, request):
        # roles = user_util.fetchusergroups(request.user.id)
        if request.method == "POST":
            payload = request.data
            serializer = serializers.ModuleSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                system_id = payload['system']
                modules = payload['modules']

                try:
                    system = models.System.objects.get(id=system_id)
                except Exception as e:
                    logger.error(e)
                    return Response({"details": "Unknown System"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    for module in modules:
                        module_name = module['name']
                        rights = module['rights']

                        raw = {
                            "name": module_name,
                            "system": system
                        }

                        moduleInstance = models.Module.objects.create(**raw)

                        bulkRights = [
                            models.Right(
                                module = moduleInstance, 
                                name = right
                            )
                            for right in rights
                        ]
                        models.Right.objects.bulk_create(bulkRights)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":
            payload = request.data

            serializer = serializers.PutModuleSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                modules = payload['modules'][0]
                # rights = module['rights']

                module_name = modules.get('name')
                rights = modules.get('rights')

                try:
                    module = models.Module.objects.get(id=request_id)
                except Exception as e:
                    logger.error(e)
                    return Response({"details": "Unknown module"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():

                    module.name = module_name
                    module.save()

                    bulkRights = [
                        models.Right(
                            module = module, 
                            name = right
                        )
                        for right in rights
                    ]
                    models.Right.objects.bulk_create(bulkRights)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            system_id = request.query_params.get('system_id')
            system_ids = request.query_params.get('system_ids')
            if request_id:
                try:
                    resp = models.Module.objects.get(Q(id=request_id))
                    resp = serializers.FetchModuleSerializer(resp, many=False).data
                    return Response(resp, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            elif system_id:
                try:
                    resp = models.Module.objects.filter(Q(system=system_id))
                    resp = serializers.FetchModuleSerializer(resp, many=True).data
                    return Response(resp, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            elif system_ids:
                system_ids = json.loads(system_ids)
                try:
                    resp = models.Module.objects.filter(Q(system__in=system_ids))
                    resp = serializers.FetchModuleSerializer(resp, many=True).data
                    return Response(resp, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:

                    resp = models.Module.objects.filter(Q(is_deleted=False)).order_by('name')
                    resp = serializers.FetchModuleSerializer(resp, many=True).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                
    @action(methods=["DELETE", "PUT"],
            detail=False,
            url_path="rights",
            url_name="rights")
    def rights(self, request):
 
        if request.method == "PUT":
            payload = request.data

            serializer = serializers.PutRightSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                name = payload['name']

                try:
                    right = models.Right.objects.get(id=request_id)
                except Exception as e:
                    logger.error(e)
                    return Response({"details": "Unknown right"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():

                    right.name = name
                    right.save()

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.Right.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)    
                except Exception as e:
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)
                

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
            
    @action(methods=["POST", "GET", "PUT", "DELETE"],
            detail=False,
            url_path="roles",
            url_name="roles")
    def roles(self, request):
        # roles = user_util.fetchusergroups(request.user.id)
        if request.method == "POST":
            payload = request.data
            serializer = serializers.RoleSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                system_id = payload['system']
                roles = payload['roles']

                try:
                    system = models.System.objects.get(id=system_id)
                except Exception as e:
                    logger.error(e)
                    return Response({"details": "Unknown System"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    
                    bulkRights = [
                        models.Roles(
                            system = system, 
                            name = role
                        )
                        for role in roles
                    ]
                    models.Roles.objects.bulk_create(bulkRights)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":
            payload = request.data

            serializer = serializers.PutRoleSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                role_name = payload['name']

                try:
                    role = models.Roles.objects.get(id=request_id)
                except Exception as e:
                    logger.error(e)
                    return Response({"details": "Unknown role"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():

                    role.name = role_name
                    role.save()

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            system_id = request.query_params.get('system_id')
            system_ids = request.query_params.get('system_ids')
            if request_id:
                try:
                    resp = models.Roles.objects.get(Q(id=request_id))
                    resp = serializers.FetchRoleSerializer(resp, many=False).data
                    return Response(resp, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            elif system_id:
                try:
                    resp = models.Roles.objects.filter(Q(system=system_id))
                    resp = serializers.FetchRoleSerializer(resp, many=True).data
                    return Response(resp, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            elif system_ids:
                system_ids = json.loads(system_ids)
                try:
                    resp = models.Roles.objects.filter(Q(system__in=system_ids))
                    resp = serializers.FetchRoleSerializer(resp, many=True).data
                    return Response(resp, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:

                    resp = models.Roles.objects.filter(Q(is_deleted=False)).order_by('name')
                    resp = serializers.FetchRoleSerializer(resp, many=True).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    user = models.Roles.objects.get(id=request_id)
                    user.is_deleted = True
                    user.save()
                    return Response('200', status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request "}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"details": "Request incomplete"}, status=status.HTTP_400_BAD_REQUEST)
            
    @action(methods=["POST"],
            detail=False,
            url_path="update-email",
            url_name="update-email")
    def update_email(self, request):
        roles = user_util.fetchusergroups(request.user.id)
        if 'ICT' not in roles:
            return Response({"details": "Permission Denied"}, status=status.HTTP_400_BAD_REQUEST)
        
        if request.method == "POST":
            payload = request.data
            serializer = serializers.UpdateEmailSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                user_id = payload['user_id']
                email = payload['email']

                try:
                    user = get_user_model().objects.get(id=user_id)
                    old_email = user.email
                    with transaction.atomic():
                        user.email = email
                        user.save()
                except:
                    return Response({"details": "Unknown User"}, status=status.HTTP_400_BAD_REQUEST)
                

                try:
                    employee = models.Employee.objects.get(email=old_email)
                    with transaction.atomic():
                        employee.email = email
                        employee.save()
                except Exception as e:
                    print(e)
                    pass


                # Notify Employee
                subject = f"ICT Access Request Email Update [ASA-AKHK]"
                message = f"Hello,\n\nYour email has been updated from: {old_email} to: {email},\nUse your new email to access the system\n\nRegards\nASA-AKHK"
                # get emails
                emails = [old_email, email]
                
                try:
                    mail = {
                        "email" : emails, 
                        "subject" : subject,
                        "message" : message
                    }
                    Sendmail.objects.create(**mail)
                except Exception as e:
                    logger.error(e)

                return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
    
    @action(methods=["POST"],
            detail=False,
            url_path="verifications",
            url_name="verifications")
    def verifications(self, request):
        roles = user_util.fetchusergroups(request.user.id)
        if not any(role in ['ICT','HOD'] for role in roles):
            return Response({"details": "Permission Denied"}, status=status.HTTP_400_BAD_REQUEST)
        
        is_hod = 'HOD' in roles
        is_ict = 'ICT' in roles
        
        if request.method == "POST":
            payload = request.data
            serializer = serializers.VerificationSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                access_id = payload['access_id']
                r_status = payload['status']

                try:
                    access = models.Access.objects.get(id=access_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
                
                current_year = datetime.datetime.now().year

                existingInstance = models.Verifications.objects.filter(
                    access=access, year=current_year
                ).first()

                if existingInstance:
                    if is_hod:
                        existingInstance.hod_status = r_status
                        existingInstance.is_hod_verified = True
                        status_for = 'HOD'

                    if is_ict:
                        existingInstance.ict_status = r_status
                        existingInstance.is_ict_verified = True
                        status_for = 'ICT'

                    existingInstance.save()
                else:
                    if is_hod:
                        raw = {
                            "hod_status": r_status,
                            "is_hod_verified": True
                        }
                        status_for = 'HOD'
                    if is_ict:
                        raw = {
                            "ict_status": r_status,
                            "is_ict_verified": True
                        }
                        status_for = 'ICT'
                    models.Verifications.objects.create(**raw)

                # create track status change
                try:
                    raw = {
                        "access": access,
                        "status": r_status,
                        "status_for": status_for,
                        "action_by": request.user
                    }
                    models.VerificationStatusChange.objects.create(**raw)
                except Exception as e:
                    print(e)

                return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        

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
            url_path="verifications",
            url_name="verifications")
    def verifications(self, request):
                    
        employee_no = request.query_params.get('employee_no')
        department = request.query_params.get('department')


        q_filters = Q()

        if employee_no:
            q_filters &= Q(employee_no=employee_no)

        if department:
            q_filters &= Q(department=department)



        if q_filters:
            resp = models.Employee.objects.filter(q_filters) 
        else:
            resp = []

        if resp:
            resp = serializers.FetchRequestSerializer(
                resp, many=True, context={"user_id":request.user.id}).data

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
        active_status = ['REQUESTED','HOD APPROVED','STAFF SIGNED']

        if 'HOD' in roles:
            requests = models.Access.objects.filter(Q(employee__department=request.user.srrs_department) | Q(created_by=request.user), is_deleted=False).count()
            approved = models.Access.objects.filter(Q(employee__department=request.user.srrs_department) |  Q(created_by=request.user), status="ICT AUTHORIZED", is_deleted=False).count()
            rejected = models.Access.objects.filter(Q(employee__department=request.user.srrs_department) |  Q(created_by=request.user), status="REJECTED", is_deleted=False).count()
            pending = models.Access.objects.filter(Q(employee__department=request.user.srrs_department) |  Q(created_by=request.user), status__in=active_status, is_deleted=False).count()
        elif 'ICT' in roles or 'SUPERUSER' in roles:
            requests = models.Access.objects.filter(is_deleted=False).count()
            approved = models.Access.objects.filter(status="ICT AUTHORIZED", is_deleted=False).count()
            rejected = models.Access.objects.filter(status="REJECTED", is_deleted=False).count()
            pending = models.Access.objects.filter(status__in=active_status, is_deleted=False).count()
        else:
            requests = models.Access.objects.filter(Q(created_by=request.user) | Q(employee__email=request.user.email),is_deleted=False).count()
            approved = models.Access.objects.filter(Q(created_by=request.user) | Q(employee__email=request.user.email) ,status="ICT AUTHORIZED", is_deleted=False).count()
            rejected = models.Access.objects.filter(Q(created_by=request.user) | Q(employee__email=request.user.email),status="REJECTED", is_deleted=False).count()
            pending = models.Access.objects.filter(
                (Q(created_by=request.user) | Q(employee__email=request.user.email)) & Q(status__in=active_status), 
                is_deleted=False
            ).count()

        resp = {
            "requests": requests,
            "rejected": rejected,
            "approved": approved,
            "pending": pending,
        }

        return Response(resp, status=status.HTTP_200_OK)