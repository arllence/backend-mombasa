import calendar
from collections import OrderedDict
import datetime
import json
import logging
import uuid
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
from sss import models
from sss import serializers
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import User, Sendmail, SRRSDepartment
from sss.utils import shared_fxns
from django.db.models import Sum
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import Group

from rest_framework.pagination import PageNumberPagination

# Get an instance of a logger
logger = logging.getLogger(__name__)

class SSSViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="application",
            url_name="application")
    def application(self, request):
        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            staff = payload['staff']
            medical = payload['medical']
            refer = payload['refer']

            uid = shared_fxns.generate_unique_identifier()

            # serialize staff payload
            staff_serializer = serializers.StaffSerializer(
                    data=staff, many=False)
            if not staff_serializer.is_valid():
                return Response({"details": staff_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
      
            # serialize medical payload
            medical_serializer = serializers.MedicalSerializer(
                    data=medical, many=False)
            if not medical_serializer.is_valid():
                return Response({"details": medical_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            
            # serialize refer payload
            refer_serializer = serializers.ReferSerializer(
                    data=refer, many=False)
            if not refer_serializer.is_valid():
                return Response({"details": refer_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
           
            department = staff['department']
            try:
                department = SRRSDepartment.objects.get(id=department)
                staff['department'] = department
            except Exception as e:
                return Response({"details": "Unknown department"}, status=status.HTTP_400_BAD_REQUEST)
                        

            if str(department.id) != str(authenticated_user.srrs_department.id):
                return Response({"details": "Request Must be within your department"}, status=status.HTTP_400_BAD_REQUEST)


            with transaction.atomic():
                # create staff instance
                staff.update({'created_by': request.user, "uid":uid})
                staffInstance = models.Staff.objects.create(
                    **staff
                )


                # create medical
                medical.update({'staff':staffInstance})
                models.Medical.objects.create(**medical)


                # create refer
                refer.update({'staff':staffInstance})
                models.Refer.objects.create(**refer)



            user_util.log_account_activity(
                authenticated_user, authenticated_user, "Sick Leave  Request created", f"Staff Id: {staffInstance.id}")
            
            return Response('success', status=status.HTTP_200_OK)
            

        elif request.method == "PUT":
            payload = request.data

            staff = payload['staff']
            medical = payload['medical']
            refer = payload['refer']

            # serialize staff payload
            staff_serializer = serializers.StaffSerializer(
                    data=staff, many=False)
            if not staff_serializer.is_valid():
                return Response({"details": staff_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
      
            # serialize medical payload
            medical_serializer = serializers.MedicalSerializer(
                    data=medical, many=False)
            if not medical_serializer.is_valid():
                return Response({"details": medical_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            
            # serialize refer payload
            refer_serializer = serializers.ReferSerializer(
                    data=refer, many=False)
            if not refer_serializer.is_valid():
                return Response({"details": refer_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
           
            department = staff['department']
            try:
                department = SRRSDepartment.objects.get(id=department)
                staff['department'] = department
            except Exception as e:
                return Response({"details": "Unknown department"}, status=status.HTTP_400_BAD_REQUEST)
                        

            if str(department.id) != str(authenticated_user.srrs_department.id):
                return Response({"details": "Request Must be within your department"}, status=status.HTTP_400_BAD_REQUEST)

            
            # extrapolate
            try:
                request_id = payload['request_id']
            except Exception as e:
                return Response({"details": "Request ID Required"}, status=status.HTTP_400_BAD_REQUEST)

            
            try:
                staffInstance = models.Staff.objects.get(id=request_id)
            except (ValidationError, ObjectDoesNotExist):
                return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                print(e)
                return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            

            with transaction.atomic():
                # update staff instance
                models.Staff.objects.filter(Q(id=request_id)).update(**staff)


                # update medical
                models.Medical.objects.filter(Q(staff=request_id)).update(**medical)


                # update refer
                models.Medical.objects.filter(Q(staff=request_id)).update(**refer)



            user_util.log_account_activity(
                authenticated_user, authenticated_user, "Sick Leave  Request updated", f"Staff Id: {request_id}")
           

            return Response('success', status=status.HTTP_200_OK)
     
  
        elif request.method == "PATCH":
            payload = request.data
            
            return Response('success', status=status.HTTP_200_OK)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            payroll_no = request.query_params.get('payroll_no')
            query = request.query_params.get('q')
            slim = request.query_params.get('slim')

            if request_id:
                try:
                    resp = models.Staff.objects.get(Q(id=request_id))

                    if slim:
                        resp = serializers.FetchStaffSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.FetchStaffSerializer(resp, many=False, context={"user_id":request.user.id}).data

                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request!"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
                
            elif payroll_no:
                try:
                    resp = models.Staff.objects.get(Q(payroll_no=payroll_no))

                    if slim:
                        resp = serializers.FetchStaffSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.FetchStaffSerializer(resp, many=False, context={"user_id":request.user.id}).data

                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request!"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
                
            else:
                try:

                    if any(role in ['SUPERUSER','OSH'] for role in roles):

                        resp = models.Staff.objects.filter(is_deleted=False).order_by('-date_created')

                    else:
                        resp = models.Staff.objects.filter(Q(is_deleted=False) & (Q(created_by=True)) ).order_by('-date_created')



                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resp, request)
                    serializer = serializers.FetchStaffSerializer(
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
                    models.Staff.objects.filter(Q(id=request_id)).update(**raw)
                    models.Medical.objects.filter(Q(staff=request_id)).update(**raw)
                    models.Refer.objects.filter(Q(staff=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)    
                except Exception as e:
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST) 
                   

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
            approved = models.Access.objects.filter(Q(employee__department=request.user.srrs_department) |  Q(created_by=request.user), status="ICT APPROVED", is_deleted=False).count()
            rejected = models.Access.objects.filter(Q(employee__department=request.user.srrs_department) |  Q(created_by=request.user), status="REJECTED", is_deleted=False).count()
            pending = models.Access.objects.filter(Q(employee__department=request.user.srrs_department) |  Q(created_by=request.user), status__in=active_status, is_deleted=False).count()
        elif 'ICT' in roles or 'SUPERUSER' in roles:
            requests = models.Access.objects.filter(is_deleted=False).count()
            approved = models.Access.objects.filter(status="ICT APPROVED", is_deleted=False).count()
            rejected = models.Access.objects.filter(status="REJECTED", is_deleted=False).count()
            pending = models.Access.objects.filter(status__in=active_status, is_deleted=False).count()
        else:
            requests = models.Access.objects.filter(Q(created_by=request.user) & Q(is_deleted=False)).count()
            approved = models.Access.objects.filter(Q(created_by=request.user) & Q(status="ICT APPROVED"), is_deleted=False).count()
            rejected = models.Access.objects.filter(Q(created_by=request.user) & Q(status="REJECTED"), is_deleted=False).count()
            pending = models.Access.objects.filter(Q(created_by=request.user) & Q(status__in=active_status), is_deleted=False).count()

        resp = {
            "requests": requests,
            "rejected": rejected,
            "approved": approved,
            "pending": pending,
        }

        return Response(resp, status=status.HTTP_200_OK)