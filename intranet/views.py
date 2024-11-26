import calendar
from collections import OrderedDict
import datetime
import json
import logging
import uuid
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.contrib.auth import get_user_model
from django.db.models import  Q
from django.db import transaction
from acl.serializers import SlimFetchSRRSDepartmentSerializer
from intranet import models
from intranet import serializers
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import User, Sendmail, SRRSDepartment
from intranet.utils import shared_fxns
from django.db.models import Sum
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import Group

from rest_framework.pagination import PageNumberPagination

# Get an instance of a logger
logger = logging.getLogger(__name__)

class GenericsViewSet(viewsets.ViewSet):
    permission_classes = (AllowAny,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["GET"], detail=False, url_path="links",url_name="links")
    def links(self, request):

        resp = models.QuickLink.objects.filter(Q(is_deleted=False)).order_by('title')
        
        paginator = PageNumberPagination()
        paginator.page_size = 50
        result_page = paginator.paginate_queryset(resp, request)
        serializer = serializers.SlimFetchQuickLinkSerializer(
            result_page, many=True, context={"user_id":request.user.id})
        
        return paginator.get_paginated_response(serializer.data)
    
    
    @action(methods=["GET"], detail=False, url_path="departments",url_name="departments")
    def departments(self, request):

        resp = models.SRRSDepartment.objects.all().order_by('name')
        serializer = serializers.FullFetchDepartmentSerializer(
            resp, many=True, context={"user_id":request.user.id})
        
        return Response(serializer.data, status=status.HTTP_200_OK)

    
    @action(methods=["GET"], detail=False, url_path="files",url_name="files")
    def files(self, request):
        department_id = request.query_params.get('department_id')
        if department_id:
            documents = models.Document.objects.filter(
                Q(department=department_id) | 
                Q(sub_department=department_id) | 
                Q(category=department_id), is_deleted=False).order_by('original_file_name')
        else:
            documents = []
        

        paginator = PageNumberPagination()
        paginator.page_size = 50
        result_page = paginator.paginate_queryset(documents, request)
        serializer = serializers.SlimFetchDocumentSerializer(
            result_page, many=True)
        
        return paginator.get_paginated_response(serializer.data)
    
    @action(methods=["GET"], detail=False, url_path="qips-files",url_name="qips-files")
    def qips_files(self, request):
        request_id = request.query_params.get('request_id')
        if request_id:
            documents = models.QipsDocument.objects.filter(
                Q(topic=request_id) | 
                Q(sub_topic=request_id) | 
                Q(category=request_id) ,is_deleted=False).order_by('file_name')
        else:
            documents = []
        

        paginator = PageNumberPagination()
        paginator.page_size = 50
        result_page = paginator.paginate_queryset(documents, request)
        serializer = serializers.SlimFetchQipsDocumentSerializer(
            result_page, many=True)
        
        return paginator.get_paginated_response(serializer.data)
    
    @action(methods=["POST"], detail=False, url_path="downloads",url_name="downloads")
    def downloads(self, request):
        payload = request.data
        try:
            request_id = payload['request_id']
            document = models.Document.objects.get(id=request_id)
        except:
            return Response("200", status=status.HTTP_200_OK)
        
        count = int(document.downloads)
        count += 1
        
        with transaction.atomic():
            try:
                document.downloads = count
                document.save()  
                return Response("200", status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)
            
    @action(methods=["POST"], detail=False, url_path="qips-downloads",url_name="qips-downloads")
    def qips_downloads(self, request):
        payload = request.data
        try:
            request_id = payload['request_id']
            document = models.QipsDocument.objects.get(id=request_id)
        except:
            return Response("200", status=status.HTTP_200_OK)
        
        count = int(document.downloads)
        count += 1
        
        with transaction.atomic():
            try:
                document.downloads = count
                document.save()  
                return Response("200", status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)
            
    
    @action(methods=["GET"], detail=False, url_path="qips",url_name="qips")
    def qips(self, request):

        resp = models.Qips.objects.filter(Q(is_deleted=False)).order_by('topic')
        serializer = serializers.FullFetchQipsSerializer(
                    resp, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(methods=["GET"], detail=False, url_path="surveys",url_name="surveys")
    def surveys(self, request):

        resp = models.Survey.objects.filter(Q(is_deleted=False)).order_by('topic')
        serializer = serializers.FullFetchSurveySerializer(
                    resp, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(methods=["GET"], detail=False, url_path="survey-links",url_name="survey-links")
    def survey_links(self, request):
        request_id = request.query_params.get('request_id')
        if request_id:
            links = models.SurveyLink.objects.filter(Q(topic=request_id) | Q(sub_topic=request_id) | Q(category=request_id) ,is_deleted=False)
        else:
            links = []
        

        paginator = PageNumberPagination()
        paginator.page_size = 50
        result_page = paginator.paginate_queryset(links, request)
        serializer = serializers.SlimFetchSurveyLinkSerializer(
            result_page, many=True)
        
        return paginator.get_paginated_response(serializer.data)
    
    @action(methods=["GET"], detail=False, url_path="modules",url_name="modules")
    def modules(self, request):

        resp = models.Module.objects.filter(Q(is_deleted=False)).order_by('topic')
        serializer = serializers.FullFetchModuleSerializer(
                    resp, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(methods=["GET"], detail=False, url_path="module-links",url_name="module-links")
    def module_links(self, request):
        request_id = request.query_params.get('request_id')
        if request_id:
            links = models.ModuleLink.objects.filter(Q(topic=request_id) | Q(sub_topic=request_id) | Q(category=request_id) ,is_deleted=False)
        else:
            links = []
        

        paginator = PageNumberPagination()
        paginator.page_size = 50
        result_page = paginator.paginate_queryset(links, request)
        serializer = serializers.SlimFetchModuleLinkSerializer(
            result_page, many=True)
        
        return paginator.get_paginated_response(serializer.data)
    
class DocumentManagerViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["POST","PUT","DELETE", "GET"], detail=False, url_path="files",url_name="files")
    def files(self, request):
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            uploaded_files = request.FILES
            if not uploaded_files:
                return Response({"details": f"No files attached"}, status=status.HTTP_400_BAD_REQUEST)

            payload = json.loads(request.data['payload'])

            serializer = serializers.UploadDocumentSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                title = payload.get('title')
                category = payload.get('category') or None
                sub_department = payload.get('sub_department') or None
                department = payload['department']

                try:
                    department = SRRSDepartment.objects.get(id=department)
                except Exception as e:
                    return Response({"details": "Unknown department"}, status=status.HTTP_400_BAD_REQUEST)
                
                if sub_department:
                    try:
                        sub_department = models.SubDepartment.objects.get(id=sub_department)
                    except Exception as e:
                        return Response({"details": "Unknown sub department"}, status=status.HTTP_400_BAD_REQUEST)
                    
                if category:
                    try:
                        category = models.SubDepartmentCategory.objects.get(id=category)
                    except Exception as e:
                        return Response({"details": "Unknown category"}, status=status.HTTP_400_BAD_REQUEST)
            

                exts = ['pdf']
                for f in request.FILES.getlist('documents'):
                    original_file_name = f.name
                    ext = original_file_name.split('.')[1].strip().lower()
                    if ext not in exts:
                        return Response({"details": f"{original_file_name} not allowed. Only Images, PDFs allowed for upload!"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    total_files = 1
                    for f in request.FILES.getlist('documents'):
                        try:
                            original_file_name = f.name.split('.')[0]                            
                            models.Document.objects.create(
                                document=f,
                                original_file_name=original_file_name, 
                                title=title, 
                                department=department,
                                sub_department=sub_department,
                                category=category,
                                uploaded_by=request.user
                            )
                        except Exception as e:
                            logger.error(e)
                            print(e)
                            return Response({"details": "Error saving files"}, status=status.HTTP_400_BAD_REQUEST)  
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":

            payload = request.data

            serializer = serializers.UpdateDocumentSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['id']
                name = payload['name']

                try:
                    document = models.Document.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():
                    document.original_file_name = name
                    document.save()
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":

            request_id = request.query_params.get('request_id')
            department_id = request.query_params.get('department_id')

            if request_id:
                documents = models.Document.objects.get(Q(id=request_id) & Q(is_deleted=False))

            elif department_id:
            
                documents = models.Document.objects.filter(Q(department=department_id) & Q(is_deleted=False))
            
            else:
                if "SUPERUSER" in roles or "ICT" in roles:
                    documents = models.Document.objects.filter(Q(is_deleted=False)).order_by('original_file_name')
                else:
                    documents = models.Document.objects.filter(Q(department=request.user.srrs_department) & Q(is_deleted=False)).order_by('original_file_name')
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(documents, request)
            serializer = serializers.FetchDocumentSerializer(
                result_page, many=True, context={"user_id":request.user.id})
            
            return paginator.get_paginated_response(serializer.data)
                 
        elif request.method == "DELETE":

            request_id = request.query_params.get('request_id')
            request_ids = request.query_params.get('request_ids')

            if not request_id and not request_ids:
                return Response({"details": "Cannot complete request !"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    if request_ids:
                        request_ids = json.loads(request_ids)
                        models.Document.objects.filter(Q(id__in=request_ids)).update(**raw)
                    else:
                        models.Document.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)
                

    @action(methods=["GET",],
            detail=False,
            url_path="search-files",
            url_name="search-files")
    def search_files(self, request):
                    
        department = request.query_params.get('department')
        sub_department = request.query_params.get('sub_department')
        title = request.query_params.get('title')
        category = request.query_params.get('category')

        q_filters = Q()

        if department:
            q_filters &= Q(department=department)

        if sub_department:
            q_filters &= Q(sub_department=sub_department)

        if category:
            q_filters &= Q(category=category)

        if title:
            q_filters &= Q(original_file_name__icontains=title)


        if q_filters:
            resp = models.Document.objects.filter(Q(is_deleted=False) & q_filters).order_by('original_file_name')
        else:
            resp = models.Document.objects.filter(Q(is_deleted=False)).order_by('original_file_name')


        paginator = PageNumberPagination()
        paginator.page_size = 5000
        result_page = paginator.paginate_queryset(resp, request)
        serializer = serializers.FetchDocumentSerializer(
            result_page, many=True, context={"user_id":request.user.id})
        
        return paginator.get_paginated_response(serializer.data)

    @action(methods=["POST","PUT","DELETE", "GET"], detail=False, url_path="qips-files",url_name="qips-files")
    def qips_files(self, request):
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            uploaded_files = request.FILES
            if not uploaded_files:
                return Response({"details": f"No files attached"}, status=status.HTTP_400_BAD_REQUEST)

            payload = json.loads(request.data['payload'])

            serializer = serializers.UploadQipsDocumentSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                category = payload.get('category') or None
                sub_topic = payload.get('sub_topic') or None
                topic = payload['topic']

                try:
                    topic = models.Qips.objects.get(id=topic)
                except Exception as e:
                    return Response({"details": "Unknown topic"}, status=status.HTTP_400_BAD_REQUEST)
                
                if sub_topic:
                    try:
                        sub_topic = models.QipsSubTopic.objects.get(id=sub_topic)
                    except Exception as e:
                        return Response({"details": "Unknown sub topic"}, status=status.HTTP_400_BAD_REQUEST)
                    
                if category:
                    try:
                        category = models.QipsCategory.objects.get(id=category)
                    except Exception as e:
                        return Response({"details": "Unknown category"}, status=status.HTTP_400_BAD_REQUEST)
            
                exts = ['pdf']
                for f in request.FILES.getlist('documents'):
                    original_file_name = f.name
                    ext = original_file_name.split('.')[1].strip().lower()
                    if ext not in exts:
                        return Response({"details": f"{original_file_name} not allowed. Only PDFs allowed for upload!"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    for f in request.FILES.getlist('documents'):
                        try:

                            original_file_name = f.name.split('.')[0]                            
                            models.QipsDocument.objects.create(
                                document=f,
                                file_name=original_file_name, 
                                topic=topic, 
                                sub_topic=sub_topic, 
                                category=category,
                                uploaded_by=request.user
                            )

                        except Exception as e:
                            logger.error(e)
                            print(e)
                            return Response({"details": "Error saving files"}, status=status.HTTP_400_BAD_REQUEST)  
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":

            payload = request.data

            serializer = serializers.UpdateDocumentSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['id']
                name = payload['name']

                try:
                    document = models.Document.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():
                    document.original_file_name = name
                    document.save()
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":

            request_id = request.query_params.get('request_id')
            topic_id = request.query_params.get('topic_id')
            sub_topic_id = request.query_params.get('sub_topic_id')
            category_id = request.query_params.get('category_id')

            if request_id:
                documents = models.QipsDocument.objects.get(Q(id=request_id) & Q(is_deleted=False))

            elif topic_id:
                documents = models.QipsDocument.objects.filter(Q(topic=topic_id) & Q(is_deleted=False))

            elif sub_topic_id:
                documents = models.QipsDocument.objects.filter(Q(sub_topic=sub_topic_id) & Q(is_deleted=False))
            
            elif category_id:
                documents = models.QipsDocument.objects.filter(Q(category=category_id) & Q(is_deleted=False))

            else:
                documents = models.QipsDocument.objects.filter(Q(is_deleted=False))
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(documents, request)
            serializer = serializers.FetchQipsDocumentSerializer(
                result_page, many=True, context={"user_id":request.user.id})
            
            return paginator.get_paginated_response(serializer.data)
            
            
        elif request.method == "DELETE":

            request_id = request.query_params.get('request_id')
            request_ids = request.query_params.get('request_ids')

            if not request_id and not request_ids:
                return Response({"details": "Cannot complete request !"}, 
                                status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    if request_ids:
                        request_ids = json.loads(request_ids)
                        models.QipsDocument.objects.filter(Q(id__in=request_ids)).update(**raw)
                    else:
                        models.QipsDocument.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)
                            
    @action(methods=["GET",],
            detail=False,
            url_path="search-qips-files",
            url_name="search-qips-files")
    def search_qips_files(self, request):
                    
        topic = request.query_params.get('topic')
        sub_topic = request.query_params.get('sub_topic')
        file_name = request.query_params.get('file_name')
        category = request.query_params.get('category')

        q_filters = Q()

        if topic:
            q_filters &= Q(topic=topic)

        if sub_topic:
            q_filters &= Q(sub_topic=sub_topic)

        if category:
            q_filters &= Q(category=category)

        if file_name:
            q_filters &= Q(file_name__icontains=file_name)


        if q_filters:
            resp = models.QipsDocument.objects.filter(Q(is_deleted=False) & q_filters).order_by('file_name')
        else:
            resp = models.QipsDocument.objects.filter(Q(is_deleted=False)).order_by('file_name')


        paginator = PageNumberPagination()
        paginator.page_size = 5000
        result_page = paginator.paginate_queryset(resp, request)
        serializer = serializers.FetchQipsDocumentSerializer(
            result_page, many=True, context={"user_id":request.user.id})
        
        return paginator.get_paginated_response(serializer.data)
       
    @action(methods=["POST"], detail=False, url_path="qips-downloads",url_name="qips-downloads")
    def qips_downloads(self, request):
        roles = user_util.fetchusergroups(request.user.id) 
        payload = request.data
        try:
            request_id = payload['request_id']
            document = models.QipsDocument.objects.get(id=request_id)
        except:
            return Response({"details": "Unknown request id"}, status=status.HTTP_400_BAD_REQUEST)
        
        count = int(document.downloads)
        count += 1
        
        with transaction.atomic():
            try:
                document.downloads = count
                document.save()  
                return Response("200", status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)
                       
class QuickLinksViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["POST","PUT","DELETE", "GET"], detail=False, url_path="links",url_name="links")
    def links(self, request):
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.QuickLinkSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                title = payload['title']
                link = payload['link']

                
                with transaction.atomic():
                    models.QuickLink.objects.create(
                        title=title,
                        link=link,
                        created_by=request.user
                    )
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":

            payload = request.data

            serializer = serializers.UpdateQuickLinkSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                title = payload['title']
                link = payload['link']

                try:
                    quickLink = models.QuickLink.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():
                    quickLink.title = title
                    quickLink.link = link

                    quickLink.save()
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

        elif request.method == "GET":

            request_id = request.query_params.get('request_id')

            if request_id:
                resp = models.QuickLink.objects.get(Q(id=request_id) & Q(is_deleted=False))
            
            else:
                resp = models.QuickLink.objects.filter(Q(is_deleted=False))
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(resp, request)
            serializer = serializers.SlimFetchQuickLinkSerializer(
                result_page, many=True, context={"user_id":request.user.id})
            
            return paginator.get_paginated_response(serializer.data)
            
            
        elif request.method == "DELETE":

            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.QuickLink.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)
                

class QipsViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["POST","PUT","DELETE", "GET"], detail=False, url_path="topics",url_name="topics")
    def topics(self, request):
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.QipsSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                topics = payload['topic']
                
                with transaction.atomic():
                    for topic in topics:
                        models.Qips.objects.create(
                            topic=topic,
                            created_by=request.user
                        )
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":

            payload = request.data

            serializer = serializers.UpdateQipsSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                topic = payload['topic']

                try:
                    topicInstance = models.Qips.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():
                    topicInstance.topic = topic
                    topicInstance.save()
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

        elif request.method == "GET":

            request_id = request.query_params.get('request_id')
            serializer = request.query_params.get('serializer')

            if request_id:
                resp = models.Qips.objects.get(Q(id=request_id) & Q(is_deleted=False))
            
            else:
                resp = models.Qips.objects.filter(Q(is_deleted=False))
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(resp, request)
            if serializer == 'full':
                serializer = serializers.FullFetchQipsSerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            else:
                serializer = serializers.SlimFetchQipsSerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            
            return paginator.get_paginated_response(serializer.data)
            
            
        elif request.method == "DELETE":

            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.Qips.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)
                

    @action(methods=["POST","PUT","DELETE", "GET"], detail=False, url_path="sub-topics",url_name="sub-topics")
    def sub_topics(self, request):
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.QipsSubTopicSerializer(
                    data=payload, many=False)
            

            if serializer.is_valid():
                qips = payload['topic']
                sub_topics = payload['sub_topic']

                try:
                    qipsInstance = models.Qips.objects.get(id=qips)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    for sub_topic in sub_topics:
                        models.QipsSubTopic.objects.create(
                            qips=qipsInstance,
                            sub_topic=sub_topic
                        )
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":

            payload = request.data

            serializer = serializers.UpdateQipsSubTopicSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                sub_topic = payload['sub_topic']

                try:
                    topicInstance = models.QipsSubTopic.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():
                    topicInstance.sub_topic = sub_topic
                    topicInstance.save()
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

        elif request.method == "GET":

            request_id = request.query_params.get('request_id')
            serializer = request.query_params.get('serializer')

            if request_id:
                resp = models.QipsSubTopic.objects.get(Q(id=request_id) & Q(is_deleted=False))
            
            else:
                resp = models.QipsSubTopic.objects.filter(Q(is_deleted=False))
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(resp, request)
            if serializer == 'full':
                serializer = serializers.FetchQipsSubTopicSerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            else: 
                serializer = serializers.SlimFetchQipsSubTopicSerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            
            return paginator.get_paginated_response(serializer.data)
            
            
        elif request.method == "DELETE":

            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.QipsSubTopic.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)
                

    @action(methods=["POST","PUT","DELETE", "GET"], detail=False, url_path="categories",url_name="categories")
    def categories(self, request):
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.QipsCategorySerializer(
                    data=payload, many=False)
            

            if serializer.is_valid():
                categories = payload['category']
                sub_topic = payload['sub_topic']

                try:
                    sub_topicInstance = models.QipsSubTopic.objects.get(id=sub_topic)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    for category in categories:
                        models.QipsCategory.objects.create(
                            category=category,
                            sub_topic=sub_topicInstance
                        )
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":

            payload = request.data

            serializer = serializers.UpdateQipsCategorySerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                category = payload['category']
                # sub_topic = payload['topic']

                try:
                    categoryInstance = models.QipsCategory.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():
                    categoryInstance.category = category
                    categoryInstance.save()
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

        elif request.method == "GET":

            request_id = request.query_params.get('request_id')
            serializer = request.query_params.get('serializer')

            if request_id:
                resp = models.QipsCategory.objects.get(Q(id=request_id) & Q(is_deleted=False))
            
            else:
                resp = models.QipsCategory.objects.filter(Q(is_deleted=False))
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(resp, request)
            if serializer == 'full':
                serializer = serializers.FetchQipsCategorySerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            else:
                serializer = serializers.SlimFetchQipsCategorySerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            
            return paginator.get_paginated_response(serializer.data)
            
            
        elif request.method == "DELETE":

            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.QipsCategory.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)

class DepartmentsViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["POST","PUT","DELETE", "GET"], detail=False, url_path="sub-departments",url_name="sub-departments")
    def sub_departments(self, request):
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.SubDepartmentSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                department_id = payload['department_id']
                sub_departments = payload['sub_departments']

                try:
                    departmentInstance = models.SRRSDepartment.objects.get(id=department_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid department'}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    for sub_department in sub_departments:
                        models.SubDepartment.objects.create(
                            name=sub_department,
                            department=departmentInstance,
                            created_by=request.user
                        )
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":

            payload = request.data

            serializer = serializers.UpdateSubDepartmentSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                sub_department = payload['sub_department']

                try:
                    sub_departmentInstance = models.SubDepartment.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid sub department'}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():
                    sub_departmentInstance.name = sub_department
                    sub_departmentInstance.save()
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

        elif request.method == "GET":

            request_id = request.query_params.get('request_id')
            serializer = request.query_params.get('serializer')

            if request_id:
                resp = models.SubDepartment.objects.get(Q(id=request_id) & Q(is_deleted=False))
            
            else:
                resp = models.SubDepartment.objects.filter(Q(is_deleted=False))
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(resp, request)
            if serializer == 'full':
                serializer = serializers.FetchSubDepartmentSerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            else:
                serializer = serializers.SlimFetchSubDepartmentSerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            
            return paginator.get_paginated_response(serializer.data)
            
            
        elif request.method == "DELETE":

            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.SubDepartment.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)
                

    @action(methods=["POST","PUT","DELETE", "GET"], detail=False, url_path="sub-department-categories",url_name="sub-department-categories")
    def sub_department_categories(self, request):
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.SubDepartmentCategoriesSerializer(
                data=payload, many=False)
            

            if serializer.is_valid():
                sub_department_id = payload['sub_department_id']
                categories = payload['category']

                try:
                    sub_departmentInstance = models.SubDepartment.objects.get(id=sub_department_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    for category in categories:
                        models.SubDepartmentCategory.objects.create(
                            sub_department=sub_departmentInstance,
                            name=category,
                            created_by=request.user
                        )
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":

            payload = request.data

            serializer = serializers.UpdateSubDepartmentCategoriesSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                category = payload['category']

                try:
                    categoryInstance = models.SubDepartmentCategory.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():
                    categoryInstance.name = category
                    categoryInstance.save()
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

        elif request.method == "GET":

            request_id = request.query_params.get('request_id')
            serializer = request.query_params.get('serializer')

            if request_id:
                resp = models.SubDepartmentCategory.objects.get(Q(id=request_id) & Q(is_deleted=False))
            
            else:
                resp = models.SubDepartmentCategory.objects.filter(Q(is_deleted=False))
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(resp, request)
            if serializer == 'full':
                serializer = serializers.FetchSubDepartmentCategorySerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            else: 
                serializer = serializers.SlimFetchSubDepartmentCategorySerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            
            return paginator.get_paginated_response(serializer.data)
            
            
        elif request.method == "DELETE":

            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.SubDepartmentCategory.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)
                

class SurveyViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["POST","PUT","DELETE", "GET"], detail=False, url_path="topics",url_name="topics")
    def topics(self, request):
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.SurveySerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                topics = payload['topic']
                
                with transaction.atomic():
                    for topic in topics:
                        models.Survey.objects.create(
                            topic=topic,
                            created_by=request.user
                        )
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":

            payload = request.data

            serializer = serializers.UpdateSurveySerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                topic = payload['topic']

                try:
                    topicInstance = models.Survey.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():
                    topicInstance.topic = topic
                    topicInstance.save()
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

        elif request.method == "GET":

            request_id = request.query_params.get('request_id')
            serializer = request.query_params.get('serializer')

            if request_id:
                resp = models.Survey.objects.get(Q(id=request_id) & Q(is_deleted=False))
            else:
                resp = models.Survey.objects.filter(Q(is_deleted=False))
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(resp, request)
            if serializer == 'full':
                serializer = serializers.FullFetchSurveySerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            else:
                serializer = serializers.SlimFetchSurveySerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            
            return paginator.get_paginated_response(serializer.data)
            
            
        elif request.method == "DELETE":

            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.Survey.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)
                

    @action(methods=["POST","PUT","DELETE", "GET"], detail=False, url_path="sub-topics",url_name="sub-topics")
    def sub_topics(self, request):
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.SurveySubTopicSerializer(
                    data=payload, many=False)
            

            if serializer.is_valid():
                survey = payload['topic']
                sub_topics = payload['sub_topic']

                try:
                    surveyInstance = models.Survey.objects.get(id=survey)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    for sub_topic in sub_topics:
                        models.SurveySubTopic.objects.create(
                            survey=surveyInstance,
                            sub_topic=sub_topic
                        )
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":

            payload = request.data

            serializer = serializers.UpdateSurveySubTopicSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                sub_topic = payload['sub_topic']

                try:
                    topicInstance = models.SurveySubTopic.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():
                    topicInstance.sub_topic = sub_topic
                    topicInstance.save()
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

        elif request.method == "GET":

            request_id = request.query_params.get('request_id')
            serializer = request.query_params.get('serializer')

            if request_id:
                resp = models.SurveySubTopic.objects.get(Q(id=request_id) & Q(is_deleted=False))
            
            else:
                resp = models.SurveySubTopic.objects.filter(Q(is_deleted=False))
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(resp, request)
            if serializer == 'full':
                serializer = serializers.FetchSurveySubTopicSerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            else: 
                serializer = serializers.SlimFetchSurveySubTopicSerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            
            return paginator.get_paginated_response(serializer.data)
            
            
        elif request.method == "DELETE":

            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.SurveySubTopic.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)
                

    @action(methods=["POST","PUT","DELETE", "GET"], detail=False, url_path="categories",url_name="categories")
    def categories(self, request):
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.SurveyCategorySerializer(
                    data=payload, many=False)
            

            if serializer.is_valid():
                categories = payload['category']
                sub_topic = payload['sub_topic']

                try:
                    sub_topicInstance = models.SurveySubTopic.objects.get(id=sub_topic)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    for category in categories:
                        models.SurveyCategory.objects.create(
                            category=category,
                            sub_topic=sub_topicInstance
                        )
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":

            payload = request.data

            serializer = serializers.UpdateSurveyCategorySerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                category = payload['category']
                # sub_topic = payload['topic']

                try:
                    categoryInstance = models.SurveyCategory.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():
                    categoryInstance.category = category
                    categoryInstance.save()
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

        elif request.method == "GET":

            request_id = request.query_params.get('request_id')
            serializer = request.query_params.get('serializer')

            if request_id:
                resp = models.SurveyCategory.objects.get(Q(id=request_id) & Q(is_deleted=False))
            
            else:
                resp = models.SurveyCategory.objects.filter(Q(is_deleted=False))
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(resp, request)
            if serializer == 'full':
                serializer = serializers.FetchSurveyCategorySerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            else:
                serializer = serializers.SlimFetchSurveyCategorySerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            
            return paginator.get_paginated_response(serializer.data)
            
            
        elif request.method == "DELETE":

            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.SurveyCategory.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)
                
                
    @action(methods=["POST","PUT","DELETE", "GET"], detail=False, url_path="links",url_name="links")
    def links(self, request):
        # roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.SurveyLinkSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                category = payload.get('category') or None
                sub_topic = payload.get('sub_topic') or None
                topic = payload['topic']
                link = payload['link']

                try:
                    topic = models.Survey.objects.get(id=topic)
                except Exception as e:
                    return Response({"details": "Unknown topic"}, status=status.HTTP_400_BAD_REQUEST)
                
                if sub_topic:
                    try:
                        sub_topic = models.SurveySubTopic.objects.get(id=sub_topic)
                    except Exception as e:
                        return Response({"details": "Unknown sub topic"}, status=status.HTTP_400_BAD_REQUEST)
                    
                if category:
                    try:
                        category = models.SurveyCategory.objects.get(id=category)
                    except Exception as e:
                        return Response({"details": "Unknown category"}, status=status.HTTP_400_BAD_REQUEST)
                    
                # check if already existing
                try:
                    existingLink = models.SurveyLink.objects.get(topic=topic,sub_topic=sub_topic,category=category)
                except (ValidationError, ObjectDoesNotExist):
                    existingLink = None
                except Exception as e:
                    print(e)
                    # logger.error(e)
                    existingLink = None
            

                with transaction.atomic():
                    if existingLink:
                        existingLink.link = link
                        existingLink.save()
                    else:
                        try:                         
                            models.SurveyLink.objects.create(
                                topic=topic, 
                                sub_topic=sub_topic, 
                                category=category,
                                link=link,
                                created_by=request.user
                            )
                        except Exception as e:
                            logger.error(e)
                            # print(e)
                            return Response({"details": "Error saving link"}, status=status.HTTP_400_BAD_REQUEST)  
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":

            payload = request.data

            serializer = serializers.UpdateSurveySerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                link = payload['link']

                try:
                    targetInstance = models.SurveyLink.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():
                    targetInstance.link = link
                    targetInstance.save()
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":

            request_id = request.query_params.get('request_id')
            topic_id = request.query_params.get('topic_id')
            sub_topic_id = request.query_params.get('sub_topic_id')
            category_id = request.query_params.get('category_id')

            if request_id:
                links = models.SurveyLink.objects.get(Q(id=request_id) & Q(is_deleted=False))

            elif topic_id:
                links = models.SurveyLink.objects.filter(Q(topic=topic_id) & Q(is_deleted=False))

            elif sub_topic_id:
                links = models.SurveyLink.objects.filter(Q(sub_topic=sub_topic_id) & Q(is_deleted=False))
            
            elif category_id:
                links = models.SurveyLink.objects.filter(Q(category=category_id) & Q(is_deleted=False))

            else:
                links = models.SurveyLink.objects.filter(Q(is_deleted=False))
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(links, request)
            serializer = serializers.FetchSurveyLinkSerializer(
                result_page, many=True, context={"user_id":request.user.id})
            
            return paginator.get_paginated_response(serializer.data)
            
            
        elif request.method == "DELETE":

            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.SurveyLink.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)


class ModuleViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["POST","PUT","DELETE", "GET"], detail=False, url_path="topics",url_name="topics")
    def topics(self, request):
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.ModuleSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                topics = payload['topic']
                
                with transaction.atomic():
                    for topic in topics:
                        models.Module.objects.create(
                            topic=topic,
                            created_by=request.user
                        )
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":

            payload = request.data

            serializer = serializers.UpdateModuleSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                topic = payload['topic']

                try:
                    topicInstance = models.Module.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():
                    topicInstance.topic = topic
                    topicInstance.save()
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

        elif request.method == "GET":

            request_id = request.query_params.get('request_id')
            serializer = request.query_params.get('serializer')

            if request_id:
                resp = models.Module.objects.get(Q(id=request_id) & Q(is_deleted=False))
            else:
                resp = models.Module.objects.filter(Q(is_deleted=False))
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(resp, request)
            if serializer == 'full':
                serializer = serializers.FullFetchModuleSerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            else:
                serializer = serializers.SlimFetchModuleSerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            
            return paginator.get_paginated_response(serializer.data)
            
            
        elif request.method == "DELETE":

            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.Module.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)
                

    @action(methods=["POST","PUT","DELETE", "GET"], detail=False, url_path="sub-topics",url_name="sub-topics")
    def sub_topics(self, request):
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.ModuleSubTopicSerializer(
                    data=payload, many=False)
            

            if serializer.is_valid():
                module = payload['topic']
                sub_topics = payload['sub_topic']

                try:
                    moduleInstance = models.Module.objects.get(id=module)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    for sub_topic in sub_topics:
                        models.ModuleSubTopic.objects.create(
                            module=moduleInstance,
                            sub_topic=sub_topic
                        )
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":

            payload = request.data

            serializer = serializers.UpdateModuleSubTopicSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                sub_topic = payload['sub_topic']

                try:
                    topicInstance = models.ModuleSubTopic.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():
                    topicInstance.sub_topic = sub_topic
                    topicInstance.save()
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

        elif request.method == "GET":

            request_id = request.query_params.get('request_id')
            serializer = request.query_params.get('serializer')

            if request_id:
                resp = models.ModuleSubTopic.objects.get(Q(id=request_id) & Q(is_deleted=False))
            
            else:
                resp = models.ModuleSubTopic.objects.filter(Q(is_deleted=False))
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(resp, request)
            if serializer == 'full':
                serializer = serializers.FetchModuleSubTopicSerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            else: 
                serializer = serializers.SlimFetchModuleSubTopicSerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            
            return paginator.get_paginated_response(serializer.data)
            
            
        elif request.method == "DELETE":

            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.ModuleSubTopic.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)
                

    @action(methods=["POST","PUT","DELETE", "GET"], detail=False, url_path="categories",url_name="categories")
    def categories(self, request):
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.ModuleCategorySerializer(
                    data=payload, many=False)
            

            if serializer.is_valid():
                categories = payload['category']
                sub_topic = payload['sub_topic']

                try:
                    sub_topicInstance = models.ModuleSubTopic.objects.get(id=sub_topic)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    for category in categories:
                        models.ModuleCategory.objects.create(
                            category=category,
                            sub_topic=sub_topicInstance
                        )
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":

            payload = request.data

            serializer = serializers.UpdateModuleCategorySerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                category = payload['category']
                # sub_topic = payload['topic']

                try:
                    categoryInstance = models.ModuleCategory.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():
                    categoryInstance.category = category
                    categoryInstance.save()
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

        elif request.method == "GET":

            request_id = request.query_params.get('request_id')
            serializer = request.query_params.get('serializer')

            if request_id:
                resp = models.ModuleCategory.objects.get(Q(id=request_id) & Q(is_deleted=False))
            
            else:
                resp = models.ModuleCategory.objects.filter(Q(is_deleted=False))
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(resp, request)
            if serializer == 'full':
                serializer = serializers.FetchModuleCategorySerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            else:
                serializer = serializers.SlimFetchModuleCategorySerializer(
                    result_page, many=True, context={"user_id":request.user.id})
            
            return paginator.get_paginated_response(serializer.data)
            
            
        elif request.method == "DELETE":

            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.ModuleCategory.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)
                
                
    @action(methods=["POST","PUT","DELETE", "GET"], detail=False, url_path="links",url_name="links")
    def links(self, request):
        # roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.ModuleLinkSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                category = payload.get('category') or None
                sub_topic = payload.get('sub_topic') or None
                topic = payload['topic']
                link = payload['link']

                try:
                    topic = models.Module.objects.get(id=topic)
                except Exception as e:
                    return Response({"details": "Unknown topic"}, status=status.HTTP_400_BAD_REQUEST)
                
                if sub_topic:
                    try:
                        sub_topic = models.ModuleSubTopic.objects.get(id=sub_topic)
                    except Exception as e:
                        return Response({"details": "Unknown sub topic"}, status=status.HTTP_400_BAD_REQUEST)
                    
                if category:
                    try:
                        category = models.ModuleCategory.objects.get(id=category)
                    except Exception as e:
                        return Response({"details": "Unknown category"}, status=status.HTTP_400_BAD_REQUEST)
                    
                # check if already existing
                try:
                    existingLink = models.ModuleLink.objects.get(topic=topic,sub_topic=sub_topic,category=category)
                except (ValidationError, ObjectDoesNotExist):
                    existingLink = None
                except Exception as e:
                    print(e)
                    # logger.error(e)
                    existingLink = None
            

                with transaction.atomic():
                    if existingLink:
                        existingLink.link = link
                        existingLink.save()
                    else:
                        try:                         
                            models.ModuleLink.objects.create(
                                topic=topic, 
                                sub_topic=sub_topic, 
                                category=category,
                                link=link,
                                created_by=request.user
                            )
                        except Exception as e:
                            logger.error(e)
                            # print(e)
                            return Response({"details": "Error saving link"}, status=status.HTTP_400_BAD_REQUEST)  
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":

            payload = request.data

            serializer = serializers.UpdateModuleSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                link = payload['link']

                try:
                    targetInstance = models.ModuleLink.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():
                    targetInstance.link = link
                    targetInstance.save()
                    
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":

            request_id = request.query_params.get('request_id')
            topic_id = request.query_params.get('topic_id')
            sub_topic_id = request.query_params.get('sub_topic_id')
            category_id = request.query_params.get('category_id')

            if request_id:
                links = models.ModuleLink.objects.get(Q(id=request_id) & Q(is_deleted=False))

            elif topic_id:
                links = models.ModuleLink.objects.filter(Q(topic=topic_id) & Q(is_deleted=False))

            elif sub_topic_id:
                links = models.ModuleLink.objects.filter(Q(sub_topic=sub_topic_id) & Q(is_deleted=False))
            
            elif category_id:
                links = models.ModuleLink.objects.filter(Q(category=category_id) & Q(is_deleted=False))

            else:
                links = models.ModuleLink.objects.filter(Q(is_deleted=False))
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(links, request)
            serializer = serializers.FetchModuleLinkSerializer(
                result_page, many=True, context={"user_id":request.user.id})
            
            return paginator.get_paginated_response(serializer.data)
            
            
        elif request.method == "DELETE":

            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.ModuleLink.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)











