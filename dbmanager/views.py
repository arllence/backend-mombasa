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
from dbmanager import models
from dbmanager import serializers
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import User, Sendmail, SRRSDepartment
from dbmanager.utils import shared_fxns
from django.db.models import Sum
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import Group

from rest_framework.pagination import PageNumberPagination

# Get an instance of a logger
logger = logging.getLogger(__name__)


class DbManagerViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["POST","PUT","DELETE", "GET"], detail=False, url_path="backup-logs",url_name="backup-logs")
    def backup_logs(self, request):
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.BackupLogSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                type = payload['type']
                date = payload['date']
                log_status = payload['status']
                size = payload['size']
                unit = payload['unit']

                try:
                    system = models.System.objects.get(id=type)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid backup log type'}, status=status.HTTP_400_BAD_REQUEST)

   
                with transaction.atomic():

                    raw = {
                        "type":system,
                        "date":date,
                        "status":log_status,
                        "size":size,
                        "unit":unit,
                        "action_by": request.user
                    }

                    models.BackupLog.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":

            payload = request.data

            serializer = serializers.UpdateBackupLogSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                type = payload['type']
                date = payload['date']
                log_status = payload['status']
                size = payload['size']
                unit = payload['unit']

                try:
                    BackupLogInstance = models.BackupLog.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    system = models.System.objects.get(id=type)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid backup log type'}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():

                    raw = {
                        "type":system,
                        "date":date,
                        "status":log_status,
                        "size":size,
                        "unit":unit,
                        "action_by": request.user
                    }

                    models.BackupLog.objects.filter(Q(id=request_id)).update(**raw)
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":

            request_id = request.query_params.get('request_id')

            if request_id:
                logs = models.BackupLog.objects.get(
                    Q(id=request_id) & Q(is_deleted=False))

            else:
                if "SUPERUSER" in roles or "ICT" in roles:
                    logs = models.BackupLog.objects.filter(
                        Q(is_deleted=False)).order_by('-date_created')
                else:
                    logs = []
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(logs, request)
            serializer = serializers.FetchBackupLogSerializer(
                result_page, many=True, context={"user_id":request.user.id})
            
            return paginator.get_paginated_response(serializer.data)
                 
        elif request.method == "DELETE":

            request_id = request.query_params.get('request_id')
            request_ids = request.query_params.get('request_ids')

            if not request_id and not request_ids:
                return Response({"details": "Cannot complete request "}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    if request_ids:
                        request_ids = json.loads(request_ids)
                        models.BackupLog.objects.filter(Q(id__in=request_ids)).update(**raw)
                    else:
                        models.BackupLog.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)


    @action(methods=["POST","PUT","DELETE", "GET"], detail=False, url_path="remote-backup-logs",url_name="remote-backup-logs")
    def remote_backup_logs(self, request):
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.RemoteBackupLogSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                type = payload['type']
                date = payload['date']
                log_status = payload['status']
                size = payload['size']
                unit = payload['unit']
                remote_location = payload['remote_location']

                try:
                    system = models.System.objects.get(id=type)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid backup log type'}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    remote_location = models.RemoteLocations.objects.get(id=remote_location)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid location'}, status=status.HTTP_400_BAD_REQUEST)


   
                with transaction.atomic():

                    raw = {
                        "type":system,
                        "date":date,
                        "status":log_status,
                        "size":size,
                        "unit":unit,
                        "remote_location":remote_location,
                        "action_by": request.user
                    }

                    models.RemoteBackupLog.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":

            payload = request.data

            serializer = serializers.UpdateRemoteBackupLogSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                type = payload['type']
                date = payload['date']
                log_status = payload['status']
                size = payload['size']
                unit = payload['unit']
                remote_location = payload['remote_location']

                try:
                    BackupLogInstance = models.RemoteBackupLog.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    system = models.System.objects.get(id=type)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid backup log type'}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    remote_location = models.RemoteLocations.objects.get(id=remote_location)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid location'}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():

                    raw = {
                        "type":system,
                        "date":date,
                        "status":log_status,
                        "size":size,
                        "unit":unit,
                        "remote_location":remote_location,
                        "action_by": request.user
                    }

                    models.RemoteBackupLog.objects.filter(Q(id=request_id)).update(**raw)
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":

            request_id = request.query_params.get('request_id')

            if request_id:
                logs = models.RemoteBackupLog.objects.get(
                    Q(id=request_id) & Q(is_deleted=False))

            else:
                if "SUPERUSER" in roles or "ICT" in roles:
                    logs = models.RemoteBackupLog.objects.filter(
                        Q(is_deleted=False)).order_by('-date_created')
                else:
                    logs = []
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(logs, request)
            serializer = serializers.FetchRemoteBackupLogSerializer(
                result_page, many=True, context={"user_id":request.user.id})
            
            return paginator.get_paginated_response(serializer.data)
                 
        elif request.method == "DELETE":

            request_id = request.query_params.get('request_id')
            request_ids = request.query_params.get('request_ids')

            if not request_id and not request_ids:
                return Response({"details": "Cannot complete request "}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    if request_ids:
                        request_ids = json.loads(request_ids)
                        models.RemoteBackupLog.objects.filter(Q(id__in=request_ids)).update(**raw)
                    else:
                        models.RemoteBackupLog.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)
                

    @action(methods=["POST","PUT","DELETE", "GET"], detail=False, url_path="system-recovery-verifications",url_name="system-recovery-verifications")
    def system_recovery_verifications(self, request):
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.SystemRecoveryVerificationSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                module_verified = payload['module_verified']
                date = payload['date']
                comments = payload['comments']

                with transaction.atomic():

                    raw = {
                        "module_verified":module_verified,
                        "date":date,
                        "comments":comments,
                        "verified_by": request.user
                    }

                    models.SystemRecoveryVerification.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":

            payload = request.data

            serializer = serializers.UpdateSystemRecoveryVerificationSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                module_verified = payload['module_verified']
                date = payload['date']
                comments = payload['comments']

                try:
                    selectedInstance = models.SystemRecoveryVerification.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():

                    raw = {
                        "module_verified":module_verified,
                        "date":date,
                        "comments":comments,
                        "verified_by": request.user
                    }

                    models.SystemRecoveryVerification.objects.filter(Q(id=request_id)).update(**raw)
                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":

            request_id = request.query_params.get('request_id')

            if request_id:
                logs = models.SystemRecoveryVerification.objects.get(
                    Q(id=request_id) & Q(is_deleted=False))

            else:
                if "SUPERUSER" in roles or "ICT" in roles:
                    logs = models.SystemRecoveryVerification.objects.filter(
                        Q(is_deleted=False)).order_by('-date_created')
                else:
                    logs = []
            

            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(logs, request)
            serializer = serializers.FetchSystemRecoveryVerificationSerializer(
                result_page, many=True, context={"user_id":request.user.id})
            
            return paginator.get_paginated_response(serializer.data)
                 
        elif request.method == "DELETE":

            request_id = request.query_params.get('request_id')
            request_ids = request.query_params.get('request_ids')

            if not request_id and not request_ids:
                return Response({"details": "Cannot complete request "}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    if request_ids:
                        request_ids = json.loads(request_ids)
                        models.SystemRecoveryVerification.objects.filter(Q(id__in=request_ids)).update(**raw)
                    else:
                        models.SystemRecoveryVerification.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Id"}, status=status.HTTP_400_BAD_REQUEST)

    
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
            url_path="remote-locations",
            url_name="remote-locations")
    def remote_locations(self, request):
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

                    models.RemoteLocations.objects.create(**raw)

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
                    system = models.RemoteLocations.objects.get(id=request_id)
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
                    system = models.RemoteLocations.objects.get(Q(id=request_id))
                    system = serializers.SlimFetchSystemsSerializer(system, many=False).data
                    return Response(system, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown system"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:

                    systems = models.RemoteLocations.objects.filter(Q(is_deleted=False)).order_by('name')
                    systems = serializers.SlimFetchSystemsSerializer(systems, many=True).data
                    return Response(systems, status=status.HTTP_200_OK)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)


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