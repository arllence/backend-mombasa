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
            url_path="expenditure",
            url_name="expenditure")
    def expenditure(self, request):
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
                    "created_by": request.user
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
                

            user_util.log_account_activity(
                authenticated_user, authenticated_user, "Expenditure created", f"Expenditure Id: {newInstance.id}")
            
            return Response('success', status=status.HTTP_200_OK)
            

        elif request.method == "PUT":
            payload = json.loads(request.data['payload'])
           
            # serialize contract payload
            serializer = serializers.UpdateContractSerializer(
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
                            contract=expenditureInstance, 
                            uploaded_by=request.user
                        )

                    except Exception as e:
                        logger.error(e)
                        print(e)
                        return Response({"details": "Error saving files"}, status=status.HTTP_400_BAD_REQUEST)  

            user_util.log_account_activity(
                authenticated_user, authenticated_user, "Expenditure updated", f"Expenditure Id: {expenditureInstance.id}")
            
            return Response('success', status=status.HTTP_200_OK)

  
        elif request.method == "PATCH":
            payload = request.data
            
            return Response('success', status=status.HTTP_200_OK)
            
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
                            resp = models.ExpenditureRequest.objects.filter(status='HOD APPROVED', is_deleted=False).order_by('-date_created')

                    elif any(role in ['HOF'] for role in roles):
                        if query == 'approved':
                            resp = models.ExpenditureRequest.objects.filter(status='CEO APPROVED',is_deleted=False).order_by('-date_created')
                        else:
                            resp = models.ExpenditureRequest.objects.filter(status='FINANCE APPROVED',is_deleted=False).order_by('-date_created')

                    elif any(role in ['CEO'] for role in roles):
                        if query == 'approved':
                            resp = models.ExpenditureRequest.objects.filter(status='CEO APPROVED', is_deleted=False).order_by('-date_created')
                        else:
                            resp = models.ExpenditureRequest.objects.filter(status='HOF APPROVED', is_deleted=False).order_by('-date_created')

                    elif any(role in ['SUPERUSER'] for role in roles):
                        if query == 'approved':
                            resp = models.ExpenditureRequest.objects.filter(status='CEO APPROVED', is_deleted=False).order_by('-date_created')
                        else:
                            resp = models.ExpenditureRequest.objects.filter(is_deleted=False).order_by('-date_created')

                    else:
                        if query == 'approved':
                            resp = models.ExpenditureRequest.objects.filter(status='CEO APPROVED', created_by=request.user, is_deleted=False).order_by('-date_created')
                        else:
                            resp = models.ExpenditureRequest.objects.filter(Q(is_deleted=False) & (Q(created_by=request.user)) ).order_by('-date_created')


                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resp, request)
                    serializer = serializers.FetchExpenditureSerializer(
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
            
           
            # serialize contract payload
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
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data
            roles = user_util.fetchusergroups(request.user.id) 

            serializer = serializers.NoteSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                comment = payload.get('comments')

                try:
                    issueInstance = models.Issue.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown issue"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    raw = {
                        "owner": request.user,
                        "issue": issueInstance,
                        "note": comment
                    }
                    models.Note.objects.create(**raw)

                # Send Note Notifications
                emails = []
                assignees = models.Assignees.objects.filter(Q(issue=issueInstance))
                for assignee in assignees:
                    emails.append(assignee.assignee.email)
                    if assignee.assigned_by:
                        emails.append(assignee.assigned_by.email)
                if issueInstance.assigned_to:
                    emails.append(issueInstance.assigned_to.email)
                if issueInstance.created_by:
                    emails.append(issueInstance.created_by.email)
                else:
                    emails.append(issueInstance.email)
                try:
                    emails.remove(request.user.email)
                except:
                    pass
                subject = f"[MHD] Note Issued for {issueInstance.uid}"
                message = f"Hello. \nA note has been added for Issue of id: {issueInstance.uid} \nby {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.\nThe Note:\n {comment}.\n"

                uri = f"requests/view/{str(issueInstance.id)}"
                link = "http://172.20.0.42:8009/" + uri
                platform = 'View Issue'

                message_template = read_template("general_template.html")
                message = message_template.substitute(
                    CONTENT=message,
                    LINK=link,
                    PLATFORM=platform
                )
                
                try:
                    mail = {
                        "email" : list(set(emails)), 
                        "subject" : subject,
                        "message" : message,
                        "is_html": True
                    }
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
                    resp = models.Note.objects.filter(Q(issue=request_id))

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
            url_path="contracts",
            url_name="contracts")
    def contracts(self, request):
                    
        department = request.query_params.get('department')
        commencement_date = request.query_params.get('date_from')
        expiry_date = request.query_params.get('date_to')

        q_filters = Q()

        if department:
            q_filters &= Q(department=department)

        if commencement_date:
            commencement_date = datetime.datetime.strptime(commencement_date, '%Y-%m-%d')
            q_filters &= Q(commencement_date=commencement_date)

        if expiry_date:
            expiry_date = datetime.datetime.strptime(expiry_date, '%Y-%m-%d')
            q_filters &= Q(expiry_date=expiry_date)

        if q_filters:
            resp = models.Contract.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
        else:
            roles = user_util.fetchusergroups(request.user.id)  

            if "MMD" in roles or "SUPERUSER" in roles:
                resp = models.Contract.objects.filter(Q(is_deleted=False)).order_by('-date_created')[:50]
                
            else:
                resp = models.Contract.objects.filter(Q(is_deleted=False)& Q(created_by=request.user)).order_by('-date_created')[:50]


        resp = serializers.FetchContractSerializer(resp, many=True, context={"user_id":request.user.id}).data

        return Response(resp, status=status.HTTP_200_OK)
    
        
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