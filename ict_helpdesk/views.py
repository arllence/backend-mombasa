import calendar
import datetime
import json
import logging
from string import Template
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
from ict_helpdesk import models
from ict_helpdesk import serializers
from ict_helpdesk.utils import shared_fxns
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import User, Sendmail, SRRSDepartment, SubDepartment, OHC
from django.db.models import Sum
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from mms.models import Quote as MMDQuote
from django.db.models import F, ExpressionWrapper, DateTimeField, DurationField

from rest_framework.pagination import PageNumberPagination

from intranet.serializers import FullFetchDepartmentSerializer
from acl.utils import track_user


# Get an instance of a logger
logger = logging.getLogger(__name__)

def read_template(filename):
    with open("acl/emails/" + filename, 'r', encoding='utf8') as template_file:
        template_file_content = template_file.read()
        return Template(template_file_content)

class GenericsViewSet(viewsets.ViewSet):
    permission_classes = (AllowAny,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["GET"], detail=False, url_path="departments",url_name="departments")
    def departments(self, request):

        resp = SRRSDepartment.objects.all().order_by('name')
        serializer = FullFetchDepartmentSerializer(
            resp, many=True, context={"user_id":request.user.id})
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(methods=["POST", "GET", "PUT"],
            detail=False,
            url_path="job-types",
            url_name="job-types")
    def job_types(self, request):
        if request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    resp = models.JobType.objects.get(Q(id=request_id))
                    resp = serializers.FetchJobTypeSerializer(resp,many=False).data
                    return Response(resp, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Job Type"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    resp = models.JobType.objects.filter(is_deleted=False).order_by('name')
                    resp = serializers.FetchJobTypeSerializer(resp,many=True).data
                    return Response(resp, status=status.HTTP_200_OK)
                    
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)


    @action(methods=["POST", "GET", "PUT"],
            detail=False,
            url_path="categories",
            url_name="categories")
    def categories(self, request): 
        if request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    resp = models.Category.objects.get(Q(id=request_id))
                    resp = serializers.FetchJobTypeSerializer(resp,many=False).data
                    return Response(resp, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown category"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    resp = models.Category.objects.filter(is_deleted=False).order_by('name')
                    resp = serializers.FetchCategorySerializer(resp,many=True).data
                    return Response(resp, status=status.HTTP_200_OK)
                    
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
                
    @action(methods=["POST", "GET", "PUT"],
            detail=False,
            url_path="facilities",
            url_name="facilities")
    def facilities(self, request): 
        if request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    resp = models.Facility.objects.get(Q(id=request_id))
                    resp = serializers.FetchJobTypeSerializer(resp,many=False).data
                    return Response(resp, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown facility"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    resp = models.Facility.objects.filter(is_deleted=False).order_by('name')
                    resp = serializers.FetchFacilitySerializer(resp,many=True).data
                    return Response(resp, status=status.HTTP_200_OK)
                    
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)

 
    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="issues",
            url_name="issues")
    def issues(self, request):
        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":
            
            attachment = request.FILES.get('attachments', None)
            forwarded = request.query_params.get('forwarded', None)

            if forwarded:
                payload = request.data
            else:
                payload = json.loads(request.data['payload'])


            serializer = serializers.GenericIssueSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                # job_type = payload['job_type'] or None
                department = payload['department']
                issue = payload['issue']
                name = payload['name']
                email = payload['email']
                category = payload.get('category')
                facility = payload['facility']
                subject = payload['subject']
                # issue_type = payload['issue_type']

                uid = shared_fxns.generate_unique_identifier()

                # track user
                try:
                    track_user.get_client_info(request,'ict_helpdesk', uid)
                except:
                    pass

                if not name or not email:
                    return Response({"details": "Name and Email Required"}, status=status.HTTP_400_BAD_REQUEST)

                if email:
                    try:
                        user = get_user_model().objects.get(email=email)
                    except:
                        user = None

                try:
                    department = SRRSDepartment.objects.get(id=department)
                except Exception as e:
                    return Response({"details": "Unknown Department"}, status=status.HTTP_400_BAD_REQUEST)
                
                # if issue_type:
                #     try:
                #         job_type = models.JobType.objects.get(id=issue_type)
                #     except Exception as e:
                #         return Response({"details": "Unknown job type"}, status=status.HTTP_400_BAD_REQUEST)
                    
                if category:
                    try:
                        category = models.Category.objects.get(id=category)
                    except Exception as e:
                        return Response({"details": "Unknown category"}, status=status.HTTP_400_BAD_REQUEST)
                    
                try:
                    if not forwarded:
                        facility = models.Facility.objects.get(id=facility)
                    else:
                        facility = models.Facility.objects.filter(name__icontains=facility).first()
                except Exception as e:
                    facility = None
                    # return Response({"details": "Unknown facility"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    raw = {
                        "department": department,
                        "created_by": user,
                        "attachment": attachment,
                        "issue": issue,
                        "facility": facility,
                        "subject": subject,
                        "email": email,
                        "name": name,
                        "uid": uid
                    }


                    issueInstance = models.Issue.objects.create(
                        **raw
                    )

                    # create track status change
                    raw = {
                        "issue": issueInstance,
                        "status": "SUBMITTED",
                        "status_for": "/".join(roles),
                        "action_by": user
                    }

                    models.StatusChange.objects.create(**raw)

                    # Notify Platform Admins
                    # emails = list(get_user_model().objects.filter(Q(groups__name__in=['ICT_ADMIN']), is_slt=False).values_list('email', flat=True))
                    emails = list(models.PlatformAdmin.objects.filter(Q(is_slt=False) & ~Q(admin__email='bobkings.otieno@akhskenya.org')).values_list('admin__email', flat=True))
                    subject = f"[ICT HELPDESK] {subject}"
                    message = f"""
                        <table border="1" class='signature-table'>
                            <tr>
                                <th colspan='5'>Ticket Details</th>
                            </tr>
                            <tr>
                                <th>Facility</th>
                                <td>{facility.name if facility else 'N/A'}</td>
                            </tr>
                            <tr>
                                <th>Department</th>
                                <td>{department.name}</td>
                            </tr>
                            <tr>
                                <th>Date and Time</th>
                                <td>{str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}</td>
                            </tr>
                            <tr>
                                <th>Subject</th>
                                <td>{subject}</td>
                            </tr>
                            <tr>
                                <th>Issue</th>
                                <td>{issue}</td>
                            </tr>
                        </table>


                    """
                    uri = f"requests/view/{str(issueInstance.id)}"
                    link = "http://172.20.0.42:8011/" + uri
                    platform = 'View Ticket'

                    message_template = read_template("general_template.html")
                    message = message_template.substitute(
                        CONTENT=message,
                        LINK=link,
                        PLATFORM=platform
                    )

                    try:
                        if emails:
                            mail = {
                                "email" : list(set(emails)), 
                                "subject" : subject,
                                "message" : message,
                                "is_html": True
                            }
                            
                            Sendmail.objects.create(**mail)
                    except Exception as e:
                        logger.error(e)

                if user:
                    user_util.log_account_activity(
                        user, user, "Issue Request created", f"Issue Request Id: {issueInstance.id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            query = request.query_params.get('q')
            slim = request.query_params.get('slim')

            if request_id:
                try:
                    resp = models.Issue.objects.get(Q(id=request_id))
                    if slim:
                        resp = serializers.SlimFetchIssueSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.FetchIssueSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            

    @action(methods=["POST"],
            detail=False,
            url_path="owner-acknowledgement",
            url_name="owner-acknowledgement")
    def owner_acknowledgement(self, request):

        if request.method == "POST":

            payload = request.data
            roles = user_util.fetchusergroups(request.user.id) 

            serializer = serializers.AcknowledgementSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                action = payload['action']

                try:
                    issueInstance = models.Issue.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown issue"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                if issueInstance.is_acknowledged:
                    return Response({"details": "Already Acknowledged"}, 
                                    status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    user = None
                    if issueInstance.created_by:
                        user = issueInstance.created_by

                    status_for = 'ACKNOWLEDGED' if action == 'DONE' else 'NOT DONE'
                    # track status change
                    raw = {
                        "issue": issueInstance,
                        "status": status_for,
                        "status_for": 'REQUESTOR',
                        "action_by": user
                    }

                    models.StatusChange.objects.create(**raw)

                    if action == 'NOT DONE':
                        is_existing = models.StatusChange.objects.filter(
                            issue=issueInstance, 
                            status=status_for
                        ).exists()
                        if is_existing:
                            return Response({"details": "Already marked as NOT DONE. Try adding a note instead."},status=status.HTTP_400_BAD_REQUEST)



                    # Notify Admins
                    # emails = list(get_user_model().objects.filter(Q(groups__name__in=['ICT_ADMIN'])).values_list('email', flat=True))
                    emails = []
                    assignees = models.Assignees.objects.filter(Q(issue=issueInstance))
                    for assignee in assignees:
                        emails.append(assignee.assignee.email)
                        if assignee.assigned_by:
                            emails.append(assignee.assigned_by.email)
                    if issueInstance.assigned_to:
                        emails.append(issueInstance.assigned_to.email)

                    subject = f"[ICT HELPDESK] Ticket {issueInstance.uid}  Status"
                    if action == 'DONE':
                        issueInstance.is_acknowledged = True
                        issueInstance.save()
                        message = f"Hello. \nTicket of id: {issueInstance.uid} has been Acknowledged by requestor as Completed / Solved\n on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.\nPending closure.\n"

                    if action == 'NOT DONE':
                        message = f"Hello. \nTicket of id: {issueInstance.uid} has been marked as NOT DONE by requestor \n on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.\nPending review.\n"

                    uri = f"requests/view/{str(issueInstance.id)}"
                    link = "http://172.20.0.42:8011/" + uri
                    platform = 'View Issue'

                    message_template = read_template("general_template.html")
                    message = message_template.substitute(
                        CONTENT=message,
                        LINK=link,
                        PLATFORM=platform
                    )
                    
                    try:
                        mail = {
                            "email" : list(set(emails)), 
                            "subject" : subject,
                            "message" : message,
                            "is_html": True
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        logger.error(e)

                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, 
                                status=status.HTTP_400_BAD_REQUEST)   
            
    
    @action(methods=["POST","GET"],
            detail=False,
            url_path="notes",
            url_name="notes")
    def notes(self, request):

        if request.method == "POST":

            payload = request.data
            roles = user_util.fetchusergroups(request.user.id) 

            serializer = serializers.NoteSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                comment = payload.get('comments')

                try:
                    issueInstance = models.Issue.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown ticket"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                if issueInstance.created_by:
                     user = issueInstance.created_by
                else:
                    if issueInstance.email:
                        try:
                            user = get_user_model().objects.get(email=issueInstance.email)
                        except:
                            return Response({"details": "Login to add note"}, 
                                    status=status.HTTP_400_BAD_REQUEST)


                
                with transaction.atomic():
                    raw = {
                        "owner": user,
                        "issue": issueInstance,
                        "note": comment
                    }
                    models.Note.objects.create(**raw)

                # Send Note Notifications
                emails = []
                assignees = models.Assignees.objects.filter(Q(issue=issueInstance))
                for assignee in assignees:
                    emails.append(assignee.assignee.email)
                    if assignee.assigned_by:
                        emails.append(assignee.assigned_by.email)
                if issueInstance.assigned_to:
                    emails.append(issueInstance.assigned_to.email)
                try:
                    emails.remove(request.user.email)
                except:
                    pass
                subject = f"[ICT HELPDESK] Note Issued for {issueInstance.uid}"
                message = f"Hello. <br>A note has been added for Ticket of id: {issueInstance.uid} <br>by {user.first_name} {user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.<br><b>Note:</b><br><i>{comment}.</i>\n"

                uri = f"requests/view/{str(issueInstance.id)}"
                link = "http://172.20.0.42:8011/" + uri
                platform = 'View Issue'

                message_template = read_template("general_template.html")
                message = message_template.substitute(
                    CONTENT=message,
                    LINK=link,
                    PLATFORM=platform
                )
                
                try:
                    mail = {
                        "email" : list(set(emails)), 
                        "subject" : subject,
                        "message" : message,
                        "is_html": True
                    }
                    Sendmail.objects.create(**mail)
                except Exception as e:
                    logger.error(e)

                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    resp = models.Note.objects.filter(Q(issue=request_id))

                    resp = serializers.FetchNoteSerializer(
                        resp, many=True, context={"user_id":request.user.id}).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response([], status=status.HTTP_200_OK)



class HelpDeskViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    

    @action(methods=["POST", "GET", "PUT", "DELETE"],
            detail=False,
            url_path="sections",
            url_name="sections")
    def Sections(self, request):
        roles = user_util.fetchusergroups(request.user.id)
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
                    models.Section.objects.create(**raw)

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
                    requestInstance = models.Section.objects.get(id=request_id)
                except Exception as e:
                    logger.error(e)
                    return Response({"details": "Unknown Section"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    requestInstance.name = name
                    requestInstance.save()

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    resp = models.Section.objects.get(Q(id=request_id))
                    resp = serializers.FetchSectionSerializer(resp,many=False).data
                    return Response(resp, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Section"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    resp = models.Section.objects.filter(is_deleted=False).order_by('name')
                    resp = serializers.FetchSectionSerializer(resp,many=True).data
                    return Response(resp, status=status.HTTP_200_OK)
                    
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Request incomplete"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                raw = {"is_deleted":True}
                models.Section.objects.filter(id=request_id).update(**raw)
                return Response('200', status=status.HTTP_200_OK)
            except (ValidationError, ObjectDoesNotExist):
                return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                print(e)
                return Response({"details": "Cannot complete request "}, status=status.HTTP_400_BAD_REQUEST)
                
    

    @action(methods=["POST", "GET", "PUT", "DELETE"],
            detail=False,
            url_path="job-types",
            url_name="job-types")
    def JobType(self, request):
        roles = user_util.fetchusergroups(request.user.id)
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
                    models.JobType.objects.create(**raw)

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
                    requestInstance = models.JobType.objects.get(id=request_id)
                except Exception as e:
                    logger.error(e)
                    return Response({"details": "Unknown Job Type"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    requestInstance.name = name
                    requestInstance.save()

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    resp = models.JobType.objects.get(Q(id=request_id))
                    resp = serializers.FetchJobTypeSerializer(resp,many=False).data
                    return Response(resp, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Job Type"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    resp = models.JobType.objects.filter(is_deleted=False).order_by('name')
                    resp = serializers.FetchJobTypeSerializer(resp,many=True).data
                    return Response(resp, status=status.HTTP_200_OK)
                    
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Request incomplete"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                raw = {"is_deleted":True}
                models.JobType.objects.filter(id=request_id).update(**raw)
                return Response('200', status=status.HTTP_200_OK)
            except (ValidationError, ObjectDoesNotExist):
                return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                print(e)
                return Response({"details": "Cannot complete request "}, status=status.HTTP_400_BAD_REQUEST)



    @action(methods=["POST", "GET", "PUT", "DELETE"],
            detail=False,
            url_path="equipment-types",
            url_name="equipment-types")
    def EquipmentType(self, request):
        roles = user_util.fetchusergroups(request.user.id)
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
                    models.EquipmentType.objects.create(**raw)

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
                    requestInstance = models.EquipmentType.objects.get(id=request_id)
                except Exception as e:
                    logger.error(e)
                    return Response({"details": "Unknown Equipment Type"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    requestInstance.name = name
                    requestInstance.save()

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    resp = models.EquipmentType.objects.get(Q(id=request_id))
                    resp = serializers.FetchJobTypeSerializer(resp,many=False).data
                    return Response(resp, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Equipment Type"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    resp = models.EquipmentType.objects.filter(is_deleted=False).order_by('name')
                    resp = serializers.FetchEquipmentTypeSerializer(resp,many=True).data
                    return Response(resp, status=status.HTTP_200_OK)
                    
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Request incomplete"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                raw = {"is_deleted":True}
                models.EquipmentType.objects.filter(id=request_id).update(**raw)
                return Response('200', status=status.HTTP_200_OK)
            except (ValidationError, ObjectDoesNotExist):
                return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                print(e)
                return Response({"details": "Cannot complete request "}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST", "GET", "PUT", "DELETE"],
            detail=False,
            url_path="facilities",
            url_name="facilities")
    def Facility(self, request):
        roles = user_util.fetchusergroups(request.user.id)
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
                    models.Facility.objects.create(**raw)

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
                    requestInstance = models.Facility.objects.get(id=request_id)
                except Exception as e:
                    logger.error(e)
                    return Response({"details": "Unknown Facility"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    requestInstance.name = name
                    requestInstance.save()

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    resp = models.Facility.objects.get(Q(id=request_id))
                    resp = serializers.FetchFacilitySerializer(resp,many=False).data
                    return Response(resp, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Facility"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    resp = models.Facility.objects.filter(is_deleted=False).order_by('name')
                    resp = serializers.FetchFacilitySerializer(resp,many=True).data
                    return Response(resp, status=status.HTTP_200_OK)
                    
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Request incomplete"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                raw = {"is_deleted":True}
                models.Facility.objects.filter(id=request_id).update(**raw)
                return Response('200', status=status.HTTP_200_OK)
            except (ValidationError, ObjectDoesNotExist):
                return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                print(e)
                return Response({"details": "Cannot complete request "}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST", "GET", "PUT", "DELETE"],
            detail=False,
            url_path="categories",
            url_name="categories")
    def Category(self, request):
        roles = user_util.fetchusergroups(request.user.id)
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
                    models.Category.objects.create(**raw)

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
                    requestInstance = models.Category.objects.get(id=request_id)
                except Exception as e:
                    logger.error(e)
                    return Response({"details": "Unknown Category"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    requestInstance.name = name
                    requestInstance.save()

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    resp = models.Category.objects.get(Q(id=request_id))
                    resp = serializers.FetchCategorySerializer(resp,many=False).data
                    return Response(resp, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Category"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    resp = models.Category.objects.filter(is_deleted=False).order_by('name')
                    resp = serializers.FetchCategorySerializer(resp,many=True).data
                    return Response(resp, status=status.HTTP_200_OK)
                    
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Request incomplete"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                raw = {"is_deleted":True}
                models.Category.objects.filter(id=request_id).update(**raw)
                return Response('200', status=status.HTTP_200_OK)
            except (ValidationError, ObjectDoesNotExist):
                return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                print(e)
                return Response({"details": "Cannot complete request "}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST", "GET", "PUT", "DELETE"],
            detail=False,
            url_path="priorities",
            url_name="priorities")
    def Priority(self, request):
        roles = user_util.fetchusergroups(request.user.id)
        if request.method == "POST":
            payload = request.data
            serializer = serializers.PrioritySerializer(
                data=payload, many=False)
            if serializer.is_valid():
                name = payload['name']
                expected_closure = payload['expected_closure']

                with transaction.atomic():
                    raw = {
                        "name": name,
                        "expected_closure": expected_closure
                    }
                    models.Priority.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":
            payload = request.data

            serializer = serializers.PutPrioritySerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                name = payload['name']
                expected_closure = payload['expected_closure']

                try:
                    requestInstance = models.Priority.objects.get(id=request_id)
                except Exception as e:
                    logger.error(e)
                    return Response({"details": "Unknown Priority"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    requestInstance.name = name
                    requestInstance.expected_closure = expected_closure
                    requestInstance.save()

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    resp = models.Priority.objects.get(Q(id=request_id))
                    resp = serializers.FetchPrioritySerializer(resp,many=False).data
                    return Response(resp, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Priority"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    resp = models.Priority.objects.filter(is_deleted=False).order_by('name')
                    resp = serializers.FetchPrioritySerializer(resp,many=True).data
                    return Response(resp, status=status.HTTP_200_OK)
                    
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Request incomplete"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                raw = {"is_deleted":True}
                models.Priority.objects.filter(id=request_id).update(**raw)
                return Response('200', status=status.HTTP_200_OK)
            except (ValidationError, ObjectDoesNotExist):
                return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                print(e)
                return Response({"details": "Cannot complete request "}, status=status.HTTP_400_BAD_REQUEST)
                 

    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="issues",
            url_name="issues")
    def issue(self, request):
        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            # payload = request.data

            payload = json.loads(request.data['payload'])
            attachment = request.FILES.get('attachments', None)

            # track user
            try:
                track_user.get_client_info(request,'ict_helpdesk')
            except:
                pass

            serializer = serializers.IssueSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                department = payload['department']
                issue = payload['issue']
                category = payload['category']
                facility = payload['facility']
                subject = payload['subject']
                issue_type = payload['issue_type']

                uid = shared_fxns.generate_unique_identifier()

                # track user
                try:
                    track_user.get_client_info(request, 'ict_helpdesk', uid)
                except:
                    pass

                try:
                    department = SRRSDepartment.objects.get(id=department)
                except Exception as e:
                    return Response({"details": "Unknown Department"}, status=status.HTTP_400_BAD_REQUEST)
                
                if issue_type:
                    try:
                        issue_type = models.JobType.objects.get(id=issue_type)
                    except Exception as e:
                        return Response({"details": "Unknown job type"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    category = models.Category.objects.get(id=category)
                except Exception as e:
                    return Response({"details": "Unknown category"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    facility = models.Facility.objects.get(id=facility)
                except Exception as e:
                    return Response({"details": "Unknown facility"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    raw = {
                        "department": department,
                        "job_type": issue_type,
                        "created_by": authenticated_user,
                        "attachment": attachment,
                        "issue": issue,
                        "category": category,
                        "facility": facility,
                        "subject": subject,
                        "uid": uid
                    }

                    issue = models.Issue.objects.create(
                        **raw
                    )

                    # create track status change
                    raw = {
                        "issue": issue,
                        "status": "SUBMITTED",
                        "status_for": "/".join(roles),
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)

                    # Notify Platform Admins
                    # emails = list(get_user_model().objects.filter(Q(groups__name__in=['ICT_ADMIN'])).values_list('email', flat=True))
                    emails = list(models.PlatformAdmin.objects.filter(Q(is_slt=False)  & ~Q(admin__email='bobkings.otieno@akhskenya.org')).values_list('admin__email', flat=True))
                    subject = f"[ICT HELPDESK] New Ticket Reported: {uid} ."
                    message = f"Hello. \nNew Ticket: {uid} from department: {department.name}, \nhas been raised by: {request.user.first_name} {request.user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending Assigning.\n\nRegards\nICT-HELPDESK-AKHK\n\n"

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
                    authenticated_user, authenticated_user, "Issue Request created", f"Issue Request Id: {issue.id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "PUT":

            payload = json.loads(request.data['payload'])
            attachment = request.FILES.get('attachment', None)

            
            serializer = serializers.PutIssueSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                issue_type = payload['issue_type']
                department = payload['department']
                issue = payload['issue']
                category = payload['category']
                facility = payload['facility']
                subject = payload['subject']


                try:
                    issueInstance = models.Issue.objects.get(id=request_id)
                except Exception as e:
                    return Response({"details": "Unknown Issue"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    department = SRRSDepartment.objects.get(id=department)
                except Exception as e:
                    return Response({"details": "Unknown Department"}, status=status.HTTP_400_BAD_REQUEST)
                
                if issue_type:
                    try:
                        job_type = models.JobType.objects.get(id=issue_type)
                    except Exception as e:
                        return Response({"details": "Unknown job type"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    category = models.Category.objects.get(id=category)
                except Exception as e:
                    return Response({"details": "Unknown category"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    facility = models.Facility.objects.get(id=facility)
                except Exception as e:
                    return Response({"details": "Unknown facility"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    raw = {
                        "department": department,
                        "job_type": job_type,
                        "issue": issue,
                        "facility": facility,
                        "category": category,
                        "subject": subject
                    }  

                    models.Issue.objects.filter(Q(id=request_id)).update(**raw)

                    if attachment:
                        issueInstance.attachment = attachment
                        issueInstance.save()

                    # create track status change
                    raw = {
                        "issue": issueInstance,
                        "status": "EDITED",
                        "status_for": "/".join(roles),
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Issue Request updated", f"Issue Id: {issueInstance.id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

  
        elif request.method == "PATCH":
            # close this incident
            payload = request.data           
            serializer = serializers.PatchIssueSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                comments = payload.get('comments') or None

                try:
                    issueInstance = models.Issue.objects.get(id=request_id)
                except Exception as e:
                    return Response({"details": "Unknown Issue"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    issueInstance.status = 'CLOSED'
                    issueInstance.closed_by = request.user
                    issueInstance.date_closed = datetime.datetime.now()
                    if not issueInstance.date_completed:
                        issueInstance.date_completed = datetime.datetime.now()
                    issueInstance.save()

                    # track status change
                    raw = {
                        "issue": issueInstance,
                        "status": "CLOSED",
                        "status_for": '/'.join(roles),
                        "action_by": request.user,
                    }
                    models.StatusChange.objects.create(**raw)

                    # note comments
                    if comments:
                        raw = {
                            "owner": request.user,
                            "issue": issueInstance,
                            "note": comments,
                        }
                        models.Note.objects.create(**raw)


                    # Notify Platform Admins
                    # emails = list(get_user_model().objects.filter(Q(groups__name__in=['ICT_ADMIN']) & Q(is_slt=False)).values_list('email', flat=True))
                    emails = []
                    subject = f"[ICT HELPDESK] Ticket {issueInstance.uid} Closed "
                    message = f"Hello. \nTicket: {issueInstance.uid} from department: {issueInstance.department.name}, \nhas been closed by: {request.user.first_name} {request.user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.\n\nRegards\nICT-HELPDESK-AKHK\n\n"

                    if issueInstance.created_by:
                        emails.append(str(issueInstance.created_by.email))
                    elif issueInstance.email:
                        emails.append(str(issueInstance.email))

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
                    resp = models.Issue.objects.get(Q(id=request_id))
                    if slim:
                        resp = serializers.SlimFetchIssueSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.FetchIssueSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:

                    if "ICT_ADMIN" in roles or "SUPERUSER" in roles:
                        if query == 'unassigned':
                            resp = models.Issue.objects.filter(
                                Q(status__in=['SUBMITTED','REOPENED']), is_deleted=False
                            ).order_by('-date_created')
                        elif query == 'assigned':
                            resp = models.Issue.objects.filter(
                                Q(status__in=['ASSIGNED']), is_deleted=False
                            ).order_by('-date_assigned')
                        elif query == 'closed':
                            resp = models.Issue.objects.filter(
                                Q(status__in=['CLOSED']), is_deleted=False
                            ).order_by('-date_closed')
                        elif query == 'my-tickets':
                            resp = models.Issue.objects.filter(
                                Q(assigned_to=request.user) |
                                Q(ict_assignee_issue_instance__assignee=request.user),
                                status__in=['ASSIGNED'], is_deleted=False
                            ).order_by('-date_assigned')
                        elif query == 'overdue':
                            from django.utils import timezone
                            now = timezone.now()
                            resp = models.Issue.objects.annotate(
                                expected_closure_datetime=ExpressionWrapper(
                                    F('date_assigned') + 
                                    ExpressionWrapper(
                                        F('priority__expected_closure') * timedelta(hours=1),
                                        output_field=DurationField()
                                    ),
                                    output_field=DateTimeField()
                                )
                            ).filter(
                                expected_closure_datetime__lt=now,
                                is_deleted=False,
                                date_assigned__isnull=False,
                                date_closed__isnull=True,
                                date_completed__isnull=True
                            ).order_by('-date_assigned')
                        else:
                            resp = models.Issue.objects.filter(
                                    Q(status__in=['COMPLETED']),
                                    is_deleted=False
                                ).order_by('-date_completed')

                    else:
                        if query == 'unassigned':
                            resp = models.Issue.objects.filter(
                                Q(assigned_to=request.user) |
                                Q(created_by=request.user) | 
                                Q(department__in=SRRSDepartment.objects.filter(hod_department__hod=request.user)) |
                                Q(ict_assignee_issue_instance__assignee=request.user),
                                status__in=['SUBMITTED','REOPENED']
                            ).order_by('-date_created')
                        elif query == 'assigned':
                            resp = models.Issue.objects.filter(
                                    Q(assigned_to=request.user) |
                                    Q(created_by=request.user) | 
                                    Q(department__in=SRRSDepartment.objects.filter(hod_department__hod=request.user)) |
                                    Q(ict_assignee_issue_instance__assignee=request.user),
                                    status__in=['ASSIGNED']
                                ).order_by('-date_assigned')
                        elif query == 'my-tickets':
                            resp = models.Issue.objects.filter(
                                    Q(assigned_to=request.user) |
                                    Q(department__in=SRRSDepartment.objects.filter(hod_department__hod=request.user)) |
                                    Q(ict_assignee_issue_instance__assignee=request.user),
                                    status__in=['ASSIGNED']
                                ).order_by('-date_assigned')
                        elif query == 'closed':
                            resp = models.Issue.objects.filter(
                                    Q(assigned_to=request.user) |
                                    Q(created_by=request.user) | 
                                    Q(department__in=SRRSDepartment.objects.filter(hod_department__hod=request.user)) |
                                    Q(ict_assignee_issue_instance__assignee=request.user),
                                    status__in=['CLOSED']
                                ).order_by('-date_closed')
                        elif query == 'overdue':
                            from django.utils import timezone
                            now = timezone.now()
                            resp = models.Issue.objects.annotate(
                                expected_closure_datetime=ExpressionWrapper(
                                    F('date_assigned') + 
                                    ExpressionWrapper(
                                        F('priority__expected_closure') * timedelta(hours=1),
                                        output_field=DurationField()
                                    ),
                                    output_field=DateTimeField()
                                )
                            ).filter(
                                Q(assigned_to=request.user) |
                                Q(created_by=request.user) | 
                                Q(department__in=SRRSDepartment.objects.filter(hod_department__hod=request.user)) |
                                Q(ict_assignee_issue_instance__assignee=request.user),
                                expected_closure_datetime__lt=now,
                                is_deleted=False,
                                date_assigned__isnull=False,
                                date_closed__isnull=True,
                                date_completed__isnull=True
                            ).order_by('-date_assigned')
                        else:
                            resp = models.Issue.objects.filter(
                                Q(assigned_to=request.user) |
                                Q(created_by=request.user) |
                                Q(department__in=SRRSDepartment.objects.filter(hod_department__hod=request.user)) |
                                Q(ict_assignee_issue_instance__assignee=request.user),
                                status__in=['COMPLETED']
                            ).order_by('-date_completed')

                    resp = list(set(resp))
                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resp, request)
                    serializer = serializers.SlimFetchIssueSerializer(
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
            forwarded = request.query_params.get('forwarded')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
        
            
            with transaction.atomic():
                try:
                    if forwarded:
                        recordInstance = models.Issue.objects.get(id=request_id)
                    else:
                        recordInstance = models.Issue.objects.get(id=request_id,created_by=request.user)
                    recordInstance.is_deleted = True
                    recordInstance.status = "DELETED"
                    recordInstance.save()
                    # track status change
                    raw = {
                        "issue": recordInstance,
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

        allowed = ["ICT_ADMIN", "SUPERUSER"]

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
                priority = payload['priority']
                category = payload['category']
                issue_type = payload['issue_type']
                comment = payload.get('comment') or 'N/A'

                # is_reassign = False
                action = 'ASSIGNED'

                try:
                    issueInstance = models.Issue.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown issue"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    priority = models.Priority.objects.get(id=priority)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown priority"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    category = models.Category.objects.get(id=category)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown category"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                try:
                    issue_type = models.JobType.objects.get(id=issue_type)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown issue type"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                is_already_assigned = models.Assignees.objects.filter(
                            issue=request_id
                        )
                if is_already_assigned:
                    # is_reassign = True
                    action = 'REASSIGNED'
                    is_already_assigned.delete()

                
                assignees = []
                for assignee in assigned_to:
                    try:
                        assigned_to = User.objects.get(id=assignee)

                        is_existing = models.Assignees.objects.filter(
                            assignee=assignee, issue=request_id
                        ).exists()

                        if is_existing:
                            return Response({"details": "Already Assigned"}, 
                                status=status.HTTP_400_BAD_REQUEST)
                        
                        is_out_of_scope = models.StatusChange.objects.filter(
                            Q(issue=issueInstance) & 
                            Q(status='OUT OF SCOPE') &
                            Q(action_by=assigned_to) 
                        ).exists()

                        if is_out_of_scope:
                            return Response({"details": f"{assigned_to.first_name} already marked this issue as out of scope"}, 
                                status=status.HTTP_400_BAD_REQUEST)
                        
                        assignees.append(assigned_to)

                    except (ValidationError, ObjectDoesNotExist):
                        return Response({"details": "Unknown assignee"}, 
                                        status=status.HTTP_400_BAD_REQUEST)
                
                
                with transaction.atomic():
                    for assignee in assignees:
                        raw = {
                            "issue": issueInstance,
                            "assignee": assignee,
                            "assigned_by": request.user,
                        }
                        models.Assignees.objects.create(**raw)

                    issueInstance.status = 'ASSIGNED'
                    issueInstance.date_assigned = datetime.datetime.now()
                    issueInstance.priority = priority
                    issueInstance.category = category
                    issueInstance.job_type = issue_type
                    issueInstance.save()

                    # track status change
                    raw = {
                        "issue": issueInstance,
                        "status": action,
                        "status_for": 'ICT_ADMIN',
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)


                    # Notify the assignee
                    emails = [user.email for user in assignees]
                    subject = f"[ICT HELPDESK] Issue {issueInstance.uid}  Assigned To You"
                    message = f"Hello, <br>A ticket of id: {issueInstance.uid} has been assigned to you<br>by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.<br>Comment: {comment}<br>Pending your action.<br><br>Regards\nICT-HELPDESK-AKHK\n\n"

                    uri = f"requests/view/{str(issueInstance.id)}"
                    link = "http://172.20.0.42:8011/" + uri
                    platform = 'View Ticket'

                    message_template = read_template("general_template.html")
                    message = message_template.substitute(
                        CONTENT=message,
                        LINK=link,
                        PLATFORM=platform
                    )
                    
                    try:
                        mail = {
                            "email" : list(set(emails)), 
                            "subject" : subject,
                            "message" : message,
                            "is_html": True
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        logger.error(e)

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Ticket Request Assigned", 
                    f"Assigning Executed UID: {str(issueInstance.id)}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, 
                                status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST"],
            detail=False,
            url_path="completed",
            url_name="completed")
    def completed(self, request):

        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data
            roles = user_util.fetchusergroups(request.user.id) 

            serializer = serializers.MarkAsCompleteSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']

                try:
                    issueInstance = models.Issue.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown issue"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    issueInstance.status = 'COMPLETED'
                    issueInstance.date_completed = datetime.datetime.now()
                    issueInstance.save()

                    # track status change
                    raw = {
                        "issue": issueInstance,
                        "status": 'COMPLETED',
                        "status_for": '/'.join(roles),
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)


                    # Notify Admins
                    # emails = []
                    # assignees = models.Assignees.objects.filter(Q(issue=issueInstance))
                    # for assignee in assignees:
                    #     emails.append(assignee.assignee.email)
                    #     if assignee.assigned_by:
                    #         emails.append(assignee.assigned_by.email)
                    # if issueInstance.assigned_to:
                    #     emails.append(issueInstance.assigned_to.email)

                    # subject = f"[ICT HELPDESK] Issue {issueInstance.uid}  Completed  "
                    # message = f"Hello. \nIssue of id: {issueInstance.uid} has been marked as Complete\nby {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.\nPending closure.\n"

                    # uri = f"requests/view/{str(issueInstance.id)}"
                    # link = "http://172.20.0.42:8011/" + uri
                    # platform = 'View Issue'

                    # message_template = read_template("general_template.html")
                    # message = message_template.substitute(
                    #     CONTENT=message,
                    #     LINK=link,
                    #     PLATFORM=platform
                    # )
                    
                    # try:
                    #     mail = {
                    #         "email" : list(set(emails)), 
                    #         "subject" : subject,
                    #         "message" : message,
                    #         "is_html": True
                    #     }
                    #     Sendmail.objects.create(**mail)
                    # except Exception as e:
                    #     logger.error(e)

                    # Notify requestor
                    if issueInstance.email:
                        emails = [issueInstance.email]
                    else:
                        emails = [issueInstance.created_by.email]
                    subject = f"[ICT HELPDESK] Issue {issueInstance.uid}  Completed "
                    message = f"Hello. \nYour Issue of id: {issueInstance.uid} has been marked as Complete\nby {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.\nClick below to review it.\n"

                    uri = f"generic/acknowledgement/{str(issueInstance.id)}"
                    link = "http://172.20.0.42:8011/" + uri
                    platform = 'Verify Issue'

                    message_template = read_template("general_template.html")
                    message = message_template.substitute(
                        CONTENT=message,
                        LINK=link,
                        PLATFORM=platform
                    )
                    
                    try:
                        mail = {
                            "email" : list(set(emails)), 
                            "subject" : subject,
                            "message" : message,
                            "is_html": True
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        logger.error(e)

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Issue Request Solved / Completed", 
                    f"Completeness Executed UID: {str(issueInstance.id)}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, 
                                status=status.HTTP_400_BAD_REQUEST)    
            
    @action(methods=["POST"],
            detail=False,
            url_path="out-of-scope",
            url_name="out-of-scope")
    def out_of_scope(self, request):

        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.MarkAsCompleteSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']

                try:
                    issueInstance = models.Issue.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown issue"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    issueInstance.status = 'SUBMITTED'
                    issueInstance.assigned_to = None
                    issueInstance.save()

                    models.Assignees.objects.filter(
                        Q(issue=issueInstance) &
                        Q(assignee=issueInstance)
                    ).delete()

                    # track status change
                    raw = {
                        "issue": issueInstance,
                        "status": 'OUT OF SCOPE',
                        "status_for": 'ICT_ADMIN',
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)


                    # Notify Admins
                    emails = list(models.StatusChange.objects.filter(Q(issue=issueInstance) & Q(status='ASSIGNED')).values_list('action_by__email', flat=True))

                    subject = f"[ICT HELPDESK] Issue {issueInstance.uid}  Out Of Scope  "
                    message = f"Hello. \nIssue of id: {issueInstance.uid} assigned to {authenticated_user.first_name} {authenticated_user.last_name}\n has been marked as: OUT OF SCOPE on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}. \nPlease Reassign to appropriate team member"

                    uri = f"requests/view/{str(issueInstance.id)}"
                    link = "http://172.20.0.42:8011/" + uri
                    platform = 'View Issue'

                    message_template = read_template("general_template.html")
                    message = message_template.substitute(
                        CONTENT=message,
                        LINK=link,
                        PLATFORM=platform
                    )
                    
                    try:
                        mail = {
                            "email" : list(set(emails)), 
                            "subject" : subject,
                            "message" : message,
                            "is_html": True
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        logger.error(e)

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Issue out of scope", 
                    f"out-of-scope Executed UID: {str(issueInstance.id)}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, 
                                status=status.HTTP_400_BAD_REQUEST) 

    @action(methods=["POST"],
            detail=False,
            url_path="reopen-issue",
            url_name="reopen-issue")
    def reopen(self, request):

        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.MarkAsCompleteSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']

                try:
                    issueInstance = models.Issue.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown issue"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    issueInstance.status = 'REOPENED'
                    issueInstance.is_acknowledged = False
                    issueInstance.date_reopened = datetime.datetime.now()
                    issueInstance.save()

                    # track status change
                    raw = {
                        "issue": issueInstance,
                        "status": 'REOPENED',
                        "status_for": 'ICT_ADMIN',
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)


                    # Notify Admins
                    # emails = list(get_user_model().objects.filter(Q(groups__name__in=['ICT_ADMIN'])).values_list('email', flat=True))
                    emails = []
                    assignees = models.Assignees.objects.filter(Q(issue=issueInstance))
                    for assignee in assignees:
                        emails.append(assignee.assignee.email)
                        if assignee.assigned_by:
                            emails.append(assignee.assigned_by.email)

                    if issueInstance.assigned_to:
                        emails.append(issueInstance.assigned_to.email)

                    if issueInstance.email:
                        emails.append(issueInstance.email)
                    else:
                        emails.append(issueInstance.created_by.email)

                    # slt = list(models.PlatformAdmin.objects.filter(Q(is_slt=True)).values_list('admin__email', flat=True))

                    # emails += slt

                    subject = f"[ICT HELPDESK] Issue {issueInstance.uid}  Reopened  "
                    message = f"Hello. \nIssue of id: {issueInstance.uid} has been marked as Reopened\nby {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}."

                    uri = f"requests/view/{str(issueInstance.id)}"
                    link = "http://172.20.0.42:8011/" + uri
                    platform = 'View Issue'

                    message_template = read_template("general_template.html")
                    message = message_template.substitute(
                        CONTENT=message,
                        LINK=link,
                        PLATFORM=platform
                    )
                    
                    try:
                        mail = {
                            "email" : list(set(emails)), 
                            "subject" : subject,
                            "message" : message,
                            "is_html": True
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        logger.error(e)

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Issue Request reopened", 
                    f"Reopen Executed UID: {str(issueInstance.id)}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, 
                                status=status.HTTP_400_BAD_REQUEST) 

    @action(methods=["POST"],
            detail=False,
            url_path="create-quote",
            url_name="create-quote")
    def quote(self, request):

        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.QuoteSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                issue_id = payload['issue_id']
                quote_id = payload['quote_id']

                try:
                    issueInstance = models.Issue.objects.get(id=issue_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "UnknMMDQuoteown issue"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    quoteInstance = MMDQuote.objects.get(qid=quote_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown MMD Quote"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    models.Quote.objects.create(
                        issue=issueInstance,
                        quote=quoteInstance
                    )

                    # track status change
                    raw = {
                        "issue": issueInstance,
                        "status": 'QUOTE REQUESTED',
                        "status_for": 'ASSIGNEE',
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Quote Requested", 
                    f"Issue Executed UID: {str(issueInstance.id)}")
                
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

        if request.method == "POST":

            payload = request.data
            roles = user_util.fetchusergroups(request.user.id) 

            serializer = serializers.NoteSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                comment = payload.get('comments')

                try:
                    issueInstance = models.Issue.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown issue"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    raw = {
                        "owner": request.user,
                        "issue": issueInstance,
                        "note": comment
                    }
                    models.Note.objects.create(**raw)

                # Send Note Notifications
                emails = []
                assignees = models.Assignees.objects.filter(Q(issue=issueInstance))
                for assignee in assignees:
                    emails.append(assignee.assignee.email)
                    if assignee.assigned_by:
                        emails.append(assignee.assigned_by.email)
                if issueInstance.assigned_to:
                    emails.append(issueInstance.assigned_to.email)
                if issueInstance.created_by:
                    emails.append(issueInstance.created_by.email)
                else:
                    emails.append(issueInstance.email)
                try:
                    emails.remove(request.user.email)
                except:
                    pass
                subject = f"[ICT HELPDESK] Note Issued for Ticket {issueInstance.uid}"
                message = f"Hello. <br>A note has been added for Issue of id: {issueInstance.uid}<br>by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.<br><b>Note:</b><br><i>{comment}</i>.\n"

                uri = f"requests/view/{str(issueInstance.id)}"
                link = "http://172.20.0.42:8011/" + uri
                platform = 'View Ticket'

                message_template = read_template("general_template.html")
                message = message_template.substitute(
                    CONTENT=message,
                    LINK=link,
                    PLATFORM=platform
                )
                
                try:
                    mail = {
                        "email" : list(set(emails)), 
                        "subject" : subject,
                        "message" : message,
                        "is_html": True
                    }
                    Sendmail.objects.create(**mail)
                except Exception as e:
                    logger.error(e)

                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    resp = models.Note.objects.filter(Q(issue=request_id))

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
                # category = payload['category']
                is_hod = True if payload['is_hod'] == 'YES' else False
                is_slt = True if payload['is_slt'] == 'YES' else False

                # try:
                #     category = models.Category.objects.get(id=category)
                # except (ValidationError, ObjectDoesNotExist):
                #     return Response({"details": "Unknown Category"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    admin = User.objects.get(id=admin)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown User"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Invalid Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                # assign ICT_ADMIN role
                # if is_slt or is_hod:
                assign_role = user_util.award_role('ICT_ADMIN', str(admin.id))
                if not assign_role:
                    return Response({"details": "Unable to assign role ICT_ADMIN"}, status=status.HTTP_400_BAD_REQUEST)
                    
                with transaction.atomic():
                    raw = {
                        "admin": admin,
                        "is_hod": is_hod,
                        "is_slt": is_slt,
                        # "category": category,
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
                # category = payload['category']
                is_hod = True if payload['is_hod'] == 'YES' else False
                is_slt = True if payload['is_slt'] == 'YES' else False

                # try:
                #     category = models.Category.objects.get(id=category)
                # except (ValidationError, ObjectDoesNotExist):
                #     return Response({"details": "Unknown Category"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    requestInstance = models.PlatformAdmin.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Invalid Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    admin = User.objects.get(id=admin)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown User"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Invalid Request"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():

                    requestInstance.admin = admin
                    requestInstance.is_hod = is_hod
                    requestInstance.is_slt = is_slt
                    # requestInstance.category = category
                    requestInstance.created_by = request.user
                    requestInstance.save()

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
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
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
                    user_util.revoke_role('ICT_ADMIN', str(user.admin.id))
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

    def get_queryset(self):
        return []

    @action(methods=["GET",],
            detail=False,
            url_path="issues",
            url_name="issues")
    def issues(self, request):
                    
        department = request.query_params.get('department')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        r_status = request.query_params.get('status')
        job_type = request.query_params.get('job_type')
        equipment_type = request.query_params.get('equipment_type')
        section = request.query_params.get('section')
        category = request.query_params.get('category')
        facility = request.query_params.get('facility')
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

        if department:
            q_filters &= Q(department=department)

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)
            
        if r_status:
            if r_status == "QUOTE REQUESTED":
                q_filters &= Q(ict_quote_issue_instance__isnull=False)
            else:
                q_filters &= Q(status=r_status)

        if job_type:
            q_filters &= Q(job_type=job_type)

        if equipment_type:
            q_filters &= Q(equipment_type=equipment_type)

        if section:
            q_filters &= Q(section=section)

        if facility:
            q_filters &= Q(facility=facility)

        if category:
            q_filters &= Q(category=category)


        if q_filters:

            resp = models.Issue.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
            
        else:
            resp = models.Issue.objects.filter(Q(is_deleted=False)).order_by('-date_created')[:50]

        resp = serializers.FetchIssueSerializer(resp, many=True, context={"user_id":request.user.id}).data

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
        active_status = ['SUBMITTED','ASSIGNED']

        
        if any(role in ['FMS_ADMIN', 'SUPERUSER'] for role in roles):
            requests = models.Issue.objects.filter(Q(is_deleted=False)).count()
            assigned = models.Issue.objects.filter(Q(status="ASSIGNED"), is_deleted=False).count()
            closed = models.Issue.objects.filter(status="CLOSED", is_deleted=False).count()
            pending = models.Issue.objects.filter(Q(status__in=active_status), is_deleted=False).count()
        else:
            requests = models.Issue.objects.filter(Q(department=request.user.srrs_department) | Q(created_by=request.user) | Q(assigned_to=request.user) | Q(ict_assignee_issue_instance__assignee=request.user), is_deleted=False).count()
            assigned = models.Issue.objects.filter(Q(department=request.user.srrs_department) |  Q(created_by=request.user) | Q(assigned_to=request.user) | Q(ict_assignee_issue_instance__assignee=request.user), status="ASSIGNED", is_deleted=False).count()
            closed = models.Issue.objects.filter(Q(department=request.user.srrs_department) |  Q(created_by=request.user) | Q(assigned_to=request.user) | Q(ict_assignee_issue_instance__assignee=request.user), status="CLOSED", is_deleted=False).count()
            pending = models.Issue.objects.filter(Q(department=request.user.srrs_department) |  Q(created_by=request.user) | Q(assigned_to=request.user) | Q(ict_assignee_issue_instance__assignee=request.user), status__in=active_status, is_deleted=False).count()

        resp = {
            "requests": requests,
            "assigned": assigned,
            "closed": closed,
            "pending": pending
        }

        return Response(resp, status=status.HTTP_200_OK)