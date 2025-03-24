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
from mms import models
from mms import serializers
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import Sendmail, User, Department
from mms.utils import shared_fxns
from django.db.models import Sum
from acl.utils import mailgun_general
from django.core.mail import send_mail

from mms.utils.custom_pagination import CustomPagination
from rest_framework.viewsets import ViewSetMixin
from rest_framework.pagination import PageNumberPagination

# Get an instance of a logger
logger = logging.getLogger(__name__)

class MmsViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    # pagination_class = CustomPagination
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="quote",
            url_name="quote")
    def quote(self, request, *args, **kwargs):
        authenticated_user = request.user
        if request.method == "POST":
            formfiles = request.FILES


            payload = json.loads(request.data['payload'])
            serializer = serializers.QuoteSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                description = payload['description']
                subject = payload['subject']
                department = payload['department']
                content = payload.get('content')
                qid = shared_fxns.generate_unique_identifier()

                try:
                    department = Department.objects.get(Q(id=department))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Department !"}, status=status.HTTP_400_BAD_REQUEST)
                
                # if formfiles:
                #     exts = ['jpeg','jpg','png','tiff','pdf','doc','docx']
                #     for f in request.FILES.getlist('documents'):
                #         original_file_name = f.name
                #         ext = original_file_name.split('.')[1].strip().lower()
                #         if ext not in exts:
                #             return Response({"details": "Only Images, Word and PDFs allowed for upload !"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    attachment = None
                    if formfiles:                        
                        f = request.FILES.getlist('documents')[0]
                        original_file_name = f.name
                        file_type = shared_fxns.identify_file_type(original_file_name.split('.')[1].strip().lower())
                        try:                          
                            attachment = models.Document.objects.create(
                                        document=f, 
                                        original_file_name=original_file_name, 
                                        uploader=authenticated_user, 
                                        file_type=file_type)

                        except Exception as e:
                            logger.error(e)
                            print(e)
                            return Response({"details": "Unable to save File(s)"}, status=status.HTTP_400_BAD_REQUEST)

                    raw = {
                        "department": department,
                        "attachment": attachment,
                        "uploader": authenticated_user,
                        "subject": subject,
                        "description": description,
                        "content": content,
                        "qid": qid
                    }  

                    quote = models.Quote.objects.create(
                        **raw
                    )

                    managers_emails = list(get_user_model().objects.filter(groups__name='MMD').values_list('email', flat=True))

                    # Notify the manager
                    subject = f"A New Quote {qid} Received [PSMDQS-AKHK]"
                    message = f"Hello, \nA new quote: {qid} of subject: {quote.subject} from department:  {department.name}\nhas been submitted by {authenticated_user.first_name} {authenticated_user.last_name}\non {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending your action.\n\nRegards\n PSMDQS-AKHK"

                    try:
                        mail = {
                            "email" : managers_emails, 
                            "subject" : subject,
                            "message" : message,
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        send_mail(subject, message, 'notification@akhskenya.org', managers_emails)
                        
                    

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Quote created", "Quote Creation Executed")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "PUT":
            formfiles = request.FILES


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
                
                # if formfiles:
                #     exts = ['jpeg','jpg','png','tiff','pdf']
                #     for f in request.FILES.getlist('documents'):
                #         original_file_name = f.name
                #         ext = original_file_name.split('.')[1].strip().lower()
                #         if ext not in exts:
                #             return Response({"details": "Only Images and PDFs allowed for upload !"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():

                    if formfiles:                        
                        f = request.FILES.getlist('documents')[0]
                        original_file_name = f.name
                        file_type = shared_fxns.identify_file_type(original_file_name.split('.')[1].strip().lower())
                        try:                         
                            attachment = models.Document.objects.create(
                                        document=f, 
                                        original_file_name=original_file_name, 
                                        uploader=authenticated_user, 
                                        file_type=file_type)

                        except Exception as e:
                            logger.error(e)
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
                        managers_emails = list(get_user_model().objects.filter(groups__name='MMD').values_list('email', flat=True))
                        assignee = models.QuoteAssignee.objects.get(Q(quote=quote))
                        managers_emails.append(assignee.assigned.email)

                        raw = {"status" : "RESUBMITTED"}
                        models.Quote.objects.filter(Q(id=quote_id)).update(**raw)

                        # Notify the manager
                        subject = f"A Quote: {quote.qid} Has Been Resubmitted [PSMDQS-AKHK]"
                        message = f"Hello, \nQuote:{quote.qid} of subject: {quote.subject} from department:  {department.name} \nhas been resubmitted by {authenticated_user.first_name} {authenticated_user.last_name} \non {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending your action.\n\nRegards\nPSMDQS-AKHK"

                        try:
                            mail = {
                                "email" : managers_emails, 
                                "subject" : subject,
                                "message" : message,
                            }
                            Sendmail.objects.create(**mail)
                        except Exception as e:
                            send_mail(subject, message, 'notification@akhskenya.org', managers_emails)
     

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Quote updated", f"QID: {quote_id}")
                
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
                reason = payload.get('reason', None)

                try:
                    quote = models.Quote.objects.get(id=quote_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Quote !"}, status=status.HTTP_400_BAD_REQUEST)
                
                if quote_status in ['REJECTED', 'INCOMPLETE']:
                    if not reason:
                        return Response({"details": "Reason for status update required !"}, status=status.HTTP_400_BAD_REQUEST)

                
                with transaction.atomic():

                    quote.status = quote_status
                    if reason:
                        current_reason = quote.reasons

                        if current_reason:
                            current_reason.append(
                                {
                                    "status": quote_status,
                                    "reason": reason,
                                    "date": str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))
                                }
                            )
                            quote.reasons = current_reason
                        else:
                            quote.reasons =  [
                                {
                                    "status": quote_status,
                                    "reason": reason,
                                    "date": str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))
                                }
                            ]

                    quote.save()

                    # Notify the manager
                    managers_emails = list(get_user_model().objects.filter(groups__name='MMD').values_list('email', flat=True))
                    emails = [quote.uploader.email] + managers_emails

                    subject = f"Quote: {quote.qid} Progress Update [PSMDQS-AKHK]"
                    if reason:
                        message = f"Hello, \n\nThe Quote of Id: {quote.qid}\nfrom department: {quote.department.name} has been marked as {quote_status}\nby {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nreason being:\n`{reason}`\n\nRegards\nPSMDQS-AKHK"
                    else:
                        message = f"Hello, \nThe Quote:{quote.qid} of subject {quote.subject}, from department: {quote.department.name} has been marked as {quote_status} by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\n\nRegards\nPSMDQS-AKHK"

                    try:
                        mail = {
                            "email" : emails, 
                            "subject" : subject,
                            "message" : message,
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        send_mail(subject, message, 'notification@akhskenya.org', emails)

                    # update quote assignee status
                    raw = {"status" : 'REVIEWED'}
                    models.QuoteAssignee.objects.filter(Q(quote=quote_id) & Q(assigned=request.user)).update(**raw)
                                                

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Quote Progress Updated", f"Updated Quote: {quote_id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            assigned = request.query_params.get('assigned')
            query = request.query_params.get('q')
            roles = user_util.fetchusergroups(request.user.id)  

            if request_id:
                try:
                    resp = models.Quote.objects.get(Q(id=request_id))
                    resp = serializers.FetchQuoteSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    return Response(resp, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Quote!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    if assigned:
                        quote_ids = models.QuoteAssignee.objects.filter(Q(assigned=request.user) & Q(is_deleted=False)).values_list('quote__id', flat=True)
                        resp = models.Quote.objects.filter(Q(is_deleted=False) & Q(id__in=quote_ids)).order_by('-date_created')

                    elif query == 'pending':
                        if not any(role in ['MMD'] for role in roles):
                            return Response([], status=status.HTTP_200_OK)  
                        resp = models.Quote.objects.filter(
                            Q(is_deleted=False)).exclude(Q(status__in=['REJECTED','CLOSED'])).order_by('date_created')
                    else:
                        if "MMD" in roles or "SUPERUSER" in roles:
                            resp = models.Quote.objects.filter(Q(is_deleted=False)).order_by('-date_created')

                        elif "HOD" in roles or "SLT" in roles:
                            resp = models.Quote.objects.filter(Q(department=request.user.department) | Q(uploader=request.user), is_deleted=False).order_by('-date_created')

                        else:
                            resp = models.Quote.objects.filter(Q(is_deleted=False) & Q(uploader=request.user)).order_by('-date_created')


                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resp, request)
                    serializer = serializers.FetchQuoteSerializer(result_page, many=True, context={"user_id":request.user.id})
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
                    subject = "Quote Received [PSMDQS-AKHK]"
                    message = f"Dear {quote.uploader.first_name}, \nYour quote has been received successfully\nand assigned to {staff.first_name} {staff.last_name} for processing.\nWe will update you on the progress.\n\nRegards\nPSMDQS-AKHK"

                    try:
                        mail = {
                            "email" : [quote.uploader.email], 
                            "subject" : subject,
                            "message" : message,
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        send_mail(subject, message, 'notification@akhskenya.org', [quote.uploader.email])

                    # Notify the staff
                    subject = "Quote Assigned To You [PSMDQS-AKHK]"
                    message = f"Dear {staff.first_name}, \nA quote has been assigned to you for review and processing.\nPlease log in to PSMDQS to review.\n\nRegards\nPSMDQS-AKHK"

                    try:
                        mail = {
                            "email" : [staff.email], 
                            "subject" : subject,
                            "message" : message,
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        send_mail(subject, message, 'notification@akhskenya.org', [staff.email])

                user_util.log_account_activity(
                    authenticated_user, staff, "Quote Assigned created", f"Quote Assignation Executed QID: {quote.id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "PUT":

            payload = request.data

            serializer = serializers.AssignQuoteSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                quote = payload['quote']
                staff = payload['staff']

                try:
                    quote = models.QuoteAssignee.objects.get(Q(quote=quote))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Quote !"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    staff = get_user_model().objects.get(Q(id=staff))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Staff !"}, status=status.HTTP_400_BAD_REQUEST)
                
                
                with transaction.atomic():
                    
                    quote.assigned = staff
                    quote.save()

                    # Notify the staff
                    subject = "Quote Assigned To You [PSMDQS-AKHK]"
                    message = f"Dear {staff.first_name}, \nA quote has been assigned to you for review and processing.\nPlease log in to PSMDQS to review.\n\nRegards\nPSMDQS-AKHK"

                    try:
                        mail = {
                            "email" : [staff.email], 
                            "subject" : subject,
                            "message" : message,
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        send_mail(subject, message, 'notification@akhskenya.org', [staff.email])

                user_util.log_account_activity(
                    authenticated_user, staff, "Quote Assigned created", f"Quote Assignation Executed QID: {quote.id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            assigned = request.query_params.get('assigned')
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
                    if assigned:
                        resp = models.QuoteAssignee.objects.filter(Q(assigned=request.user) & Q(is_deleted=False))

                    elif "MMD" in roles or "USER_MANAGER" in roles:
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
                
    
    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="close-quote",
            url_name="close-quote")
    def close_quote(self, request):
        authenticated_user = request.user
        if request.method == "POST":
            formfiles = request.FILES
            if not formfiles:
                return Response({"details": "Please upload attachments"}, status=status.HTTP_400_BAD_REQUEST)

            payload = json.loads(request.data['payload'])
            serializer = serializers.CloseQuoteSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                quote = payload['quote']

                try:
                    quote = models.Quote.objects.get(Q(id=quote))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Quote !"}, status=status.HTTP_400_BAD_REQUEST)
                
                # if formfiles:
                #     exts = ['jpeg','jpg','png','tiff','pdf','doc','docx']

                #     for f in request.FILES.getlist('quote'):
                #         original_file_name = f.name
                #         ext = original_file_name.split('.')[1].strip().lower()
                #         if ext not in exts:
                #             return Response({"details": "Only Images, Word and PDF files allowed for upload !"}, status=status.HTTP_400_BAD_REQUEST)

                
                with transaction.atomic():
    
                    try:
                        quoteFile = request.FILES.getlist('quote')[0]
                        file_type1 = shared_fxns.identify_file_type(quoteFile.name.split('.')[1].strip().lower())
                        title1 = "CLOSE_QUOTE_FILE"
                    except Exception as e:
                        return Response({"details": "Upload Quote File !"}, status=status.HTTP_400_BAD_REQUEST)                  
                    
                    try:                         
                        quote_file = models.Document.objects.create(
                                    document=quoteFile, 
                                    original_file_name=quoteFile.name, 
                                    uploader=authenticated_user, 
                                    file_type=file_type1,
                                    title=title1,
                                    )

                        
                        attachments = {
                            "quote_file": str(quote_file.id),
                        }

                        # update quote instance
                        quote.close_attachments = attachments
                        quote.status = "CLOSED"
                        quote.date_closed = datetime.datetime.now()
                        quote.save()

                        emails = list(get_user_model().objects.filter(groups__name='MMD').values_list('email', flat=True))
                        emails.append(quote.uploader.email)

                        # Notify the manager and users
                        subject = f"Quote: {quote.qid} Request Uploaded [PSMDQS-AKHK]"
                        message = f"Hello. \nQuote: {quote.qid} of subject {quote.subject} from department:  {quote.department.name} has been UPLOADED by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.\nPlease log in to PSMDQS to download.\n\nRegards\n PSMDQS-AKHK"

                        try:
                            mail = {
                                "email" : emails, 
                                "subject" : subject,
                                "message" : message,
                            }
                            Sendmail.objects.create(**mail)
                        except Exception as e:
                            send_mail(subject, message, 'notification@akhskenya.org', emails)

                        user_util.log_account_activity(
                            authenticated_user, authenticated_user, "Quote Closed", f"Quote Closure Executed QID: {quote.id}")

                    except Exception as e:
                        logger.error(e)
                        print(e)
                        return Response({"details": "Unable to save File(s)"}, status=status.HTTP_400_BAD_REQUEST)


                    
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class MMQSReportsViewSet(viewsets.ViewSet):
    # search_fields = ['id', ]

    def get_queryset(self):
        return []

    @action(methods=["GET",],
            detail=False,
            url_path="quotation",
            url_name="quotation")
    def quotation_reports(self, request):
                    
        department = request.query_params.get('department')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        quote_status = request.query_params.get('status')
        assigned = request.query_params.get('assigned')
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
            
        if quote_status:
            q_filters &= Q(status=quote_status)

        resp = models.Quote.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
        if not q_filters:
            roles = user_util.fetchusergroups(request.user.id)  

            if assigned:
                quote_ids = models.QuoteAssignee.objects.filter(Q(assigned=request.user) & Q(is_deleted=False)).values_list('quote__id', flat=True)
                resp = models.Quote.objects.filter(Q(is_deleted=False) & Q(id__in=quote_ids)).order_by('-date_created')[:20]


            if "MMD" in roles or "USER_MANAGER" in roles:
                resp = models.Quote.objects.filter(Q(is_deleted=False)).order_by('-date_created')[:20]

            elif "USER" in roles:
                resp = models.Quote.objects.filter(Q(is_deleted=False) & Q(uploader=request.user)).order_by('-date_created')[:20]

        resp = serializers.FetchQuoteSerializer(resp, many=True, context={"user_id":request.user.id}).data
        return Response(resp, status=status.HTTP_200_OK)

        
class MMQSAnalyticsViewSet(viewsets.ViewSet):
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
            quotes = models.Quote.objects.filter(Q(is_deleted=False) & Q(uploader=request.user)).count()
            requested = models.Quote.objects.filter(Q(status="REQUESTED") | Q(status="ASSIGNED"),is_deleted=False, uploader=request.user).count()
            closed = models.Quote.objects.filter(Q(status="CLOSED") & Q(is_deleted=False) & Q(uploader=request.user)).count()
            assiged = models.Quote.objects.filter(Q(status="ASSIGNED") & Q(is_deleted=False) & Q(uploader=request.user)).count()
            incomplete = models.Quote.objects.filter(Q(status="INCOMPLETE") & Q(is_deleted=False) & Q(uploader=request.user)).count()
        else:
            quotes = models.Quote.objects.filter(Q(is_deleted=False)).count()
            requested = models.Quote.objects.filter(Q(status="REQUESTED") | Q(status="ASSIGNED"),is_deleted=False).count()
            closed = models.Quote.objects.filter(Q(status="CLOSED") & Q(is_deleted=False)).count()
            assiged = models.Quote.objects.filter(Q(status="ASSIGNED") & Q(is_deleted=False)).count()
            incomplete = models.Quote.objects.filter(Q(status="INCOMPLETE") & Q(is_deleted=False)).count()

        resp = {
            "quotes": quotes,
            "requested": requested,
            "closed": closed,
            "assiged": assiged,
            "incomplete": incomplete,
        }

        return Response(resp, status=status.HTTP_200_OK)