import datetime
import json
import logging
from datetime import timedelta
from string import Template
from django.utils import timezone
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
from expenditure import models
from expenditure import serializers
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import User, Sendmail, SRRSDepartment, SubDepartment, OHC
from expenditure.utils import shared_fxns
from django.db.models import Sum
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import Group
from acl.models import Hods

from rest_framework.pagination import PageNumberPagination

# Get an instance of a logger
logger = logging.getLogger(__name__)

def read_template(filename):
    with open("acl/emails/" + filename, 'r', encoding='utf8') as template_file:
        template_file_content = template_file.read()
        return Template(template_file_content)

class CoreViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="core",
            url_name="core")
    def expenditure(self, request):
        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = json.loads(request.data['payload'])

            if not request.FILES.getlist('documents'):
                return Response({"details": f"Supporting Documents must be attached"}, status=status.HTTP_400_BAD_REQUEST)
            

            exts = ['pdf']
            for f in request.FILES.getlist('documents'):
                original_file_name = f.name
                ext = original_file_name.split('.')[-1].strip().lower()
                if ext not in exts:
                    return Response({"details": f"{original_file_name} not allowed. Only PDFs allowed for upload!"}, status=status.HTTP_400_BAD_REQUEST)
            

            uid = shared_fxns.generate_unique_identifier()
           
            # serialize payload
            serializer = serializers.CreateExpenditureSerializer(
                    data=payload, many=False)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            reference_no = payload['reference_no']
            description = payload['description']
            invoice_number = payload['invoice_number']
            amount_kes = payload['amount_kes']
            department = payload['department']
            
            try:
                department = SRRSDepartment.objects.get(id=department)
            except Exception as e:
                return Response({"details": "Unknown department"}, status=status.HTTP_400_BAD_REQUEST)

                    
            with transaction.atomic():
                # create instance
                raw = {
                    "uid" : uid,
                    "reference_no" : reference_no,
                    "description" : description,
                    "invoice_number" : invoice_number,
                    "amount_kes" : amount_kes,
                    "department" : department,
                    "requested_by": request.user
                }
                newInstance = models.ExpenditureRequest.objects.create(**raw)

                for f in request.FILES.getlist('documents'):
                    try:
                        original_file_name = f.name.upper()                        
                        models.Document.objects.create(
                            document=f,
                            file_name=original_file_name, 
                            expenditure=newInstance, 
                            uploaded_by=request.user
                        )

                    except Exception as e:
                        logger.error(e)
                        print(e)
                        return Response({"details": "Error saving files"}, status=status.HTTP_400_BAD_REQUEST)  
                    
                # track status change
                raw = {
                    "expenditure": newInstance,
                    "status": "REQUESTED",
                    "action_by": request.user
                }
                models.StatusChange.objects.create(**raw)

                # Send Note Notifications
                emails = list(Hods.objects.filter(hod=request.user, department=requestInstance.department).values_list('hod__email', flat=True))

                uri = f"requests/view/{str(newInstance.id)}"
                link = "http://172.20.0.42:8017/" + uri

                subject = f"[EXPENDITURE] Request Raised for {newInstance.reference_no}"
                message = f"Hello. \nAn expenditure request has been raised\nby {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.\nTo approve visit: {link}\n\nRegards\nEAS-AKHK"

                try:
                    mail = {
                        "email" : list(set(emails)), 
                        "subject" : subject,
                        "message" : message
                    }
                    if emails:
                        Sendmail.objects.create(**mail)
                except Exception as e:
                    logger.error(e)
                

            user_util.log_account_activity(
                authenticated_user, authenticated_user, "Expenditure created", f"Expenditure Id: {newInstance.id}")
            
            return Response('success', status=status.HTTP_200_OK)
            

        elif request.method == "PUT":
            payload = json.loads(request.data['payload'])
           
            # serialize contract payload
            serializer = serializers.UpdateExpenditureSerializer(
                    data=payload, many=False)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            request_id = payload['request_id']
            reference_no = payload['reference_no']
            description = payload['description']
            invoice_number = payload['invoice_number']
            amount_kes = payload['amount_kes']
            department = payload['department']
            

            try:
                expenditureInstance = models.ExpenditureRequest.objects.get(id=request_id)
            except Exception as e:
                return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                department = SRRSDepartment.objects.get(id=department)
            except Exception as e:
                return Response({"details": "Unknown department"}, status=status.HTTP_400_BAD_REQUEST)

                    
            with transaction.atomic():
                # create contract instance
                raw = {
                    "reference_no" : reference_no,
                    "description" : description,
                    "invoice_number" : invoice_number,
                    "amount_kes" : amount_kes,
                    "department" : department
                }
                models.ExpenditureRequest.objects.filter(id=request_id).update(**raw)

                for f in request.FILES.getlist('documents'):
                    exts = ['pdf']
                    original_file_name = f.name
                    ext = original_file_name.split('.')[-1].strip().lower()
                    if ext not in exts:
                        return Response({"details": f"{original_file_name} not allowed. Only PDFs allowed for upload!"}, status=status.HTTP_400_BAD_REQUEST)
                    
                    try:
                        original_file_name = f.name.upper()                        
                        models.Document.objects.create(
                            document=f,
                            file_name=original_file_name, 
                            expenditure=expenditureInstance, 
                            uploaded_by=request.user
                        )

                    except Exception as e:
                        logger.error(e)
                        print(e)
                        return Response({"details": "Error saving files"}, status=status.HTTP_400_BAD_REQUEST)  
                    
                # track status change
                raw = {
                    "expenditure": expenditureInstance,
                    "status": "EDITED",
                    "action_by": request.user
                }
                models.StatusChange.objects.create(**raw)

            user_util.log_account_activity(
                authenticated_user, authenticated_user, "Expenditure updated", f"Expenditure Id: {expenditureInstance.id}")
            
            return Response('success', status=status.HTTP_200_OK)

  
        elif request.method == "PATCH":
            # Approvals hod / finance_manager / ceo / hof

            if not any(role in ["HOD","FINANCE_MANAGER","CEO","HOF","SUPERUSER", "CASH_OFFICE"] for role in roles):
                return Response({"details": "Permission Denied"}, status=status.HTTP_400_BAD_REQUEST)
            
            payload = request.data

            serializer = serializers.PatchExpenditureSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                request_status = payload['status']
                comment = payload['comments']
                payments_made_to = payload.get('payments_made_to') or None
                payments_date = payload.get('payments_date') or None

                try:
                    requestInstance = models.ExpenditureRequest.objects.get(id=request_id)
                except Exception as e:
                    logger.error(e)
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                
                
                is_hod, is_finance_manager, is_ceo, is_hof, is_cash_office = [False, False, False, False, False]
                if "HOD" in roles:
                    is_hod = Hods.objects.filter(hod=request.user, department=requestInstance.department).exists()

                if "FINANCE_MANAGER" in roles:
                    is_finance_manager = True

                if "HOF" in roles:
                    is_hof = True

                if "CEO" in roles:
                    is_ceo = True

                if "CASH_OFFICE" in roles:
                    is_cash_office = True
                
                if request_status == 'REJECTED':
                    requestInstance.status = "REJECTED"
                    requestInstance.save()

                else:
                    if not is_cash_office and request_status == 'DISBURSED':
                        return Response({"details": "Permission Denied"}, status=status.HTTP_400_BAD_REQUEST)

                    if request_status == 'DISBURSED':
                        requestInstance.payments_made_to = payments_made_to
                        requestInstance.payments_date = payments_date
                        requestInstance.is_cash_office_approved = True
                        request_status = "DISBURSED"

                    if is_hod:
                        requestInstance.is_hod_approved = True
                        requestInstance.status = "HOD APPROVED"
                        request_status = "HOD APPROVED"

                    if is_finance_manager:
                        requestInstance.is_finance_manager_approved = True
                        requestInstance.status = "FINANCE APPROVED"
                        request_status = "FINANCE APPROVED"

                    if is_hof:
                        requestInstance.is_hof_approved = True
                        requestInstance.status = "HOF APPROVED"
                        request_status = "HOF APPROVED"
                        
                    if is_ceo:
                        requestInstance.is_ceo_approved = True
                        requestInstance.status = "CEO APPROVED"
                        request_status = "CEO APPROVED"                    


                # track status change
                raw = {
                    "expenditure": requestInstance,
                    "status": request_status,
                    "action_by": request.user
                }

                with transaction.atomic():
                    requestInstance.save()
                    models.StatusChange.objects.create(**raw)

                    if comment:
                        final_comment = f"[{request_status}] {comment}"
                        models.Note.objects.create(
                            expenditure=requestInstance,
                            note=final_comment,
                            created_by=request.user
                        )
                        comment = f"[Comment: {comment}]"

                    # send requestor notification email
                    emails = [requestInstance.requested_by.email]
                    if is_ceo:
                        emails_x = list(get_user_model().objects.filter(Q(groups__name__in=['CASH_OFFICE','HOF','FINANCE_MANAGER'])).values_list('email', flat=True))
                        emails += emails_x
                    subject = f"[EXPENDITURE] Request Status: {requestInstance.reference_no} ."
                    message = f"Hello. \nExpenditure approval for: {requestInstance.reference_no}, \nhas been {request_status} by: {request.user.first_name} {request.user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\n{comment}\n\nRegards\nEAS-AKHK\n--Auto-generated--\n"

                    try:
                        if emails:
                            mail = {
                                "email" : list(set(emails)), 
                                "subject" : subject,
                                "message" : message,
                            }                            
                            Sendmail.objects.create(**mail)
                    except Exception as e:
                        logger.error(e)

                    # send approver notification email
                    if request_status != "REJECTED":
                        emails = []
                        if is_hod:
                            emails =  list(get_user_model().objects.filter(Q(groups__name='FINANCE_MANAGER')).values_list('email', flat=True))
                        if is_finance_manager:
                            emails =  list(get_user_model().objects.filter(Q(groups__name='HOF')).values_list('email', flat=True))
                        if is_hof:
                            emails =  list(get_user_model().objects.filter(Q(groups__name='CEO')).values_list('email', flat=True))
                            
                        subject = f"[EXPENDITURE] Request {requestInstance.reference_no} Pending Approval."
                        message = f"Hello. \nExpenditure request: {requestInstance.reference_no}, \nis pending your approval\nVisit http://172.20.0.42:8017/requests/view/{request_id}\n\nRegards\nEAS-AKHK\n--Auto-generated--\n"
                        try:
                            if emails:
                                mail = {
                                    "email" : list(set(emails)), 
                                    "subject" : subject,
                                    "message" : message,
                                }
                                Sendmail.objects.create(**mail)
                        except Exception as e:
                            logger.error(e)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            reference_no = request.query_params.get('reference_no')
            invoice_number = request.query_params.get('invoice_number')
            query = request.query_params.get('q')
            slim = request.query_params.get('slim')

            if request_id or reference_no or invoice_number:
 
                try:
                    if request_id:
                        resp = models.ExpenditureRequest.objects.get(id=request_id)
                    elif reference_no:
                        resp = models.ExpenditureRequest.objects.get(reference_no=reference_no)
                    elif invoice_number:
                        resp = models.ExpenditureRequest.objects.get(invoice_number=invoice_number)

                    if slim:
                        resp = serializers.SlimFetchExpenditureSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.FetchExpenditureSerializer(resp, many=False, context={"user_id":request.user.id}).data

                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
                
            elif query:
                try:
                    resp = models.ExpenditureRequest.objects.filter(
                        Q(invoice_number__icontains=query) |
                        Q(reference_no__icontains=query) |
                        Q(description__icontains=query) |
                        Q(uid__icontains=query) |
                        Q(department__name__icontains=query)
                    )

                    if slim:
                        resp = serializers.SlimFetchExpenditureSerializer(resp, many=True, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.SlimFetchExpenditureSerializer(resp, many=True, context={"user_id":request.user.id}).data

                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
                
                
            else:
                try:
                    if any(role in ['HOD'] for role in roles):
                        departments = list(Hods.objects.filter(hod=request.user).values_list('department__id', flat=True))
  
                        filters = Q(department__in=departments) | Q(requested_by=request.user)
                        base_query = models.ExpenditureRequest.objects.filter(filters, is_deleted=False)

                        if query == 'approved':
                            base_query = base_query.filter(status='CEO APPROVED')

                        resp = base_query.order_by('-date_created')

                    elif any(role in ['FINANCE_MANAGER'] for role in roles):
                        if query == 'approved':
                            resp = models.ExpenditureRequest.objects.filter(status='CEO APPROVED', is_deleted=False).order_by('-date_created')
                        else:
                            resp = models.ExpenditureRequest.objects.filter(Q(status='HOD APPROVED') | Q(requested_by=request.user), is_deleted=False).order_by('-date_created')

                    elif any(role in ['HOF'] for role in roles):
                        if query == 'approved':
                            resp = models.ExpenditureRequest.objects.filter(status='CEO APPROVED',is_deleted=False).order_by('-date_created')
                        else:
                            resp = models.ExpenditureRequest.objects.filter(Q(status='FINANCE APPROVED') | Q(requested_by=request.user),is_deleted=False).order_by('-date_created')

                    elif any(role in ['CEO'] for role in roles):
                        if query == 'approved':
                            resp = models.ExpenditureRequest.objects.filter(status='CEO APPROVED', is_deleted=False).order_by('-date_created')
                        else:
                            resp = models.ExpenditureRequest.objects.filter(Q(status='HOF APPROVED') | Q(requested_by=request.user), is_deleted=False).order_by('-date_created')

                    elif any(role in ['SUPERUSER'] for role in roles):
                        if query == 'approved':
                            resp = models.ExpenditureRequest.objects.filter(status='CEO APPROVED', is_deleted=False).order_by('-date_created')
                        else:
                            resp = models.ExpenditureRequest.objects.filter(is_deleted=False).order_by('-date_created')

                    elif any(role in ['CASH_OFFICE'] for role in roles):
                        if query == 'approved':
                            resp = models.ExpenditureRequest.objects.filter(is_cash_office_approved=True, is_deleted=False).order_by('-date_created')
                        else:
                            resp = models.ExpenditureRequest.objects.filter((Q(status='CEO APPROVED') & Q(is_cash_office_approved=False)) | Q(requested_by=request.user),is_deleted=False).order_by('-date_created')

                    else:
                        if query == 'approved':
                            resp = models.ExpenditureRequest.objects.filter(status='CEO APPROVED', requested_by=request.user, is_deleted=False).order_by('-date_created')
                        else:
                            resp = models.ExpenditureRequest.objects.filter(Q(is_deleted=False) & (Q(requested_by=request.user)) ).order_by('-date_created')


                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resp, request)
                    serializer = serializers.SlimFetchExpenditureSerializer(
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
                    models.ExpenditureRequest.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)    
                except Exception as e:
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST) 
                
    
    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="documents",
            url_name="documents")
    def documents(self, request):
        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = json.loads(request.data['payload'])

            exts = ['pdf']
            for f in request.FILES.getlist('documents'):
                original_file_name = f.name
                ext = original_file_name.split('.')[-1].strip().lower()
                if ext not in exts:
                    return Response({"details": f"{original_file_name} not allowed. Only PDFs allowed for upload!"}, status=status.HTTP_400_BAD_REQUEST)
           
            # serialize payload
            serializer = serializers.UploadFileSerializer(
                    data=payload, many=False)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            request_id = payload['request_id']
            file_type = payload['file_type']

            try:
                requestInstance = models.ExpenditureRequest.objects.get(id=request_id)
            except Exception as e:
                return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                    
            with transaction.atomic():
                # create instance

                for f in request.FILES.getlist('documents'):
                    try:
                        original_file_name = f.name.upper()                        
                        models.Document.objects.create(
                            document=f,
                            file_name=original_file_name, 
                            file_type=file_type, 
                            expenditure=requestInstance, 
                            uploaded_by=request.user
                        )

                    except Exception as e:
                        logger.error(e)
                        print(e)
                        return Response({"details": "Error saving files"}, status=status.HTTP_400_BAD_REQUEST)  
                

            user_util.log_account_activity(
                authenticated_user, authenticated_user, "File uploaded", f"Expenditure Id: {requestInstance.id}")
            
            return Response('success', status=status.HTTP_200_OK)

        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            expenditure_id = request.query_params.get('expenditure_id')
            query = request.query_params.get('q')
            slim = request.query_params.get('slim')
            previous = request.query_params.get('previous')

            if request_id or expenditure_id:
                try:
                    if request_id:
                        resp = models.Document.objects.get(Q(id=request_id))

                    if expenditure_id:
                        resp = models.Document.objects.get(Q(expenditure=expenditure_id))

                    if slim:
                        resp = serializers.SlimFetchDocumentSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.SlimFetchDocumentSerializer(resp, many=False, context={"user_id":request.user.id}).data

                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
        
            elif query:
                try:
                    resp = models.Document.objects.filter(
                        Q(file_name__icontains=query) |
                        Q(file_type__icontains=query) |
                        Q(expenditure__uid__icontains=query) |
                        Q(expenditure__title__icontains=query) |
                        Q(expenditure__department__name__icontains=query)
                    )

                    if slim:
                        resp = serializers.SlimFetchDocumentSerializer(resp, many=True, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.SlimFetchDocumentSerializer(resp, many=True, context={"user_id":request.user.id}).data

                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
                
            else:
                try:

                    if any(role in ['SUPERUSER'] for role in roles):

                        resp = models.Document.objects.filter(is_deleted=False).order_by('-date_created')

                    else:
                        resp = models.Document.objects.filter(Q(is_deleted=False) & (Q(uploaded_by=request.user)) ).order_by('-date_created')



                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resp, request)
                    serializer = serializers.SlimFetchDocumentSerializer(
                        result_page, many=True, context={"user_id":request.user.id})
                    return paginator.get_paginated_response(serializer.data)
                
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.Document.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)    
                except Exception as e:
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST) 
                

    @action(methods=["POST", "GET", "PUT", "DELETE"],
            detail=False,
            url_path="platform-admins",
            url_name="platform-admins")
    def platform_admins(self, request):
        if request.method == "POST":
            payload = request.data
            serializer = serializers.PlatformAdminSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                admin = payload['admin']

                try:
                    admin = User.objects.get(id=admin)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown User"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Invalid Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                # assign FMS_ADMIN role
                assign_role = user_util.award_role('CMS_ADMIN', str(admin.id))
                if not assign_role:
                    return Response({"details": "Unable to assign role CMS_ADMIN"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    raw = {
                        "admin": admin,
                        "created_by": request.user
                    }

                    models.PlatformAdmin.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":
            payload = request.data

            serializer = serializers.UpdatePlatformAdminSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                admin = payload['admin']

                try:
                    request = models.PlatformAdmin.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Invalid Request"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():

                    request.admin = admin
                    request.created_by = request.user
                    request.save()

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    request = models.PlatformAdmin.objects.get(Q(id=request_id))
                    request = serializers.FetchPlatformAdminSerializer(request, many=False).data
                    return Response(request, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:

                    request = models.PlatformAdmin.objects.filter(Q(is_deleted=False)).order_by('-date_created')
                    request = serializers.FetchPlatformAdminSerializer(request, many=True).data
                    return Response(request, status=status.HTTP_200_OK)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                
        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    user = models.PlatformAdmin.objects.get(id=request_id)
                    user_util.revoke_role('CMS_ADMIN', str(user.admin.id))
                    user.delete()
                    return Response('200', status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request "}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"details": "Request incomplete"}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(methods=["POST","GET"],
            detail=False,
            url_path="notes",
            url_name="notes")
    def notes(self, request):

        authenticated_user = request.user

        if request.method == "POST":

            payload = request.data

            serializer = serializers.NoteSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                comment = payload.get('comments')

                try:
                    targetInstance = models.ExpenditureRequest.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    raw = {
                        "created_by": request.user,
                        "expenditure": targetInstance,
                        "note": comment
                    }
                    models.Note.objects.create(**raw)

                # Send Note Notifications
                emails = list(models.StatusChange.objects.filter(Q(expenditure=targetInstance)).values_list('action_by__email', flat=True))

                try:
                    emails.remove(request.user.email)
                except:
                    pass

                uri = f"requests/view/{str(targetInstance.id)}"
                link = "http://172.20.0.42:8017/" + uri

                subject = f"[EXPENDITURE] Note Issued for {targetInstance.reference_no}"
                message = f"Hello. \nA note has been added for expenditure: {targetInstance.reference_no} \nby {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.\n\nThe Note:\n {comment}.\n\nVisit: {link}"

                try:
                    mail = {
                        "email" : list(set(emails)), 
                        "subject" : subject,
                        "message" : message
                    }
                    if emails:
                        Sendmail.objects.create(**mail)
                except Exception as e:
                    logger.error(e)

                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    resp = models.Note.objects.filter(Q(expenditure=request_id))

                    resp = serializers.FetchNoteSerializer(
                        resp, many=True, context={"user_id":request.user.id}).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response([], status=status.HTTP_200_OK)
                   

class ReportsViewSet(viewsets.ViewSet):
    # search_fields = ['id', ]

    def get_queryset(self):
        return []

    @action(methods=["GET",],
            detail=False,
            url_path="general",
            url_name="general")
    def general(self, request):
                    
        department = request.query_params.get('department')
        r_status = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
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

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required 😏"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)

        if department:
            q_filters &= Q(department=department)

        if r_status:
            q_filters &= Q(status=r_status)

        if q_filters:
            resp = models.ExpenditureRequest.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
        else:
            resp = models.ExpenditureRequest.objects.filter(Q(is_deleted=False)).order_by('-date_created')

        paginator = PageNumberPagination()
        paginator.page_size = max(len(resp), 1) if q_filters else 50
        result_page = paginator.paginate_queryset(resp, request)
        serializer = serializers.SlimFetchExpenditureSerializer(
            result_page, many=True, context={"user_id":request.user.id})
        return paginator.get_paginated_response(serializer.data)
    
        
class AnalyticsViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return []

    @action(methods=["GET",],
            detail=False,
            url_path="general",
            url_name="general")
    def general(self, request):
   
        # Get the current date
        now = timezone.now().date()

        # Calculate the date 4 months from now
        four_months_from_now = now + timedelta(days=4*30)  # Approximating 4 months as 120 days

        total = models.Contract.objects.filter(Q(is_deleted=False)).count()
        almost = models.Contract.objects.filter(Q(is_deleted=False),expiry_date__gte=now, expiry_date__lte=four_months_from_now).count()
        expired = models.Contract.objects.filter(Q(is_deleted=False),expiry_date__lt=now).count()
        renewed = models.Contract.objects.filter(Q(is_deleted=False)).exclude(previous__isnull=False).count()

        resp = {
            "total": total,
            "almost": almost,
            "expired": expired,
            "renewed": renewed,
        }

        return Response(resp, status=status.HTTP_200_OK)