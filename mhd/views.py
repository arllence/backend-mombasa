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
from mhd import models
from mhd import serializers
from mhd.utils import shared_fxns
from django.db import IntegrityError, DatabaseError
from acl.utils import track_user, user_util
from acl.models import User, Sendmail, SRRSDepartment, SubDepartment, OHC
from django.db.models import Sum
from django.core.mail import send_mail
# from django.utils import timezone
from mms.models import Quote as MMDQuote
from django.db.models import F, ExpressionWrapper, DateTimeField, DurationField
from datetime import timedelta

from rest_framework.pagination import PageNumberPagination

from intranet.serializers import FullFetchDepartmentSerializer
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
            url_path="equipment-types",
            url_name="equipment-types")
    def equipment_types(self, request): 
        if request.method == "GET":
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

    @action(methods=["POST", "GET", "PUT"],
            detail=False,
            url_path="sections",
            url_name="sections")
    def sections(self, request): 
        if request.method == "GET":
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
                job_type = payload.get('job_type') or None
                equipment_type = payload.get('equipment_type') or None
                section = payload.get('section') or None
                department = payload['department']
                issue = payload['issue']
                name = payload['name']
                email = payload['email']
                category = payload.get('category')
                facility = payload['facility']
                subject = payload['subject']

                uid = shared_fxns.generate_unique_identifier()

                # track user
                try:
                    track_user.get_client_info(request,'mhd', uid)
                except:
                    pass

                if not name or not email:
                    return Response({"details": "Name and Email Required"}, status=status.HTTP_400_BAD_REQUEST)


                try:
                    user = get_user_model().objects.get(email=email)
                except:
                    user = None
                    pass

                try:
                    department = SRRSDepartment.objects.get(id=department)
                except Exception as e:
                    return Response({"details": "Unknown Department"}, status=status.HTTP_400_BAD_REQUEST)
                
                if job_type:
                    try:
                        job_type = models.JobType.objects.get(id=job_type)
                    except Exception as e:
                        return Response({"details": "Unknown job type"}, status=status.HTTP_400_BAD_REQUEST)
                    
                if equipment_type:   
                    try:
                        equipment_type = models.EquipmentType.objects.get(id=equipment_type)
                    except Exception as e:
                        return Response({"details": "Unknown equipment type"}, status=status.HTTP_400_BAD_REQUEST)
                    
                if section:
                    try:
                        section = models.Section.objects.get(id=section)
                    except Exception as e:
                        return Response({"details": "Unknown section"}, status=status.HTTP_400_BAD_REQUEST)
                    
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

                with transaction.atomic():
                    raw = {
                        "department": department,
                        "section": section,
                        "job_type": job_type,
                        "equipment_type": equipment_type,
                        "created_by": user,
                        "attachment": attachment,
                        "issue": issue,
                        "facility": facility,
                        "category": category,
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
                    if not forwarded:
                        emails = list(models.PlatformAdmin.objects.filter(Q(category=category) & Q(location=facility.category)).values_list('admin__email', flat=True))
                    else:
                        emails = list(models.PlatformAdmin.objects.filter(Q(is_hod=True)).values_list('admin__email', flat=True))

                    subject = f"[MHD] {subject}"
                    message = f"""
                        <table border="1" class='signature-table'>
                            <tr>
                                <th colspan='5'>Issue Details</th>
                            </tr>
                            <tr>
                                <th>Facility</th>
                                <td>{facility.name if facility else 'N/A'}</td>
                            </tr>
                            <tr>
                                <th>Category</th>
                                <td>{category.name if category else 'N/A'}</td>
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
                    link = "http://172.20.0.42:8009/" + uri
                    platform = 'View Issue'

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

                    # Notify the requestor
                    emails = [email]

                    subject = f"[MHD] Your Issue {uid}  Received "
                    message = f"Hello.<br>Your issue has been submitted successfully.<br>on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.<br>Ticket reference id is: {uid}<br>You will be updated on the progress.<br><br>Regards<br>MHD-AKHK<br>"

                    uri = f"requests/view/{str(issueInstance.id)}"
                    link = "http://172.20.0.42:8009/" + uri
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
                            return Response({"details": "Already marked as NOT DONE. Try adding a note instead."}, 
                                    status=status.HTTP_400_BAD_REQUEST)



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

                    subject = f"[MHD] Issue {issueInstance.uid}  Status"
                    if action == 'DONE':
                        issueInstance.is_acknowledged = True
                        issueInstance.save()
                        message = f"Hello. <br>Issue of id: {issueInstance.uid} has been Acknowledged by requestor as Completed / Solved <br> on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.<br>Pending closure.\n"

                    if action == 'NOT DONE':
                        message = f"Hello. <br>Issue of id: {issueInstance.uid} has been marked as NOT DONE by requestor <br> on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.<br>Pending review.\n"

                    uri = f"requests/view/{str(issueInstance.id)}"
                    link = "http://172.20.0.42:8009/" + uri
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
                subject = f"[MHD] Note Issued for {issueInstance.uid}"
                message = f"Hello. <br>A note has been added for Issue of id: {issueInstance.uid} <br>by {user.first_name} {user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.<br><b>Note:</b><br><i>{comment}.</i>\n"

                uri = f"requests/view/{str(issueInstance.id)}"
                link = "http://172.20.0.42:8009/" + uri
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



class MHSViewSet(viewsets.ViewSet):
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
                try:
                    category = payload['category'].upper()
                except Exception as e:
                    return Response({"details": "Category required"}, 
                                    status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    raw = {
                        "name": name,
                        "category": category,
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
                    category = payload['category'].upper()
                except Exception as e:
                    return Response({"details": "Category required"}, 
                                    status=status.HTTP_400_BAD_REQUEST)

                try:
                    requestInstance = models.Facility.objects.get(id=request_id)
                except Exception as e:
                    logger.error(e)
                    return Response({"details": "Unknown Facility"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    requestInstance.name = name
                    requestInstance.category = category
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
            q = request.query_params.get('q')
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
                    if q == 'all':
                        resp = models.Category.objects.all().order_by('name')
                    else:
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

            
            serializer = serializers.IssueSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                job_type = payload['job_type'] or None
                equipment_type = payload['equipment_type'] or None
                section = payload['section'] or None
                department = payload['department']
                issue = payload['issue']
                category = payload['category']
                facility = payload['facility']
                subject = payload['subject']
                request_type = payload.get('request_type') or "ISSUE"
                maintenance_type = payload.get('maintenance_type')  

                uid = shared_fxns.generate_unique_identifier()

                # track user
                try:
                    track_user.get_client_info(request, 'mhd', uid)
                except:
                    pass

                try:
                    department = SRRSDepartment.objects.get(id=department)
                except Exception as e:
                    return Response({"details": "Unknown Department"}, status=status.HTTP_400_BAD_REQUEST)
                
                if job_type:
                    try:
                        job_type = models.JobType.objects.get(id=job_type)
                    except Exception as e:
                        return Response({"details": "Unknown job type"}, status=status.HTTP_400_BAD_REQUEST)
                    
                if equipment_type:   
                    try:
                        equipment_type = models.EquipmentType.objects.get(id=equipment_type)
                    except Exception as e:
                        return Response({"details": "Unknown equipment type"}, status=status.HTTP_400_BAD_REQUEST)
                    
                if section:
                    try:
                        section = models.Section.objects.get(id=section)
                    except Exception as e:
                        return Response({"details": "Unknown section"}, status=status.HTTP_400_BAD_REQUEST)

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
                        "section": section,
                        "job_type": job_type,
                        "equipment_type": equipment_type,
                        "created_by": authenticated_user,
                        "attachment": attachment,
                        "issue": issue,
                        "category": category,
                        "facility": facility,
                        "subject": subject,
                        "request_type": request_type,
                        "maintenance_type": maintenance_type,
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
                    # emails = list(get_user_model().objects.filter(Q(groups__name__in=['MHD_ADMIN'])).values_list('email', flat=True))
                    # emails = list(models.PlatformAdmin.objects.filter(Q(category=category)).values_list('admin__email', flat=True))
                    emails = list(models.PlatformAdmin.objects.filter(Q(category=category) & Q(location=facility.category)).values_list('admin__email', flat=True))
                    subject = f"[MHD] New Issue Reported: {uid} ."
                    message = f"Hello. \nNew Issue: {uid} from department: {department.name}, \nhas been raised by: {request.user.first_name} {request.user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending Assigning.\n\nRegards\nMHD-AKHK\n\n"

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


                    # Notify the requestor
                    emails = [request.user.email]

                    subject = f"[MHD] Your Issue {uid}  Received "
                    message = f"Hello. <br>Your issue has been submitted successfully.<br>on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}<br>Ticket reference id is: {uid}.<br>You will be updated on progress.<br><br>Regards<br>MHD-AKHK<br>"

                    uri = f"requests/view/{str(issue.id)}"
                    link = "http://172.20.0.42:8009/" + uri
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
                job_type = payload['job_type']
                equipment_type = payload['equipment_type']
                department = payload['department']
                section = payload['section']
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
                
                if job_type:
                    try:
                        job_type = models.JobType.objects.get(id=job_type)
                    except Exception as e:
                        return Response({"details": "Unknown job type"}, status=status.HTTP_400_BAD_REQUEST)
                
                if equipment_type:    
                    try:
                        equipment_type = models.EquipmentType.objects.get(id=equipment_type)
                    except Exception as e:
                        return Response({"details": "Unknown equipment type"}, status=status.HTTP_400_BAD_REQUEST)
                
                if section:
                    try:
                        section = models.Section.objects.get(id=section)
                    except Exception as e:
                        return Response({"details": "Unknown section"}, status=status.HTTP_400_BAD_REQUEST)

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
                        "section": section,
                        "job_type": job_type,
                        "equipment_type": equipment_type,
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
                    # emails = list(get_user_model().objects.filter(Q(groups__name__in=['MHD_ADMIN'])).values_list('email', flat=True))
                    emails = list(models.PlatformAdmin.objects.filter(Q(category=issueInstance.category) & Q(location=issueInstance.facility.category)).values_list('admin__email', flat=True))
                    subject = f"[MHD] Issue {issueInstance.uid} Closed "
                    message = f"Hello. \nIssue: {issueInstance.uid} from department: {issueInstance.department.name}, \nhas been closed by: {request.user.first_name} {request.user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.\n\nRegards\nMHD-AKHK\n\n"

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
            location = request.query_params.get('location')
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

                    if "MHD_ADMIN" in roles or "SUPERUSER" in roles:
                        if query == 'unassigned':
                            if location:
                                resp = models.Issue.objects.filter(
                                    Q(status__in=['SUBMITTED','REOPENED']) & 
                                    Q(facility__category=location) & 
                                    Q(request_type='ISSUE'), is_deleted=False
                                ).order_by('-date_created')
                            else:
                                resp = models.Issue.objects.filter(
                                    Q(status__in=['SUBMITTED','REOPENED']) & 
                                    Q(request_type='ISSUE'), is_deleted=False
                                ).order_by('-date_created')
                        elif query == 'assigned':
                            if location:
                                resp = models.Issue.objects.filter(
                                    Q(status__in=['ASSIGNED'])  & 
                                    Q(facility__category=location) & 
                                    Q(request_type='ISSUE'), is_deleted=False
                                ).order_by('-date_created')
                            else:
                                resp = models.Issue.objects.filter(
                                    Q(status__in=['ASSIGNED']) & 
                                    Q(request_type='ISSUE'), is_deleted=False
                                ).order_by('-date_created')
                        elif query == 'closed':
                            if location:
                                resp = models.Issue.objects.filter(
                                    Q(status__in=['CLOSED']) & 
                                    Q(facility__category=location) & 
                                    Q(request_type='ISSUE'), is_deleted=False
                                ).order_by('-date_created')
                            else:
                                resp = models.Issue.objects.filter(
                                    Q(status__in=['CLOSED']) & 
                                    Q(request_type='ISSUE'), is_deleted=False
                                ).order_by('-date_created')
                        elif query == 'reopened':
                            if location:
                                resp = models.Issue.objects.filter(
                                    Q(status__in=['REOPENED']) & 
                                    Q(facility__category=location) & 
                                    Q(request_type='ISSUE'), is_deleted=False
                                ).order_by('-date_created')
                            else:
                                resp = models.Issue.objects.filter(
                                    Q(status__in=['REOPENED']) & 
                                    Q(request_type='ISSUE'), is_deleted=False
                                ).order_by('-date_created')
                        elif query == 'overdue':
                            # Current time
                            from django.utils import timezone
                            now = timezone.now()
                            if location:
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
                                    facility__category=location,
                                    expected_closure_datetime__lt=now,
                                    request_type='ISSUE',
                                    is_deleted=False,
                                    date_assigned__isnull=False,  # avoid unassigned
                                    date_closed__isnull=True,      # only still-open issues
                                    date_completed__isnull=True
                                ).order_by('-date_created')
                            else:
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
                                    request_type='ISSUE',
                                    is_deleted=False,
                                    date_assigned__isnull=False,
                                    date_closed__isnull=True,
                                    date_completed__isnull=True
                                ).order_by('-date_created')
                        else:
                            if location:
                                resp = models.Issue.objects.filter(
                                    Q(status__in=['COMPLETED']) & 
                                    Q(facility__category=location) & 
                                    Q(request_type='ISSUE'),
                                    is_deleted=False
                                ).order_by('-date_created')
                            else:
                                resp = models.Issue.objects.filter(
                                    Q(status__in=['COMPLETED']) & 
                                    Q(request_type='ISSUE'),
                                    is_deleted=False
                                ).order_by('-date_created')

                    else:
                        if query == 'unassigned':
                            resp = models.Issue.objects.filter(
                                Q(assigned_to=request.user) |
                                Q(created_by=request.user) | 
                                Q(department__in=SRRSDepartment.objects.filter(hod_department__hod=request.user)) |
                                Q(assignee_issue_instance__assignee=request.user),
                                request_type='ISSUE',
                                status__in=['SUBMITTED','REOPENED']
                            ).order_by('-date_created')
                        elif query == 'assigned':
                            resp = models.Issue.objects.filter(
                                    Q(assigned_to=request.user) |
                                    Q(created_by=request.user) | 
                                    Q(department__in=SRRSDepartment.objects.filter(hod_department__hod=request.user)) |
                                    Q(assignee_issue_instance__assignee=request.user),
                                    request_type='ISSUE',
                                    status__in=['ASSIGNED']
                                ).order_by('-date_created')
                        elif query == 'closed':
                            resp = models.Issue.objects.filter(
                                    Q(assigned_to=request.user) |
                                    Q(created_by=request.user) | 
                                    Q(department__in=SRRSDepartment.objects.filter(hod_department__hod=request.user)) |
                                    Q(assignee_issue_instance__assignee=request.user),
                                    request_type='ISSUE',
                                    status__in=['CLOSED']
                                ).order_by('-date_created')
                        elif query == 'reopened':
                            resp = models.Issue.objects.filter(
                                    Q(assigned_to=request.user) |
                                    Q(created_by=request.user) | 
                                    Q(department__in=SRRSDepartment.objects.filter(hod_department__hod=request.user)) |
                                    Q(assignee_issue_instance__assignee=request.user),
                                    request_type='ISSUE',
                                    status__in=['REOPENED']
                                ).order_by('-date_created')
                        elif query == 'overdue':
                            from django.utils import timezone
                            now = timezone.now()
                            if location:
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
                                    Q(assignee_issue_instance__assignee=request.user),
                                    request_type='ISSUE',
                                    facility__category=location,
                                    expected_closure_datetime__lt=now,
                                    is_deleted=False,
                                    date_assigned__isnull=False,  # avoid unassigned
                                    date_closed__isnull=True,      # only still-open issues
                                    date_completed__isnull=True
                                ).order_by('-date_created')
                            else:
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
                                    Q(assignee_issue_instance__assignee=request.user),
                                    expected_closure_datetime__lt=now,
                                    request_type='ISSUE',
                                    is_deleted=False,
                                    date_assigned__isnull=False,
                                    date_closed__isnull=True,
                                    date_completed__isnull=True
                                ).order_by('-date_created')
                        else:
                            resp = models.Issue.objects.filter(
                                Q(assigned_to=request.user) |
                                Q(created_by=request.user) |
                                Q(department__in=SRRSDepartment.objects.filter(hod_department__hod=request.user)) |
                                Q(assignee_issue_instance__assignee=request.user),
                                request_type='ISSUE',
                                status__in=['COMPLETED']
                            ).order_by('-date_created')

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

    @action(methods=["POST", "PUT", "GET"],
            detail=False,
            url_path="maintenance",
            url_name="maintenance")
    def maintenance(self, request):

        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            # payload = request.data

            payload = json.loads(request.data['payload'])
            attachment = request.FILES.get('attachments', None)

            serializer = serializers.IssueSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                job_type = payload['job_type'] or None
                equipment_type = payload['equipment_type'] or None
                section = payload['section'] or None
                department = payload['department']
                issue = payload['issue']
                category = payload['category']
                facility = payload['facility']
                subject = payload['subject']
                request_type = payload.get('request_type') or "ISSUE"
                maintenance_type = payload.get('maintenance_type')  
                maintenance_duration = payload.get('maintenance_duration')  

                uid = shared_fxns.generate_unique_identifier()

                if not maintenance_type:
                    return Response({"details": "Maintenance Type Required"}, status=status.HTTP_400_BAD_REQUEST)

                if not maintenance_duration:
                    return Response({"details": "Maintenance Duration Required"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    department = SRRSDepartment.objects.get(id=department)
                except Exception as e:
                    return Response({"details": "Unknown Department"}, status=status.HTTP_400_BAD_REQUEST)
                
                if job_type:
                    try:
                        job_type = models.JobType.objects.get(id=job_type)
                    except Exception as e:
                        return Response({"details": "Unknown job type"}, status=status.HTTP_400_BAD_REQUEST)
                    
                if equipment_type:   
                    try:
                        equipment_type = models.EquipmentType.objects.get(id=equipment_type)
                    except Exception as e:
                        return Response({"details": "Unknown equipment type"}, status=status.HTTP_400_BAD_REQUEST)
                    
                if section:
                    try:
                        section = models.Section.objects.get(id=section)
                    except Exception as e:
                        return Response({"details": "Unknown section"}, status=status.HTTP_400_BAD_REQUEST)

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
                        "section": section,
                        "job_type": job_type,
                        "equipment_type": equipment_type,
                        "created_by": authenticated_user,
                        "attachment": attachment,
                        "issue": issue,
                        "category": category,
                        "facility": facility,
                        "subject": subject,
                        "request_type": request_type,
                        "maintenance_type": maintenance_type,
                        "maintenance_duration": maintenance_duration,
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

                    # auto assign to requestor
                    raw = {
                        "issue": issue,
                        "assignee": request.user,
                        "assigned_by": request.user,
                    }
                    models.Assignees.objects.create(**raw)

                    issue.status = 'ASSIGNED'
                    issue.date_assigned = datetime.datetime.now()
                    issue.save()

                    # create track status change
                    raw = {
                        "issue": issue,
                        "status": "ASSIGNED",
                        "status_for": "Auto Assigned",
                        "action_by": authenticated_user
                    }
                    models.StatusChange.objects.create(**raw)

                    emails = list(models.PlatformAdmin.objects.filter(
                        Q(category=category) & 
                        Q(location=facility.category)).values_list('admin__email', flat=True))
                    subject = f"[MHD] New Maintenance Created: {uid} ."
                    message = f"Hello. \nNew {maintenance_type} Maintenance request of id: {uid} from department: {department.name}, \nhas been raised and auto assigned to: {request.user.first_name} {request.user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\n\nRegards\nMHD-AKHK\n\n"

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
                    authenticated_user, authenticated_user, "Maintenance Request created", f"Maintenance Request Id: {issue.id}")
                
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
                job_type = payload['job_type']
                equipment_type = payload['equipment_type']
                department = payload['department']
                section = payload['section']
                issue = payload['issue']
                category = payload['category']
                facility = payload['facility']
                subject = payload['subject']
                request_type = payload.get('request_type') or "ISSUE"
                maintenance_type = payload.get('maintenance_type')  
                maintenance_duration = payload.get('maintenance_duration')  

                if not maintenance_type:
                    return Response({"details": "Maintenance Type Required"}, status=status.HTTP_400_BAD_REQUEST)

                if not maintenance_duration:
                    return Response({"details": "Maintenance Duration Required"}, status=status.HTTP_400_BAD_REQUEST)


                try:
                    issueInstance = models.Issue.objects.get(id=request_id)
                except Exception as e:
                    return Response({"details": "Unknown Issue"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    department = SRRSDepartment.objects.get(id=department)
                except Exception as e:
                    return Response({"details": "Unknown Department"}, status=status.HTTP_400_BAD_REQUEST)
                
                if job_type:
                    try:
                        job_type = models.JobType.objects.get(id=job_type)
                    except Exception as e:
                        return Response({"details": "Unknown job type"}, status=status.HTTP_400_BAD_REQUEST)
                
                if equipment_type:    
                    try:
                        equipment_type = models.EquipmentType.objects.get(id=equipment_type)
                    except Exception as e:
                        return Response({"details": "Unknown equipment type"}, status=status.HTTP_400_BAD_REQUEST)
                
                if section:
                    try:
                        section = models.Section.objects.get(id=section)
                    except Exception as e:
                        return Response({"details": "Unknown section"}, status=status.HTTP_400_BAD_REQUEST)

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
                        "section": section,
                        "job_type": job_type,
                        "equipment_type": equipment_type,
                        "issue": issue,
                        "facility": facility,
                        "category": category,
                        "subject": subject,
                        "request_type": request_type,
                        "maintenance_type": maintenance_type,
                        "maintenance_duration": maintenance_duration,
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
                    authenticated_user, authenticated_user, "Maintenance Request updated", f"Maintenance Id: {issueInstance.id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


        if request.method == "GET":
            request_id = request.query_params.get('request_id')
            query = request.query_params.get('q')
            location = request.query_params.get('location')
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

                    if "MHD_ADMIN" in roles or "SUPERUSER" in roles:
                        if query == 'unassigned':
                            if location:
                                resp = models.Issue.objects.filter(
                                    Q(status__in=['SUBMITTED','REOPENED']) & 
                                    Q(facility__category=location) & 
                                    Q(request_type='MAINTENANCE'), is_deleted=False
                                ).order_by('-date_created')
                            else:
                                resp = models.Issue.objects.filter(
                                    Q(status__in=['SUBMITTED','REOPENED']) & 
                                    Q(request_type='MAINTENANCE'), is_deleted=False
                                ).order_by('-date_created')
                        elif query == 'assigned':
                            if location:
                                resp = models.Issue.objects.filter(
                                    Q(status__in=['ASSIGNED'])  & 
                                    Q(facility__category=location) & 
                                    Q(request_type='MAINTENANCE'), is_deleted=False
                                ).order_by('-date_created')
                            else:
                                resp = models.Issue.objects.filter(
                                    Q(status__in=['ASSIGNED']) & 
                                    Q(request_type='MAINTENANCE'), is_deleted=False
                                ).order_by('-date_created')
                        elif query == 'closed':
                            if location:
                                resp = models.Issue.objects.filter(
                                    Q(status__in=['CLOSED']) & 
                                    Q(facility__category=location) & 
                                    Q(request_type='MAINTENANCE'), is_deleted=False
                                ).order_by('-date_created')
                            else:
                                resp = models.Issue.objects.filter(
                                    Q(status__in=['CLOSED']) & 
                                    Q(request_type='MAINTENANCE'), is_deleted=False
                                ).order_by('-date_created')
                        elif query == 'overdue':
                            # Current time
                            from django.utils import timezone
                            now = timezone.now()
                            if location:
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
                                    facility__category=location,
                                    request_type='MAINTENANCE',
                                    expected_closure_datetime__lt=now,
                                    is_deleted=False,
                                    date_assigned__isnull=False,  # avoid unassigned
                                    date_closed__isnull=True,      # only still-open issues
                                    date_completed__isnull=True
                                ).order_by('-date_created')
                            else:
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
                                    request_type='MAINTENANCE',
                                    is_deleted=False,
                                    date_assigned__isnull=False,
                                    date_closed__isnull=True,
                                    date_completed__isnull=True
                                ).order_by('-date_created')
                        else:
                            if location:
                                resp = models.Issue.objects.filter(
                                    Q(status__in=['COMPLETED']) & 
                                    Q(facility__category=location) & 
                                    Q(request_type='MAINTENANCE'),
                                    is_deleted=False
                                ).order_by('-date_created')
                            else:
                                resp = models.Issue.objects.filter(
                                    Q(status__in=['COMPLETED']) & 
                                    Q(request_type='MAINTENANCE'),
                                    is_deleted=False
                                ).order_by('-date_created')

                    else:
                        if query == 'unassigned':
                            resp = models.Issue.objects.filter(
                                Q(assigned_to=request.user) |
                                Q(created_by=request.user) | 
                                Q(assignee_issue_instance__assignee=request.user),
                                request_type='MAINTENANCE',
                                status__in=['SUBMITTED','REOPENED']
                            ).order_by('-date_created')
                        elif query == 'assigned':
                            resp = models.Issue.objects.filter(
                                    Q(assigned_to=request.user) |
                                    Q(created_by=request.user) | 
                                    Q(assignee_issue_instance__assignee=request.user),
                                    request_type='MAINTENANCE',
                                    status__in=['ASSIGNED']
                                ).order_by('-date_created')
                        elif query == 'closed':
                            resp = models.Issue.objects.filter(
                                    Q(assigned_to=request.user) |
                                    Q(created_by=request.user) | 
                                    Q(assignee_issue_instance__assignee=request.user),
                                    request_type='MAINTENANCE',
                                    status__in=['CLOSED']
                                ).order_by('-date_created')
                        elif query == 'overdue':
                            from django.utils import timezone
                            now = timezone.now()
                            if location:
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
                                    Q(assignee_issue_instance__assignee=request.user),
                                    facility__category=location,
                                    expected_closure_datetime__lt=now,
                                    request_type='MAINTENANCE',
                                    is_deleted=False,
                                    date_assigned__isnull=False,  # avoid unassigned
                                    date_closed__isnull=True,      # only still-open issues
                                    date_completed__isnull=True
                                ).order_by('-date_created')
                            else:
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
                                    Q(assignee_issue_instance__assignee=request.user),
                                    expected_closure_datetime__lt=now,
                                    request_type='MAINTENANCE',
                                    is_deleted=False,
                                    date_assigned__isnull=False,
                                    date_closed__isnull=True,
                                    date_completed__isnull=True
                                ).order_by('-date_created')
                        else:
                            resp = models.Issue.objects.filter(
                                Q(assigned_to=request.user) |
                                Q(created_by=request.user) |
                                Q(assignee_issue_instance__assignee=request.user),
                                request_type='MAINTENANCE',
                                status__in=['COMPLETED']
                            ).order_by('-date_created')

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
        
    
    @action(methods=["POST"],
            detail=False,
            url_path="assign",
            url_name="assign")
    def assign(self, request):

        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        allowed = ["MHD_ADMIN", "SUPERUSER"]

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
                job_type = payload['job_type']
                comment = payload.get('comment') or 'N/A'

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
                    job_type = models.JobType.objects.get(id=job_type)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown job type"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                assignees = []
                assignee_names = []
                for assignee in assigned_to:
                    try:
                        assigned_to = User.objects.get(id=assignee)
                        is_existing = models.Assignees.objects.filter(
                            assignee=assignee, issue=request_id
                        ).exists()
                        if is_existing:
                            return Response({"details": "Already Assigned"}, 
                                status=status.HTTP_400_BAD_REQUEST)
                        assignees.append(assigned_to)
                        name = f"{assigned_to.first_name} {assigned_to.last_name}"
                        assignee_names.append(name)
                    except (ValidationError, ObjectDoesNotExist):
                        return Response({"details": "Unknown assignee"}, 
                                        status=status.HTTP_400_BAD_REQUEST)
                
                # if issueInstance.assigned_to:
                #     if issueInstance.assigned_to == assigned_to:
                #         return Response({"details": "Already Assigned"}, 
                #                     status=status.HTTP_400_BAD_REQUEST)
                
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
                    issueInstance.job_type = job_type
                    issueInstance.save()

                    # track status change
                    raw = {
                        "issue": issueInstance,
                        "status": 'ASSIGNED',
                        "status_for": 'MHD_ADMIN',
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)


                    # Notify the assignee
                    emails = [user.email for user in assignees]
                    subject = f"[MHD] Issue {issueInstance.uid}  Assigned To You  "
                    message = f"Hello.<br>An issue of id: {issueInstance.uid} has been assigned to you<br>by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.<br>Comment: <i>{comment}</i><br>Pending your action.<br><br>Regards<br>MHD-AKHK\n\n"

                    uri = f"requests/view/{str(issueInstance.id)}"
                    link = "http://172.20.0.42:8009/" + uri
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

                    # Notify the requestor
                    emails = []
                    if issueInstance.created_by:
                        emails.append(issueInstance.created_by.email)
                    if issueInstance.email:
                        emails.append(issueInstance.email)

                    subject = f"[MHD] Your Issue {issueInstance.uid}  Assigned "
                    message = f"Hello. <br>Your issue of id: {issueInstance.uid} has been assigned to {' & '.join(assignee_names)}<br>on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.<br>You will be notified when completed.<br><br>Regards<br>MHD-AKHK<br>"

                    uri = f"requests/view/{str(issueInstance.id)}"
                    link = "http://172.20.0.42:8009/" + uri
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
                    authenticated_user, authenticated_user, "Issue Request Assigned", 
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
                    # emails = list(get_user_model().objects.filter(Q(groups__name__in=['MHD_ADMIN'])).values_list('email', flat=True))
                    emails = []
                    assignees = models.Assignees.objects.filter(Q(issue=issueInstance))
                    for assignee in assignees:
                        emails.append(assignee.assignee.email)
                        if assignee.assigned_by:
                            emails.append(assignee.assigned_by.email)
                    if issueInstance.assigned_to:
                        emails.append(issueInstance.assigned_to.email)

                    subject = f"[MHD] Issue {issueInstance.uid}  Completed  "
                    message = f"Hello. \nIssue of id: {issueInstance.uid} has been marked as Complete\nby {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.\nPending closure.\n"

                    uri = f"requests/view/{str(issueInstance.id)}"
                    link = "http://172.20.0.42:8009/" + uri
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

                    # Notify requestor
                    if issueInstance.email:
                        emails = [issueInstance.email]
                    else:
                        emails = [issueInstance.created_by.email]
                    subject = f"[MHD] Issue {issueInstance.uid}  Completed "
                    message = f"Hello. <br>Your Issue of id: {issueInstance.uid} has been marked as Complete <br>by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.<br>Click on the button below to review it.\n"

                    uri = f"generic/acknowledgement/{str(issueInstance.id)}"
                    link = "http://172.20.0.42:8009/" + uri
                    platform = 'Review Issue'

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
                        "status_for": 'MHD_ADMIN',
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)


                    # Notify Admins
                    # emails = list(get_user_model().objects.filter(Q(groups__name__in=['MHD_ADMIN'])).values_list('email', flat=True))
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

                    slt = list(models.PlatformAdmin.objects.filter(Q(is_slt=True)).values_list('admin__email', flat=True))

                    emails += slt

                    subject = f"[MHD] Issue {issueInstance.uid}  Reopened  "
                    message = f"Hello. \nIssue of id: {issueInstance.uid} has been marked as Reopened\nby {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}."

                    uri = f"requests/view/{str(issueInstance.id)}"
                    link = "http://172.20.0.42:8009/" + uri
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
            url_path="outliers",
            url_name="outliers")
    def outliers(self, request):

        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

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
                
                with transaction.atomic():
                    issueInstance.status = action
                    issueInstance.closed_by = authenticated_user
                    issueInstance.date_closed = datetime.datetime.now()
                    issueInstance.save()

                    # track status change
                    raw = {
                        "issue": issueInstance,
                        "status": action,
                        "status_for": 'MHD_ADMIN',
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)


                    # Notify requestor
                    if issueInstance.email:
                        emails = [issueInstance.email]
                    else:
                        emails = [issueInstance.created_by.email]
                    subject = f"[MHD] Your Issue {issueInstance.uid}  Status "
                    message = f"Hello. <br>Your Issue of id: {issueInstance.uid} has been marked as {action} <br>by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.<br>Contact Maintenance Department for more details.\n"

                    uri = f"generic/acknowledgement/{str(issueInstance.id)}"
                    link = "http://172.20.0.42:8009/" + uri
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
                subject = f"[MHD] Note Issued for {issueInstance.uid}"
                message = f"Hello. \nA note has been added for Issue of id: {issueInstance.uid} \nby {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.\nThe Note:\n {comment}.\n"

                uri = f"requests/view/{str(issueInstance.id)}"
                link = "http://172.20.0.42:8009/" + uri
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
                category = payload['category']
                location = payload.get('location') or None
                is_hod = True if payload['is_hod'] == 'YES' else False
                is_slt = True if payload['is_slt'] == 'YES' else False

                try:
                    category = models.Category.objects.get(id=category)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Category"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    admin = User.objects.get(id=admin)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown User"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Invalid Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                # assign MHD_ADMIN role
                if is_slt or is_hod:
                    assign_role = user_util.award_role('MHD_ADMIN', str(admin.id))
                    if not assign_role:
                        return Response({"details": "Unable to assign role MHD_ADMIN"}, status=status.HTTP_400_BAD_REQUEST)
                    
                with transaction.atomic():
                    raw = {
                        "admin": admin,
                        "is_hod": is_hod,
                        "is_slt": is_slt,
                        "category": category,
                        "location": location,
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
                category = payload['category']
                location = payload.get('location') or None
                is_hod = True if payload['is_hod'] == 'YES' else False
                is_slt = True if payload['is_slt'] == 'YES' else False

                try:
                    category = models.Category.objects.get(id=category)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Category"}, status=status.HTTP_400_BAD_REQUEST)

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
                
                # assign MHD_ADMIN role
                if is_slt or is_hod:
                    assign_role = user_util.award_role('MHD_ADMIN', str(admin.id))
                    if not assign_role:
                        return Response({"details": "Unable to assign role MHD_ADMIN"}, status=status.HTTP_400_BAD_REQUEST)
                    

                with transaction.atomic():

                    requestInstance.admin = admin
                    requestInstance.is_hod = is_hod
                    requestInstance.is_slt = is_slt
                    requestInstance.category = category
                    requestInstance.location = location
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
                    user_util.revoke_role('MHD_ADMIN', str(user.admin.id))
                    user.delete()
                    return Response('200', status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request "}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"details": "Request incomplete"}, status=status.HTTP_400_BAD_REQUEST)


class JobCardViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    

    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="core",
            url_name="core")
    def core(self, request):
        roles = user_util.fetchusergroups(request.user.id)
        if request.method == "POST":
            payload = request.data
            serializer = serializers.JobCardSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                issue = payload['issue']
                supplier = payload['supplier']
                materials = payload['materials']
                material_cost = payload['material_cost']
                labour_cost = payload['labour_cost']
                contract_type = payload['contract_type']
                contract_to = payload['contract_to']
                lpo_no = payload['lpo_no']
                payments_made_to = payload['payments_made_to']
                payments_date = payload['payments_date']

                try:
                    issueInstance = models.Issue.objects.get(id=issue)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown issue"}, 
                                    status=status.HTTP_400_BAD_REQUEST)

                if not serializers.MaterialItemSerializer(data=materials, many=False):
                    return Response({"details": "Materials required"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    raw = {
                        "issue": issueInstance,
                        "job_card_no": issueInstance.uid,
                        "supplier": supplier,
                        "material_cost": material_cost,
                        "labour_cost": labour_cost,
                        "contract_type": contract_type,
                        "contract_to": contract_to,
                        "lpo_no": lpo_no,
                        "payments_made_to": payments_made_to,
                        "payments_date": payments_date,
                        "requested_by": request.user
                    }
                    jobCardInstance = models.JobCard.objects.create(**raw)

                    # save job card materials
                    for m in materials:
                        models.MaterialItem.objects.create(job_card=jobCardInstance, **m)

                    # send notification email
                    emails = list(models.PlatformAdmin.objects.filter(Q(category=issueInstance.category) & Q(location=issueInstance.facility.category), is_hod=True).values_list('admin__email', flat=True))
                    # emails = list(models.PlatformAdmin.objects.filter(Q(category=issueInstance.category), is_hod=True).values_list('admin__email', flat=True))
                    subject = f"[MHD] New Job Card Raised: {issueInstance.uid} ."
                    message = f"Hello. \nNew Job card for issue id: {issueInstance.uid}, \nhas been raised by: {request.user.first_name} {request.user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending approval.\n\nRegards\nMHD-AKHK\n\n"

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
            
        elif request.method == "PATCH":
            # Approvals hod / slt / ceo

            if not any(role in ["HOD","SLT","CEO","SUPERUSER","MHD_ADMIN","CASH_OFFICE"] for role in roles):
                return Response({"details": "Permission Denied"}, status=status.HTTP_400_BAD_REQUEST)
            
            payload = request.data

            serializer = serializers.PatchJobCardSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                request_status = payload['status']
                comment = payload['comments']

                try:
                    requestInstance = models.JobCard.objects.get(id=request_id)
                except Exception as e:
                    logger.error(e)
                    return Response({"details": "Unknown Job Card"}, status=status.HTTP_400_BAD_REQUEST)
                
                
                is_hod, is_slt, is_ceo, is_cash_office = [False, False, False, False]
                if "MHD_ADMIN" in roles:
                    adminInstance = models.PlatformAdmin.objects.filter(admin=request.user).first()
                    is_hod = adminInstance.is_hod
                    is_slt = adminInstance.is_slt

                if "CEO" in roles:
                    is_ceo = True

                if "CASH_OFFICE" in roles:
                    is_cash_office = True
                
                if request_status == 'REJECTED':
                    requestInstance.status = "REJECTED"
                    requestInstance.save()
                    status_for = None

                else:
                    # is_hod, is_slt, is_ceo, is_cash_office = [False, False, False, False]
                    # if "MHD_ADMIN" in roles:
                    #     adminInstance = models.PlatformAdmin.objects.filter(admin=request.user).first()
                    #     is_hod = adminInstance.is_hod
                    #     is_slt = adminInstance.is_slt

                    if is_hod:
                        requestInstance.is_hod_approved = True
                        requestInstance.status = "HOD APPROVED"
                        request_status = "HOD APPROVED"
                        status_for = "HOD"

                    if is_slt:
                        requestInstance.is_slt_approved = True
                        requestInstance.status = "SLT APPROVED"
                        request_status = "SLT APPROVED"
                        status_for = "SLT"
                        
                    if is_ceo:
                        requestInstance.is_ceo_approved = True
                        requestInstance.status = "CEO APPROVED"
                        request_status = "CEO APPROVED"
                        status_for = "CEO"
                        is_ceo = True

                    if is_cash_office:
                        requestInstance.is_cash_office_approved = True
                        request_status = "DISBURSED"
                        status_for = "CASH OFFICE"
                        is_cash_office = True

                # track status change
                raw = {
                    "job_card": requestInstance,
                    "status": request_status,
                    "status_for": status_for,
                    "action_by": request.user
                }

                with transaction.atomic():
                    requestInstance.save()
                    models.JobCardStatusChange.objects.create(**raw)

                    if comment:
                        final_comment = f"[{request_status}] {comment}"
                        models.JobCardNote.objects.create(
                            job_card=requestInstance,
                            note=final_comment,
                            owner=request.user
                        )
                        comment = f"[Comment: {comment}]"

                    # send requestor notification email
                    emails = [requestInstance.requested_by.email]
                    subject = f"[MHD] Job Card Status: {requestInstance.job_card_no} ."
                    message = f"Hello. \nJob card for issue id: {requestInstance.job_card_no}, \nhas been {request_status} by: {request.user.first_name} {request.user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\n{comment}\n\nRegards\nMHD-AKHK\n\n"

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

                    # send approver notification email
                    if request_status != "REJECTED":
                        emails = []
                        if is_hod:
                            emails = list(models.PlatformAdmin.objects.filter(is_slt=True).values_list('admin__email', flat=True))
                        if is_slt:
                            emails =  list(get_user_model().objects.filter(Q(groups__name='CEO')).values_list('email', flat=True))
                        if is_ceo:
                            emails =  list(get_user_model().objects.filter(Q(groups__name='CASH_OFFICE')).values_list('email', flat=True))
                            
                        subject = f"[MHD] Job Card {requestInstance.job_card_no} Pending Approval."
                        message = f"Hello. \nJob card for issue id: {requestInstance.job_card_no}, \nis pending your approval\nVisit http://172.20.0.42:8009/requests/job-cards\n\nRegards\nMHD-AKHK\n\n"
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

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            location = request.query_params.get('location')
            query = request.query_params.get('q')
            if request_id:
                try:
                    resp = models.JobCard.objects.get(Q(id=request_id))
                    resp = serializers.FetchJobCardSerializer(resp,many=False).data
                    return Response(resp, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown JobCard"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    resp = []
                    if "MHD_ADMIN" in roles:
                        admin = models.PlatformAdmin.objects.filter(admin=request.user).first()
                        is_hod = admin.is_hod
                        is_slt = admin.is_slt

                        filters = (Q(is_deleted=False) & ~Q(status='REJECTED'))

                        if location:
                            filters &= Q(issue__facility__category=location)

                        # if query == 'approved':
                        #     filters &= Q(status__in=['CEO APPROVED'])

                        # Define separate query parts
                        hod_filter = Q(is_hod_approved=False)
                        slt_filter = Q(is_hod_approved=True) & Q(is_slt_approved=False)

                        # Combine filters based on roles
                        if is_hod and is_slt:
                            filters &= (hod_filter | slt_filter)
                        elif is_hod:
                            filters &= hod_filter
                        elif is_slt:
                            filters &= slt_filter
                        else:
                            filters = None

                        # Apply the final filter
                        if filters:
                            if query == 'approved':
                                filters = (Q(status='CEO APPROVED'))
                                resp = models.JobCard.objects.filter(filters).order_by('-date_created')

                            elif query == 'all':
                                resp = models.JobCard.objects.all().order_by('-date_created')

                            else:
                                resp = models.JobCard.objects.filter(filters).order_by('-date_created')
                            
                        else:
                            resp = models.JobCard.objects.none()

                    if "CEO" in roles:
                        
                        if query == 'approved':
                            filters = (Q(status='CEO APPROVED'))
                            if location:
                                filters &= Q(issue__facility__category=location)
                            resp = models.JobCard.objects.filter(filters).order_by('-date_created')
                        else:
                            resp = models.JobCard.objects.filter(Q(is_hod_approved=True) & Q(is_slt_approved=True) & Q(is_ceo_approved=False) & ~Q(status='REJECTED')).order_by('-date_created')

                    if "CASH_OFFICE" in roles:
                        
                        if query == 'approved':
                            filters = (Q(is_cash_office_approved=True))
                            if location:
                                filters &= Q(issue__facility__category=location)
                            resp = models.JobCard.objects.filter(filters).order_by('-date_created')
                        else:
                            resp = models.JobCard.objects.filter(Q(is_ceo_approved=True) & Q(is_cash_office_approved=False) & ~Q(status='REJECTED')).order_by('-date_created')
                        
                    if "SUPERUSER" in roles:
                        
                        if query == 'approved':
                            filters = (Q(status='CEO APPROVED'))
                            if location:
                                filters &= Q(issue__facility__category=location)
                            resp = models.JobCard.objects.filter(filters).order_by('-date_created')
                        elif query == 'all':
                            resp = models.JobCard.objects.all().order_by('-date_created')
                        else:
                            resp = models.JobCard.objects.filter( ~Q(status='CEO APPROVED')).order_by('-date_created')


                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resp, request)
                    serializer = serializers.FetchJobCardSerializer(
                        result_page, many=True, context={"user_id":request.user.id})
                    return paginator.get_paginated_response(serializer.data)

                    # resp = serializers.FetchJobCardSerializer(resp, many=True).data
                    # return Response(resp, status=status.HTTP_200_OK)
                    
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
                models.JobCard.objects.filter(id=request_id).update(**raw)
                return Response('200', status=status.HTTP_200_OK)
            except (ValidationError, ObjectDoesNotExist):
                return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                print(e)
                return Response({"details": "Cannot complete request "}, status=status.HTTP_400_BAD_REQUEST)
            

    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="documents",
            url_name="documents")
    def documents(self, request):
        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = json.loads(request.data['payload'])

            exts = ['pdf','jpeg','jpg', 'png']
            for f in request.FILES.getlist('documents'):
                original_file_name = f.name
                ext = original_file_name.split('.')[-1].strip().lower()
                if ext not in exts:
                    return Response({"details": f"{original_file_name} not allowed. Only PDFs / Images allowed for upload!"}, status=status.HTTP_400_BAD_REQUEST)
            
           
            # serialize training payload
            serializer = serializers.UploadFileSerializer(
                    data=payload, many=False)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            job_card_id = payload['job_card_id']
            file_type = payload['file_type']
            description = payload.get('description') or None

            try:
                targetInstance = models.JobCard.objects.get(id=job_card_id)
            except Exception as e:
                return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                    
            with transaction.atomic():
                # create contract instance

                for f in request.FILES.getlist('documents'):
                    try:
                        original_file_name = f.name.upper()                        
                        models.JobCardDocument.objects.create(
                            document=f,
                            file_name=original_file_name, 
                            file_type=file_type, 
                            description=description, 
                            job_card=targetInstance, 
                            uploaded_by=request.user
                        )

                    except Exception as e:
                        logger.error(e)
                        print(e)
                        return Response({"details": "Error saving files"}, status=status.HTTP_400_BAD_REQUEST)  
                

            user_util.log_account_activity(
                authenticated_user, authenticated_user, "File uploaded", f"TrainingMaterial Id: {targetInstance.id}")
            
            return Response('success', status=status.HTTP_200_OK)

        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            job_card_id = request.query_params.get('job_card_id')
            query = request.query_params.get('q')
            slim = request.query_params.get('slim')
            previous = request.query_params.get('previous')

            if request_id:
                try:
                    resp = models.JobCardDocument.objects.get(Q(id=request_id))

                    if slim:
                        resp = serializers.SlimFetchDocumentSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.SlimFetchDocumentSerializer(resp, many=False, context={"user_id":request.user.id}).data

                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
                
            elif job_card_id:
                try:
                    resp = models.JobCardDocument.objects.filter(Q(job_card=job_card_id))

                    if slim:
                        resp = serializers.SlimFetchDocumentSerializer(resp, many=True, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.SlimFetchDocumentSerializer(resp, many=True, context={"user_id":request.user.id}).data

                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
                
            elif query:
                try:
                    resp = models.JobCardDocument.objects.filter(
                        Q(file_name__icontains=query) |
                        Q(file_type__icontains=query) |
                        Q(job_card__job_card_no__icontains=query) 
                    )

                    if slim:
                        resp = serializers.SlimFetchDocumentSerializer(resp, many=True, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.SlimFetchDocumentSerializer(resp, many=True, context={"user_id":request.user.id}).data

                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
                
            else:
                try:

                    if any(role in ['SUPERUSER','MHD_ADMIN'] for role in roles):

                        resp = models.JobCardDocument.objects.filter(is_deleted=False).order_by('-date_created')

                    else:
                        resp = models.JobCardDocument.objects.filter(Q(is_deleted=False) & (Q(uploaded_by=request.user)) ).order_by('-date_created')



                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resp, request)
                    serializer = serializers.SlimFetchDocumentSerializer(
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
                return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.JobCardDocument.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)    
                except Exception as e:
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)         
 
    
    @action(methods=["POST","GET"],
            detail=False,
            url_path="notes",
            url_name="notes")
    def notes(self, request):

        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.NoteSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                comment = payload.get('comments')

                try:
                    targetInstance = models.JobCard.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown job card"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    raw = {
                        "owner": request.user,
                        "job_card": targetInstance,
                        "note": comment
                    }
                    models.JobCardNote.objects.create(**raw)

                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    resp = models.JobCardNote.objects.filter(Q(job_card=request_id))

                    resp = serializers.FetchJobCardNoteSerializer(
                        resp, many=True, context={"user_id":request.user.id}).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response([], status=status.HTTP_200_OK)
            
   
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
                q_filters &= Q(quote_issue_instance__isnull=False)
            elif r_status == "NOT DONE":
                q_filters &= (Q(status_change_issue_instance__status="NOT DONE") & ~Q(status__in=['REOPENED','CLOSED']))
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

        resp = list(set(resp))

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
            requests = models.Issue.objects.filter(Q(department=request.user.srrs_department) | Q(created_by=request.user) | Q(assigned_to=request.user) | Q(assignee_issue_instance__assignee=request.user), is_deleted=False).count()
            assigned = models.Issue.objects.filter(Q(department=request.user.srrs_department) |  Q(created_by=request.user) | Q(assigned_to=request.user) | Q(assignee_issue_instance__assignee=request.user), status="ASSIGNED", is_deleted=False).count()
            closed = models.Issue.objects.filter(Q(department=request.user.srrs_department) |  Q(created_by=request.user) | Q(assigned_to=request.user) | Q(assignee_issue_instance__assignee=request.user), status="CLOSED", is_deleted=False).count()
            pending = models.Issue.objects.filter(Q(department=request.user.srrs_department) |  Q(created_by=request.user) | Q(assigned_to=request.user) | Q(assignee_issue_instance__assignee=request.user), status__in=active_status, is_deleted=False).count()

        resp = {
            "requests": requests,
            "assigned": assigned,
            "closed": closed,
            "pending": pending
        }

        return Response(resp, status=status.HTTP_200_OK)