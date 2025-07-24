import datetime
import json
import logging
from string import Template
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.contrib.auth import get_user_model
from django.db.models import  Q
from django.db import transaction
from invoice_tracking import models
from invoice_tracking import serializers
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import User, Hods, SRRSDepartment, Sendmail
from invoice_tracking.utils import shared_fxns
from django.db.models import Sum
from django.core.mail import send_mail

from rest_framework.pagination import PageNumberPagination
from ict_helpdesk.models import Facility

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
            url_path="tracking",
            url_name="tracking")
    def tracking(self, request):
        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.CreateTrackingSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                facility = payload['facility']
                weigh_bill_no = payload['weigh_bill_no']
                courier = payload['courier']
                collector = payload['collector']
                notes = payload.get('notes')

                try:
                    facility = Facility.objects.get(id=facility)
                except Exception as e:
                    return Response({"details": "Unknown Facility"}, status=status.HTTP_400_BAD_REQUEST)

                
                with transaction.atomic():
                    raw = {
                        "created_by": authenticated_user,
                        "facility": facility,
                        "weigh_bill_no": weigh_bill_no,
                        "courier": courier,
                        "collector": collector,
                        "notes": notes
                    } 

                    trackingInstance = models.Tracking.objects.create(
                        **raw
                    )

                    # track status change
                    raw = {
                        "tracked": trackingInstance,
                        "status": "SUBMITTED",
                        "action_by": authenticated_user
                    }

                    models.TrackingStatusChange.objects.create(**raw)

                    
                    # Notify selected send to
                    
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "PUT":
            payload = request.data

            serializer = serializers.UpdatePatientSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                facility = payload['facility']
                weigh_bill_no = payload['weigh_bill_no']
                courier = payload['courier']
                collector = payload['collector']
                notes = payload.get('notes')

                try:
                    trackedInstance = models.Tracking.objects.get(id=request_id)
                except Exception as e:
                    return Response({"details": "Unknown record"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    facility = Facility.objects.get(id=facility)
                except Exception as e:
                    return Response({"details": "Unknown Facility"}, status=status.HTTP_400_BAD_REQUEST)

                
                with transaction.atomic():
                    raw = {
                        "facility": facility,
                        "weigh_bill_no": weigh_bill_no,
                        "courier": courier,
                        "collector": collector,
                        "notes": notes
                    } 

                    models.Tracking.objects.filter(Q(id=request_id)).update(
                        **raw
                    )

                    # track status change
                    raw = {
                        "tracked": trackedInstance,
                        "status": "EDITED",
                        "action_by": authenticated_user
                    }

                    models.TrackingStatusChange.objects.create(**raw)

                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PATCH":
            # Accepting parcel
            payload = request.data
            for key, value in payload.items():
                if not value:
                    return Response({"details": "All fields required"}, status=status.HTTP_400_BAD_REQUEST)
                
            request_id = payload.get('request_id')

            try:
                trackedInstance = models.Tracking.objects.get(id=request_id)
            except Exception as e:
                return Response({"details": "Unknown record"}, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                trackedInstance.received_on = datetime.datetime.now()
                trackedInstance.status = 'RECEIVED'
                trackedInstance.save()

                # track status change
                raw = {
                    "tracked": trackedInstance,
                    "status": "RECEIVED",
                    "action_by": authenticated_user
                }

                models.TrackingStatusChange.objects.create(**raw)
                
                return Response('200', status=status.HTTP_200_OK)  


        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            facility = request.query_params.get('facility')
            weigh_bill_no = request.query_params.get('weigh_bill_no')
            query = request.query_params.get('q')

            if request_id:
                try:
                    resp = models.Tracking.objects.get(id=request_id)
                    resp = serializers.FetchTrackingSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    logger.error(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
                
            elif weigh_bill_no:
                try:
                    resp = models.Tracking.objects.filter(Q(weigh_bill_no=weigh_bill_no))
                    resp = serializers.FetchTrackingSerializer(resp, many=True, context={"user_id":request.user.id}).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    logger.error(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    if query:
                        if query == 'pending':
                            resp = models.Tracking.objects.filter(
                                Q(status='PENDING')).order_by('-date_created')
                            
                        elif query == 'received':
                            resp = models.Tracking.objects.filter(
                                Q(status='RECEIVED')).order_by('-date_created')
                            
                        else:
                            resp = models.Tracking.objects.filter(
                                Q(weigh_bill_no__icontains=query) |
                                Q(courier__icontains=query) |
                                Q(collector__icontains=query)).order_by('-date_created')
                            
                    else:
                        if facility:
                            resp = models.Tracking.objects.filter(
                            Q(facility=facility)).order_by('-date_created')
                        else:
                            resp = models.Tracking.objects.all().order_by('-date_created')
                    

                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resp, request)
                    serializer = serializers.FetchTrackingSerializer(
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
                    models.Tracking.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)   
                 

    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="cancellation",
            url_name="cancellation")
    def cancellation(self, request):
        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.CreateCancellationSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                facility = payload['facility']
                invoice_no = payload['invoice_no']
                action = payload['action']
                reason = payload['reason']

                try:
                    facility = Facility.objects.get(id=facility)
                except Exception as e:
                    return Response({"details": "Unknown Facility"}, status=status.HTTP_400_BAD_REQUEST)

                
                with transaction.atomic():
                    raw = {
                        "created_by": authenticated_user,
                        "facility": facility,
                        "invoice_no": invoice_no,
                        "action": action,
                        "reason": reason
                    } 

                    itemInstance = models.Cancellation.objects.create(
                        **raw
                    )

                    # track status change
                    raw = {
                        "cancelled": itemInstance,
                        "status": "SUBMITTED",
                        "action_by": authenticated_user
                    }

                    models.CancellationStatusChange.objects.create(**raw)

                    
                    # Notify selected send to
                    
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "PUT":
            payload = request.data

            serializer = serializers.UpdatePatientSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                facility = payload['facility']
                invoice_no = payload['invoice_no']
                action = payload['action']
                reason = payload['reason']

                try:
                    itemInstance = models.Cancellation.objects.get(id=request_id)
                except Exception as e:
                    return Response({"details": "Unknown record"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    facility = Facility.objects.get(id=facility)
                except Exception as e:
                    return Response({"details": "Unknown Facility"}, status=status.HTTP_400_BAD_REQUEST)

                
                with transaction.atomic():
                    raw = {
                        "facility": facility,
                        "invoice_no": invoice_no,
                        "action": action,
                        "reason": reason
                    } 

                    models.Cancellation.objects.filter(Q(id=request_id)).update(
                        **raw
                    )

                    # track status change
                    raw = {
                        "cancelled": itemInstance,
                        "status": "EDITED",
                        "action_by": authenticated_user
                    }

                    models.CancellationStatusChange.objects.create(**raw)

                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PATCH":
            # Accepting parcel
            payload = request.data
            for key, value in payload.items():
                if not value:
                    return Response({"details": "All fields required"}, status=status.HTTP_400_BAD_REQUEST)
                
            request_id = payload.get('request_id')

            try:
                itemInstance = models.Cancellation.objects.get(id=request_id)
            except Exception as e:
                return Response({"details": "Unknown record"}, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                itemInstance.received_on = datetime.datetime.now()
                itemInstance.status = 'RECEIVED'
                itemInstance.save()

                # track status change
                raw = {
                    "cancelled": itemInstance,
                    "status": "RECEIVED",
                    "action_by": authenticated_user
                }

                models.CancellationStatusChange.objects.create(**raw)
                
                return Response('200', status=status.HTTP_200_OK)  


        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            invoice_no = request.query_params.get('invoice_no')
            facility = request.query_params.get('facility')
            query = request.query_params.get('q')

            if request_id:
                try:
                    resp = models.Cancellation.objects.get(id=request_id)
                    resp = serializers.FetchCancellationSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    logger.error(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
                
            elif invoice_no:
                try:
                    resp = models.Cancellation.objects.filter(Q(invoice_no=invoice_no))
                    resp = serializers.FetchCancellationSerializer(resp, many=True, context={"user_id":request.user.id}).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    logger.error(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
                
            else:
                try:
                    if query:
                        if query == 'pending':
                            resp = models.Cancellation.objects.filter(
                                Q(status='PENDING')).order_by('-date_created')
                            
                        elif query == 'received':
                            resp = models.Cancellation.objects.filter(
                                Q(status='RECEIVED')).order_by('-date_created')
                            
                        else:
                            resp = models.Cancellation.objects.filter(
                                Q(invoice_no__icontains=query) |
                                Q(action__icontains=query) |
                                Q(reason__icontains=query)).order_by('-date_created')
                    else:
                        if facility:
                            resp = models.Cancellation.objects.filter(
                            Q(facility=facility)).order_by('-date_created')
                        else:
                            resp = models.Cancellation.objects.all().order_by('-date_created')

                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resp, request)
                    serializer = serializers.FetchCancellationSerializer(
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
                    models.Cancellation.objects.filter(Q(id=request_id)).update(**raw)
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
                
                # assign PSD_ADMIN role
                assign_role = user_util.award_role('PSD_ADMIN', str(admin.id))
                if not assign_role:
                    return Response({"details": "Unable to assign role PSD_ADMIN"}, status=status.HTTP_400_BAD_REQUEST)
                
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
                    user_util.revoke_role('PSD_ADMIN', str(user.admin.id))
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
            url_path="requests",
            url_name="requests")
    def requests(self, request):
                    
        doctor = request.query_params.get('doctor')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        x_status = request.query_params.get('status')
        date = False

        if date_to and date_from:
            date = True

        def create_date_range(date_from,date_to):
            # Convert the string dates to datetime objects
            date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d')
            date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d')

            q_filters = Q(date_created__gte=date_from) & Q(date_created__lte=date_to)

            return q_filters
        
        q_filters = Q()

        if doctor:
            q_filters &= (Q(handover_to=doctor) | Q(handover_by=doctor))

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)
            
        if x_status:
            q_filters &= Q(status=x_status)


        if q_filters:
            resp = models.Patient.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
        else:
            resp = models.Patient.objects.filter(Q(is_deleted=False)).order_by('-date_created')[:50]

        resp = serializers.FetchPatientSerializer(resp, many=True, context={"user_id":request.user.id}).data

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
        roles = user_util.fetchusergroups(request.user.id)

        trackings = {
            "total" :  models.Tracking.objects.filter(Q(is_deleted=False)).count(),
            "pending" :  models.Tracking.objects.filter(Q(status="PENDING") & Q(is_deleted=False)).count(),
            "received" :  models.Tracking.objects.filter(Q(status="RECEIVED") & Q(is_deleted=False)).count(),
        }
        cancellations = {
            "total" :  models.Cancellation.objects.filter(Q(is_deleted=False)).count(),
            "pending" :  models.Cancellation.objects.filter(Q(status="PENDING") & Q(is_deleted=False)).count(),
            "approved" :  models.Cancellation.objects.filter(Q(status="APPROVED") & Q(is_deleted=False)).count(),
        }

        resp = {
            "trackings": trackings,
            "cancellations": cancellations
        }

        return Response(resp, status=status.HTTP_200_OK)