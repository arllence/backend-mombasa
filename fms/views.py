import calendar
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
from fms import models
from fms import serializers
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import User, Sendmail, SRRSDepartment, SubDepartment, OHC
from fms.utils import shared_fxns
from django.db.models import Sum
from django.core.mail import send_mail
from django.utils import timezone

from rest_framework.pagination import PageNumberPagination

# Get an instance of a logger
logger = logging.getLogger(__name__)

class FmsViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="incident",
            url_name="incident")
    def incident(self, request):
        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            # payload = request.data

            payload = json.loads(request.data['payload'])
            attachment = request.FILES.get('attachments', None)

            serializer = serializers.IncidentSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                type_of_incident = payload['type_of_incident']
                priority = payload['priority']
                department = payload['department']
                location = payload['location']
                affected_person_name = payload['affected_person_name']
                person_affected = payload['person_affected']
                date_of_incident = payload['date_of_incident']
                time_of_incident = payload['time_of_incident']
                type_of_issue = payload['type_of_issue']
                subject = payload['subject']
                message = payload['message']

                ohc = payload.get('ohc') or None
                ks_number = payload.get('ks_number') or None
                affected_person_phone = payload.get('affected_person_phone') or None


                uid = shared_fxns.generate_unique_identifier()



                try:
                    department = SRRSDepartment.objects.get(id=department)
                except Exception as e:
                    return Response({"details": "Unknown Department"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    location = SubDepartment.objects.get(id=location)
                except Exception as e:
                    return Response({"details": "Unknown Location"}, status=status.HTTP_400_BAD_REQUEST)
                
                if ohc:
                    try:
                        ohc = OHC.objects.get(id=ohc)
                    except Exception as e:
                        return Response({"details": "Unknown OHC "}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():
                    raw = {
                        "department": department,
                        "location": location,
                        "created_by": authenticated_user,
                        "type_of_incident": type_of_incident,
                        "priority": priority,
                        "attachment": attachment,
                        "affected_person_name": affected_person_name,
                        "person_affected": person_affected,
                        "date_of_incident": date_of_incident,
                        "time_of_incident": time_of_incident,
                        "type_of_issue": type_of_issue,
                        "ohc": ohc,
                        "subject": subject,
                        "message": message,
                        "ks_number": ks_number,
                        "affected_person_phone": affected_person_phone,
                        "uid": uid
                    }

                    incident = models.Incident.objects.create(
                        **raw
                    )

                    # create track status change
                    raw = {
                        "incident": incident,
                        "status": "SUBMITTED",
                        "status_for": "/".join(roles),
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)

                    # Notify Platform Admins
                    emails = list(get_user_model().objects.filter(Q(groups__name__in=['FMS_ADMIN'])).values_list('email', flat=True))
                    subject = f"New Incident Reported: {uid} .  [FMS-AKHK]"
                    message = f"Hello. \nNew Incident: {uid} from department: {department.name}, \nhas been raised by: {request.user.first_name} {request.user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending Assigning.\n\nRegards\nFMS-AKHK"

                    try:
                        if emails:
                            mail = {
                                "email" : list(set(emails)), 
                                "subject" : subject,
                                "message" : message,
                            }
                            
                            Sendmail.objects.create(**mail)
                    except Exception as e:
                        logger.error(e)

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Incident Request created", f"Incident Request Id: {incident.id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "PUT":

            payload = json.loads(request.data['payload'])
            attachment = request.FILES.get('attachment', None)

            
            serializer = serializers.PutIncidentSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                type_of_incident = payload['type_of_incident']
                priority = payload['priority']
                department = payload['department']
                location = payload['location']
                affected_person_name = payload['affected_person_name']
                person_affected = payload['person_affected']
                date_of_incident = payload['date_of_incident']
                time_of_incident = payload['time_of_incident']
                type_of_issue = payload['type_of_issue']
                subject = payload['subject']
                message = payload['message']

                ohc = payload.get('ohc') or None
                ks_number = payload.get('ks_number') or None
                affected_person_phone = payload.get('affected_person_phone') or None


                uid = shared_fxns.generate_unique_identifier()

                try:
                    incidentInstance = models.Incident.objects.get(id=request_id)
                except Exception as e:
                    return Response({"details": "Unknown Incident"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    department = SRRSDepartment.objects.get(id=department)
                except Exception as e:
                    return Response({"details": "Unknown Department"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    location = SubDepartment.objects.get(id=location)
                except Exception as e:
                    return Response({"details": "Unknown Location"}, status=status.HTTP_400_BAD_REQUEST)
                
                if ohc:
                    try:
                        ohc = OHC.objects.get(id=ohc)
                    except Exception as e:
                        return Response({"details": "Unknown OHC "}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():
                    raw = {
                        "department": department,
                        "location": location,
                        "created_by": authenticated_user,
                        "type_of_incident": type_of_incident,
                        "priority": priority,
                        "affected_person_name": affected_person_name,
                        "person_affected": person_affected,
                        "date_of_incident": date_of_incident,
                        "time_of_incident": time_of_incident,
                        "type_of_issue": type_of_issue,
                        "ohc": ohc,
                        "subject": subject,
                        "message": message,
                        "ks_number": ks_number,
                        "affected_person_phone": affected_person_phone,
                        "uid": uid
                    }  

                    models.Incident.objects.filter(Q(id=request_id)).update(**raw)

                    if attachment:
                        incidentInstance.attachment = attachment
                        incidentInstance.save()

                    # create track status change
                    raw = {
                        "incident": incidentInstance,
                        "status": "EDITED",
                        "status_for": "/".join(roles),
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Incident Request updated", f"Incident Id: {incidentInstance.id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

  
        elif request.method == "PATCH":
            # close this incident
            payload = request.data           
            serializer = serializers.PatchIncidentSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                comments = payload.get('comments') or None
                try:
                    incidentInstance = models.Incident.objects.get(id=request_id)
                except Exception as e:
                    return Response({"details": "Unknown Incident"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    incidentInstance.status = 'CLOSED'
                    incidentInstance.closed_by = request.user
                    incidentInstance.save()

                    # track status change
                    raw = {
                        "incident": incidentInstance,
                        "status": "CLOSED",
                        "status_for": '/'.join(roles),
                        "action_by": request.user,
                    }
                    models.StatusChange.objects.create(**raw)

                    # note comments
                    if comments:
                        raw = {
                            "owner": request.user,
                            "incident": incidentInstance,
                            "note": comments,
                        }
                        models.Note.objects.create(**raw)


                    # Notify Platform Admins
                    emails = list(get_user_model().objects.filter(Q(groups__name__in=['FMS_ADMIN'])).values_list('email', flat=True))
                    subject = f"Incident {incidentInstance.uid} Closed [FMS-AKHK]"
                    message = f"Hello. \nIncident: {incidentInstance.uid} from department: {incidentInstance.department.name}, \nhas been closed by: {request.user.first_name} {request.user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.\n\nRegards\nFMS-AKHK"

                    emails.append(str(incidentInstance.created_by.email))

                    try:
                        if emails:
                            mail = {
                                "email" : list(set(emails)), 
                                "subject" : subject,
                                "message" : message,
                            }
                            
                            Sendmail.objects.create(**mail)
                    except Exception as e:
                        logger.error(e)

                    return Response('success', status=status.HTTP_200_OK)

            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            query = request.query_params.get('q')
            slim = request.query_params.get('slim')

            if request_id:
                try:
                    resp = models.Incident.objects.get(Q(id=request_id))
                    if slim:
                        resp = serializers.SlimFetchIncidentSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.FetchIncidentSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:

                    if "FMS_ADMIN" in roles or "SUPERUSER" in roles:

                        resp = models.Incident.objects.filter(
                                is_deleted=False
                            ).order_by('-date_created')

                    else:
                        resp = models.Incident.objects.filter(
                                Q(assigned_to=request.user) |
                                Q(created_by=request.user) 
                            ).order_by('-date_created')


                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resp, request)
                    serializer = serializers.SlimFetchIncidentSerializer(
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
                return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
        
            
            with transaction.atomic():
                try:
                    recordInstance = models.Incident.objects.get(id=request_id,created_by=request.user)
                    recordInstance.is_deleted = True
                    recordInstance.status = "DELETED"
                    recordInstance.save()
                    # track status change
                    raw = {
                        "incident": recordInstance,
                        "status": "DELETED",
                        "status_for": '/'.join(roles),
                        "action_by": authenticated_user,
                    }
                    models.StatusChange.objects.create(**raw)

                    return Response('200', status=status.HTTP_200_OK)    
                 
                except Exception as e:
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)    

    
    @action(methods=["POST"],
            detail=False,
            url_path="assign",
            url_name="assign")
    def assign(self, request):

        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        allowed = ["FMS_ADMIN", "SUPERUSER"]

        if not any(role in allowed for role in roles):
            return Response({"details": "Permission Denied !"}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "POST":

            payload = request.data
            roles = user_util.fetchusergroups(request.user.id) 

            serializer = serializers.AssignSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                assigned_to = payload['assign_to']
                comment = payload.get('comment') or None

                try:
                    incidentInstance = models.Incident.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown incident"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    assigned_to = User.objects.get(id=assigned_to)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown assignee"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    incidentInstance.assigned_to = assigned_to
                    incidentInstance.assignee_comment = comment
                    incidentInstance.status = 'ASSIGNED'
                    incidentInstance.save()

                    # track status change
                    raw = {
                        "incident": incidentInstance,
                        "status": 'ASSIGNED',
                        "status_for": '/'.join(roles),
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)


                    # Notify the assignee
                    emails = [assigned_to.email]
                    subject = f"Incident {incidentInstance.uid}  Assigned To You  [FMS-AKHK]"
                    message = f"Hello, \nAn incident of id: {incidentInstance.uid} has been assigned to you\nby {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.\nPending your action.\n\nRegards\nFMS-AKHK"
                    
                    try:
                        mail = {
                            "email" : list(set(emails)), 
                            "subject" : subject,
                            "message" : message,
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        logger.error(e)



                user_util.log_account_activity(
                    authenticated_user, incidentInstance.created_by, "Incident Request Assigned", 
                    f"Assigning Executed UID: {str(incidentInstance.id)}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, 
                                status=status.HTTP_400_BAD_REQUEST)
            

    @action(methods=["POST","GET"],
            detail=False,
            url_path="notes",
            url_name="notes")
    def notes(self, request):

        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        # allowed = ["FMS_ADMIN", "SUPERUSER"]

        # if not any(role in allowed for role in roles):
        #     return Response({"details": "Permission Denied !"}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "POST":

            payload = request.data
            roles = user_util.fetchusergroups(request.user.id) 

            serializer = serializers.NoteSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                comment = payload.get('comments')

                try:
                    incidentInstance = models.Incident.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown incident"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    raw = {
                        "owner": request.user,
                        "incident": incidentInstance,
                        "note": comment,
                    }
                    models.Note.objects.create(**raw)
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    resp = models.Note.objects.filter(Q(incident=request_id))

                    resp = serializers.FetchNoteSerializer(
                        resp, many=True, context={"user_id":request.user.id}).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response([], status=status.HTTP_200_OK)
            

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
                assign_role = user_util.award_role('FMS_ADMIN', str(admin.id))
                if not assign_role:
                    return Response({"details": "Unable to assign role FMS_ADMIN"}, status=status.HTTP_400_BAD_REQUEST)
                
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
                    user_util.revoke_role('FMS_ADMIN', str(user.admin.id))
                    user.delete()
                    return Response('200', status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request "}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"details": "Request incomplete"}, status=status.HTTP_400_BAD_REQUEST)


            

   
class SRRSReportsViewSet(viewsets.ViewSet):
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
        nature_of_hiring = request.query_params.get('nature_of_hiring')
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
            q_filters &= Q(department=department)

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)
            
        if r_status:
            q_filters &= Q(status=r_status)

        if position_type:
            q_filters &= Q(position_type=position_type)

        if nature_of_hiring:
            q_filters &= Q(nature_of_hiring=nature_of_hiring)


        if q_filters:

            resp = models.Recruit.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
            
        else:
            roles = user_util.fetchusergroups(request.user.id)  

            if "HOD" in roles:
                resp = models.Recruit.objects.filter(Q(is_deleted=False) & Q(created_by=request.user)).order_by('-date_created')[:50]

            else:
                resp = models.Recruit.objects.filter(Q(is_deleted=False)).order_by('-date_created')[:50]

        resp = serializers.FetchRecruitSerializer(resp, many=True, context={"user_id":request.user.id}).data

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
        
        
class SRRSAnalyticsViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return []

    @action(methods=["GET",],
            detail=False,
            url_path="general",
            url_name="general")
    def general(self, request):
        roles = user_util.fetchusergroups(request.user.id)
        active_status = ['REQUESTED','CEO APPROVED','HR APPROVED','SLT APPROVED','CLOSED']

        
        if any(role in ['HHR', 'HR', 'HOF', 'CEO', 'SUPERUSER'] for role in roles):
            requests = models.Recruit.objects.filter(Q(is_deleted=False)).count()
            canceled = models.Recruit.objects.filter(Q(status="REFERRED"), is_deleted=False).count()
            declined = models.Recruit.objects.filter(status="DECLINED", is_deleted=False).count()
            pending = models.Recruit.objects.filter(Q(status__in=active_status), is_ceo_approved=False, is_deleted=False).count()
        else:
            requests = models.Recruit.objects.filter(Q(department=request.user.srrs_department) | Q(created_by=request.user), is_deleted=False).count()
            canceled = models.Recruit.objects.filter(Q(department=request.user.srrs_department) |  Q(created_by=request.user), status="REFERRED", is_deleted=False).count()
            declined = models.Recruit.objects.filter(Q(department=request.user.srrs_department) |  Q(created_by=request.user), status="DECLINED", is_deleted=False).count()
            pending = models.Recruit.objects.filter(Q(department=request.user.srrs_department) |  Q(created_by=request.user), status__in=active_status, is_ceo_approved=False, is_deleted=False).count()

        resp = {
            "requests": requests,
            "canceled": canceled,
            "declined": declined,
            "pending": pending
        }

        return Response(resp, status=status.HTTP_200_OK)