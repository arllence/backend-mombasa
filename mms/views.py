import datetime
import json
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
from mms import models
from mms import serializers
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import User, Department
from main.utils import shared_fxns
from django.db.models import Sum
from acl.utils import mailgun_general
from django.core.mail import send_mail




class MmsViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]

    def get_queryset(self):
        return []
    
    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="quote",
            url_name="quote")
    def quote(self, request):
        authenticated_user = request.user
        if request.method == "POST":
            formfiles = request.FILES
            if not formfiles:
                return Response({"details": "Please upload attachment"}, status=status.HTTP_400_BAD_REQUEST)

            payload = json.loads(request.data['payload'])
            serializer = serializers.QuoteSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                description = payload['description']
                subject = payload['subject']
                department = payload['department']
                content = payload.get('content')

                try:
                    department = Department.objects.get(Q(id=department))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Department !"}, status=status.HTTP_400_BAD_REQUEST)
                
                if formfiles:
                    exts = ['jpeg','jpg','png','tiff','pdf']
                    for f in request.FILES.getlist('documents'):
                        original_file_name = f.name
                        ext = original_file_name.split('.')[1].strip().lower()
                        if ext not in exts:
                            return Response({"details": "Only Images and PDFs allowed for upload !"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():

                    if formfiles:                        
                        f = request.FILES.getlist('documents')[0]
                        file_type = shared_fxns.identify_file_type(original_file_name.split('.')[1].strip().lower())
                        try:
                            original_file_name = f.name                            
                            attachment = models.Document.objects.create(
                                        document=f, 
                                        original_file_name=original_file_name, 
                                        uploader=authenticated_user, 
                                        file_type=file_type)

                        except Exception as e:
                            # logger.error(e)
                            print(e)
                            return Response({"details": "Unable to save File(s)"}, status=status.HTTP_400_BAD_REQUEST)

                    raw = {
                        "department": department,
                        "attachment": attachment,
                        "uploader": authenticated_user,
                        "subject": subject,
                        "description": description,
                        "content": content,
                    }  

                    quote = models.Quote.objects.create(
                        **raw
                    )

                    managers_emails = get_user_model().objects.filter(groups__name='MMD_MANAGER').values_list('email', flat=True)

                    # Notify the manager
                    subject = "A New Quote Received [MMS-AKHK]"
                    message = f"Hello, \nA new quote: {quote.subject} from department:  {department.name} has been submitted by {authenticated_user.first_name} {authenticated_user.last_name} at {str(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))}\nPending your action.\n\nRegards\n MMS-AKHK"
                    # mailgun_general.send_mail(quote.uploader.first_name, quote.uploader.email,subject,message)
                    send_mail(subject, message, 'notification@akhskenya.org', managers_emails)

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Quote created", "Quote Creation Executed")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "PUT":
            formfiles = request.FILES
            # if not formfiles:
            #     return Response({"details": "Please upload attachment"}, status=status.HTTP_400_BAD_REQUEST)

            payload = json.loads(request.data['payload'])
            serializer = serializers.PutQuoteSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                quote_id = payload['id']
                description = payload['description']
                subject = payload['subject']
                department = payload['department']
                content = payload.get('content')

                try:
                    department = Department.objects.get(Q(id=department))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Department !"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    quote = models.Quote.objects.get(Q(id=quote_id))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Quote !"}, status=status.HTTP_400_BAD_REQUEST)
                
                if formfiles:
                    exts = ['jpeg','jpg','png','tiff','pdf']
                    for f in request.FILES.getlist('documents'):
                        original_file_name = f.name
                        ext = original_file_name.split('.')[1].strip().lower()
                        if ext not in exts:
                            return Response({"details": "Only Images and PDFs allowed for upload !"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():

                    if formfiles:                        
                        f = request.FILES.getlist('documents')[0]
                        file_type = shared_fxns.identify_file_type(original_file_name.split('.')[1].strip().lower())
                        try:
                            original_file_name = f.name                            
                            attachment = models.Document.objects.create(
                                        document=f, 
                                        original_file_name=original_file_name, 
                                        uploader=authenticated_user, 
                                        file_type=file_type)

                        except Exception as e:
                            # logger.error(e)
                            print(e)
                            return Response({"details": "Unable to save File(s)"}, status=status.HTTP_400_BAD_REQUEST)

                        raw = {
                            "department": department,
                            "attachment": attachment,
                            "uploader": authenticated_user,
                            "subject": subject,
                            "description": description,
                            "content": content,
                        }  
                    else:
                        raw = {
                            "department": department,
                            "uploader": authenticated_user,
                            "subject": subject,
                            "description": description,
                            "content": content,
                        } 


                    models.Quote.objects.filter(Q(id=quote_id)).update(**raw)

                    if quote.status == "INCOMPLETE":
                        managers_emails = list(get_user_model().objects.filter(groups__name='MMD_MANAGER').values_list('email', flat=True))
                        assignee = models.QuoteAssignee.objects.get(Q(quote=quote))
                        managers_emails.append(assignee.assigned.email)

                        raw = {"status" : "RESUBMITTED"}
                        models.Quote.objects.filter(Q(id=quote_id)).update(**raw)

                        # Notify the manager
                        subject = "A Quote Has Been Resubmitted [MMS-AKHK]"
                        message = f"Hello, \nQuote: {quote.subject} from department:  {department.name} has been resubmitted by {authenticated_user.first_name} {authenticated_user.last_name} at {str(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))}\nPending your action.\n\nRegards\nMMS-AKHK"
                        # mailgun_general.send_mail(quote.uploader.first_name, quote.uploader.email,subject,message)
                        send_mail(subject, message, 'notification@akhskenya.org', managers_emails)

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Quote created", "Quote Creation Executed")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PATCH":
            payload = request.data
            serializer = serializers.PatchQuoteSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                quote_id = payload['quote_id']
                quote_status = payload['status'].upper()

                try:
                    quote = models.Quote.objects.get(id=quote_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Quote !"}, status=status.HTTP_400_BAD_REQUEST)
                
                

                
                with transaction.atomic():

                    quote.status = quote_status
                    quote.save()

                    # Notify the manager
                    managers_emails = list(get_user_model().objects.filter(groups__name='MMD_MANAGER').values_list('email', flat=True))
                    emails = [quote.uploader.email] + managers_emails

                    subject = "Quote Progress Update [MMS-AKHK]"
                    message = f"Hello, \nThe Quote: {quote.subject}, from department: {quote.department.name} has been marked as {quote_status} by {authenticated_user.first_name} {authenticated_user.last_name} at {str(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))}\n\nRegards\nMMS-AKHK"

                    # mailgun_general.send_mail(quote.uploader.first_name, quote.uploader.email,subject,message)
                    send_mail(subject, message, 'notification@akhskenya.org', emails)

                    # update quote assignee status
                    raw = {"status" : 'REVIEWED'}
                    models.QuoteAssignee.objects.filter(Q(quote=quote_id) & Q(assigned=request.user)).update(**raw)
                                                

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Quote Progress Updated", f"Updated Quote: {quote_id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            roles = user_util.fetchusergroups(request.user.id)  

            if request_id:
                try:
                    resp = models.Quote.objects.get(Q(id=request_id))
                    resp = serializers.FetchQuoteSerializer(resp,many=False).data
                    return Response(resp, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Quote!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    if "MMD_STAFF" in roles:
                        quote_ids = models.QuoteAssignee.objects.filter(Q(assigned=request.user) & Q(is_deleted=False)).values_list('quote__id', flat=True)
                        resp = models.Quote.objects.filter(Q(is_deleted=False) & Q(id__in=quote_ids)).order_by('-date_created')

                    elif "MMD_MANAGER" in roles or "USER_MANAGER" in roles:
                        resp = models.Quote.objects.filter(Q(is_deleted=False)).order_by('-date_created')

                    elif "USER" in roles:
                        resp = models.Quote.objects.filter(Q(is_deleted=False) & Q(uploader=request.user)).order_by('-date_created')

                    resp = serializers.FetchQuoteSerializer(resp,many=True).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request !"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')
            if not request_id:
                return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.Quote.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)    

    
    @action(methods=["POST", "GET", "PUT", "DELETE"],
            detail=False,
            url_path="assign",
            url_name="assign")
    def assign_quote(self, request):
        authenticated_user = request.user
        if request.method == "POST":

            payload = request.data

            serializer = serializers.AssignQuoteSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                quote = payload['quote']
                staff = payload['staff']

                try:
                    quote = models.Quote.objects.get(Q(id=quote))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Quote !"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    staff = get_user_model().objects.get(Q(id=staff))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Staff !"}, status=status.HTTP_400_BAD_REQUEST)
                
                
                with transaction.atomic():

                    raw = {
                        "quote": quote,
                        "assigned": staff,
                    }  

                    models.QuoteAssignee.objects.create(
                        **raw
                    )

                    quote.status = 'ASSIGNED'
                    quote.save()

                    # Notify the uploader
                    subject = "Quote Received [MMS-AKHK]"
                    message = f"Dear {quote.uploader.first_name}, \nYour quote has been received succefully and queued for processing.\nWe will update you on the progress.\n\nRegards\nMMS-AKHK"

                    # mailgun_general.send_mail(quote.uploader.first_name, quote.uploader.email,subject,message)
                    send_mail(subject, message, 'notification@akhskenya.org', [quote.uploader.email])

                    # Notify the staff
                    subject = "Quote Assigned To You [MMS-AKHK]"
                    message = f"Dear {staff.first_name}, \nA quote has been assigned to you for review and processing.\nPlease log in to MMS to review.\n\nRegards\nMMS-AKHK"

                    # mailgun_general.send_mail(staff.first_name, staff.email,subject,message)
                    send_mail(subject, message, 'notification@akhskenya.org', [staff.email])

                user_util.log_account_activity(
                    authenticated_user, staff, "Quote Assigned created", "Quote Assignation Executed")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            roles = user_util.fetchusergroups(request.user.id)  

            if request_id:
                try:
                    resp = models.QuoteAssignee.objects.get(Q(id=request_id))
                    resp = serializers.FetchAssignQuoteSerializer(resp,many=False).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    if "MMD_STAFF" in roles:
                        resp = models.QuoteAssignee.objects.filter(Q(assigned=request.user) & Q(is_deleted=False))

                    elif "MMD_MANAGER" in roles or "USER_MANAGER" in roles:
                        resp = models.QuoteAssignee.objects.filter(Q(is_deleted=False)).order_by('-date_created')

                    resp = serializers.FetchAssignQuoteSerializer(resp,many=True).data

                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Request !"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == "DELETE":
            request_id = request.query_params.get('request_id')

            if not request_id:
                return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                try:
                    raw = {"is_deleted" : True}
                    models.QuoteAssignee.objects.filter(Q(id=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)
