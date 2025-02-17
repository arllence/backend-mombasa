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
from mhs import models
from mhs import serializers
from mhs.utils import shared_fxns
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import User, Sendmail, SRRSDepartment, SubDepartment, OHC
from django.db.models import Sum
from django.core.mail import send_mail
from django.utils import timezone

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
                name = payload.get('name')
                email = payload.get('email')
                category = payload['category']
                facility = payload['facility']
                subject = payload['subject']

                uid = shared_fxns.generate_unique_identifier()

                user = None
                if email:
                    try:
                        user = get_user_model().objects.get(email=email)
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
                        "created_by": user,
                        "attachment": attachment,
                        "issue": issue,
                        "facility": facility,
                        "category": category,
                        "subject": subject,
                        "uid": uid
                    }
                    if not user:
                        raw.update(
                            {
                                "email": email,
                                "name": name
                            }
                        )

                    issue = models.Issue.objects.create(
                        **raw
                    )

                    # create track status change
                    raw = {
                        "issue": issue,
                        "status": "SUBMITTED",
                        "status_for": "/".join(roles),
                        # "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)

                    # Notify Platform Admins
                    emails = list(get_user_model().objects.filter(Q(groups__name__in=['MHS_ADMIN'])).values_list('email', flat=True))
                    subject = subject
                    message = f"""
                        <table border="1" class='signature-table'>
                            <tr>
                                <th colspan='5'>Issue Details</th>
                            </tr>
                            <tr>
                                <th>Facility</th>
                                <td>{facility.name}</td>
                            </tr>
                            <tr>
                                <th>Category</th>
                                <td>{category.name}</td>
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
                    link = "http://172.20.0.42:8008/generic/home"
                    platform = 'MHD'

                    message_template = read_template("general_template.html")
                    message = message_template.substitute(
                        # NAME=name, 
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
                            }
                            
                            Sendmail.objects.create(**mail)
                    except Exception as e:
                        logger.error(e)

                if user:
                    user_util.log_account_activity(
                        user, user, "Issue Request created", f"Issue Request Id: {issue.id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)



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

                uid = shared_fxns.generate_unique_identifier()

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
                    emails = list(get_user_model().objects.filter(Q(groups__name__in=['MHS_ADMIN'])).values_list('email', flat=True))
                    subject = f"New Issue Reported: {uid} .  [MHD-AKHK]"
                    message = f"Hello. \nNew Issue: {uid} from department: {department.name}, \nhas been raised by: {request.user.first_name} {request.user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending Assigning.\n\nRegards\nFMS-AKHK"

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
                
                
                try:
                    job_type = models.JobType.objects.get(id=job_type)
                except Exception as e:
                    return Response({"details": "Unknown job type"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    equipment_type = models.EquipmentType.objects.get(id=equipment_type)
                except Exception as e:
                    return Response({"details": "Unknown equipment type"}, status=status.HTTP_400_BAD_REQUEST)
 
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
                    emails = list(get_user_model().objects.filter(Q(groups__name__in=['MHS_ADMIN'])).values_list('email', flat=True))
                    subject = f"Issue {issueInstance.uid} Closed [MHD-AKHK]"
                    message = f"Hello. \nIssue: {issueInstance.uid} from department: {issueInstance.department.name}, \nhas been closed by: {request.user.first_name} {request.user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.\n\nRegards\nFMS-AKHK"

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
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:

                    if "MHS_ADMIN" in roles or "SUPERUSER" in roles:

                        resp = models.Issue.objects.filter(
                                is_deleted=False
                            ).order_by('-date_created')

                    else:
                        resp = models.Issue.objects.filter(
                                Q(assigned_to=request.user) |
                                Q(created_by=request.user) 
                            ).order_by('-date_created')


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
            if not request_id:
                return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
        
            
            with transaction.atomic():
                try:
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

        allowed = ["MHS_ADMIN", "SUPERUSER"]

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
                comment = payload.get('comment') or 'N/A'

                try:
                    issueInstance = models.Issue.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown issue"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    assigned_to = User.objects.get(id=assigned_to)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown assignee"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    issueInstance.assigned_to = assigned_to
                    # issueInstance.assignee_comment = comment
                    issueInstance.status = 'ASSIGNED'
                    issueInstance.save()

                    # track status change
                    raw = {
                        "issue": issueInstance,
                        "status": 'ASSIGNED',
                        "status_for": '/'.join(roles),
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)


                    # Notify the assignee
                    emails = [assigned_to.email]
                    subject = f"Issue {issueInstance.uid}  Assigned To You  [MHD-AKHK]"
                    message = f"Hello, \nAn issue of id: {issueInstance.uid} has been assigned to you\nby {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.\nComment: {comment}\nPending your action.\n\nRegards\nFMS-AKHK"
                    
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
                    authenticated_user, authenticated_user, "Issue Request Assigned", 
                    f"Assigning Executed UID: {str(issueInstance.id)}")
                
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

                try:
                    admin = User.objects.get(id=admin)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown User"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logger.error(e)
                    print(e)
                    return Response({"details": "Invalid Request"}, status=status.HTTP_400_BAD_REQUEST)
                
                # assign FMS_ADMIN role
                assign_role = user_util.award_role('MHS_ADMIN', str(admin.id))
                if not assign_role:
                    return Response({"details": "Unable to assign role MHS_ADMIN"}, status=status.HTTP_400_BAD_REQUEST)
                
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
                    user_util.revoke_role('MHS_ADMIN', str(user.admin.id))
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
            q_filters &= Q(status=r_status)

        if job_type:
            q_filters &= Q(job_type=job_type)

        if equipment_type:
            q_filters &= Q(equipment_type=equipment_type)

        if section:
            q_filters &= Q(section=section)


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
            requests = models.Issue.objects.filter(Q(department=request.user.srrs_department) | Q(created_by=request.user) | Q(assigned_to=request.user), is_deleted=False).count()
            assigned = models.Issue.objects.filter(Q(department=request.user.srrs_department) |  Q(created_by=request.user) | Q(assigned_to=request.user), status="ASSIGNED", is_deleted=False).count()
            closed = models.Issue.objects.filter(Q(department=request.user.srrs_department) |  Q(created_by=request.user) | Q(assigned_to=request.user), status="CLOSED", is_deleted=False).count()
            pending = models.Issue.objects.filter(Q(department=request.user.srrs_department) |  Q(created_by=request.user) | Q(assigned_to=request.user), status__in=active_status, is_deleted=False).count()

        resp = {
            "requests": requests,
            "assigned": assigned,
            "closed": closed,
            "pending": pending
        }

        return Response(resp, status=status.HTTP_200_OK)