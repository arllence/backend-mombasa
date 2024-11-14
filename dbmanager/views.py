import calendar
from collections import OrderedDict
import csv
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
from rest_framework.exceptions import NotFound, ParseError

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
            q = request.query_params.get('q')

            if request_id:
                logs = models.BackupLog.objects.get(
                    Q(id=request_id) & Q(is_deleted=False))
                serializer = serializers.FetchBackupLogSerializer(
                logs, many=False, context={"user_id":request.user.id})
                return Response(serializer.data, status=status.HTTP_200_OK)   
            elif q:
                if "SUPERUSER" in roles or "ICT" in roles:
                    logs = models.BackupLog.objects.filter(
                        Q(unit__icontains=q) | 
                        Q(size__icontains=q) |
                        Q(status__icontains=q) |
                        Q(date__icontains=q) |
                        Q(type__name__icontains=q), is_deleted=False).order_by('-date')
                else:
                    logs = []
            else:
                if "SUPERUSER" in roles or "ICT" in roles:
                    logs = models.BackupLog.objects.filter(
                        Q(is_deleted=False)).order_by('-date')
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


    @action(methods=["POST"],
            detail=False,
            url_path="upload-local-backup-logs",
            url_name="upload-local-backup-logs")
    def upload_local(self, request):
        if request.method == "POST":
            formfiles = request.FILES
            if not formfiles:
                return Response({"details": "Please upload attachment"}, status=status.HTTP_400_BAD_REQUEST)
            
            def get_system(name):
                try:
                    system = models.System.objects.get(name=name.upper())
                except Exception as e:
                    system = None
                return system
            
            f = request.FILES.getlist('documents')[0]
            if f.name.endswith('.csv'):
                decoded_file = f.read().decode('utf-8')
                csv_data = csv.reader(decoded_file.splitlines(), delimiter=',')
                # Skip the header row
                next(csv_data)
                data = [
                    models.BackupLog(
                        type=get_system(row[0].strip()),
                        status=row[1].strip().upper(),
                        size=row[2].strip(),
                        unit=row[3].strip().upper(),
                        date=row[4].strip(),
                        action_by=request.user
                    ) 
                    for row in csv_data
                ]
                with transaction.atomic():
                    try:
                        models.BackupLog.objects.bulk_create(data)
                    except Exception as e:
                        logger.error(e)
                        return Response({"details": str(e)}, status=status.HTTP_400_BAD_REQUEST)
                return Response('Data uploaded successfully', status=status.HTTP_200_OK)
            else:
                return Response({"details": "Please upload a CSV file."}, status=status.HTTP_400_BAD_REQUEST)
            


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
            q = request.query_params.get('q')

            if request_id:
                logs = models.RemoteBackupLog.objects.get(
                    Q(id=request_id) & Q(is_deleted=False))
                serializer = serializers.FetchRemoteBackupLogSerializer(
                logs, many=True, context={"user_id":request.user.id})
                return Response(serializer.data, status=status.HTTP_200_OK)  
            elif q:
                if "SUPERUSER" in roles or "ICT" in roles:
                    logs = models.RemoteBackupLog.objects.filter(
                        Q(unit__icontains=q) | 
                        Q(size__icontains=q) |
                        Q(status__icontains=q) |
                        Q(date__icontains=q) |
                        Q(remote_location__name__icontains=q) |
                        Q(type__name__icontains=q), is_deleted=False).order_by('-date')
                else:
                    logs = []
            else:
                if "SUPERUSER" in roles or "ICT" in roles:
                    logs = models.RemoteBackupLog.objects.filter(
                        Q(is_deleted=False)).order_by('-date')
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

    
    @action(methods=["POST"],
            detail=False,
            url_path="upload-remote-backup-logs",
            url_name="upload-remote-backup-logs")
    def upload_remote(self, request):
        if request.method == "POST":
            formfiles = request.FILES
            if not formfiles:
                return Response({"details": "Please upload attachment"}, status=status.HTTP_400_BAD_REQUEST)
            
            def get_system(name):
                try:
                    system = models.System.objects.get(name__icontains=name.upper())
                except Exception as e:
                    system = None
                    raise ParseError({"details": f"Unknown system: {name}"})
                return system
            
            def get_location(name):
                try:
                    location = models.RemoteLocations.objects.get(name__icontains=name.upper())
                except Exception as e:
                    location = None
                    raise ParseError({"details": f"Unknown remote location: {name}"})
                return location
            
            f = request.FILES.getlist('documents')[0]
            if f.name.endswith('.csv'):
                decoded_file = f.read().decode('utf-8')
                csv_data = csv.reader(decoded_file.splitlines(), delimiter=',')
                # Skip the header row
                next(csv_data)
                data = [
                    models.RemoteBackupLog(
                        type=get_system(row[0].strip()),
                        status=row[1].strip().upper(),
                        size=row[2].strip(),
                        unit=row[3].strip().upper(),
                        date=row[4].strip(),
                        remote_location=get_location(row[5].strip()),
                        action_by=request.user
                    ) 
                    for row in csv_data
                ]
                with transaction.atomic():
                    try:
                        models.RemoteBackupLog.objects.bulk_create(data)
                    except Exception as e:
                        logger.error(e)
                        return Response({"details": str(e)}, status=status.HTTP_400_BAD_REQUEST)
                return Response('Data uploaded successfully', status=status.HTTP_200_OK)
            else:
                return Response({"details": "Please upload a CSV file."}, status=status.HTTP_400_BAD_REQUEST)
                

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
            url_path="local-backups",
            url_name="local-backups")
    def local_backups(self, request):
                    
        type = request.query_params.get('system')
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

            q_filters = Q(date__gte=date_from) & Q(date__lte=date_to)

            return q_filters

        q_filters = Q()

        if type:
            q_filters &= Q(type=type)

        if r_status:
            q_filters &= Q(status=r_status)

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)
            

        if q_filters:

            resp = models.BackupLog.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date')

        else:
            roles = user_util.fetchusergroups(request.user.id)  

            if "ICT" in roles or "SUPERUSER" in roles:
                resp = models.BackupLog.objects.filter(Q(is_deleted=False)).order_by('-date')[:20]
                
            else:
                resp = models.BackupLog.objects.filter(Q(is_deleted=False)& Q(created_by=request.user)).order_by('-date')[:20]

        resp = serializers.FetchBackupLogSerializer(resp, many=True, context={"user_id":request.user.id}).data

        return Response(resp, status=status.HTTP_200_OK)
    

    @action(methods=["GET",],
            detail=False,
            url_path="remote-backups",
            url_name="remote-backups")
    def remote_backups(self, request):
                    
        type = request.query_params.get('system')
        r_status = request.query_params.get('status')
        location = request.query_params.get('location')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        date = False

        if date_to and date_from:
            date = True

        def create_date_range(date_from,date_to):
            # Convert the string dates to datetime objects
            date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d')
            date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d')

            q_filters = Q(date__gte=date_from) & Q(date__lte=date_to)

            return q_filters

        q_filters = Q()

        if type:
            q_filters &= Q(type=type)

        if r_status:
            q_filters &= Q(status=r_status)

        if location:
            q_filters &= Q(remote_location=location)

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)
            
            
        if q_filters:

            resp = models.RemoteBackupLog.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date')

        else:
            roles = user_util.fetchusergroups(request.user.id)  

            if "ICT" in roles or "SUPERUSER" in roles:
                resp = models.RemoteBackupLog.objects.filter(Q(is_deleted=False)).order_by('-date')[:20]
                
            else:
                resp = models.RemoteBackupLog.objects.filter(Q(is_deleted=False)& Q(created_by=request.user)).order_by('-date')[:20]

        resp = serializers.FetchRemoteBackupLogSerializer(resp, many=True, context={"user_id":request.user.id}).data

        return Response(resp, status=status.HTTP_200_OK)
    
    
    @action(methods=["GET",],
            detail=False,
            url_path="recoveries",
            url_name="recoveries")
    def recoveries(self, request):
                    
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        date = False

        if date_to and date_from:
            date = True

        def create_date_range(date_from,date_to):
            # Convert the string dates to datetime objects
            date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d')
            date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d')

            q_filters = Q(date__gte=date_from) & Q(date__lte=date_to)

            return q_filters

        q_filters = Q()

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)
            
            
        if q_filters:

            resp = models.SystemRecoveryVerification.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')

        else:
            roles = user_util.fetchusergroups(request.user.id)  

            if "ICT" in roles or "SUPERUSER" in roles:
                resp = models.SystemRecoveryVerification.objects.filter(Q(is_deleted=False)).order_by('-date_created')[:20]
                
            else:
                resp = models.SystemRecoveryVerification.objects.filter(Q(is_deleted=False)& Q(created_by=request.user)).order_by('-date_created')[:20]

        resp = serializers.FetchSystemRecoveryVerificationSerializer(resp, many=True, context={"user_id":request.user.id}).data

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

        backups = (models.BackupLog.objects.filter( Q(is_deleted=False)).count()) + (models.RemoteBackupLog.objects.filter( Q(is_deleted=False)).count())
        succeeded = (models.BackupLog.objects.filter(Q(status='SUCCEEDED') & Q(is_deleted=False)).count()) + (models.RemoteBackupLog.objects.filter(Q(status='SUCCEEDED') & Q(is_deleted=False)).count())
        failed = (models.BackupLog.objects.filter(Q(status='FAILED') & Q(is_deleted=False)).count()) + (models.RemoteBackupLog.objects.filter(Q(status='FAILED') & Q(is_deleted=False)).count())
        verifications = models.SystemRecoveryVerification.objects.filter(Q(is_deleted=False)).count()
 
        resp = {
            "backups": backups,
            "succeeded": succeeded,
            "failed": failed,
            "verifications": verifications,
        }

        return Response(resp, status=status.HTTP_200_OK)