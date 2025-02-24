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
from system_directory import models
from system_directory import serializers
from acl.utils import user_util
from django.contrib.auth.models import Group

from django.db.models import F, IntegerField
from django.db.models.functions import Cast, Substr

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
                
