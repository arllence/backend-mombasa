import datetime
import json
import logging
from string import Template
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
from ipass import models
from ipass import serializers
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import User, Hods, SRRSDepartment, Sendmail
from ipass.utils import shared_fxns
from django.db.models import Sum
from django.core.mail import send_mail

from mms.utils.custom_pagination import CustomPagination
from rest_framework.viewsets import ViewSetMixin
from rest_framework.pagination import PageNumberPagination

# Get an instance of a logger
logger = logging.getLogger(__name__)

def read_template(filename):
    with open("acl/emails/" + filename, 'r', encoding='utf8') as template_file:
        template_file_content = template_file.read()
        return Template(template_file_content)

class IpassViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="handover",
            url_name="handover")
    def handover(self, request):
        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.CreatePatientSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                admission_no = payload['admission_no']
                illness_severity = payload['illness_severity']
                patient_summary = payload['patient_summary']
                action_list = payload['action_list']
                attestation = payload['attestation']
                synthesis_by_receiver = payload.get('synthesis_by_receiver')
                acknowledgement = payload.get('acknowledgement')
                bio = payload['bio']
                handover_to = payload['handover_to']
                uid = shared_fxns.generate_unique_identifier()

                if not attestation:
                    return Response({"details": "Attestation required"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    handover_to = get_user_model().objects.get(id=handover_to)
                except Exception as e:
                    return Response({"details": "Unknown Doctor"}, status=status.HTTP_400_BAD_REQUEST)

                
                with transaction.atomic():
                    raw = {
                        "uid": uid,
                        "handover_by": authenticated_user,
                        "handover_to": handover_to,
                        "admission_no": admission_no,
                        "illness_severity": illness_severity,
                        "patient_summary": patient_summary,
                        "action_list": action_list,
                        "attestation": attestation,
                        "synthesis_by_receiver": synthesis_by_receiver,
                        "acknowledgement": acknowledgement,
                        "bio": bio
                    } 

                    patientInstance = models.Patient.objects.create(
                        **raw
                    )

                    # track status change
                    raw = {
                        "patient": patientInstance,
                        "status": "SUBMITTED",
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)

                    
                    # Notify selected send to
                    subject = f"[IPASS] Patient Handover {uid} Raised"

                    message = f"""
                        <table class="main" width="100%">
                            <tr>
                                <th style="text-align: left; padding: 6px 0" colspan="5">IPASS DETAILS</th>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Raised By</th>
                                <td style="text-align: left; padding: 5px 0">{authenticated_user.first_name} {authenticated_user.last_name}</td>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Patient Admission No.</th>
                                <td style="text-align: left; padding: 5px 0">{admission_no}</td>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Ward</th>
                                <td style="text-align: left; padding: 5px 0">{bio.get('ward_des')}</td>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Bed</th>
                                <td style="text-align: left; padding: 5px 0"> {bio.get('bed_no')} </td>
                            </tr>
                        </table>
                    """

                    try:
                        message_template = read_template("custom_template.html")
                        call_to_action = 'View Request'
                        platform = 'IPASS HANDOVER TOOL'
                        # for email in emails:
                        uri = f"authentication/auto/{handover_to.email}/{str(patientInstance.id)}"
                        link = "http://172.20.0.42:8012/" + uri
                        approve = link + '/approve'
                        reject = link + '/reject'

                        msg = message_template.substitute(
                            CONTENT=message,
                            LINK=link,
                            PLATFORM=platform,
                            APPROVE=approve,
                            REJECT=reject
                        )
                        mail = {
                            "email" : [handover_to.email], 
                            "subject" : subject,
                            "message" : msg,
                            "is_html": True
                        }

                        Sendmail.objects.create(**mail)

                    except Exception as e:
                        logger.error(e)

                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "PUT":
            payload = request.data

            serializer = serializers.UpdatePatientSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                admission_no = payload['admission_no']
                illness_severity = payload['illness_severity']
                patient_summary = payload['patient_summary']
                action_list = payload['action_list']
                attestation = payload['attestation']
                synthesis_by_receiver = payload.get('synthesis_by_receiver')
                acknowledgement = payload.get('acknowledgement')
                bio = payload['bio']
                handover_to = payload['handover_to']

                if not attestation:
                    return Response({"details": "Attestation required"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    handoverInstance = models.Patient.objects.get(id=request_id)
                except Exception as e:
                    return Response({"details": "Unknown Handover"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    handover_to = get_user_model().objects.get(id=handover_to)
                except Exception as e:
                    return Response({"details": "Unknown Doctor"}, status=status.HTTP_400_BAD_REQUEST)

                
                with transaction.atomic():
                    raw = {
                        "handover_to": handover_to,
                        "admission_no": admission_no,
                        "illness_severity": illness_severity,
                        "patient_summary": patient_summary,
                        "action_list": action_list,
                        "attestation": attestation,
                        "synthesis_by_receiver": synthesis_by_receiver,
                        "acknowledgement": acknowledgement
                    } 

                    models.Patient.objects.filter(Q(id=request_id)).update(
                        **raw
                    )

                    # track status change
                    raw = {
                        "patient": handoverInstance,
                        "status": "EDITED",
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)

                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PATCH":
            # Accepting handover
            payload = request.data
            for key, value in payload.items():
                if not value:
                    return Response({"details": "All fields required"}, status=status.HTTP_400_BAD_REQUEST)
                
            request_id = payload.get('request_id')
            synthesis_by_receiver = payload.get('synthesis_by_receiver')

            del payload['request_id']
            del payload['synthesis_by_receiver']


            try:
                handoverInstance = models.Patient.objects.get(id=request_id)
            except Exception as e:
                return Response({"details": "Unknown handover"}, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                handoverInstance.acknowledgement = payload
                handoverInstance.synthesis_by_receiver = synthesis_by_receiver
                handoverInstance.handover_acceptance_date = datetime.datetime.now()
                handoverInstance.status = 'ACCEPTED'
                handoverInstance.save()

                # track status change
                raw = {
                    "patient": handoverInstance,
                    "status": "ACCEPTED",
                    "action_by": authenticated_user
                }

                models.StatusChange.objects.create(**raw)
                
                return Response('200', status=status.HTTP_200_OK)  


        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            admission_no = request.query_params.get('admission_no')
            query = request.query_params.get('q')

            if request_id:
                try:
                    resp = models.Patient.objects.get(id=request_id)
                    resp = serializers.FetchPatientSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    logger.error(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            elif admission_no:
                try:
                    resp = models.Patient.objects.filter(Q(admission_no=admission_no))
                    resp = serializers.FetchPatientSerializer(resp, many=True, context={"user_id":request.user.id}).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    logger.error(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    if query == 'pending':
                        resp = models.Patient.objects.filter(
                            Q(status='PENDING') & Q(handover_to=request.user)).order_by('-date_created')
                        
                    elif query == 'assigned':
                        resp = models.Patient.objects.filter(
                            Q(handover_to=request.user)).order_by('-date_created')
                        
                    else:
                        resp = models.Patient.objects.all()

                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resp, request)
                    serializer = serializers.FetchPatientSerializer(
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
                    models.Patient.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)   
                 

    @action(methods=["POST", "GET", "PUT", "DELETE"],
            detail=False,
            url_path="doctors",
            url_name="doctors")
    def platform_doctors(self, request):
        # roles = user_util.fetchusergroups(request.user.id)
        if request.method == "POST":
            payload = request.data
            serializer = serializers.PlatformDoctorSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                doctor = payload['doctor']

                try:
                    doctor = User.objects.get(id=doctor)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown User"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Invalid Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                # assign role
                assign_role = user_util.award_role('IPASS', str(doctor.id))
                if not assign_role:
                    return Response({"details": "Unable to assign role IPASS"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    raw = {
                        "doctor": doctor,
                        "created_by": request.user
                    }

                    models.PlatformDoctor.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":
            payload = request.data

            serializer = serializers.UpdatePlatformDoctorSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                doctor = payload['doctor']

                try:
                    request = models.PlatformDoctor.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Invalid Request"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():

                    request.doctor = doctor
                    request.created_by = request.user
                    request.save()

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    request = models.PlatformDoctor.objects.get(Q(id=request_id))
                    request = serializers.FetchPlatformDoctorSerializer(request, many=False).data
                    return Response(request, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:

                    request = models.PlatformDoctor.objects.filter(Q(is_deleted=False)).order_by('-date_created')
                    request = serializers.FetchPlatformDoctorSerializer(request, many=True).data
                    return Response(request, status=status.HTTP_200_OK)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                
        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    user = models.PlatformDoctor.objects.get(id=request_id)
                    user_util.revoke_role('IPASS', str(user.doctor.id))
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
            q_filters &= Q(handover_to=doctor)

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
        
  


        
class TRSAnalyticsViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return []

    @action(methods=["GET",],
            detail=False,
            url_path="general",
            url_name="general")
    def general(self, request):
        roles = user_util.fetchusergroups(request.user.id)

        if 'USER' in roles:
            requests = models.Traveler.objects.filter(Q(is_deleted=False) & Q(traveler=request.user)).count()
            # requested = models.Traveler.objects.filter(Q(status="REQUESTED") & Q(is_deleted=False) & Q(traveler=request.user)).count()
            requested = models.Traveler.objects.filter(Q(status="REQUESTED") | Q(status="RESUBMITTED") & Q(traveler=request.user), is_deleted=False).count()

            closed = models.Traveler.objects.filter(Q(status="CLOSED") & Q(is_deleted=False) & Q(traveler=request.user)).count()
            # assigned = models.Traveler.objects.filter(Q(status="ASSIGNED") & Q(is_deleted=False) & Q(traveler=request.user)).count()
            incomplete = models.Traveler.objects.filter(Q(status="INCOMPLETE") & Q(is_deleted=False) & Q(traveler=request.user)).count()
        else:
            requests = models.Traveler.objects.filter(Q(is_deleted=False)).count()
            requested = models.Traveler.objects.filter(Q(status="REQUESTED") | Q(status="RESUBMITTED"), is_deleted=False).count()
            closed = models.Traveler.objects.filter(Q(status="CLOSED") & Q(is_deleted=False)).count()
            assigned = models.Traveler.objects.filter(Q(status="ASSIGNED") & Q(is_deleted=False)).count()
            incomplete = models.Traveler.objects.filter(Q(status="INCOMPLETE") & Q(is_deleted=False)).count()

        if 'CEO' in roles or 'HOF' in roles:
            requested = models.Traveler.objects.filter(Q(status="APPROVED"), is_ceo_approved=False, is_deleted=False).count()

        resp = {
            "requests": requests,
            "requested": requested,
            "closed": closed,
            # "assigned": assigned,
            "incomplete": incomplete,
        }

        return Response(resp, status=status.HTTP_200_OK)