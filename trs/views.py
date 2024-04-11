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
from trs import models
from trs import serializers
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import User, Department
from trs.utils import shared_fxns
from django.db.models import Sum
from django.core.mail import send_mail

from mms.utils.custom_pagination import CustomPagination
from rest_framework.viewsets import ViewSetMixin
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
            url_path="traveler-details",
            url_name="traveler-details")
    def traveler(self, request):
        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        

        if request.method == "POST":

            payload = request.data

            serializer = serializers.TravelerSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                is_individual = True
                description = payload['description']
                purpose = payload['purpose']
                route = payload['route']
                departure_date = payload['departure_date']
                return_date = payload['return_date']
                mode_of_transport = payload['mode_of_transport']
                department = payload['department']
                visa_required_date = payload.get('visa_required_date')
                accommodation = bool(payload.get('accommodation'))
                salary_advance_required = bool(payload.get('salary_advance_required'))
                salary_amount_required = payload.get('salary_amount_required')
                requesting_for = payload.get('requesting_for')
                travel_cost = payload.get('travel_cost')
                travel_cost_items = payload.get('travel_cost_items')
                send_to = payload.get('send_to')
                tid = shared_fxns.generate_unique_identifier()

                if not send_to:
                    if 'USER' in roles:
                        send_to = 'HOD'
                    else:
                        return Response({"details": "Please select Send To!"}, status=status.HTTP_400_BAD_REQUEST)

                if requesting_for == 'OTHERS':
                    employees = list(payload.get('employees'))

                    if not employees:
                        return Response({"details": "Target Employees Required !"}, status=status.HTTP_400_BAD_REQUEST)
                    
                    is_individual = False
                else:
                    try:
                        position = payload['position']
                        employee_no = payload['employee_no']
                    except Exception as e:
                        return Response({"details": "Employee No / Position Title Required !"}, status=status.HTTP_400_BAD_REQUEST)
                
                if travel_cost and not travel_cost_items:
                    return Response({"details": "Travel Cost Breakdown Required !"}, status=status.HTTP_400_BAD_REQUEST)

                if not salary_advance_required:
                    salary_amount_required = 0
                else:
                    if int(salary_amount_required) < 1:
                        return Response({"details": "Advance Amount Required !"}, status=status.HTTP_400_BAD_REQUEST)


                # update employee no
                try:
                    empno = authenticated_user.employee_no
                    if not empno:
                        authenticated_user.employee_no = employee_no
                        authenticated_user.save()
                    else:
                        employee_no = authenticated_user.employee_no
                except Exception as e:
                    pass

                try:
                    department = Department.objects.get(id=department)
                except Exception as e:
                    return Response({"details": "Unknown Department !"}, status=status.HTTP_400_BAD_REQUEST)

                
                with transaction.atomic():
                    traveler_raw = {
                        "purpose": purpose,
                        "created_by": authenticated_user,
                        "description": description,
                        "department": department,
                        "mode_of_transport": mode_of_transport,
                        "requesting_for": requesting_for,
                        "salary_advance_required": salary_advance_required,
                        "tid": tid,
                        "travel_cost": travel_cost,
                        "travel_cost_items": travel_cost_items
                    }  

                    if is_individual:
                        traveler_raw.update({
                                                "traveler": authenticated_user,
                                                "employee_no": employee_no,
                                                "position": position,
                                            })

                    if not is_individual:
                        traveler_raw.update({"employees": employees})

                    if send_to == 'CEO':
                        traveler_raw.update({"requires_ceo_approval": True})
                    elif send_to == 'HOF':
                        traveler_raw.update({"requires_hof_approval": True})
                    elif send_to == 'SLT':
                        traveler_raw.update({"requires_slt_approval": True})
                    elif send_to == 'HOD':
                        traveler_raw.update({"requires_hod_approval": True})

                    if "HOD" in roles:
                        traveler_raw.update({
                                "is_hod_approved": True,
                                "status": "APPROVED"
                            })

                    traveler = models.Traveler.objects.create(
                        **traveler_raw
                    )

                    # create trip instance
                    trip_raw = {
                        "traveler": traveler,
                        "route": route,
                        "departure_date": departure_date,
                        "return_date": return_date,
                        "accommodation": accommodation,
                    }  

                    if visa_required_date:
                        traveler_raw.update({"visa_required_date": visa_required_date})

                    models.Trip.objects.create(
                        **trip_raw
                    )

                    # create approval instance
                    if "HOD" in roles:
                        raw = {
                            "traveler": traveler,
                            "approval_for": "HOD",
                            "approved_by": authenticated_user,
                        }  

                        models.Approval.objects.create(
                            **raw
                        )

                    if salary_advance_required:
                        # save salary advances
                        salary_raw = {
                            "traveler": traveler,
                            "amount": salary_amount_required,
                        }  

                        models.AdvanceSalaryRequests.objects.create(
                            **salary_raw
                        )

                    if send_to == 'HOD':
                        managers_emails = get_user_model().objects.filter(Q(groups__name='HOD') & Q(department=department) ).values_list('email', flat=True)

                    elif send_to == 'SLT':
                        if department.slt:
                            managers_emails = [department.slt.lead.email]
                        else:
                            return Response({"details": "Selected Department has no SLT assigned !"}, status=status.HTTP_400_BAD_REQUEST)
                        
                    elif send_to == 'HOF':
                        managers_emails = get_user_model().objects.filter(Q(groups__name='HOF')).values_list('email', flat=True)

                    elif send_to == 'CEO':
                        managers_emails = get_user_model().objects.filter(Q(groups__name='CEO')).values_list('email', flat=True)
                        

                    # Notify selected send to
                    subject = f"Travel Request {tid} Received [TRS-AKHK]"
                    message = f"Hello, \nA new travel request: {tid} has been submitted by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending your action.\n\nRegards\nTRS-AKHK"

                    send_mail(subject, message, 'notification@akhskenya.org', managers_emails)

                    # Notify the hof
                    if salary_advance_required:
                        emails = get_user_model().objects.filter(Q(groups__name='HOF')).values_list('email', flat=True)

                        subject = f"Travel Advance Request {tid} Received [TRS-AKHK]"
                        message = f"Hello, \nSalary Travel Advance request has been submitted for a new travel request: {tid} by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending your action.\n\nRegards\nTRS-AKHK"

                        send_mail(subject, message, 'notification@akhskenya.org', emails)

   
                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Travel Request created", f"Travel Request Id: {traveler.id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "PUT":
            payload = request.data
            serializer = serializers.PutTravelerSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                traveler_id = payload['id']
                description = payload['description']
                purpose = payload['purpose']
                position = payload['position']
                employee_no = payload['employee_no']
                route = payload['route']
                departure_date = payload['departure_date']
                return_date = payload['return_date']
                visa_required_date = payload.get('visa_required_date')
                accommodation = bool(payload.get('accommodation'))
                salary_advance_required = bool(payload.get('salary_advance_required'))
                salary_amount_required = payload.get('salary_amount_required')

                if not salary_advance_required:
                    salary_amount_required = 0
                else:
                    if int(salary_amount_required) < 1:
                        return Response({"details": "Advance Amount Required !"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    traveler = models.Traveler.objects.get(id=traveler_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Trip !"}, status=status.HTTP_400_BAD_REQUEST)

                
                with transaction.atomic():

                    traveler_raw = {
                        "employee_no": employee_no,
                        "position": position,
                        "purpose": purpose,
                        "traveler": authenticated_user,
                        "description": description,
                        "salary_advance_required": salary_advance_required,
                    }  
                    models.Traveler.objects.filter(Q(id=traveler_id)).update(**traveler_raw)

                    trip_raw = {
                        "route": route,
                        "departure_date": departure_date,
                        "return_date": return_date,
                        "visa_required_date": visa_required_date,
                        "accommodation": accommodation,
                    }  
                    models.Trip.objects.filter(Q(traveler=traveler_id)).update(**trip_raw)

                    if salary_advance_required:
                        # save salary advances
                        salary_raw = {
                            "traveler": traveler,
                            "amount": salary_amount_required,
                        }  
                        # models.AdvanceSalaryRequests.objects.filter(Q(traveler=traveler_id)).update(**salary_raw)
                        advance = models.AdvanceSalaryRequests.objects.filter(Q(traveler=traveler_id))
                        if advance:
                            advance = advance[0]
                            current_status = advance.status
                            if current_status != 'REJECTED':
                                advance.amount = salary_amount_required
                                advance.save()
                        else:
                            models.AdvanceSalaryRequests.objects.create(
                                **salary_raw
                            )


                    if traveler.status == "INCOMPLETE":
                        targets = ['HOD','SLT']
                        managers_emails = get_user_model().objects.filter(Q(groups__name__in=targets) & Q(department=authenticated_user.department)).values_list('email', flat=True)

                        # assignee = models.QuoteAssignee.objects.get(Q(quote=quote))
                        # managers_emails.append(assignee.assigned.email)

                        raw = {"status" : "RESUBMITTED"}
                        models.Traveler.objects.filter(Q(id=traveler_id)).update(**raw)

                        # Notify the manager
                        subject = f"Travel Request: {traveler.tid} Has Been Resubmitted [TRS-AKHK]"
                        message = f"Hello, \nTravel Request: {traveler.tid} has been resubmitted by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending your action.\n\nRegards\nTRS-AKHK"

                        send_mail(subject, message, 'notification@akhskenya.org', managers_emails)

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Travel Request updated", f"TID: {traveler_id}")
                
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
                roles = user_util.fetchusergroups(request.user.id)  

                try:
                    traveler = models.Traveler.objects.get(id=traveler_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Travel !"}, status=status.HTTP_400_BAD_REQUEST)
            
                
                with transaction.atomic():

                    if traveler_status == 'REJECTED':
                        traveler.rejected_by = authenticated_user

                    traveler.status = traveler_status
                    traveler.save()

                    raw = {
                        "traveler": traveler,
                        "status": traveler_status,
                        "action_by": authenticated_user,
                    }

                    models.StatusChange.objects.create(**raw)

                    # Notify requestor
                    emails = [traveler.traveler.email]

                    subject = f"Travel Request: {traveler.tid} Progress Update [TRS-AKHK]"
                    message = f"Hello, \nThe Request:{traveler.tid} has been marked as {traveler_status} by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\n\nRegards\nTRS-AKHK"

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
                            targets = models.AdvanceSalaryRequests.objects.filter(Q(is_deleted=False)).order_by('-date_created')
                            resp = [x.traveler for x in targets]
                        else:
                            resp = models.Traveler.objects.filter(Q(traveler__department=request.user.department) | Q(department=request.user.department) | Q(created_by=request.user) | Q(requires_hod_approval=True) , is_deleted=False).order_by('-date_created')

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
                        if query == 'salary-advance':
                            targets = models.AdvanceSalaryRequests.objects.filter(Q(is_deleted=False)).order_by('-date_created')
                            resp = [
                                    x.traveler 
                                    for x in targets 
                                    if x.department.slt.lead == authenticated_user
                                ]
                        else:
                            if "HOF" in roles:
                                resp = models.Traveler.objects.filter(Q(is_deleted=False) & Q(department__slt__lead=authenticated_user) | Q(requires_slt_approval=True) | Q(requires_hof_approval=True)).order_by('-date_created')
                            else:
                                resp = models.Traveler.objects.filter(Q(is_deleted=False) & Q(department__slt__lead=authenticated_user) & Q(requires_slt_approval=True)).order_by('-date_created')

                    elif "HOF" in roles:
                        if not query:
                            resp = models.Traveler.objects.filter(Q(requires_hof_approval=True),is_deleted=False).order_by('-date_created')

                        if query == 'salary-advance':
                            # targets = models.AdvanceSalaryRequests.objects.filter(Q(status='REQUESTED')).order_by('-date_created')
                            targets = models.AdvanceSalaryRequests.objects.filter(Q(is_deleted=False)).order_by('-date_created')
                            resp = [x.traveler for x in targets]
                    
                    elif "CEO" in roles:
                        if not query:
                            resp = models.Traveler.objects.filter(Q(requires_ceo_approval=True), is_deleted=False).order_by('-date_created')

                        if query == 'salary-advance':
                            targets = models.AdvanceSalaryRequests.objects.filter(Q(is_deleted=False)).order_by('-date_created')
                            resp = [x.traveler for x in targets]

                    elif "USER" in roles:
                        if not query:
                            resp = models.Traveler.objects.filter(Q(is_deleted=False) & Q(traveler=request.user)).order_by('-date_created')

                        if query == 'salary-advance':
                            targets = models.AdvanceSalaryRequests.objects.filter(Q(is_deleted=False) & Q(traveler__traveler=request.user)).order_by('-date_created')
                            resp = [x.traveler for x in targets]

                    elif "ADMINISTRATOR" in roles :
                        allowed_statuses = ['APPROVED', 'CLOSED']
                        resp = models.Traveler.objects.filter(Q(is_deleted=False) & Q(requires_administrator_approval=True) & Q(status__in=allowed_statuses)).order_by('-date_created')
                    
                    elif "CASH_OFFICE" in roles :
                        allowed_statuses = ['APPROVED', 'CLOSED']
                        resp = models.Traveler.objects.filter(Q(is_deleted=False) & Q(requires_cash_office_approval=True) & Q(status__in=allowed_statuses)).order_by('-date_created')

                    elif "TRANSPORT" in roles :
                        allowed_statuses = ['APPROVED', 'CLOSED']
                        resp = models.Traveler.objects.filter(Q(is_deleted=False) & Q(requires_transport_approval=True) & Q(status__in=allowed_statuses) ).order_by('-date_created')


                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resp, request)
                    serializer = serializers.FetchTravelerSerializer(result_page, many=True, context={"user_id":request.user.id})
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
                        
                    elif travel_status == "CEO":
                        is_ceo = True
                        approval_for = "CEO"

                    elif travel_status == "TRANSPORT":
                        is_transport_office = True
                        approval_for = "TRANSPORT"

                    elif travel_status == "CASH_OFFICE":
                        is_cash_office = True
                        approval_for = "CASH_OFFICE"

                        approval_msg = payload.get('text')
                        if not approval_msg:
                            return Response({"details": "Amount / Transaction Code / Message Required !"}, status=status.HTTP_400_BAD_REQUEST)


                    is_existing = models.Approval.objects.filter(Q(traveler=traveler) & Q(approval_for=approval_for)).exists()

                    raw = {
                        "traveler": traveler,
                        "approval_for": approval_for,
                        "approved_by": authenticated_user,
                    }  

                    if is_cash_office:
                        raw.update({"approval_msg": approval_msg})

                    if is_existing:
                        models.Approval.objects.filter(Q(traveler=traveler) & Q(approval_for=approval_for)).update(**raw)
                    else:
                        models.Approval.objects.create(
                            **raw
                        )

                    
                    traveler.budget_code = budget_code

                    if is_hod:
                        traveler.status = traveler_status
                        traveler.is_hod_approved = is_hod

                    if is_ceo:
                        traveler.is_ceo_approved = is_ceo

                    if is_slt:
                        traveler.is_slt_approved = is_slt

                    if is_hof:
                        traveler.is_hof_approved = is_hof

                    if is_cash_office:
                        traveler_status = "CLOSED"
                        traveler.status = "CLOSED"
                        traveler.closed_by = authenticated_user
                        traveler.date_closed = datetime.datetime.now()
                        traveler.is_cash_office_approved = is_cash_office

                    if is_transport_office:
                        traveler_status = "CLOSED"
                        traveler.status = "CLOSED"
                        traveler.closed_by = authenticated_user
                        traveler.date_closed = datetime.datetime.now()
                        traveler.is_transport_dpt_approved = is_transport_office

                    traveler.save()

                    raw = {
                        "traveler": traveler,
                        "status": traveler_status,
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)

                    # Notify the requestor
                    if is_hod:
                        subject = f"Travel Request {traveler.tid} Status  [TRS-AKHK]"
                        message = f"Dear {traveler.created_by.first_name}, \nYour Travel Request has been Approved by HOD.\nPending SLT Approval.\n\nRegards\nTRS-AKHK"
                    elif is_slt:
                        subject = f"Travel Request {traveler.tid} Status  [TRS-AKHK]"
                        message = f"Dear {traveler.created_by.first_name}, \nYour Travel Request has been Approved by SLT.\nPending Finance Approval.\n\nRegards\nTRS-AKHK"
                    elif is_hof:
                        subject = f"Travel Request {traveler.tid} Status  [TRS-AKHK]"
                        message = f"Dear {traveler.created_by.first_name}, \nYour Travel Request has been Approved by Finance.\n\nRegards\nTRS-AKHK"
                    elif is_ceo:
                        subject = f"Travel Request {traveler.tid} Status  [TRS-AKHK]"
                        message = f"Dear {traveler.created_by.first_name}, \nYour Travel Request has been Approved by CEO.\n\nRegards\nTRS-AKHK"
                    elif is_cash_office:
                        subject = f"Travel Request {traveler.tid} Status  [TRS-AKHK]"
                        message = f"Dear {traveler.created_by.first_name}, \nYour Travel Request has been Approved by Cash Office.\n\nRegards\nTRS-AKHK"
                    elif is_transport_office:
                        subject = f"Travel Request {traveler.tid} Status  [TRS-AKHK]"
                        message = f"Dear {traveler.created_by.first_name}, \nYour Travel Request has been Approved by Transport Office.\n\nRegards\nTRS-AKHK"

                    send_mail(subject, message, 'notification@akhskenya.org', [traveler.created_by.email])

                    # Notify HOF
                    if is_slt and traveler_status == 'APPROVED':
                        emails = list(get_user_model().objects.filter(Q(groups__name='HOF')).values_list('email', flat=True))
                        subject = f"Request for Travel Budget Approval: {traveler.tid}.  [TRS-AKHK]"
                        message = f"Hello. \nTravel Request: {traveler.tid} is pending budget approval by CEO/HOF.\n\nRegards\nTRS-AKHK"

                        send_mail(subject, message, 'notification@akhskenya.org', emails)

                    # Notify CEO
                    if is_hof and traveler.mode_of_transport == 'FLIGHT':
                        emails = list(get_user_model().objects.filter(Q(groups__name='CEO')).values_list('email', flat=True))
                        subject = f"Travel Request: {traveler.tid} Pending Your Action.  [TRS-AKHK]"
                        message = f"Hello. \nTravel Request: {traveler.tid} has been approved by Finance\nand is now pending your approval.\n\nRegards\nTRS-AKHK"

                        send_mail(subject, message, 'notification@akhskenya.org', emails)

                    # Notify ADMINISTRATOR
                    if is_ceo:
                        emails = list(get_user_model().objects.filter(Q(groups__name='ADMINISTRATOR')).values_list('email', flat=True))
                        subject = f"Travel Request: {traveler.tid} Pending Your Action.  [TRS-AKHK]"
                        message = f"Hello. \nTravel Request: {traveler.tid} has been approved by both HOD/SLT and HOF/CEO, and is now pending administration and costing\n\nRegards\nTRS-AKHK"

                        send_mail(subject, message, 'notification@akhskenya.org', emails)

                    # Notify CASH OFFICE
                    if is_hof and traveler.mode_of_transport == 'PSV':
                        emails = list(get_user_model().objects.filter(Q(groups__name='CASH_OFFICE')).values_list('email', flat=True))
                        subject = f"Travel Request: {traveler.tid} Pending Your Action.  [TRS-AKHK]"
                        message = f"Hello. \nTravel Request: {traveler.tid} has been approved by finance office and is now pending your action\n\nRegards\nTRS-AKHK"

                        send_mail(subject, message, 'notification@akhskenya.org', emails)

                    # Notify TRANSPORT
                    if is_hof and traveler.mode_of_transport == 'HOSPITAL VEHICLE':
                        emails = list(get_user_model().objects.filter(Q(groups__name='TRANSPORT')).values_list('email', flat=True))
                        subject = f"Travel Request: {traveler.tid} Pending Your Action.  [TRS-AKHK]"
                        message = f"Hello. \nTravel Request: {traveler.tid} has been approved by finance office and is now pending your action\n\nRegards\nTRS-AKHK"

                        send_mail(subject, message, 'notification@akhskenya.org', emails)

                user_util.log_account_activity(
                    authenticated_user, traveler.created_by, "Travel Request approval", f"Approval Executed TID: {str(traveler.id)}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

    @action(methods=["POST", "GET", "PUT", "DELETE"],
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
                    subject = f"Salary Advance Request {update_status.capitalize()}  [TRS-AKHK]"
                    message = f"Hello, \nYour Advance Salary Request for travel:{salaryRequest.traveler.tid} has been {update_status.capitalize()} by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\n\nRegards\nTRS-AKHK"

                    send_mail(subject, message, 'notification@akhskenya.org', [salaryRequest.traveler.traveler.email])

                user_util.log_account_activity(
                    authenticated_user, salaryRequest.traveler.traveler, "Salary Request approval", f"Approval Executed instance ID: {str(salaryRequest.id)}")
                
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

            payload = request.data
            roles = user_util.fetchusergroups(request.user.id) 

            if "ADMINISTRATOR" not in roles:
                return Response({"details": "Permission Denied !"}, status=status.HTTP_400_BAD_REQUEST)

            serializer = serializers.CostingSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                travel_order_no = payload['travel_order_no']
                traveler = payload['traveler']
                bill_settlement_by = payload['bill_settlement_by']
                accommodation = payload.get('accommodation')
                cost = payload.get('cost')

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
                        "created_by": authenticated_user
                    }  

                    is_existing = models.Costing.objects.filter(Q(traveler=traveler)).exists()

                    if is_existing:
                        models.Costing.objects.filter(Q(traveler=traveler)).update(**raw)
                    else:
                        models.Costing.objects.create(
                            **raw
                        )

                    traveler.status = "CLOSED"
                    traveler.closed_by = authenticated_user
                    traveler.travel_order_no = travel_order_no
                    traveler.is_administrator_approved = True
                    traveler.date_closed = datetime.datetime.now()
                    traveler.save()

                    # Notify the requestor
                    subject = f"Travel Request {traveler.tid} Closed  [TRS-AKHK]"
                    message = f"Dear {traveler.created_by.first_name}, \nYour Transport Request: {traveler.tid},  has been fully processed and closed.\nThank you for your patience.\n\nRegards\nTRS-AKHK"

                    send_mail(subject, message, 'notification@akhskenya.org', [traveler.created_by.email])

                user_util.log_account_activity(
                    authenticated_user, traveler.created_by, "Travel Request closed", f"TID: {str(traveler.id)}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

                
    
    # @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
    #         detail=False,
    #         url_path="close-quote",
    #         url_name="close-quote")
    # def close_quote(self, request):
    #     authenticated_user = request.user
    #     if request.method == "POST":
    #         formfiles = request.FILES
    #         if not formfiles:
    #             return Response({"details": "Please upload attachments"}, status=status.HTTP_400_BAD_REQUEST)

    #         payload = json.loads(request.data['payload'])
    #         serializer = serializers.CloseQuoteSerializer(
    #                 data=payload, many=False)
            
    #         if serializer.is_valid():
    #             quote = payload['quote']

    #             try:
    #                 quote = models.Quote.objects.get(Q(id=quote))
    #             except (ValidationError, ObjectDoesNotExist):
    #                 return Response({"details": "Unknown Quote !"}, status=status.HTTP_400_BAD_REQUEST)
                
    #             if formfiles:
    #                 exts = ['jpeg','jpg','png','tiff','pdf','doc','docx']

    #                 for f in request.FILES.getlist('quote'):
    #                     original_file_name = f.name
    #                     ext = original_file_name.split('.')[1].strip().lower()
    #                     if ext not in exts:
    #                         return Response({"details": "Only Images, Word and PDF files allowed for upload !"}, status=status.HTTP_400_BAD_REQUEST)

    #             with transaction.atomic():
    
    #                 try:
    #                     quoteFile = request.FILES.getlist('quote')[0]
    #                     file_type1 = shared_fxns.identify_file_type(quoteFile.name.split('.')[1].strip().lower())
    #                     title1 = "CLOSE_QUOTE_FILE"
    #                 except Exception as e:
    #                     return Response({"details": "Upload Quote File !"}, status=status.HTTP_400_BAD_REQUEST)
                    
    #                 try:                         
    #                     quote_file = models.Document.objects.create(
    #                                 document=quoteFile, 
    #                                 original_file_name=quoteFile.name, 
    #                                 uploader=authenticated_user, 
    #                                 file_type=file_type1,
    #                                 title=title1,
    #                                 )
                        
    #                     attachments = {
    #                         "quote_file": str(quote_file.id),
    #                     }

    #                     # update quote instance
    #                     quote.close_attachments = attachments
    #                     quote.status = "CLOSED"
    #                     quote.date_closed = datetime.datetime.now()
    #                     quote.save()

    #                     emails = list(get_user_model().objects.filter(groups__name='MMD').values_list('email', flat=True))
    #                     emails.append(quote.uploader.email)

    #                     # Notify the manager and users
    #                     subject = f"Quote: {quote.qid} Request Uploaded [TRS-AKHK]"
    #                     message = f"Hello. \nQuote: {quote.qid} of subject {quote.subject} from department:  {quote.department.name} has been UPLOADED by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}.\n\nRegards\n TRS-AKHK"
    #                     # mailgun_general.send_mail(quote.uploader.first_name, quote.uploader.email,subject,message)
    #                     send_mail(subject, message, 'notification@akhskenya.org', emails)

    #                     user_util.log_account_activity(
    #                         authenticated_user, authenticated_user, "Quote Closed", f"Quote Closure Executed QID: {quote.id}")

    #                 except Exception as e:
    #                     logger.error(e)
    #                     print(e)
    #                     return Response({"details": "Unable to save File(s)"}, status=status.HTTP_400_BAD_REQUEST)


                    
                
    #             return Response('success', status=status.HTTP_200_OK)
            
    #         else:
    #             return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

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

        if not q_filters:
            roles = user_util.fetchusergroups(request.user.id)  

            if assigned:
                quote_ids = models.QuoteAssignee.objects.filter(Q(assigned=request.user) & Q(is_deleted=False)).values_list('quote__id', flat=True)
                resp = models.Quote.objects.filter(Q(is_deleted=False) & Q(id__in=quote_ids)).order_by('-date_created')[:50]


            if "MMD" in roles or "USER_MANAGER" in roles:
                resp = models.Quote.objects.filter(Q(is_deleted=False)).order_by('-date_created')[:50]

            elif "USER" in roles:
                resp = models.Quote.objects.filter(Q(is_deleted=False) & Q(uploader=request.user)).order_by('-date_created')[:50]

            


        # if department and date and status:
        #     q_filters &= Q(create_date_range())
        # elif department and date:
        #     q_filters &= Q(create_date_range())
        # elif status and menu_type:
        #     q_filters &= Q(patient__menu=menu_type)
        # elif meal_type and menu_type:
        #     q_filters &= Q(patient__menu=menu_type)
        #     q_filters &= Q(meal_type=meal_type)
        

        resp = models.Quote.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
        resp = serializers.FetchQuoteSerializer(resp, many=True, context={"user_id":request.user.id}).data
        return Response(resp, status=status.HTTP_200_OK)
        
        # except (ValidationError, ObjectDoesNotExist):
        #     return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
        # except Exception as e:
        #     print(e)
        #     return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
        
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