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
from srrs import models
from srrs import serializers
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import User, Department, Sendmail
from srrs.utils import shared_fxns
from django.db.models import Sum
from django.core.mail import send_mail

from rest_framework.pagination import PageNumberPagination

# Get an instance of a logger
logger = logging.getLogger(__name__)

class TrsViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    
    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="recruit",
            url_name="recruit")
    def recruit(self, request):
        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.RecruitSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                position_title = payload['position_title']
                position_type = payload['position_type']
                qualifications = payload['qualifications']
                job_description = payload['job_description']
                nature_of_hiring = payload['nature_of_hiring']
                existing_staff_same_title = payload['existing_staff_same_title']
                reasons_for_not_sharing_tasks = payload['reasons_for_not_sharing_tasks']
                filling_period_from = payload['filling_period_from']
                filling_period_to = payload['filling_period_to']
                temporary_task_assignment_to = payload['temporary_task_assignment_to']

                uid = shared_fxns.generate_unique_identifier()

                department = authenticated_user.department
                if not department:
                    return Response({"details": "Department Required !"}, status=status.HTTP_400_BAD_REQUEST)

                if not qualifications:
                    return Response({"details": "Qualifications Required !"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    raw = {
                        "department": department,
                        "created_by": authenticated_user,
                        "position_title": position_title,
                        "position_type": position_type,
                        "qualifications": qualifications,
                        "job_description": job_description,
                        "nature_of_hiring": nature_of_hiring,
                        "existing_staff_same_title": existing_staff_same_title,
                        "reasons_for_not_sharing_tasks": reasons_for_not_sharing_tasks,
                        "filling_period_from": filling_period_from,
                        "filling_period_to": filling_period_to,
                        "temporary_task_assignment_to": temporary_task_assignment_to,
                        "uid": uid
                    }  

                    recruit = models.Recruit.objects.create(
                        **raw
                    )

                    # create track status change
                    raw = {
                        "recruit": recruit,
                        "status": "REQUESTED",
                        "status_for": "HOD",
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)


                    if department.slt:
                        managers_emails = [department.slt.lead.email]
                    else:
                        return Response({"details": "Your Department has no SLT assigned !"}, status=status.HTTP_400_BAD_REQUEST)
                        
                        

                    # Notify SLT
                    subject = f"New Recruitment Request {uid} Received [SRRS-AKHK]"
                    message = f"Hello, \n\nA new recruit request of id: {uid}, from department: {department.name}\nhas been submitted by {authenticated_user.first_name} {authenticated_user.last_name}on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending your action.\n\nRegards\SRRS-AKHK"

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
                    authenticated_user, authenticated_user, "Recruitment Request created", f"Recruitment Request Id: {recruit.id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "PUT":
            payload = request.data

            serializer = serializers.PutRecruitSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                position_title = payload['position_title']
                position_type = payload['position_type']
                qualifications = payload['qualifications']
                job_description = payload['job_description']
                nature_of_hiring = payload['nature_of_hiring']
                existing_staff_same_title = payload['existing_staff_same_title']
                reasons_for_not_sharing_tasks = payload['reasons_for_not_sharing_tasks']
                filling_period_from = payload['filling_period_from']
                filling_period_to = payload['filling_period_to']
                temporary_task_assignment_to = payload['temporary_task_assignment_to']

                try:
                    recruit = models.Recruit.objects.get(id=request_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Recruit Request !"}, status=status.HTTP_400_BAD_REQUEST)
                
                # keep history
                try:
                    history = serializers.SlimFetchRecruitSerializer(recruit, many=False).data
                    raw = {
                        "uid" : recruit.uid,
                        "data" : history,
                        "triggered_by": authenticated_user
                    }
                    models.RecruitHistory.objects.create(**raw)
                except Exception as e:
                    print(e)


                department = authenticated_user.department
                if not department:
                    return Response({"details": "Department Required !"}, status=status.HTTP_400_BAD_REQUEST)

                if not qualifications:
                    return Response({"details": "Qualifications Required !"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    raw = {
                        "department": department,
                        "created_by": authenticated_user,
                        "position_title": position_title,
                        "position_type": position_type,
                        "qualifications": qualifications,
                        "job_description": job_description,
                        "nature_of_hiring": nature_of_hiring,
                        "existing_staff_same_title": existing_staff_same_title,
                        "reasons_for_not_sharing_tasks": reasons_for_not_sharing_tasks,
                        "filling_period_from": filling_period_from,
                        "filling_period_to": filling_period_to,
                        "temporary_task_assignment_to": temporary_task_assignment_to,
                    }  

                    models.Recruit.objects.filter(Q(id=request_id)).update(**raw)

                    # create track status change
                    raw = {
                        "recruit": recruit,
                        "status": "UPDATED",
                        "status_for": '/'.join(roles),
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)


                    # Notify SLT
                    subject = f"New Recruitment Request {uid} Received [SRRS-AKHK]"
                    message = f"Hello, \n\nA new recruit request of id: {uid}, from department: {department.name}\nhas been submitted by {authenticated_user.first_name} {authenticated_user.last_name}on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending your action.\n\nRegards\SRRS-AKHK"

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
                    authenticated_user, authenticated_user, "Recruitment Request created", f"Recruitment Request Id: {recruit.id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            
        elif request.method == "PATCH":
            payload = request.data
            serializer = serializers.PatchTravelerSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                traveler_id = payload['traveler_id']
                traveler_status = payload['status'].upper()
                # roles = user_util.fetchusergroups(request.user.id)  

                try:
                    traveler = models.Traveler.objects.get(id=traveler_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Travel !"}, status=status.HTTP_400_BAD_REQUEST)
            
                
                with transaction.atomic():

                    if traveler_status == 'REJECTED':
                        traveler.rejected_by = authenticated_user

                    traveler.status = traveler_status
                    traveler.save()

                    # update advance travel request
                    try:
                        salaryRequest = models.AdvanceSalaryRequests.objects.get(
                            traveler=traveler)
                        salaryRequest.status = traveler_status
                        salaryRequest.approved_by = authenticated_user
                        salaryRequest.save()
                    except (ValidationError, ObjectDoesNotExist):
                        pass

                    raw = {
                        "traveler": traveler,
                        "status": traveler_status,
                        "status_for": '/'.join(roles),
                        "action_by": authenticated_user,
                    }

                    models.StatusChange.objects.create(**raw)

                    # Notify requestor
                    emails = [traveler.created_by.email]

                    subject = f"Travel Request: {traveler.tid} Progress Update [TRS-AKHK]"
                    message = f"Hello, \nThe Request:{traveler.tid} has been marked as {traveler_status} by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\n\nRegards\nTRS-AKHK"

                    # try:
                    #     send_mail(subject, message, 'notification@akhskenya.org', emails)
                    # except Exception as e:
                    #     pass
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
                    authenticated_user, authenticated_user, f"Travel Request Status: {traveler_status}", f"Travel Request: {traveler_id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            query = request.query_params.get('q')
            # roles = user_util.fetchusergroups(request.user.id)  

            if request_id:
                try:
                    resp = models.Traveler.objects.get(Q(id=request_id))
                    resp = serializers.FetchTravelerSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Quote!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:

                    if "HOD" in roles:

                        if query == 'salary-advance':
                            targets = models.AdvanceSalaryRequests.objects.filter(
                                Q(traveler__created_by=authenticated_user) & Q(traveler__department=request.user.department),is_deleted=False).order_by('-date_created')
                            resp = [x.traveler for x in targets]

                        elif query == 'pending':
                            resp = models.Traveler.objects.filter(Q(traveler__department=request.user.department) | Q(department=request.user.department) | Q(created_by=request.user) | Q(requires_hod_approval=True) , is_hod_approved=False, is_deleted=False).order_by('-date_created')

                        else:
                            resp = models.Traveler.objects.filter(Q(traveler__department=request.user.department) | Q(department=request.user.department) | Q(created_by=request.user) | Q(requires_hod_approval=True) |  Q(created_by=authenticated_user), is_deleted=False).order_by('-date_created')

                    elif "USER_MANAGER" in roles:
                        if query == 'salary-advance':
                            targets = models.AdvanceSalaryRequests.objects.filter(Q(is_deleted=False)).order_by('-date_created')
                            resp = [
                                    x.traveler 
                                    for x in targets 
                                ]
                        else:
                            resp = models.Traveler.objects.filter(Q(is_deleted=False) ).order_by('-date_created')

                    elif "SLT" in roles:
                        resp = []
                        if "HOF" in roles:

                            if query == 'salary-advance':
                                targets = models.AdvanceSalaryRequests.objects.filter(Q(is_deleted=False)).order_by('-date_created')
                                resp = [x.traveler for x in targets]

                            elif query == 'pending':
                                resp = models.Traveler.objects.filter((Q(department__slt__lead=authenticated_user) & Q(requires_slt_approval=True)) | Q(requires_hof_approval=True), is_deleted=False,is_hof_approved=False).order_by('-date_created')

                            else:
                                resp = models.Traveler.objects.filter((Q(department__slt__lead=authenticated_user) & Q(requires_slt_approval=True)) | Q(requires_hof_approval=True), is_deleted=False).order_by('-date_created')

                        else:
                            resp = models.Traveler.objects.filter(Q(is_deleted=False) & Q(department__slt__lead=authenticated_user) & Q(requires_slt_approval=True)).order_by('-date_created')

                    elif "HOF" in roles:
                        if not query:
                            resp = models.Traveler.objects.filter(Q(requires_hof_approval=True),is_deleted=False).order_by('-date_created')

                        if query == 'salary-advance':
                            targets = models.AdvanceSalaryRequests.objects.filter(Q(is_deleted=False)).order_by('-date_created')
                            resp = [x.traveler for x in targets]

                        elif query == 'pending':
                            resp = models.Traveler.objects.filter(Q(requires_hof_approval=True) & Q(is_hof_approved=False), is_deleted=False).order_by('-date_created')
                    
                    elif "CEO" in roles:
                        if not query:
                            resp = models.Traveler.objects.filter(Q(requires_ceo_approval=True), is_deleted=False).order_by('-date_created')

                        if query == 'salary-advance':
                            targets = models.AdvanceSalaryRequests.objects.filter(Q(is_deleted=False)).order_by('-date_created')
                            resp = [x.traveler for x in targets]

                        elif query == 'pending':
                            resp = models.Traveler.objects.filter(Q(requires_ceo_approval=True) & Q(is_ceo_approved=False), is_deleted=False).order_by('-date_created')

                    elif "USER" in roles:
                        if not query:
                            resp = models.Traveler.objects.filter(Q(is_deleted=False) & Q(traveler=request.user)).order_by('-date_created')

                        if query == 'salary-advance':
                            targets = models.AdvanceSalaryRequests.objects.filter(Q(is_deleted=False) & Q(traveler__traveler=request.user)).order_by('-date_created')
                            resp = [x.traveler for x in targets]

                    elif "ADMINISTRATOR" in roles :
                        allowed_statuses = ['APPROVED', 'CLOSED']

                        if query == 'pending':
                            resp = models.Traveler.objects.filter(Q(requires_administrator_approval=True) & Q(is_administrator_approved=False), is_deleted=False).order_by('-date_created')

                        elif query == 'salary-advance':
                            resp = []

                        else:
                            resp = models.Traveler.objects.filter(Q(is_deleted=False) & Q(requires_administrator_approval=True) & Q(status__in=allowed_statuses)).order_by('-date_created')

                    
                    elif "CASH_OFFICE" in roles :
                        allowed_statuses = ['APPROVED', 'CLOSED']
                        
                        if query == 'pending':
                            print("is pending")
                            resp = models.Traveler.objects.filter(Q(requires_cash_office_approval=True) & Q(is_cash_office_approved=False), is_deleted=False).order_by('-date_created')

                        if query == 'salary-advance':
                            targets = models.AdvanceSalaryRequests.objects.filter(Q(is_deleted=False), status='APPROVED').order_by('-date_created')
                            resp = [x.traveler for x in targets]

                        else:
                            resp = models.Traveler.objects.filter(Q(is_deleted=False) & Q(requires_cash_office_approval=True) & Q(status__in=allowed_statuses)).order_by('-date_created')

                    elif "TRANSPORT" in roles :
                        allowed_statuses = ['APPROVED', 'CLOSED']
                        
                        if query == 'pending':
                            resp = models.Traveler.objects.filter(Q(requires_transport_approval=True) & Q(is_administrator_approved=False), is_deleted=False).order_by('-date_created')
                        elif query == 'salary-advance':
                            resp = []
                        else:
                            resp = models.Traveler.objects.filter(Q(is_deleted=False) & Q(requires_transport_approval=True) & Q(status__in=allowed_statuses) ).order_by('-date_created')


                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resp, request)
                    serializer = serializers.FetchTravelerSerializer(
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
                    models.Traveler.objects.filter(Q(id=request_id)).update(**raw)
                    models.Trip.objects.filter(Q(traveler=request_id)).update(**raw)
                    models.Approval.objects.filter(Q(traveler=request_id)).update(**raw)
                    return Response('200', status=status.HTTP_200_OK)     
                except Exception as e:
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)    

    
    @action(methods=["POST", "GET", "PUT", "DELETE"],
            detail=False,
            url_path="approve-request",
            url_name="approve-request")
    def approval(self, request):

        authenticated_user = request.user

        if request.method == "POST":

            payload = request.data
            roles = user_util.fetchusergroups(request.user.id) 

            serializer = serializers.ApprovalSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                traveler = payload['traveler']
                travel_status = payload['status']
                budget_code = payload.get('budget_code')

                try:
                    traveler = models.Traveler.objects.get(Q(id=traveler))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Trip !"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():

                    is_hod = False
                    is_ceo = False
                    is_slt = False
                    is_hof = False
                    is_cash_office = False
                    is_transport_office = False
                    is_administrator_office = False

                    traveler_status = "APPROVED"

                    if travel_status == 'HOD':
                        is_hod = True
                        approval_for = "HOD"
                        traveler_status = "APPROVED"
                        
                    elif travel_status == "SLT":
                        is_slt = True
                        approval_for = "SLT"
                        traveler_status = "APPROVED"

                    elif travel_status == "HOF" :
                        is_hof = True
                        approval_for = "HOF"
                        traveler.status = 'APPROVED'
                        
                    elif travel_status == "CEO":
                        is_ceo = True
                        approval_for = "CEO"
                        traveler.status = 'APPROVED'
                        traveler.requires_cash_office_approval = True
                        traveler.requires_hof_approval = True

                        if traveler.mode_of_transport == 'FLIGHT':
                            traveler.requires_administrator_approval = True
                        elif traveler.mode_of_transport == 'HOSPITAL VEHICLE':
                            traveler.requires_transport_approval = True


                        try:
                            salaryRequest = models.AdvanceSalaryRequests.objects.get(
                                traveler=traveler)
                            salaryRequest.status = 'APPROVED'
                            salaryRequest.approved_by = authenticated_user
                            salaryRequest.save()
                        except (ValidationError, ObjectDoesNotExist):
                            pass


                    elif travel_status == "TRANSPORT":
                        is_transport_office = True
                        approval_for = "TRANSPORT"

                        approval_msg = payload.get('text')
                        if not approval_msg:
                            return Response({"details": "Number Plate / Date of Travel !"}, status=status.HTTP_400_BAD_REQUEST)
                        
                        approval_msg.update({"date_created": str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))})

                    elif travel_status == "CASH_OFFICE":
                        is_cash_office = True
                        approval_for = "CASH_OFFICE"

                        approval_msg = payload.get('text')
                        disbursement_type =  approval_msg.get('disbursement_type')

                        if not approval_msg:
                            return Response({"details": "Amount / Transaction Code / Remarks Required !"}, status=status.HTTP_400_BAD_REQUEST)
                        
                        approval_msg.update({"date_created": str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))})
                        original_approval_msg = approval_msg


                    is_existing = models.Approval.objects.filter(Q(traveler=traveler) & 
                                                                 Q(approval_for=approval_for)).first()

                    raw = {
                        "traveler": traveler,
                        "approval_for": approval_for,
                        "approved_by": authenticated_user,
                    }  

                    if is_cash_office:
                        raw.update({"approval_msg": [approval_msg]})

                    if is_transport_office:
                        raw.update({"approval_msg": approval_msg})

                    if is_existing:
                        is_update = True
                        # previous_approval_msg = is_existing.approval_msg
                        # previous_approval_msg.append(approval_msg)

                        # # update existing instance
                        # is_existing.approval_msg = previous_approval_msg
                        # is_existing.approved_by = authenticated_user
                        # is_existing.save()

                    else:
                        is_update = False
                        createdInstance = models.Approval.objects.create(
                            **raw
                        )

                    
                    traveler.budget_code = budget_code

                    def update_approval():
                        previous_approval_msg = is_existing.approval_msg
                        previous_approval_msg.append(original_approval_msg)

                        # update existing instance
                        is_existing.approval_msg = previous_approval_msg
                        is_existing.approved_by = authenticated_user
                        is_existing.save()

                    def close_request():
                        if traveler.mode_of_transport != 'FLIGHT' and traveler.is_ceo_approved and traveler.is_hof_approved and traveler.is_transport_dpt_approved:
                            traveler_status = "CLOSED"
                            traveler.status = traveler_status
                            traveler.closed_by = authenticated_user
                            traveler.date_closed = datetime.datetime.now()

                        if traveler.mode_of_transport == 'FLIGHT' and traveler.is_ceo_approved and traveler.is_hof_approved and traveler.is_administrator_approved:
                            traveler_status = "CLOSED"
                            traveler.status = traveler_status
                            traveler.closed_by = authenticated_user
                            traveler.date_closed = datetime.datetime.now()


                    if is_hod:
                        traveler.status = traveler_status
                        traveler.is_hod_approved = is_hod

                    if is_ceo:
                        traveler.is_ceo_approved = is_ceo

                    if is_slt:
                        traveler.is_slt_approved = is_slt

                    if is_hof:
                        traveler.is_hof_approved = is_hof
                        close_request()

                    if is_cash_office:

                        amount = int(approval_msg.get('amount',0))
                        travel_cost = int(traveler.travel_cost)
                        
                        if is_update:
                            amount = int(payload.get('text').get('amount'))
                            approval_msg = is_existing.approval_msg

                            for msg in approval_msg:
                                if disbursement_type == msg.get('disbursement_type'):
                                    amount += int(msg.get('amount',0))

                            if disbursement_type == 'Travel Cost':
                                if amount == travel_cost:
                                    traveler.is_cash_office_approved = is_cash_office
                                    close_request()
                                    update_approval()
                                elif amount < travel_cost:
                                    update_approval()
                                elif amount > travel_cost:
                                    return Response({"details": "Disbursement cannot be more than requested amount!"},status=status.HTTP_400_BAD_REQUEST)
                                
                            elif disbursement_type == 'Travel Advance':
                                amount = int(payload.get('text').get('amount'))
                                for msg in approval_msg:
                                    if disbursement_type == msg.get('disbursement_type'):
                                        amount += int(msg.get('amount',0))

                                advance = models.AdvanceSalaryRequests.objects.get(traveler=traveler)
                                travel_cost = advance.amount
                                
                                if amount == travel_cost:
                                    advance.status = "CLOSED"
                                    advance.save()
                                elif amount > travel_cost:
                                    return Response({"details": "Disbursement cannot be more than requested amount!"}, 
                                                    status=status.HTTP_400_BAD_REQUEST)
                                update_approval()
                        else:
                            if disbursement_type == 'Travel Cost':

                                if amount == travel_cost:
                                    close_request()

                                elif amount > travel_cost:
                                    createdInstance.approval_msg = []
                                    createdInstance.save()
                                    return Response({"details": "Disbursement cannot be more than requested amount!"}, 
                                                    status=status.HTTP_400_BAD_REQUEST)
                            elif disbursement_type == 'Travel Advance':
                                advance = models.AdvanceSalaryRequests.objects.get(traveler=traveler)
                                travel_cost = advance.amount
                                if amount == travel_cost:
                                    advance.status = "CLOSED"
                                    advance.save()
                                elif amount > travel_cost:
                                    createdInstance.approval_msg = []
                                    createdInstance.save()
                                    return Response({"details": "Disbursement cannot be more than requested amount!"}, 
                                                    status=status.HTTP_400_BAD_REQUEST)

                    if is_transport_office:
                        if traveler.is_ceo_approved and traveler.is_hof_approved and traveler.is_cash_office_approved:
                            traveler_status = "CLOSED"
                            traveler.status = traveler_status
                            traveler.closed_by = authenticated_user
                            traveler.date_closed = datetime.datetime.now()

                        traveler.is_transport_dpt_approved = is_transport_office

                    traveler.save()

                    raw = {
                        "traveler": traveler,
                        "status": traveler_status,
                        "status_for": travel_status,
                        "action_by": authenticated_user
                    }

                    if not is_update:
                        models.StatusChange.objects.create(**raw)

                    # Notify the requestor
                    if is_hod:
                        subject = f"Travel Request {traveler.tid} Status  [TRS-AKHK]"
                        message = f"Dear {traveler.created_by.first_name}, \n\nYour Travel Request has been\n Approved by HOD.\nPending SLT Approval.\n\nRegards\nTRS-AKHK"
                    elif is_slt:
                        subject = f"Travel Request {traveler.tid} Status  [TRS-AKHK]"
                        message = f"Dear {traveler.created_by.first_name}, \n\nYour Travel Request has been Approved by SLT.\nPending Finance Approval.\n\nRegards\nTRS-AKHK"
                    elif is_hof:
                        subject = f"Travel Request {traveler.tid} Status  [TRS-AKHK]"
                        message = f"Dear {traveler.created_by.first_name}, \n\nYour Travel Request has been\n Approved by Finance.\n\nRegards\nTRS-AKHK"
                    elif is_ceo:
                        subject = f"Travel Request {traveler.tid} Status  [TRS-AKHK]"
                        message = f"Dear {traveler.created_by.first_name}, \n\nYour Travel Request has been\n Approved by CEO.\n\nRegards\nTRS-AKHK"
                    elif is_cash_office:
                        subject = f"Travel Request {traveler.tid} Status  [TRS-AKHK]"
                        message = f"Dear {traveler.created_by.first_name}, \n\nYour Travel Request has been\n Approved by Cash Office.\n\nRegards\nTRS-AKHK"
                    elif is_transport_office:
                        subject = f"Travel Request {traveler.tid} Status  [TRS-AKHK]"
                        message = f"Dear {traveler.created_by.first_name}, \n\nYour Travel Request has been\n Approved by Transport Office.\n\nRegards\nTRS-AKHK"

                    # try:
                    #     send_mail(subject, message, 'notification@akhskenya.org', [traveler.created_by.email])
                    # except Exception as e:
                    #     pass
                    try:
                        mail = {
                            "email" : [traveler.created_by.email], 
                            "subject" : subject,
                            "message" : message,
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        send_mail(subject, message, 'notification@akhskenya.org', [traveler.created_by.email])

                    # # Notify HOF
                    # if is_slt and traveler_status == 'APPROVED':
                    #     emails = list(get_user_model().objects.filter(Q(groups__name='HOF')).values_list('email', flat=True))
                    #     subject = f"Request for Travel Budget Approval: {traveler.tid}.  [TRS-AKHK]"
                    #     message = f"Hello. \n\nTravel Request: {traveler.tid} \nis pending budget approval by HOF.\n\nRegards\nTRS-AKHK"

                    #     send_mail(subject, message, 'notification@akhskenya.org', emails)

                    # # Notify CEO
                    # if is_hof and traveler.mode_of_transport == 'FLIGHT':
                    #     emails = list(get_user_model().objects.filter(Q(groups__name='CEO')).values_list('email', flat=True))
                    #     subject = f"Travel Request: {traveler.tid} Pending Your Action.  [TRS-AKHK]"
                    #     message = f"Hello. \n\nTravel Request: {traveler.tid} has been\n approved by Finance\nand is now pending your approval.\n\nRegards\nTRS-AKHK"

                    #     send_mail(subject, message, 'notification@akhskenya.org', emails)

                    # Notify ADMINISTRATOR
                    if is_ceo and traveler.mode_of_transport == 'FLIGHT':
                        emails = list(get_user_model().objects.filter(Q(groups__name='ADMINISTRATOR')).values_list('email', flat=True))
                        subject = f"Travel Request: {traveler.tid} Pending Your Action.  [TRS-AKHK]"
                        message = f"Hello. \nTravel Request: {traveler.tid} has been approved by the CEO, and is now pending administration and costing\n\nRegards\nTRS-AKHK"

                        # try:
                        #     send_mail(subject, message, 'notification@akhskenya.org', emails)
                        # except Exception as e:
                        #     pass

                        try:
                            mail = {
                                "email" : emails, 
                                "subject" : subject,
                                "message" : message,
                            }
                            Sendmail.objects.create(**mail)
                        except Exception as e:
                            send_mail(subject, message, 'notification@akhskenya.org', emails)

                    # Notify CASH OFFICE, HOF, MMD
                    if is_ceo:
                        emails = list(get_user_model().objects.filter(Q(groups__name='CASH_OFFICE') | Q(groups__name='HOF') | Q(groups__name='MMD')).values_list('email', flat=True))
                        subject = f"Travel Request: {traveler.tid} Pending Your Action.  [TRS-AKHK]"
                        message = f"Hello. \nTravel Request: {traveler.tid} has been approved by the CEO,\n currently pending your action\n\nRegards\nTRS-AKHK"

                        # try:
                        #     send_mail(subject, message, 'notification@akhskenya.org', emails)
                        # except Exception as e:
                        #     pass

                        try:
                            mail = {
                                "email" : emails, 
                                "subject" : subject,
                                "message" : message,
                            }
                            Sendmail.objects.create(**mail)
                        except Exception as e:
                            send_mail(subject, message, 'notification@akhskenya.org', emails)

                    # # Notify TRANSPORT
                    if is_ceo and traveler.mode_of_transport == 'HOSPITAL VEHICLE':
                        emails = list(get_user_model().objects.filter(Q(groups__name='TRANSPORT')).values_list('email', flat=True))
                        subject = f"Travel Request: {traveler.tid} Pending Your Action.  [TRS-AKHK]"
                        message = f"Hello. \nTravel Request: {traveler.tid} has been approved by CEO,\n currently pending your action\n\nRegards\nTRS-AKHK"

                        # try:
                        #     send_mail(subject, message, 'notification@akhskenya.org', emails)
                        # except Exception as e:
                        #     pass

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
                    authenticated_user, traveler.created_by, "Travel Request approval", 
                    f"Approval Executed TID: {str(traveler.id)}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
    @action(methods=["POST", "GET", "PUT", "DELETE"],
            detail=False,
            url_path="forward-request",
            url_name="forward-request")
    def forward(self, request):

        authenticated_user = request.user

        if request.method == "POST":

            payload = request.data
            roles = user_util.fetchusergroups(request.user.id) 

            serializer = serializers.TravelForwardingSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                traveler = payload['traveler']
                send_to = payload['send_to']

                try:
                    traveler = models.Traveler.objects.get(Q(id=traveler))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Travel Request !"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():

                    if send_to == 'HOD':
                        traveler.requires_hod_approval = True
                        emails = list(get_user_model().objects.filter(Q(groups__name='HOD') & Q(department=traveler.department)).values_list('email', flat=True))
                        
                    elif send_to == "SLT":
                        traveler.requires_slt_approval = True
                        if traveler.department.slt:
                            emails = [traveler.department.slt.lead.email]
                        else:
                            return Response({"details": "Department has no SLT assigned !"}, status=status.HTTP_400_BAD_REQUEST)

                    elif send_to == "HOF" :
                        traveler.requires_hof_approval = True
                        emails = list(get_user_model().objects.filter(Q(groups__name='HOF')).values_list('email', flat=True))
                        
                    elif send_to == "CEO":
                        traveler.requires_ceo_approval = True
                        emails = list(get_user_model().objects.filter(Q(groups__name='CEO')).values_list('email', flat=True))

                    elif send_to == "TRANSPORT":
                        traveler.requires_transport_approval = True
                        emails = list(get_user_model().objects.filter(Q(groups__name='TRANSPORT')).values_list('email', flat=True))

                    elif send_to == "CASH_OFFICE":
                        traveler.requires_cash_office_approval = True
                        emails = list(get_user_model().objects.filter(Q(groups__name='CASH_OFFICE')).values_list('email', flat=True))

                    elif send_to == "ADMINISTRATOR":
                        traveler.requires_administrator_approval = True
                        emails = list(get_user_model().objects.filter(Q(groups__name='ADMINISTRATOR')).values_list('email', flat=True))

                    # update travel
                    traveler.save()


                    # create forwarding instance
                    previous_forwarder = models.TravelForwarding.objects.filter(
                        Q(traveler=traveler)).order_by('-date_created').first()
                    if previous_forwarder:
                        previous_forwarder = previous_forwarder.forward_to
                    else:
                        previous_forwarder = "CREATOR"

                    raw = {
                        "traveler": traveler,
                        "forward_to": send_to,
                        "forward_from": previous_forwarder,
                        "forward_by": authenticated_user,
                    }
                    models.TravelForwarding.objects.create(**raw)

                    # Notify recipient
                    subject = f"Travel Request Received [{traveler.tid}]"
                    message = f"Hello. \n\nTravel Request: of ID {traveler.tid}\nhas been forwarded to you by {authenticated_user.first_name} {authenticated_user.last_name},\npending your action.\n\nRegards\nTRS-AKHK"

                    # try:
                    #     send_mail(subject, message, 'notification@akhskenya.org', emails)
                    # except Exception as e:
                    #     pass

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
                    authenticated_user, traveler.created_by, f"Travel Request forwarded to {send_to}", f"Approval Executed TID: {str(traveler.id)}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

    @action(methods=["POST",],
            detail=False,
            url_path="update-salary-request",
            url_name="update-salary-request")
    def salary_request(self, request):

        authenticated_user = request.user

        if request.method == "POST":

            payload = request.data
            roles = user_util.fetchusergroups(request.user.id) 

            serializer = serializers.PatchAdvanceSalaryRequestsSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                update_status = payload['status'].upper()
                request_id = payload.get('request_id')

                try:
                    salaryRequest = models.AdvanceSalaryRequests.objects.get(Q(id=request_id))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Salary Request !"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():

                    if "CEO" in roles or "HOF" in roles:
                        salaryRequest.status = update_status
                        salaryRequest.approved_by = authenticated_user
                        salaryRequest.save()
                    else:
                        return Response({"details": "Not Permitted !"}, status=status.HTTP_400_BAD_REQUEST)

                    # Notify the requestor
                    subject = f"Travel Advance Request {update_status.capitalize()}  [TRS-AKHK]"
                    message = f"Hello, \nYour Advance Travel Request for travel:{salaryRequest.traveler.tid} has been {update_status.capitalize()} by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\n\nRegards\nTRS-AKHK"

                    # try:
                    #     send_mail(subject, message, 'notification@akhskenya.org', [salaryRequest.traveler.traveler.email])
                    # except Exception as e:
                    #     pass

                    try:
                        mail = {
                            "email" : [salaryRequest.traveler.traveler.email], 
                            "subject" : subject,
                            "message" : message,
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        send_mail(subject, message, 'notification@akhskenya.org', [salaryRequest.traveler.traveler.email])

                user_util.log_account_activity(
                    authenticated_user, salaryRequest.traveler.created_by, "Travel Request approval", f"Approval Executed instance ID: {str(salaryRequest.id)}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

    @action(methods=["POST",],
            detail=False,
            url_path="update-budget-code",
            url_name="update-budget-code")
    def budget_code(self, request):

        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        allowed = ["HOF","CEO", "FINANCE"]

        if not any(item in allowed for item in roles):
            return Response({"details": "Permission Denied !"}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "POST":

            payload = request.data
            roles = user_util.fetchusergroups(request.user.id) 

            serializer = serializers.PatchBudgetCodeSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                code = payload['budget_code']
                request_id = payload.get('request_id')

                try:
                    traveler = models.Traveler.objects.get(Q(id=request_id))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Travel Request !"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():

                    traveler.budget_code = code
                    traveler.save()

                user_util.log_account_activity(
                    authenticated_user, traveler.created_by, "Budget Code", f"Travel Budget Code Updated. ID : {str(traveler.id)}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            
    @action(methods=["POST", "GET", "PUT", "DELETE"],
            detail=False,
            url_path="process-travel-request",
            url_name="process-travel-request")
    def process_travel_request(self, request):

        authenticated_user = request.user

        if request.method == "POST":

            # payload = request.data
            roles = user_util.fetchusergroups(request.user.id) 

            payload = json.loads(request.data['payload'])
            air_ticket_file = request.FILES.get('ticket', None)

            if "ADMINISTRATOR" not in roles:
                return Response({"details": "Permission Denied !"}, status=status.HTTP_400_BAD_REQUEST)

            serializer = serializers.CostingSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                traveler = payload['traveler']
                bill_settlement_by = payload['bill_settlement_by']
                accommodation = payload.get('accommodation')
                cost = payload.get('cost')

                traveler_status = 'APPROVED'

                try:
                    traveler = models.Traveler.objects.get(Q(id=traveler))
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Trip !"}, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():

                    raw = {
                        "traveler": traveler,
                        "bill_settlement_by": bill_settlement_by,
                        "accommodation": accommodation,
                        "cost": cost,
                        "air_ticket": air_ticket_file,
                        "created_by": authenticated_user
                    }  

                    is_existing = models.Costing.objects.filter(Q(traveler=traveler)).exists()

                    if is_existing:
                        models.Costing.objects.filter(Q(traveler=traveler)).update(**raw)
                    else:
                        models.Costing.objects.create(
                            **raw
                        )

                    if traveler.is_ceo_approved and traveler.is_hof_approved and traveler.is_cash_office_approved:
                        traveler_status = 'CLOSED'
                        traveler.status = traveler_status
                        traveler.closed_by = authenticated_user
                        traveler.date_closed = datetime.datetime.now()

                    traveler.is_administrator_approved = True
                    traveler.save()

                    is_existing = models.Approval.objects.filter(Q(traveler=traveler) & 
                                                                 Q(approval_for='ADMINISTRATOR')).first()

                    raw = {
                        "traveler": traveler,
                        "approval_for": 'ADMINISTRATOR',
                        "approved_by": authenticated_user,
                    }  

                    models.Approval.objects.create(
                            **raw
                        )
                    
                    raw = {
                        "traveler": traveler,
                        "status": traveler_status,
                        "status_for": 'ADMINISTRATOR',
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)

                    # Notify the requestor
                    subject = f"Travel Request {traveler.tid} Closed  [TRS-AKHK]"
                    message = f"Dear {traveler.created_by.first_name}, \nYour Travel Request: {traveler.tid}, \nhas been fully processed by administrator.\nThank you for your patience.\n\nRegards\nTRS-AKHK"

                    # try:
                    #     send_mail(subject, message, 'notification@akhskenya.org', [traveler.created_by.email])
                    # except Exception as e:
                    #     pass

                    try:
                        mail = {
                            "email" : [traveler.created_by.email], 
                            "subject" : subject,
                            "message" : message,
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        send_mail(subject, message, 'notification@akhskenya.org', [traveler.created_by.email])

                user_util.log_account_activity(
                    authenticated_user, traveler.created_by, "Travel Request closed", f"TID: {str(traveler.id)}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

                
    
   
class TRSReportsViewSet(viewsets.ViewSet):
    # search_fields = ['id', ]

    def get_queryset(self):
        return []

    @action(methods=["GET",],
            detail=False,
            url_path="requests",
            url_name="requests")
    def requests(self, request):
                    
        department = request.query_params.get('department')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        quote_status = request.query_params.get('status')
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
            
        if quote_status:
            q_filters &= Q(status=quote_status)


        if q_filters:

            resp = models.Traveler.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
            
        else:
            roles = user_util.fetchusergroups(request.user.id)  

            if "HOD" in roles:
                resp = models.Traveler.objects.filter(Q(is_deleted=False) & Q(created_by=request.user)).order_by('-date_created')[:50]

            else:
                resp = models.Traveler.objects.filter(Q(is_deleted=False)).order_by('-date_created')[:50]

        resp = serializers.FetchTravelerSerializer(resp, many=True, context={"user_id":request.user.id}).data

        return Response(resp, status=status.HTTP_200_OK)
        
    @action(methods=["GET",],
            detail=False,
            url_path="transport",
            url_name="transport")
    def transport(self, request):
                    
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

        q_filters = Q(approval_for='TRANSPORT')

        if department:
            q_filters &= Q(department=department)

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)
            
        # if quote_status:
        #     q_filters &= Q(status=quote_status)


        if q_filters:

            resp = models.Approval.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
            
        else:
            roles = user_util.fetchusergroups(request.user.id)  

            resp = models.Approval.objects.filter(Q(is_deleted=False)).order_by('-date_created')[:50]

        resp = serializers.FullFetchApprovalSerializer(resp, many=True, context={"user_id":request.user.id}).data

        return Response(resp, status=status.HTTP_200_OK)
        

    @action(methods=["GET",],
            detail=False,
            url_path="flights",
            url_name="flights")
    def flight(self, request):
                    
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

        q_filters = Q(approval_for='ADMINISTRATOR')

        if department:
            q_filters &= Q(department=department)

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)
            
        if type:
            q_filters &= Q(traveler__type_of_travel=type)


        if q_filters:

            resp = models.Approval.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
            
        else:
            roles = user_util.fetchusergroups(request.user.id)  

            resp = models.Approval.objects.filter(Q(is_deleted=False)).order_by('-date_created')[:50]

        resp = serializers.FullFetchApprovalSerializer(resp, many=True, context={"user_id":request.user.id}).data

        return Response(resp, status=status.HTTP_200_OK)
    

    @action(methods=["GET",],
            detail=False,
            url_path="journeys",
            url_name="journeys")
    def journeys(self, request):
                    
        employee_no = request.query_params.get('employee_no')
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

        q_filters = Q()

        if employee_no:
            q_filters &= (Q(employee_no=employee_no) | Q(employees__contains=[{"employee_no": employee_no}]))

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)
            
        if type:
            q_filters &= Q(type_of_travel=type)


        if q_filters:

            resp = models.Traveler.objects.filter(Q(is_deleted=False) & q_filters).order_by('date_created')
            
        else:
            roles = user_util.fetchusergroups(request.user.id)  

            resp = []

        resp = serializers.FetchTravelerSerializer(resp, many=True, context={"user_id":request.user.id}).data

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