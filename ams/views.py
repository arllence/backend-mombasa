import calendar
from collections import OrderedDict
import datetime
import json
import logging
import uuid
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.contrib.auth import get_user_model
from django.db.models import  Q
from django.db import transaction
from django.utils import timezone
from ams import models
from ams import serializers
from ams.utils import shared_fxns
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import User, Sendmail, SRRSDepartment
from django.db.models import Sum
from django.core.mail import send_mail

from rest_framework.pagination import PageNumberPagination
from ict_helpdesk.models import Facility

# Get an instance of a logger
logger = logging.getLogger(__name__)

class AMSViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="asset-management",
            url_name="asset-management")
    def asset(self, request):
        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            # serialize employee payload
            serializer = serializers.AssetSerializer(
                    data=payload, many=False)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            asset_no = payload['asset_no'].strip()
            facility = payload['facility'].strip()
            department = payload['department'].strip()
            asset_status = payload['status'].strip()
            type = payload['type'].strip()
            category = payload['category'] or None
            custodian = payload['custodian'] or None
            specific_location = payload['specific_location'] or None
            properties = payload['properties'] or None
            description = payload['description'] or None
            procurement_date = payload['procurement_date'] or None

            exists = models.Asset.objects.filter(Q(asset_no=asset_no)).exists()
            if exists:
                return Response({"details": "Asset already added"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                department = SRRSDepartment.objects.get(id=department)
            except Exception as e:
                return Response({"details": "Unknown department"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                facility = Facility.objects.get(id=facility)
            except Exception as e:
                return Response({"details": "Unknown facility"}, status=status.HTTP_400_BAD_REQUEST)
            
    
            with transaction.atomic():
                raw_obj = {
                    "asset_no": asset_no,
                    "facility": facility,
                    "department": department,
                    "status": asset_status,
                    "type": type,
                    "category": category,
                    "custodian": custodian,
                    "properties": properties,
                    "specific_location": specific_location,
                    "description": description,
                    "procurement_date": procurement_date,
                    "created_by": authenticated_user
                }

                newInstance = models.Asset.objects.create(**raw_obj)


            user_util.log_account_activity(
                authenticated_user, authenticated_user, "Asset created", f"Asset Id: {newInstance.id}")
            
            return Response('success', status=status.HTTP_200_OK)
            

        elif request.method == "PUT":
            payload = request.data

            # serialize employee payload
            serializer = serializers.UpdateAssetSerializer(
                    data=payload, many=False)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            request_id = payload['request_id'].strip()
            asset_no = payload['asset_no'].strip()
            facility = payload['facility'].strip()
            department = payload['department'].strip()
            asset_status = payload['status'].strip()
            type = payload['type'].strip()
            category = payload['category'] or None
            custodian = payload['custodian'] or None
            specific_location = payload['specific_location'] or None
            properties = payload['properties'] or None
            description = payload['description'] or None
            procurement_date = payload['procurement_date'] or None
            
            try:
                asset = models.Asset.objects.get(id=request_id)
            except Exception as e:
                return Response({"details": "Unknown Asset"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                department = SRRSDepartment.objects.get(id=department)
            except Exception as e:
                return Response({"details": "Unknown department"}, status=status.HTTP_400_BAD_REQUEST)
            
    
            with transaction.atomic():
                raw_obj = {
                    "asset_no": asset_no,
                    "facility": facility,
                    "department": department,
                    "status": asset_status,
                    "type": type,
                    "category": category,
                    "custodian": custodian,
                    "properties": properties,
                    "specific_location": specific_location,
                    "description": description,
                    "procurement_date": procurement_date,
                    "last_updated": timezone.now()
                }

                models.Asset.objects.filter(Q(id=request_id)).update(**raw_obj)


            user_util.log_account_activity(
                authenticated_user, authenticated_user, "Asset updated", f"Asset Id: {request_id}")
            
            return Response('success', status=status.HTTP_200_OK)
     
  
        elif request.method == "PATCH":
            payload = request.data
            serializer = serializers.PatchRecruitSerializer(
                data=payload, many=False)
            
            return
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            type = request.query_params.get('type')
            asset_no = request.query_params.get('asset_no')
            facility = request.query_params.get('facility')
            query = request.query_params.get('q')
            slim = request.query_params.get('slim')

            q_filters = Q()

            if request_id:
                q_filters &= Q(id=request_id)

            if type:
                q_filters &= Q(type=type)

            if asset_no:
                q_filters &= Q(asset_no=asset_no)

            if facility:
                q_filters &= Q(facility=facility)

            if query:
                q_filters &= (Q(asset_no__icontains=query) | 
                              Q(asset_no__icontains=query) | 
                              Q(category__icontains=query) |
                              Q(status__icontains=query) |
                              Q(created_by__first_name__icontains=query) |
                              Q(created_by__last_name__icontains=query) |
                              Q(specific_location__icontains=query) |
                              Q(custodian__icontains=query) |
                              Q(type__icontains=query) |
                              Q(description__icontains=query) 
                            )

            if q_filters:
                resp = models.Asset.objects.filter(q_filters)
               
            else:
                try:

                    if any(role in ['SUPERUSER','ICT'] for role in roles):
                        resp = models.Asset.objects.filter(Q(is_deleted=False) ).order_by('-date_created')

                    else:
                        resp = models.Asset.objects.filter(Q(created_by=request.user), is_deleted=False).order_by('-date_created')
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request !"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
                
            paginator = PageNumberPagination()
            paginator.page_size = 50
            result_page = paginator.paginate_queryset(resp, request)
            serializer = serializers.FetchAssetSerializer(
                result_page, many=True, context={"user_id":request.user.id})
            return paginator.get_paginated_response(serializer.data)
        
        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.Asset.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)    
                except Exception as e:
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)  



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
            url_path="replacements",
            url_name="replacements")
    def replacements(self, request):
                    
        department = request.query_params.get('department')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        # quote_status = request.query_params.get('status')
        date = False

        if date_to and date_from:
            date = True

        def create_date_range(date_from,date_to):
            # Convert the string dates to datetime objects
            date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d')
            date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d')

            q_filters = Q(date_created__gte=date_from) & Q(date_created__lte=date_to)

            return q_filters

        q_filters = Q(nature_of_hiring='Replacement')

        if department:
            q_filters &= Q(department=department)

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)
            
        # if quote_status:
        #     q_filters &= Q(status=quote_status)


        if q_filters:

            resp = models.Recruit.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
            
        else:
            roles = user_util.fetchusergroups(request.user.id)  

            resp = models.Recruit.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')[:50]

        resp = serializers.FetchRecruitSerializer(resp, many=True, context={"user_id":request.user.id}).data

        return Response(resp, status=status.HTTP_200_OK)
    
    @action(methods=["GET",],
            detail=False,
            url_path="hires",
            url_name="hires")
    def hires(self, request):
                    
        department = request.query_params.get('department')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        type = request.query_params.get('type')
        date = False

        if date_to and date_from:
            date = True

        def create_date_range(date_from,date_to):
            # Convert the string dates to datetime objects
            date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d')
            date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d')

            q_filters = Q(date_created__gte=date_from) & Q(date_created__lte=date_to)

            return q_filters

        q_filters = Q(status='ACTIVE')
        q_filters &= Q(recruit__status='HIRED')

        if department:
            q_filters &= Q(recruit__department=department)

        if type:
            q_filters &= Q(recruit__position_type=type)

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)


        resp = models.Employee.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
            
        resp = serializers.FullFetchEmployeeSerializer(resp, many=True, context={"user_id":request.user.id}).data

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
        active_status = ['REQUESTED','HOD APPROVED','CLOSED']

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
            requests = models.Access.objects.filter(Q(created_by=request.user) & Q(is_deleted=False)).count()
            approved = models.Access.objects.filter(Q(created_by=request.user) & Q(status="ICT AUTHORIZED"), is_deleted=False).count()
            rejected = models.Access.objects.filter(Q(created_by=request.user) & Q(status="REJECTED"), is_deleted=False).count()
            pending = models.Access.objects.filter(Q(created_by=request.user) & Q(status__in=active_status), is_deleted=False).count()

        resp = {
            "requests": requests,
            "rejected": rejected,
            "approved": approved,
            "pending": pending,
        }

        return Response(resp, status=status.HTTP_200_OK)