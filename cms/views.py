import datetime
import json
import logging
from datetime import timedelta
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
from cms import models
from cms import serializers
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import User, Sendmail, SRRSDepartment, SubDepartment, OHC
from cms.utils import shared_fxns
from django.db.models import Sum
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import Group

from rest_framework.pagination import PageNumberPagination

# Get an instance of a logger
logger = logging.getLogger(__name__)

class CoreViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="contracts",
            url_name="contracts")
    def contracts(self, request):
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
           
            # serialize contract payload
            serializer = serializers.CreateContractSerializer(
                    data=payload, many=False)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            title = payload['title']
            description = payload['description']
            commencement_date = payload['commencement_date']
            expiry_date = payload['expiry_date']
            department = payload['department']
            previous_contract = payload['previous_contract']
            
 
            # validate off period
            period = shared_fxns.find_date_difference(commencement_date,expiry_date,'days')
            if period < 0:
                return Response({"details": "Invalid contract duration / dates"}, status=status.HTTP_400_BAD_REQUEST)
                 
            try:
                department = SRRSDepartment.objects.get(id=department)
            except Exception as e:
                return Response({"details": "Unknown department"}, status=status.HTTP_400_BAD_REQUEST)

                    
            with transaction.atomic():
                # create contract instance
                raw = {
                    "uid" : uid,
                    "title" : title,
                    "description" : description,
                    "commencement_date" : commencement_date,
                    "expiry_date" : expiry_date,
                    "department" : department,
                    "previous" : previous_contract,
                    "created_by": request.user
                }
                contractInstance = models.Contract.objects.create(**raw)

                for f in request.FILES.getlist('documents'):
                    try:
                        original_file_name = f.name.upper()                        
                        models.Document.objects.create(
                            document=f,
                            file_name=original_file_name, 
                            contract=contractInstance, 
                            uploaded_by=request.user
                        )

                    except Exception as e:
                        logger.error(e)
                        print(e)
                        return Response({"details": "Error saving files"}, status=status.HTTP_400_BAD_REQUEST)  
                

            user_util.log_account_activity(
                authenticated_user, authenticated_user, "Contract created", f"Contract Id: {contractInstance.id}")
            
            return Response('success', status=status.HTTP_200_OK)
            

        elif request.method == "PUT":
            payload = json.loads(request.data['payload'])
           
            # serialize contract payload
            serializer = serializers.UpdateContractSerializer(
                    data=payload, many=False)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            request_id = payload['request_id']
            title = payload['title']
            description = payload['description']
            commencement_date = payload['commencement_date']
            expiry_date = payload['expiry_date']
            department = payload['department']
            previous_contract = payload['previous_contract']
            
 
            # validate off period
            period = shared_fxns.find_date_difference(commencement_date,expiry_date,'days')
            if period < 0:
                return Response({"details": "Invalid contract duration / dates"}, status=status.HTTP_400_BAD_REQUEST)
                 
            try:
                contractInstance = models.Contract.objects.get(id=request_id)
            except Exception as e:
                return Response({"details": "Unknown contract"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                department = SRRSDepartment.objects.get(id=department)
            except Exception as e:
                return Response({"details": "Unknown department"}, status=status.HTTP_400_BAD_REQUEST)

                    
            with transaction.atomic():
                # create contract instance
                raw = {
                    "title" : title,
                    "description" : description,
                    "commencement_date" : commencement_date,
                    "expiry_date" : expiry_date,
                    "department" : department,
                    "previous" : previous_contract
                }
                models.Contract.objects.filter(id=request_id).update(**raw)

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
                            contract=contractInstance, 
                            uploaded_by=request.user
                        )

                    except Exception as e:
                        logger.error(e)
                        print(e)
                        return Response({"details": "Error saving files"}, status=status.HTTP_400_BAD_REQUEST)  

            user_util.log_account_activity(
                authenticated_user, authenticated_user, "Contract updated", f"Contract Id: {contractInstance.id}")
            
            return Response('success', status=status.HTTP_200_OK)

  
        elif request.method == "PATCH":
            payload = request.data
            
            return Response('success', status=status.HTTP_200_OK)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            previous = request.query_params.get('previous')
            query = request.query_params.get('q')
            slim = request.query_params.get('slim')

            if request_id:
                try:
                    resp = models.Contract.objects.get(Q(id=request_id))

                    if slim:
                        resp = serializers.SlimFetchContractSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.FetchContractSerializer(resp, many=False, context={"user_id":request.user.id}).data

                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request!"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
                
            elif previous:
                try:
                    resp = models.Contract.objects.filter(Q(previous=previous))

                    if slim:
                        resp = serializers.SlimFetchContractSerializer(resp, many=True, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.SlimFetchContractSerializer(resp, many=True, context={"user_id":request.user.id}).data

                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request!"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
                
            elif query:
                try:
                    resp = models.Contract.objects.filter(
                        Q(title__icontains=query) |
                        Q(uid__icontains=query) |
                        Q(department__name__icontains=query)
                    )

                    if slim:
                        resp = serializers.SlimFetchContractSerializer(resp, many=True, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.SlimFetchContractSerializer(resp, many=True, context={"user_id":request.user.id}).data

                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
                
                
            else:
                try:

                    if any(role in ['SUPERUSER'] for role in roles):

                        resp = models.Contract.objects.filter(is_deleted=False).order_by('-date_created')

                    else:
                        resp = models.Contract.objects.filter(Q(is_deleted=False) & (Q(created_by=request.user)) ).order_by('-date_created')



                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resp, request)
                    serializer = serializers.FetchContractSerializer(
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
                    models.Contract.objects.filter(Q(id=request_id)).update(**raw)
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
            
            contract_id = payload['contract_id']
            file_type = payload['file_type']

            try:
                contractInstance = models.Contract.objects.get(id=contract_id)
            except Exception as e:
                return Response({"details": "Unknown contract"}, status=status.HTTP_400_BAD_REQUEST)
                    
            with transaction.atomic():
                # create contract instance

                for f in request.FILES.getlist('documents'):
                    try:
                        original_file_name = f.name.upper()                        
                        models.Document.objects.create(
                            document=f,
                            file_name=original_file_name, 
                            file_type=file_type, 
                            contract=contractInstance, 
                            uploaded_by=request.user
                        )

                    except Exception as e:
                        logger.error(e)
                        print(e)
                        return Response({"details": "Error saving files"}, status=status.HTTP_400_BAD_REQUEST)  
                

            user_util.log_account_activity(
                authenticated_user, authenticated_user, "File uploaded", f"Contract Id: {contractInstance.id}")
            
            return Response('success', status=status.HTTP_200_OK)

        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            contract_id = request.query_params.get('contract_id')
            query = request.query_params.get('q')
            slim = request.query_params.get('slim')
            previous = request.query_params.get('previous')

            if request_id:
                try:
                    resp = models.Document.objects.get(Q(id=request_id))

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
                
            elif contract_id:
                try:
                    resp = models.Document.objects.get(Q(contract=contract_id))

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
                
            elif previous:
                try:
                    resp = models.Document.objects.filter(Q(contract__previous=previous))

                    if slim:
                        resp = serializers.SlimFetchDocumentSerializer(resp, many=True, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.SlimFetchDocumentSerializer(resp, many=True, context={"user_id":request.user.id}).data

                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request!"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
                
            elif query:
                try:
                    resp = models.Document.objects.filter(
                        Q(file_name__icontains=query) |
                        Q(file_type__icontains=query) |
                        Q(contract__uid__icontains=query) |
                        Q(contract__title__icontains=query) |
                        Q(contract__department__name__icontains=query)
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
        # roles = user_util.fetchusergroups(request.user.id)
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