class ReportsViewSet(viewsets.ViewSet):
    # search_fields = ['id', ]

    def get_queryset(self):
        return []

    @action(methods=["GET",],
            detail=False,
            url_path="applications",
            url_name="applications")
    def applications(self, request):
                    
        department = request.query_params.get('department')
        location = request.query_params.get('location')
        ohc = request.query_params.get('ohc')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        # r_status = request.query_params.get('status')
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
            
        # if r_status:
        #     q_filters &= Q(status=r_status)

        if location:
            q_filters &= Q(location=location)

        if ohc:
            q_filters &= Q(ohc=ohc)


        if q_filters:

            resp = models.Staff.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')

        else:
            roles = user_util.fetchusergroups(request.user.id)  

            if "OSH" in roles or "SUPERUSER" in roles:
                resp = models.Staff.objects.filter(Q(is_deleted=False)).order_by('-date_created')[:50]
                
            else:
                resp = models.Staff.objects.filter(Q(is_deleted=False)& Q(created_by=request.user)).order_by('-date_created')[:50]


        resp = serializers.FetchStaffSerializer(resp, many=True, context={"user_id":request.user.id}).data

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
        # roles = user_util.fetchusergroups(request.user.id)
        # active_status = ['REQUESTED','HOD APPROVED','CLOSED']

        applications = models.Medical.objects.filter( Q(is_deleted=False)).count()
        is_fit = models.Medical.objects.filter(Q(is_fit_to_work='YES') & Q(is_deleted=False)).count()
        un_fit = models.Medical.objects.filter(Q(is_fit_to_work='NO') & Q(is_deleted=False)).count()
        # approved = models.Medical.objects.aggregate(total=Sum('days'))['total']
        referred = models.Refer.objects.filter(consultant_name__isnull=False).exclude(consultant_name="").count()

        resp = {
            "applications": applications,
            "is_fit": is_fit,
            "un_fit": un_fit,
            "referred": referred,
        }

        return Response(resp, status=status.HTTP_200_OK)