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
        serializer = SlimFetchSRRSDepartmentSerializer(
            resp, many=True, context={"user_id":request.user.id})
        
        return Response(serializer.data, status=status.HTTP_200_OK)

    
    @action(methods=["GET"], detail=False, url_path="files",url_name="files")
    def files(self, request):
        department_id = request.query_params.get('department_id')
        if department_id:
            documents = models.Document.objects.filter(Q(department=department_id) & Q(is_deleted=False))
        else:
            documents = []
        

        paginator = PageNumberPagination()
        paginator.page_size = 50
        result_page = paginator.paginate_queryset(documents, request)
        serializer = serializers.SlimFetchDocumentSerializer(
            result_page, many=True)
        
        return paginator.get_paginated_response(serializer.data)
    
    @action(methods=["POST"], detail=False, url_path="downloads",url_name="downloads")
    def downloads(self, request):
        payload = request.data
        try:
            request_id = payload['request_id']
            document = models.Document.objects.get(id=request_id)
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
                title = payload['title']
                department = payload['department']

                try:
                    department = SRRSDepartment.objects.get(id=department)
                except Exception as e:
                    return Response({"details": "Unknown department"}, status=status.HTTP_400_BAD_REQUEST)
            

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
                            if total_files > 1:
                                title = f"{title} - {str(total_files)}"

                            original_file_name = f.name.split('.')[0]                            
                            models.Document.objects.create(
                                document=f,
                                original_file_name=original_file_name, 
                                title=title, 
                                department=department,
                                uploaded_by=request.user
                            )
                            total_files += 1
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
                    documents = models.Document.objects.filter(Q(is_deleted=False))
                else:
                    documents = models.Document.objects.filter(Q(department=request.user.srrs_department) & Q(is_deleted=False))
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(documents, request)
            serializer = serializers.FetchDocumentSerializer(
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
                    models.Document.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)
                
    
    @action(methods=["POST"], detail=False, url_path="downloads",url_name="downloads")
    def downloads(self, request):
        roles = user_util.fetchusergroups(request.user.id) 
        payload = request.data
        try:
            request_id = payload['request_id']
            document = models.Document.objects.get(id=request_id)
        except:
            return Response({"details": "Unknown request id"}, status=status.HTTP_400_BAD_REQUEST)
        
        count = int(document.downloads)
        count += 1
        
        with transaction.atomic():
            try:
                document.downloads = count
                # document.save()  
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