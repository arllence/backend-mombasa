import datetime
import json
import logging
from datetime import date, timedelta
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
from django.db import transaction
from ctp import models
from ctp import serializers
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import Hods, User, Sendmail, SRRSDepartment, SubDepartment, OHC
from ctp.utils import shared_fxns
from django.db.models import Sum
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Count, Q, F, Value
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, Concat


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
            url_path="training-materials",
            url_name="training-materials")
    def training_materials(self, request):
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
            serializer = serializers.CreateTrainingMaterialSerializer(
                    data=payload, many=False)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            title = payload['title']
            type = payload['type']
            external_link = payload['external_link']
            description = payload['description']
            department = payload['department']
            category = payload['category']
            
                 
            try:
                department = SRRSDepartment.objects.get(id=department)
            except Exception as e:
                return Response({"details": "Unknown department"}, status=status.HTTP_400_BAD_REQUEST)

                    
            with transaction.atomic():
                # create instance
                raw = {
                    "uid" : uid,
                    "title" : title,
                    "type" : type,
                    "category" : category,
                    "external_url" : external_link,
                    "description" : description,
                    "department" : department,
                    "created_by": request.user
                }
                createdInstance = models.TrainingMaterial.objects.create(**raw)

                for f in request.FILES.getlist('documents'):
                    try:
                        original_file_name = f.name.upper()                        
                        models.Document.objects.create(
                            document=f,
                            file_name=original_file_name, 
                            training=createdInstance, 
                            uploaded_by=request.user
                        )

                    except Exception as e:
                        logger.error(e)
                        print(e)
                        return Response({"details": "Error saving files"}, status=status.HTTP_400_BAD_REQUEST)  
                

            user_util.log_account_activity(
                authenticated_user, authenticated_user, "Training created", f"Training Id: {createdInstance.id}")
            
            return Response('success', status=status.HTTP_200_OK)
            

        elif request.method == "PUT":
            payload = json.loads(request.data['payload'])
           
            # serialize contract payload
            serializer = serializers.UpdateTrainingMaterialSerializer(
                    data=payload, many=False)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            request_id = payload['request_id']
            title = payload['title']
            type = payload['type']
            external_link = payload['external_link']
            description = payload['description']
            department = payload['department']
            category = payload['category']
        
                 
            try:
                targetInstance = models.TrainingMaterial.objects.get(id=request_id)
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
                    "type" : type,
                    "category" : category,
                    "external_url" : external_link,
                    "description" : description,
                    "department" : department,
                }
                models.TrainingMaterial.objects.filter(id=request_id).update(**raw)

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
                            training=targetInstance, 
                            uploaded_by=request.user
                        )

                    except Exception as e:
                        logger.error(e)
                        print(e)
                        return Response({"details": "Error saving files"}, status=status.HTTP_400_BAD_REQUEST)  

            user_util.log_account_activity(
                authenticated_user, authenticated_user, "TrainingMaterial updated", f"TrainingMaterial Id: {targetInstance.id}")
            
            return Response('success', status=status.HTTP_200_OK)

  
        elif request.method == "PATCH":
            payload = request.data
            
            return Response('success', status=status.HTTP_200_OK)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            department_id = request.query_params.get('department')
            type = request.query_params.get('type')
            category = request.query_params.get('category')
            query = request.query_params.get('q')
            slim = request.query_params.get('slim')
            resp = []

            filters = Q(is_deleted=False)

            if department_id:
                filters &= Q(department=department_id)

            if category:
                filters &= Q(category=category)

            if type:
                filters &= Q(type=type)

            if query:
                if query == 'all':
                    resp = models.TrainingMaterial.objects.filter(is_deleted=False).order_by('title')
                    resp = serializers.SlimFetchTrainingMaterialSerializer(resp, many=True, context={"user_id":request.user.id}).data
                    return Response(resp, status=status.HTTP_200_OK)
                else:
                    filters &= (
                        Q(title__icontains=query) |
                        Q(uid__icontains=query) |
                        Q(type__icontains=query) |
                        Q(department__name__icontains=query)
                    )

            if request_id:
                try:
                    resp = models.TrainingMaterial.objects.get(Q(id=request_id))

                    if slim:
                        resp = serializers.SlimFetchTrainingMaterialSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.FetchTrainingMaterialSerializer(resp, many=False, context={"user_id":request.user.id}).data

                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request!"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
                
            else:
                try:

                    if any(role in ['SUPERUSER','CTP_ADMIN', 'HR'] for role in roles):

                        if filters:
                            resp = models.TrainingMaterial.objects.filter(filters).order_by('-date_created')
                        else:
                            resp = models.TrainingMaterial.objects.filter(is_deleted=False).order_by('-date_created')

                    elif any(role in ['HOD'] for role in roles):
                        try:
                            dept = (Hods.objects.get(hod=request.user)).department
                        except:
                            return Response({"details": "HOD role not understood"}, status=status.HTTP_400_BAD_REQUEST)
                        
                        if filters:
                            filters |= (Q(created_by=request.user) | Q(department=dept) )
                            resp = models.TrainingMaterial.objects.filter(filters).order_by('-date_created')
                        else:
                            resp = models.TrainingMaterial.objects.filter(
                                Q(department=dept) | 
                                Q(created_by=request.user) | 
                                Q(category='GENERAL'), is_deleted=False).order_by('-date_created')                   

                    else:
                        filters &= (Q(created_by=request.user) | 
                                    Q(department=request.user.srrs_department) |
                                    Q(category='GENERAL'))
                        resp = models.TrainingMaterial.objects.filter(filters).order_by('-date_created')
                
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            
            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(resp, request)
            serializer = serializers.FetchTrainingMaterialSerializer(
                result_page, many=True, context={"user_id":request.user.id})
            return paginator.get_paginated_response(serializer.data)
        
        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.TrainingMaterial.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)    
                except Exception as e:
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST) 


    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="training-assignment",
            url_name="training-assignment")
    def training_assignment(self, request):
        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            uid = shared_fxns.generate_unique_identifier()
           
            # serialize payload
            serializer = serializers.CreateTrainingAssignmentSerializer(
                    data=payload, many=False)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            assign_to = payload['assign_to']
            training = payload['training']  
            completion_date = payload['completion_date']            
            departments = payload['department']            
            assignees = payload['assignees']  

            try:
                training = models.TrainingMaterial.objects.get(id=training)
            except Exception as e:
                return Response({"details": "Unknown training"}, status=status.HTTP_400_BAD_REQUEST)

            if assign_to == 'Individuals':   
                try:
                    users = get_user_model().objects.filter(id__in=assignees)
                except Exception as e:
                    print(e)
                    return Response({"details": "Unknown user"}, status=status.HTTP_400_BAD_REQUEST)
                
            if assign_to == 'Department':   
                try:
                    users = get_user_model().objects.filter(srrs_department__in=departments)
                except Exception as e:
                    return Response({"details": "Unknown user"}, status=status.HTTP_400_BAD_REQUEST)
                
            if assign_to == 'Everyone':  
                try:
                    users = get_user_model().objects.filter(is_suspended=False)
                except Exception as e:
                    return Response({"details": "Unknown user"}, status=status.HTTP_400_BAD_REQUEST)


            with transaction.atomic():
                raw = {
                    "training" : training,
                    "completion_date" : completion_date,
                    "assigned_by": request.user
                }
                bulkCreate = [
                    models.TrainingAssignment(
                        user = user, 
                        **raw
                    )
                    for user in users
                ]
                try:
                    createdInstance = models.TrainingAssignment.objects.bulk_create(bulkCreate)   
                except IntegrityError:
                    return Response({"details": "Assignments already exists"}, status=status.HTTP_400_BAD_REQUEST)            

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Training Assignment created", f"Training Id: {[x.id for x in createdInstance]}")
            
            return Response('success', status=status.HTTP_200_OK)
            

        elif request.method == "PUT":
            # serialize payload
            serializer = serializers.UpdateTrainingAssignmentSerializer(
                    data=payload, many=False)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            request_id = payload['request_id']
            user = payload['user']
            training = payload['training']  
            completion_date = payload['training']         
                 
            try:
                targetInstance = models.TrainingAssignment.objects.get(id=request_id)
            except Exception as e:
                return Response({"details": "Unknown assignment"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                user = get_user_model.objects.get(id=user)
            except Exception as e:
                return Response({"details": "Unknown user"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                training = models.TrainingAssignment.objects.get(id=training)
            except Exception as e:
                return Response({"details": "Unknown training"}, status=status.HTTP_400_BAD_REQUEST)

                    
            with transaction.atomic():
                # create instance
                raw = {
                    "user" : user,
                    "training" : training,
                    "completion_date" : completion_date,
                    "assigned_by": request.user
                }
                models.TrainingAssignment.objects.filter(id=request_id).update(**raw)

            user_util.log_account_activity(
                authenticated_user, authenticated_user, "Training Assignment updated", f"Training Assignment Id: {targetInstance.id}")
            
            return Response('success', status=status.HTTP_200_OK)

  
        elif request.method == "PATCH":
            # self assign training
            payload = request.data
            training_id = payload.get('training_id')

            if not training_id:
                return Response({"details": "Select training"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                training = models.TrainingMaterial.objects.get(id=training_id)
            except Exception as e:
                return Response({"details": "Unknown training"}, status=status.HTTP_400_BAD_REQUEST)
            
            raw = {
                "training" : training,
                "user": request.user,
                "assigned_by": request.user
            }
            models.TrainingAssignment.objects.create(**raw)
            
            return Response('success', status=status.HTTP_200_OK)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            department_id = request.query_params.get('department_id')
            training_id = request.query_params.get('training_id')
            r_status = request.query_params.get('status')
            query = request.query_params.get('q')
            slim = request.query_params.get('slim')

            filters = Q(is_deleted=False)

            if training_id:
                filters &= Q(training=training_id)

            if department_id:
                filters &= Q(training__department=department_id)

            if r_status:
                is_complete = True if r_status == 'COMPLETE' else False
                filters &= Q(is_completed=is_complete)

            if query:
                filters &= (
                                Q(title__icontains=query) |
                                Q(uid__icontains=query) |
                                Q(department__name__icontains=query)
                            )

            if request_id:
                try:
                    resp = models.TrainingAssignment.objects.get(Q(id=request_id))

                    if slim:
                        resp = serializers.SlimFetchTrainingAssignmentSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.FetchTrainingAssignmentSerializer(resp, many=False, context={"user_id":request.user.id}).data

                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request!"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
                   
                
            else:
                try:

                    if any(role in ['SUPERUSER','CTP_ADMIN', 'HR'] for role in roles):

                        if filters:
                            resp = models.TrainingAssignment.objects.filter(
                                    filters
                                ).order_by('-date_created')
                        else:
                            resp = models.TrainingAssignment.objects.filter(is_deleted=False).order_by('-date_created')

                    elif any(role in ['HOD'] for role in roles):
                        try:
                            dept = (Hods.objects.get(hod=request.user)).department
                        except:
                            return Response({"details": "HOD role not understood"}, status=status.HTTP_400_BAD_REQUEST)
                        
                        if filters:
                            filters |= (Q(training__department=dept) | Q(assigned_by=request.user))
                            resp = models.TrainingAssignment.objects.filter(
                                    filters
                                ).order_by('-date_created')
                        else:
                            try:
                                resp = models.TrainingAssignment.objects.filter(
                                Q(training__department=dept) | Q(assigned_by=request.user),
                                is_deleted=False).order_by('-date_created')
                            except:
                                resp = []                        

                    else:
                        if filters:
                            filters &= Q(user=request.user)
                            resp = models.TrainingAssignment.objects.filter(
                                    filters
                                ).order_by('-date_created')
                        else:
                            resp = models.TrainingAssignment.objects.filter(Q(is_deleted=False) & (Q(user=request.user)) ).order_by('-date_created')
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request !"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
                
            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(resp, request)
            serializer = serializers.FetchTrainingAssignmentSerializer(
                result_page, many=True, context={"user_id":request.user.id})
            return paginator.get_paginated_response(serializer.data)
        
        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.TrainingAssignment.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)    
                except Exception as e:
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)          


    @action(methods=["POST", "GET", "DELETE"],
            detail=False,
            url_path="upload-certificate",
            url_name="upload-certificate")
    def upload_certificate(self, request):
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
            
           
            # serialize training payload
            serializer = serializers.UploadFileSerializer(
                    data=payload, many=False)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            training_id = payload['training_id']

            try:
                targetInstance = models.TrainingAssignment.objects.get(training=training_id,user=request.user)
            except Exception as e:
                return Response({"details": "No assignment"}, status=status.HTTP_400_BAD_REQUEST)
                    
            with transaction.atomic():
                f = request.FILES.getlist('documents')[0]
                targetInstance.certificate = f
                targetInstance.is_completed = True
                targetInstance.date_completed =  date.today()
                targetInstance.save()
     
            user_util.log_account_activity(
                authenticated_user, authenticated_user, "Certificate uploaded", f"Assignment Id: {targetInstance.id}")
            
            return Response('success', status=status.HTTP_200_OK)

        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            training_id = request.query_params.get('training_id')
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
                
            elif training_id:
                try:
                    resp = models.Document.objects.get(Q(training=training_id))

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
                        Q(training__uid__icontains=query) |
                        Q(training__title__icontains=query) |
                        Q(training__department__name__icontains=query)
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

                    if any(role in ['SUPERUSER','HR','CTP_ADMIN'] for role in roles):

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
            
           
            # serialize training payload
            serializer = serializers.UploadFileSerializer(
                    data=payload, many=False)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            training_id = payload['training_id']
            file_type = payload['file_type']

            try:
                targetInstance = models.TrainingMaterial.objects.get(id=training_id)
            except Exception as e:
                return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                    
            with transaction.atomic():
                # create contract instance

                for f in request.FILES.getlist('documents'):
                    try:
                        original_file_name = f.name.upper()                        
                        models.Document.objects.create(
                            document=f,
                            file_name=original_file_name, 
                            file_type=file_type, 
                            contract=targetInstance, 
                            uploaded_by=request.user
                        )

                    except Exception as e:
                        logger.error(e)
                        print(e)
                        return Response({"details": "Error saving files"}, status=status.HTTP_400_BAD_REQUEST)  
                

            user_util.log_account_activity(
                authenticated_user, authenticated_user, "File uploaded", f"TrainingMaterial Id: {targetInstance.id}")
            
            return Response('success', status=status.HTTP_200_OK)

        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            training_id = request.query_params.get('training_id')
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
                
            elif training_id:
                try:
                    resp = models.Document.objects.get(Q(training=training_id))

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
                        Q(training__uid__icontains=query) |
                        Q(training__title__icontains=query) |
                        Q(training__department__name__icontains=query)
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

                    if any(role in ['SUPERUSER','HR','CTP_ADMIN'] for role in roles):

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
                assign_role = user_util.award_role('CTP_ADMIN', str(admin.id))
                if not assign_role:
                    return Response({"details": "Unable to assign role CTP_ADMIN"}, status=status.HTTP_400_BAD_REQUEST)
                
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
                    user_util.revoke_role('CTP_ADMIN', str(user.admin.id))
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
            url_path="general",
            url_name="general")
    def general(self, request):
                    
        department = request.query_params.get('department')
        training = request.query_params.get('training')
        r_status = request.query_params.get('status')

        q_filters = Q()

        if department:
            q_filters &= Q(user__srrs_department=department)

        if training:
            q_filters &= Q(training=training)

        if r_status:
            r_status = True if r_status == 'COMPLETE' else False
            q_filters &= Q(is_completed=r_status)

        if q_filters:
            resp = models.TrainingAssignment.objects.filter(
                Q(is_deleted=False) & q_filters).order_by('-date_created')
        else:
            resp = models.TrainingAssignment.objects.filter(
                Q(is_deleted=False)).order_by('-date_created')[:50]


        resp = serializers.FetchTrainingAssignmentSerializer(
            resp, many=True, context={"user_id":request.user.id}).data

        return Response(resp, status=status.HTTP_200_OK)


    @action(methods=["GET",],
            detail=False,
            url_path="departmental",
            url_name="departmental")
    def department_training_report(self, request):
        """
        Aggregated report for a department with per-training breakdown.
        """
        department_id = request.query_params.get('department') or None
        training_id = request.query_params.get('training') or None

        if not department_id:
            return Response({"details": "Department required"}, status=status.HTTP_400_BAD_REQUEST)


        filters = Q()

        if department_id:
            filters &= Q(user__srrs_department=department_id)

        if training_id:
            filters &= Q(training=training_id)

        total = models.TrainingAssignment.objects.filter(filters).count()
        completed = models.TrainingAssignment.objects.filter(
            user__srrs_department=department_id, is_completed=True
        ).count()
        pending = total - completed

        # Per-training breakdown
        breakdown = (
            models.TrainingAssignment.objects.filter(filters)
            .values(
                training_uid=F("training__pk"), 
                training_title=F("training__title"),
                user_uid=F("user__id"),
                user_name=Concat(F("user__first_name"), Value(" "), F("user__last_name"))
            )
            .annotate(
                total_assigned=Count("id"),
                completed=Count("id", filter=Q(is_completed=True)),
            )
            .annotate(pending=F("total_assigned") - F("completed"))
            .annotate(
                completion_rate=F("completed") * 100.0 / F("total_assigned")
            )
        )

        return Response(
            {
                "department_id": department_id,
                "total_assignments": total,
                "completed": completed,
                "pending": pending,
                "completion_rate": (completed / total * 100) if total > 0 else 0,
                "per_training": list(breakdown),
            }, status=status.HTTP_200_OK
        )
    
        
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

        total = models.TrainingMaterial.objects.filter(Q(is_deleted=False)).count()
        almost = models.TrainingMaterial.objects.filter(Q(is_deleted=False),expiry_date__gte=now, expiry_date__lte=four_months_from_now).count()
        expired = models.TrainingMaterial.objects.filter(Q(is_deleted=False),expiry_date__lt=now).count()
        renewed = models.TrainingMaterial.objects.filter(Q(is_deleted=False)).exclude(previous__isnull=False).count()

        resp = {
            "total": total,
            "almost": almost,
            "expired": expired,
            "renewed": renewed,
        }

        return Response(resp, status=status.HTTP_200_OK)
    
  
    @action(methods=["GET",],
            detail=False,
            url_path="type-summary",
            url_name="type-summary")
    def type_analytic(self, request):
        """_summary_
            Training type
        Args:
            request (_type_): _description_

        Returns:
            _type_: _description_
        """
        mandatory = models.TrainingMaterial.objects.filter(Q(type="MANDATORY")).count()
        optional = models.TrainingMaterial.objects.filter(Q(type="OPTIONAL")).count()

        resp = {
            "mandatory": mandatory,
            "optional": optional
        }

        return Response(resp, status=status.HTTP_200_OK)
    
    
    @action(methods=["GET",],
            detail=False,
            url_path="summary",
            url_name="summary")
    def summary(self, request):
        """
            Dashboard summary view for training platform.
        """
        # Filters
        active_materials = models.TrainingMaterial.objects.filter(is_deleted=False)
        active_assignments = models.TrainingAssignment.objects.filter(is_deleted=False)

        # Time Filter (Last 6 months)
        six_months_ago = timezone.now().date() - timedelta(days=180)

        # Base stats
        total_materials = active_materials.count()
        total_assignments = active_assignments.count()
        completed_assignments = active_assignments.filter(is_completed=True).count()
        overdue_assignments = active_assignments.filter(
            is_completed=False, 
            completion_date__lt=timezone.now().date()
        ).count()

        completion_rate = (
            (completed_assignments / total_assignments) * 100
            if total_assignments > 0 else 0
        )

        # Materials per Department
        materials_by_department = active_materials.values('department__name').annotate(
            count=Count('id')
        )

        # Assignments per Department (via user)
        assignments_by_department = active_assignments.values(
            'user__department__name'
        ).annotate(count=Count('id'))

        # Completion Trend (last 6 months)
        completions_over_time = active_assignments.filter(
            is_completed=True,
            date_completed__gte=six_months_ago
        ).extra(select={'month': "DATE_TRUNC('month', date_completed)"}).values('month').annotate(
            count=Count('id')
        ).order_by('month')

        return Response({
            "summary": {
                "total_training_materials": total_materials,
                "total_assignments": total_assignments,
                "completed_assignments": completed_assignments,
                "completion_rate": round(completion_rate, 2),
                "overdue_assignments": overdue_assignments,
            },
            "materials_by_department": list(materials_by_department),
            "assignments_by_department": list(assignments_by_department),
            "completions_over_time": [
                {"month": item["month"].strftime("%Y-%m"), "count": item["count"]}
                for item in completions_over_time
            ]
        })
    

    @action(methods=["GET",],
            detail=False,
            url_path="completion-report",
            url_name="completion-report")
    def completion_report(self,request):
        """
        Combined report:
        - Trend over time
        - Department breakdown (with completion rate)
        - Training breakdown (with completion rate)
        """
        period = request.GET.get("period", "month")
        department_id = request.GET.get("department_id")
        training_id = request.GET.get("training_id")

        # Choose grouping function
        if period == "day":
            trunc_func = TruncDay("date_completed")
        elif period == "week":
            trunc_func = TruncWeek("date_completed")
        else:
            trunc_func = TruncMonth("date_completed")

        # Base queryset
        qs = models.TrainingAssignment.objects.all()

        # Apply filters
        if department_id:
            qs = qs.filter(user__department_id=department_id)
        if training_id:
            qs = qs.filter(training_id=training_id)

        # --- 1. Trend over time (completed only)
        trend_data = (
            qs.filter(is_completed=True)
            .annotate(period=trunc_func)
            .values("period")
            .annotate(total_completed=Count("id"))
            .order_by("period")
        )
        trend = [
            {
                "period": entry["period"].strftime("%Y-%m-%d"),
                "total_completed": entry["total_completed"],
            }
            for entry in trend_data
        ]

        # --- 2. Breakdown by department (completion rate)
        dept_data = (
            qs.values("user__department__id", "user__department__name")
            .annotate(
                total_assigned=Count("id"),
                total_completed=Count("id", filter=Q(is_completed=True)),
            )
            .order_by("user__department__name")
        )
        department_breakdown = [
            {
                "department_id": entry["user__department__id"],
                "department_name": entry["user__department__name"],
                "total_assigned": entry["total_assigned"],
                "total_completed": entry["total_completed"],
                "completion_rate": round(
                    (entry["total_completed"] / entry["total_assigned"]) * 100, 2
                ) if entry["total_assigned"] > 0 else 0,
            }
            for entry in dept_data
        ]

        # --- 3. Breakdown by training (completion rate)
        training_data = (
            qs.values("training__id", "training__title")
            .annotate(
                total_assigned=Count("id"),
                total_completed=Count("id", filter=Q(is_completed=True)),
            )
            .order_by("training__title")
        )
        training_breakdown = [
            {
                "training_id": entry["training__id"],
                "training_title": entry["training__title"],
                "total_assigned": entry["total_assigned"],
                "total_completed": entry["total_completed"],
                "completion_rate": round(
                    (entry["total_completed"] / entry["total_assigned"]) * 100, 2
                ) if entry["total_assigned"] > 0 else 0,
            }
            for entry in training_data
        ]

        return Response({
            "trend": trend,
            "department_breakdown": department_breakdown,
            "training_breakdown": training_breakdown,
        })