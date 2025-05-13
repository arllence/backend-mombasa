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
from trs import models
from trs import serializers
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import User, Hods, SRRSDepartment, Sendmail
from trs.utils import shared_fxns
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
                estimated_distance = payload['estimated_distance']
                departure_date = payload['departure_date']
                departure_time = payload['departure_time']
                return_date = payload['return_date']
                mode_of_transport = payload['mode_of_transport']
                type_of_travel = payload['type_of_travel']
                department = payload['department']
                visa_required_date = payload.get('visa_required_date')
                accommodation = bool(payload.get('accommodation'))
                salary_advance_required = bool(payload.get('salary_advance_required'))
                salary_amount_required = payload.get('salary_amount_required') or 0
                requesting_for = payload.get('requesting_for')
                travel_cost = payload.get('travel_cost')
                travel_cost_items = payload.get('travel_cost_items')
                send_to = payload.get('send_to', None)
                tid = shared_fxns.generate_unique_identifier()

                if salary_advance_required and not salary_amount_required:
                    return Response({"details": "Enter Travel Advance Amount"}, status=status.HTTP_400_BAD_REQUEST)

                # Get today's date
                today_date = datetime.date.today()

                # find difference in dates / validate dates
                hours = shared_fxns.find_date_difference(str(today_date.strftime('%Y-%m-%d')),departure_date,'hours')
                if hours < 48:
                    return Response({"details": "Request to be made at least 48hrs before travel date"}, status=status.HTTP_400_BAD_REQUEST)

                exempted = ['HOD','HOF','CEO']

                if not send_to:
                    if any(item in exempted for item in roles):
                        send_to = 'CEO'
                    else:
                        send_to = 'HOD'

                if requesting_for == 'OTHERS':
                    employees = list(payload.get('employees'))

                    if not employees:
                        return Response({"details": "Target Employees Required !"}, status=status.HTTP_400_BAD_REQUEST)
                    
                    no_of_travelers = len(employees)
                    
                    is_individual = False
                else:
                    try:
                        position = payload['position']
                        employee_no = payload['employee_no']
                    except Exception as e:
                        return Response({"details": "Employee No / Position Title Required !"}, status=status.HTTP_400_BAD_REQUEST)
                    
                    no_of_travelers = 1
                
                if travel_cost and not travel_cost_items:
                    return Response({"details": "Travel Cost Breakdown Required !"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    if not travel_cost:
                        travel_cost = 0
                        for item in travel_cost_items:
                            travel_cost += int(item['cost'])
                except:
                    pass

                if not salary_advance_required:
                    salary_amount_required = 0
                else:
                    if requesting_for == 'OTHERS':
                        advance_requests = list(payload.get('advance_requests'))

                        if not advance_requests:
                            return Response({"details": "Target Employees Required !"}, status=status.HTTP_400_BAD_REQUEST)
                        
                        salary_amount_required = 0
                        for item in advance_requests:
                            salary_amount_required += int(item['amount'])

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
                    department = SRRSDepartment.objects.get(id=department)
                except Exception as e:
                    return Response({"details": "Unknown Department !"}, status=status.HTTP_400_BAD_REQUEST)

                
                with transaction.atomic():
                    traveler_raw = {
                        "purpose": purpose,
                        "created_by": authenticated_user,
                        "description": description,
                        "department": department,
                        "mode_of_transport": mode_of_transport,
                        "type_of_travel": type_of_travel,
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

                    if salary_advance_required and not is_individual:
                        traveler_raw.update({"advance_requests": advance_requests})

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
                        "departure_time": departure_time,
                        "return_date": return_date,
                        "accommodation": accommodation,
                        "estimated_distance": estimated_distance
                    }  

                    if visa_required_date:
                        trip_raw.update({"visa_required_date": visa_required_date})

                    tripInstance = models.Trip.objects.create(
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

                        # track status change
                        raw = {
                            "traveler": traveler,
                            "status": "APPROVED",
                            "status_for": "HOD",
                            "action_by": authenticated_user
                        }

                        models.StatusChange.objects.create(**raw)

                    # create forwarding instance
                    raw = {
                        "traveler": traveler,
                        "forward_to": send_to,
                        "forward_from": "CREATOR",
                        "forward_by": authenticated_user,
                    }
                    models.TravelForwarding.objects.create(**raw)

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
                        managers_emails = list(get_user_model().objects.filter(Q(groups__name='HOD') & Q(srrs_department=department) ).values_list('email', flat=True))

                    if send_to == 'SLT':
                        if department.slt:
                            managers_emails = [department.slt.lead.email]
                        else:
                            return Response({"details": "Selected Department has no SLT assigned !"}, status=status.HTTP_400_BAD_REQUEST)
                        
                    if send_to == 'HOF':
                        managers_emails = list(get_user_model().objects.filter(Q(groups__name='HOF')).values_list('email', flat=True))

                    if send_to == 'CEO':
                        managers_emails = list(get_user_model().objects.filter(Q(groups__name='CEO')).values_list('email', flat=True))
                        

                    # Notify selected send to
                    subject = f"Travel Request {tid} Received [TRF-AKHK]"
                    # message = f"Hello, \nA new travel request: {tid} has been submitted by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending your action.\n\nRegards\nTRS-AKHK"


                    message = f"""
                        <table class="main" width="100%">
                            <tr>
                                <th style="text-align: left; padding: 6px 0" colspan="5">TRAVEL DETAILS</th>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Request From</th>
                                <td style="text-align: left; padding: 5px 0">{tripInstance.traveler.created_by.first_name} {tripInstance.traveler.created_by.last_name}</td>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Department</th>
                                <td style="text-align: left; padding: 5px 0">{tripInstance.traveler.department.name}</td>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Travel Route</th>
                                <td style="text-align: left; padding: 5px 0">{tripInstance.route}</td>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Travel Justification</th>
                                <td style="text-align: left; padding: 5px 0"> {tripInstance.traveler.description} </td>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Departure Date</th>
                                <td style="text-align: left; padding: 5px 0"> {str(tripInstance.departure_date)} </td>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Return Date</th>
                                <td style="text-align: left; padding: 5px 0"> {str(tripInstance.return_date)} </td>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Mode of Transport</th>
                                <td style="text-align: left; padding: 5px 0">{tripInstance.traveler.mode_of_transport}</td>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Number of Travelers</th>
                                <td style="text-align: left; padding: 5px 0">{str(no_of_travelers)}</td>
                            </tr>
                        </table>
                    """
                    # uri = f"requests/view/{str(tripInstance.traveler.id)}"
                    

                    try:
                        # message_template = read_template("custom_template.html")
                        call_to_action = 'View Request'
                        platform = 'Travel Request System'
                        emails = list(set(managers_emails))
                        for email in emails:
                            message_template = read_template("custom_template.html")
                            uri = f"authentication/auto/{email}/{str(tripInstance.traveler.id)}"
                            link = "http://172.20.0.42:8000/" + uri
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
                                "email" : [email], 
                                "subject" : subject,
                                "message" : msg,
                                "is_html": True
                            }

                            Sendmail.objects.create(**mail)

                    except Exception as e:
                        logger.error(e)

                    # Notify transport department
                    subject = f"Travel Request {tid} Has Been Initiated [TRF-AKHK]"
                    message = f"Hello. \nA new travel request: {tid} of mode: {mode_of_transport.capitalize()}\nhas been initiated by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nDeparture date: {departure_date}-{departure_time}. Route: {route}. Number of people: {str(no_of_travelers)} \n\nRegards\nTRS-AKHK"
                    emails = list(get_user_model().objects.filter(Q(groups__name='TRANSPORT')).values_list('email', flat=True))

                    try:
                        mail = {
                            "email" : list(set(emails)), 
                            "subject" : subject,
                            "message" : message
                        }

                        Sendmail.objects.create(**mail)

                    except Exception as e:
                        logger.error(e)


   
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
                is_individual = True
                record_id = payload['record_id']
                description = payload['description']
                purpose = payload['purpose']
                route = payload['route']
                estimated_distance = payload['estimated_distance']
                departure_date = payload['departure_date']
                departure_time = payload['departure_time']
                return_date = payload['return_date']
                mode_of_transport = payload['mode_of_transport']
                type_of_travel = payload['type_of_travel']
                department = payload['department']
                visa_required_date = payload.get('visa_required_date')
                accommodation = bool(payload.get('accommodation'))
                salary_advance_required = bool(payload.get('salary_advance_required'))
                salary_amount_required = payload.get('salary_amount_required')
                requesting_for = payload.get('requesting_for')
                travel_cost = payload.get('travel_cost')
                travel_cost_items = payload.get('travel_cost_items')


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
                    if requesting_for == 'OTHERS':
                        advance_requests = list(payload.get('advance_requests'))

                        if not advance_requests:
                            return Response({"details": "Target Employees Required !"}, status=status.HTTP_400_BAD_REQUEST)
                        
                        salary_amount_required = 0
                        for item in advance_requests:
                            salary_amount_required += int(item['amount'])

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
                    department = SRRSDepartment.objects.get(id=department)
                except Exception as e:
                    return Response({"details": "Unknown Department !"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    traveler = models.Traveler.objects.get(id=record_id)
                except Exception as e:
                    return Response({"details": "Unknown Travel !"}, status=status.HTTP_400_BAD_REQUEST)

                
                with transaction.atomic():
                    traveler_raw = {
                        "purpose": purpose,
                        "created_by": authenticated_user,
                        "description": description,
                        "department": department,
                        "mode_of_transport": mode_of_transport,
                        "type_of_travel": type_of_travel,
                        "requesting_for": requesting_for,
                        "salary_advance_required": salary_advance_required,
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

                    if salary_advance_required and not is_individual:
                        traveler_raw.update({"advance_requests": advance_requests})


                    models.Traveler.objects.filter(Q(id=record_id)).update(**traveler_raw)

                    # update trip instance
                    trip_raw = {
                        "traveler": traveler,
                        "route": route,
                        "departure_date": departure_date,
                        "departure_time": departure_time,
                        "return_date": return_date,
                        "accommodation": accommodation,
                        "estimated_distance": estimated_distance,
                    }  

                    if visa_required_date:
                        trip_raw.update({"visa_required_date": visa_required_date})


                    models.Trip.objects.filter(Q(traveler=traveler)).update(**trip_raw)

                    raw = {
                        "traveler": traveler,
                        "status": 'EDITED',
                        "status_for": 'Requestor',
                        "action_by": authenticated_user,
                    }

                    models.StatusChange.objects.create(**raw)

                    # Notify CEO / FINANCE
                    managers_emails = list(get_user_model().objects.filter(Q(groups__name='CEO')).values_list('email', flat=True))
                    if traveler.requires_hof_approval:
                        list(managers_emails) + list(get_user_model().objects.filter(Q(groups__name='HOF')).values_list('email', flat=True))

                    # Notify selected send to
                    subject = f"Travel Request {traveler.tid} Resubmitted [TRF-AKHK]"
                    message = f"Hello, \nTravel request: {traveler.tid} has been resubmitted by\n{authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nPending your action.\n\nRegards\nTRS-AKHK"

                    try:
                        mail = {
                            "email" :  list(set(managers_emails)), 
                            "subject" : subject,
                            "message" : message,
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        logger.error(e)
   
                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Travel Request resubmitted", f"Travel Request Id: {traveler.id}")
                
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
                comments = payload.get('comments') or None
                # roles = user_util.fetchusergroups(request.user.id)  

                try:
                    traveler = models.Traveler.objects.get(id=traveler_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Travel !"}, status=status.HTTP_400_BAD_REQUEST)
            
                
                with transaction.atomic():
                    rejection_statuses = ['REJECTED','INCOMPLETE']
                    if traveler_status in rejection_statuses:
                        if not comments:
                            return Response({"details": "Reasons for selected action required"}, status=status.HTTP_400_BAD_REQUEST)
                        traveler.rejection_comments = comments

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

                    subject = f"Travel Request: {traveler.tid} Progress Update [TRF-AKHK]"
                    message = f"Hello, \nThe Request:{traveler.tid} has been marked as {traveler_status} by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\n\nRegards\nTRS-AKHK"

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
                    logger.error(e)
                    return Response({"details": "Cannot complete request !"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    resps = []
                    if "HOD" in roles:

                        if query == 'salary-advance':
                            targets = models.AdvanceSalaryRequests.objects.filter(
                                Q(traveler__department=request.user.srrs_department),is_deleted=False).order_by('-date_created')
                            resp = [x.traveler for x in targets]

                        elif query == 'pending':
                            resp = models.Traveler.objects.filter(
                                Q(department=request.user.srrs_department) & 
                                Q(requires_hod_approval=True) , is_hod_approved=False, is_deleted=False).order_by('-date_created')

                        else:
                            resp = models.Traveler.objects.filter((Q(department=request.user.srrs_department) &  Q(requires_hod_approval=True)) |  Q(traveler=authenticated_user), is_deleted=False).order_by('-date_created')

                        resps += resp

                    if "USER_MANAGER" in roles:
                        if query == 'salary-advance':
                            targets = models.AdvanceSalaryRequests.objects.filter(Q(is_deleted=False)).order_by('-date_created')
                            resp = [
                                    x.traveler 
                                    for x in targets 
                                ]
                        else:
                            resp = models.Traveler.objects.filter(Q(is_deleted=False) ).order_by('-date_created')

                        resps += resp

                    if "SLT" in roles:
                        resp = []

                        resp = models.Traveler.objects.filter(
                            Q(department=request.user.srrs_department) |  Q(traveler=authenticated_user), is_deleted=False).order_by('-date_created')

                        resps += resp

                    if "HOF" in roles:
                        if not query:
                            resp = models.Traveler.objects.filter(Q(requires_hof_approval=True),is_deleted=False).order_by('-date_created')

                        if query == 'salary-advance':
                            targets = models.AdvanceSalaryRequests.objects.filter(Q(is_deleted=False)).order_by('-date_created')
                            resp = [x.traveler for x in targets]

                        elif query == 'pending':
                            resp = models.Traveler.objects.filter(Q(requires_hof_approval=True) & Q(is_hof_approved=False), is_deleted=False).order_by('-date_created')

                        resps += resp
                    
                    if "CEO" in roles:
                        if not query:
                            # resp = models.Traveler.objects.filter(Q(requires_ceo_approval=True), is_deleted=False).order_by('-date_created')

                            resp = models.Traveler.objects.filter(Q(requires_ceo_approval=True) & Q(is_ceo_approved=False), is_deleted=False).order_by('-date_created')

                        if query == 'salary-advance':
                            targets = models.AdvanceSalaryRequests.objects.filter(Q(is_deleted=False)).order_by('-date_created')
                            resp = [x.traveler for x in targets]

                        elif query == 'pending':
                            resp = models.Traveler.objects.filter(Q(requires_ceo_approval=True) & Q(is_ceo_approved=False), is_deleted=False).order_by('-date_created')

                        resps += resp

                        # filter for hod
                        resp = models.Traveler.objects.filter(
                                Q(department=request.user.srrs_department) & 
                                Q(requires_hod_approval=True),
                                is_hod_approved=False, is_deleted=False).exclude(requires_ceo_approval=False).order_by('-date_created')
                        
                        resps += resp


                    if "ADMINISTRATOR" in roles :
                        allowed_statuses = ['APPROVED', 'CLOSED']

                        if query == 'pending':
                            resp = models.Traveler.objects.filter(Q(requires_administrator_approval=True) & Q(is_administrator_approved=False), is_deleted=False).order_by('-date_created')

                        elif query == 'salary-advance':
                            resp = []

                        else:
                            resp = models.Traveler.objects.filter(Q(is_deleted=False) & Q(requires_administrator_approval=True) & Q(status__in=allowed_statuses)).order_by('-date_created')

                        resps += resp

                    
                    if "CASH_OFFICE" in roles :
                        allowed_statuses = ['APPROVED', 'CLOSED']
                        
                        if query == 'pending':
                            resp = models.Traveler.objects.filter(Q(requires_cash_office_approval=True) & Q(is_cash_office_approved=False), is_deleted=False).order_by('-date_created')

                        if query == 'salary-advance':
                            targets = models.AdvanceSalaryRequests.objects.filter(Q(is_deleted=False), status='APPROVED').order_by('-date_created')
                            resp = [x.traveler for x in targets]

                        else:
                            resp = models.Traveler.objects.filter(Q(is_deleted=False) & Q(requires_cash_office_approval=True) & Q(status__in=allowed_statuses)).order_by('-date_created')

                        resps += resp

                    if "TRANSPORT" in roles :
                        allowed_statuses = ['APPROVED', 'CLOSED']
                        
                        if query == 'pending':
                            resp = models.Traveler.objects.filter(Q(requires_transport_approval=True) & Q(is_administrator_approved=False), is_deleted=False).order_by('-date_created')
                        elif query == 'salary-advance':
                            resp = []
                        else:
                            resp = models.Traveler.objects.filter(Q(is_deleted=False) & Q(requires_transport_approval=True) & Q(status__in=allowed_statuses) ).order_by('-date_created')

                        resps += resp

                    # else:
                    if not query:
                        resp = models.Traveler.objects.filter(Q(created_by=request.user) | Q(traveler=request.user),is_deleted=False).order_by('-date_created')

                    if query == 'salary-advance':
                        targets = models.AdvanceSalaryRequests.objects.filter(Q(traveler__created_by=request.user) & Q(traveler__traveler=request.user), is_deleted=False).order_by('-date_created')
                        resp = [x.traveler for x in targets]

                    resps += resp

                    resps = list(set(resps))
                    resps = sorted(resps, key=lambda x: x.date_created, reverse=True)

                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resps, request)
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
                comments = payload.get('comments') or None
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
                        traveler.hod_comments = comments
                        
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
                        traveler.ceo_comments = comments

                        if traveler.mode_of_transport == 'FLIGHT':
                            traveler.requires_administrator_approval = True

                        if traveler.mode_of_transport == 'HOSPITAL VEHICLE':
                            traveler.requires_transport_approval = True

                        if traveler.mode_of_transport == 'PSV':
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
                        traveler.requires_ceo_approval = True

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
                                if int(amount) == travel_cost:
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
                        subject = f"Travel Request {traveler.tid} Status  [TRF-AKHK]"
                        message = f"Dear {traveler.created_by.first_name}, \n\nYour Travel Request has been\n Approved by HOD.\nPending other approvals.\n\nRegards\nTRS-AKHK"
                    elif is_slt:
                        subject = f"Travel Request {traveler.tid} Status  [TRF-AKHK]"
                        message = f"Dear {traveler.created_by.first_name}, \n\nYour Travel Request has been Approved by SLT.\nPending Finance Approval.\n\nRegards\nTRS-AKHK"
                    elif is_hof:
                        subject = f"Travel Request {traveler.tid} Status  [TRF-AKHK]"
                        message = f"Dear {traveler.created_by.first_name}, \n\nYour Travel Request has been\n Approved by Finance.\n\nRegards\nTRS-AKHK"
                    elif is_ceo:
                        subject = f"Travel Request {traveler.tid} Status  [TRF-AKHK]"
                        message = f"Dear {traveler.created_by.first_name}, \n\nYour Travel Request has been\n Approved by CEO.\n\nRegards\nTRS-AKHK"
                    elif is_cash_office:
                        subject = f"Travel Request {traveler.tid} Status  [TRF-AKHK]"
                        message = f"Dear {traveler.created_by.first_name}, \n\nYour Travel Request has been\n Approved by Cash Office.\n\nRegards\nTRS-AKHK"
                    elif is_transport_office:
                        subject = f"Travel Request {traveler.tid} Status  [TRF-AKHK]"
                        message = f"Dear {traveler.created_by.first_name}, \n\nYour Travel Request has been\n Approved by Transport Office.\n\nRegards\nTRS-AKHK"

                    try:
                        mail = {
                            "email" : [traveler.created_by.email], 
                            "subject" : subject,
                            "message" : message,
                        }
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        logger.error(e)


                    # Notify ADMINISTRATOR
                    if is_ceo and traveler.mode_of_transport == 'FLIGHT':
                        emails = list(get_user_model().objects.filter(Q(groups__name='ADMINISTRATOR')).values_list('email', flat=True))
                        subject = f"Travel Request: {traveler.tid} Pending Your Action.  [TRF-AKHK]"
                        message = f"Hello. \nTravel Request: {traveler.tid} has been approved by the CEO, and is now pending administration and costing\n\nRegards\nTRS-AKHK"


                        try:
                            mail = {
                                "email" : list(set(emails)), 
                                "subject" : subject,
                                "message" : message,
                            }
                            Sendmail.objects.create(**mail)
                        except Exception as e:
                            logger.error(e)

                    # Notify CASH OFFICE, HOF, MMD
                    if is_ceo:
                        emails = list(get_user_model().objects.filter(Q(groups__name='CASH_OFFICE') | Q(groups__name='HOF') | Q(groups__name='MMD')).values_list('email', flat=True))
                        subject = f"Travel Request: {traveler.tid} Pending Your Action.  [TRF-AKHK]"
                        message = f"Hello. \nTravel Request: {traveler.tid} has been approved by the CEO,\n currently pending your action\n\nRegards\nTRS-AKHK"

                        # emails.append("ksm.logistics@akhskenya.org")

                        try:
                            mail = {
                                "email" : list(set(emails)), 
                                "subject" : subject,
                                "message" : message,
                            }
                            Sendmail.objects.create(**mail)
                        except Exception as e:
                            logger.error(e)

                    # Notify CEO
                    if is_hod:
                        emails = list(get_user_model().objects.filter(Q(groups__name='CEO')).values_list('email', flat=True))
                        subject = f"Travel Request: {traveler.tid} Pending Your Action.  [TRF-AKHK]"
                        # message = f"Hello. \nTravel Request: {traveler.tid} has been approved by HOD,\n currently pending your action\n\nRegards\nTRS-AKHK"
                        no_of_travelers = 1
                        if traveler.requesting_for == 'OTHERS':
                            no_of_travelers = len(traveler.employees)

                        # try:
                        #     mail = {
                        #         "email" : list(set(emails)), 
                        #         "subject" : subject,
                        #         "message" : message,
                        #     }
                        #     Sendmail.objects.create(**mail)
                        # except Exception as e:
                        #     logger.error(e)

                        message = f"""
                        <table class="main" width="100%">
                            <tr>
                                <th style="text-align: left; padding: 6px 0" colspan="5">TRAVEL DETAILS</th>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Request From</th>
                                <td style="text-align: left; padding: 5px 0">{traveler.created_by.first_name} {traveler.created_by.last_name}</td>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Department</th>
                                <td style="text-align: left; padding: 5px 0">{traveler.department.name}</td>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Travel Route</th>
                                <td style="text-align: left; padding: 5px 0">{traveler.trip.route}</td>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Travel Justification</th>
                                <td style="text-align: left; padding: 5px 0"> {traveler.trip.traveler.description} </td>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Departure Date</th>
                                <td style="text-align: left; padding: 5px 0"> {str(traveler.trip.departure_date)} </td>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Return Date</th>
                                <td style="text-align: left; padding: 5px 0"> {str(traveler.trip.return_date)} </td>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Mode of Transport</th>
                                <td style="text-align: left; padding: 5px 0">{traveler.trip.traveler.mode_of_transport}</td>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 5px 0">Number of Travelers</th>
                                <td style="text-align: left; padding: 5px 0">{str(no_of_travelers)}</td>
                            </tr>
                        </table>
                    """                    

                    try:
                        call_to_action = 'View Request'
                        platform = 'Travel Request System'
                        emails = list(set(emails))
                        for email in emails:
                            message_template = read_template("custom_template.html")
                            uri = f"authentication/auto/{email}/{str(traveler.id)}"
                            link = "http://172.20.0.42:8000/" + uri
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
                                "email" : [email], 
                                "subject" : subject,
                                "message" : msg,
                                "is_html": True
                            }

                            Sendmail.objects.create(**mail)

                    except Exception as e:
                        logger.error(e)

                        

                    # Notify transport department
                    if is_ceo:
                        Trip = models.Trip.objects.get(traveler=traveler)
                        no_of_travelers = 1
                        if traveler.requesting_for == 'OTHERS':
                            no_of_travelers = len(traveler.employees)
                        subject = f"Travel Request {traveler.tid} Approved by CEO [TRF-AKHK]"
                        message = f"Hello. \nA new travel request: {traveler.tid} of mode: {traveler.mode_of_transport.capitalize()}\nis approved by {authenticated_user.first_name} {authenticated_user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\nDeparture date: {str(Trip.departure_date)}-{str(Trip.departure_time)}. Route: {Trip.route}. Number of people: {str(no_of_travelers)} \n\nRegards\nTRS-AKHK"
                        emails = list(get_user_model().objects.filter(Q(groups__name='TRANSPORT')).values_list('email', flat=True))
                        emails.append('ksm.logistics@akhskenya.org')

                        try:
                            mail = {
                                "email" : list(set(emails)), 
                                "subject" : subject,
                                "message" : message,
                            }

                            Sendmail.objects.create(**mail)

                        except Exception as e:
                            logger.error(e)

                    # Notify control office
                    if is_transport_office:
                        emails = list(get_user_model().objects.filter(Q(groups__name='CONTROL_ROOM')).values_list('email', flat=True))
                        subject = f"Travel Request {traveler.tid} Approved  [TRF-AKHK]"
                        message = f"Hello, \n\nTravel Request: {traveler.tid} has been approved by Transport Office.\nDetails include:\nDriver: {approval_msg.get('driver_name')}\nVehicle: {approval_msg.get('vehicle_number_plate')}\nDate of travel: {approval_msg.get('date_of_travel')}\nTime of travel: {approval_msg.get('time_of_travel')}\n\nRegards\nTRS-AKHK"

                        try:
                            mail = {
                                "email" : list(set(emails)), 
                                "subject" : subject,
                                "message" : message,
                            }
                            if emails:
                                Sendmail.objects.create(**mail)
                        except Exception as e:
                            logger.error(e)

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
                        emails = list(get_user_model().objects.filter(Q(groups__name='HOD') & Q(srrs_department=traveler.department)).values_list('email', flat=True))
                        
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
                    #     logger.error(e)
                    # except Exception as e:
                    #     pass

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
                    subject = f"Travel Advance Request {update_status.capitalize()}  [TRF-AKHK]"
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
                    subject = f"Travel Request {traveler.tid} Closed  [TRF-AKHK]"
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
            q_filters &= Q(traveler__srrs_department=department)

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
            q_filters &= Q(traveler__srrs_department=department)

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