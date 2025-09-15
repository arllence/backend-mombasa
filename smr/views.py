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
from smr import models
from smr import serializers
from smr.utils import shared_fxns
from django.db import IntegrityError, DatabaseError
from acl.utils import user_util
from acl.models import User, Sendmail, SRRSDepartment, SubDepartment, OHC
from django.db.models import Sum
from django.core.mail import send_mail
from django.utils import timezone
from django.contrib.auth.models import Group

from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import NotFound, ParseError

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
    
    @action(methods=["GET"], detail=False, url_path="list-users-with-role", url_name="list-users-with-role")
    def list_users_with_role(self, request):
        authenticated_user = request.user
        role_name = request.query_params.get('role_name')
        if role_name is None:
            return Response({'details': 'Role is Required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            role = Group.objects.get(name=role_name)
        except (ValidationError, ObjectDoesNotExist):
            return Response({'details': 'Role does not exist'}, status=status.HTTP_400_BAD_REQUEST)
        selected_users = get_user_model().objects.filter(groups__name=role.name)
        user_info = serializers.SlimUsersSerializer(selected_users, many=True)
        return Response(user_info.data, status=status.HTTP_200_OK)
    
    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="meals",
            url_name="meals")
    def meals(self, request):
        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":
            payload = request.data

            serializer = serializers.GenericMealSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                department = payload['department']
                slt = payload['slt']
                name = payload['name']
                email = payload['email']
                am_tea = payload['am_tea']
                pm_tea = payload['pm_tea']
                lunch = payload['lunch']
                dinner = payload['dinner']
                date_of_event = payload['date_of_event']
                location_of_function = payload['location_of_function']
                number_of_participants = payload['number_of_participants']

                uid = shared_fxns.generate_unique_identifier()

                if not name or not email:
                    return Response({"details": "Name and Email Required"}, status=status.HTTP_400_BAD_REQUEST)


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
                
                try:
                    slt = get_user_model().objects.get(id=slt)
                except Exception as e:
                    return Response({"details": "Unknown SLT"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    raw = {
                        "department": department,
                        "slt": slt,
                        "am_tea": am_tea,
                        "pm_tea": pm_tea,
                        "lunch": lunch,
                        "dinner": dinner,
                        "created_by": user,
                        "date_of_event": date_of_event,
                        "location_of_function": location_of_function,
                        "number_of_participants": number_of_participants,
                        "uid": uid
                    }
                    if not user:
                        raw.update(
                            {
                                "email": email,
                                "name": name
                            }
                        )

                    meal = models.Meal.objects.create(
                        **raw
                    )

                    # create track status change
                    raw = {
                        "meal": meal,
                        "status": "SUBMITTED",
                        "status_for": "/".join(roles),
                        # "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)



                    # Notify Platform Admins
                    # emails = list(get_user_model().objects.filter(Q(groups__name__in=['SMR_ADMIN'])).values_list('email', flat=True))
                    emails = [slt.email]
                    subject = f"[SMR] New Meal Request: {uid}"
                    message = f"""
                        <table border="1" class='signature-table'>
                            <tr>
                                <th colspan='5'>Meal Details</th>
                            </tr>
                            <tr>
                                <th>Location</th>
                                <td>{location_of_function}</td>
                            </tr>
                            <tr>
                                <th>Date of Event</th>
                                <td>{date_of_event}</td>
                            </tr>
                            <tr>
                                <th>Number of Participants</th>
                                <td>{number_of_participants}</td>
                            </tr>
                            <tr>
                                <th>AM Tea</th>
                                <td>
                                    <strong>Description:</strong><br>
                                    {am_tea.get('description') or 'N/A'} <br>
                                    <strong>Time:</strong><br>
                                    {am_tea.get('time') or 'N/A'} <br>
                                </td>
                            </tr>
                            <tr>
                                <th>Lunch</th>
                                <td>
                                    <strong>Description:</strong><br>
                                    {lunch.get('description') or 'N/A'} <br>
                                    <strong>Time:</strong><br>
                                    {lunch.get('time') or 'N/A'} <br>
                                </td>
                            </tr>
                            <tr>
                                <th>PM Tea</th>
                                <td>
                                    <strong>Description:</strong><br>
                                    {pm_tea.get('description') or 'N/A'} <br>
                                    <strong>Time:</strong><br>
                                    {pm_tea.get('time') or 'N/A'} <br>
                                </td>
                            </tr>
                            <tr>
                                <th>Dinner</th>
                                <td>
                                    <strong>Description:</strong><br>
                                    {dinner.get('description') or 'N/A'} <br>
                                    <strong>Time:</strong><br>
                                    {dinner.get('time') or 'N/A'} <br>
                                </td>
                            </tr>
                        </table>


                    """
                    uri = f"requests/view/{str(meal.id)}"
                    link = "http://172.20.0.42:8010/" + uri
                    platform = 'View Meal'

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
                        user, user, "Meal Request created", f"Meal Request Id: {meal.id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

class SMRViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]
    

    def get_queryset(self):
        return []
    

    @action(methods=["POST", "GET", "PUT", "PATCH", "DELETE"],
            detail=False,
            url_path="meals",
            url_name="meals")
    def meals(self, request):
        authenticated_user = request.user
        roles = user_util.fetchusergroups(request.user.id) 

        if request.method == "POST":

            payload = request.data

            serializer = serializers.MealSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                department = payload['department']
                am_tea_required = payload['am_tea_required']
                pm_tea_required = payload['pm_tea_required']
                lunch_required = payload['lunch_required']
                dinner_required = payload['dinner_required']
                am_tea = payload['am_tea'] if am_tea_required else {}
                pm_tea = payload['pm_tea'] if pm_tea_required else {}
                lunch = payload['lunch'] if lunch_required else {}
                dinner = payload['dinner'] if dinner_required else {}
                date_of_event = payload['date_of_event']
                location_of_function = payload['location_of_function']
                number_of_participants = payload['number_of_participants']
                reason = payload['reason']

                uid = shared_fxns.generate_unique_identifier()

                requested = [
                    am_tea_required, pm_tea_required, lunch_required, dinner_required
                ]

                checked = 0
                for item in requested:
                    if item:
                        checked += 1

                if not checked:
                    return Response({"details": "No meal requested"}, status=status.HTTP_400_BAD_REQUEST)

                # Get today's date
                today_date = datetime.date.today()

                # find difference in dates / validate dates
                hours = shared_fxns.find_date_difference(str(today_date.strftime('%Y-%m-%d')),date_of_event,'hours')
                if hours < 48:
                    return Response({"details": "Request to be made at least 48hrs before event date"}, status=status.HTTP_400_BAD_REQUEST)


                try:
                    department = SRRSDepartment.objects.get(id=department)
                except Exception as e:
                    return Response({"details": "Unknown Department"}, status=status.HTTP_400_BAD_REQUEST)
                
                slt = department.slt
                meals_cost = 0

                def check_items(meal,name):
                    found_meal = True
                    items = 2

                    if not meal:
                        found_meal = False

                    for k, v in meal.items():
                        if not v:
                            found_meal = False
                            items -= 1

                    if found_meal:
                        meals.append(name)
                        if "TEA" in name:
                            costs.append(200)
                        else:
                            costs.append(500)

                    if items == 1:
                        raise ParseError({"details": f"Both Description and time required for {name}"})
                    

                meals =  []
                costs =  []
                check_items(am_tea,"AM TEA")
                check_items(pm_tea,"PM TEA")
                check_items(lunch,"LUNCH")
                check_items(dinner,"DINNER")

                if not meals:
                    return Response({"details": "Both Description and serving time required for selected meals"}, status=status.HTTP_400_BAD_REQUEST)
                
                meals_cost = sum(costs)
                total_meals_cost = meals_cost * int(number_of_participants)

                with transaction.atomic():
                    raw = {
                        "department": department,
                        "slt": slt,
                        "am_tea": am_tea,
                        "pm_tea": pm_tea,
                        "lunch": lunch,
                        "dinner": dinner,
                        "meals": meals,
                        "created_by": request.user,
                        "date_of_event": date_of_event,
                        "reason": reason,
                        "total_cost" : total_meals_cost,
                        "location_of_function": location_of_function,
                        "number_of_participants": number_of_participants,
                        "uid": uid
                    }

                    meal = models.Meal.objects.create(
                        **raw
                    )

                    # create track status change
                    raw = {
                        "meal": meal,
                        "status": "REQUESTED",
                        "status_for": "/".join(roles),
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)

                    # Notify SLT for approval
                    emails = [slt.email]
                    subject = f"[SMR] New Meal Request: {uid}"
                    message = f"""
                        <table border="1" class='signature-table'>
                            <tr>
                                <th colspan='5'>Meal Details</th>
                            </tr>
                            <tr>
                                <th>Location</th>
                                <td>{location_of_function}</td>
                            </tr>
                            <tr>
                                <th>Date of Event</th>
                                <td>{date_of_event}</td>
                            </tr>
                            <tr>
                                <th>Event Justification</th>
                                <td>{reason}</td>
                            </tr>
                            <tr>
                                <th>Number of Participants</th>
                                <td>{number_of_participants}</td>
                            </tr>
                            <tr>
                                <th>AM Tea</th>
                                <td>
                                    <strong>Time: </strong>
                                    {am_tea.get('time') or 'N/A'} <br>
                                    <strong>Description:</strong><br>
                                    {am_tea.get('description') or 'N/A'}                                    
                                </td>
                            </tr>
                            <tr>
                                <th>Lunch</th>
                                <td>
                                    <strong>Time: </strong>
                                    {lunch.get('time') or 'N/A'} <br>
                                    <strong>Description:</strong><br>
                                    {lunch.get('description') or 'N/A'}
                                </td>
                            </tr>
                            <tr>
                                <th>PM Tea</th>
                                <td>
                                    <strong>Time: </strong>
                                    {pm_tea.get('time') or 'N/A'} <br>
                                    <strong>Description:</strong><br>
                                    {pm_tea.get('description') or 'N/A'}
                                    
                                </td>
                            </tr>
                            <tr>
                                <th>Dinner</th>
                                <td>
                                    <strong>Time: </strong>
                                    {dinner.get('time') or 'N/A'} <br>
                                    <strong>Description:</strong><br>
                                    {dinner.get('description') or 'N/A'}
                                </td>
                            </tr>
                            <tr>
                                <th>Total Meal Cost</th>
                                <td>
                                    <strong>KES </strong>
                                    {total_meals_cost:,.2f}
                                </td>
                            </tr>
                        </table>


                    """
                    uri = f"requests/view/{str(meal.id)}"
                    link = "http://172.20.0.42:8010/" + uri
                    platform = 'View Meal'

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

                    try:
                        # notify requestor
                        msg = f"""Hello.\nYour meal request has been submitted.\nMeal Request ID: {uid}.\nTotal cost for the meal is Kes {total_meals_cost:,.2f}.\nYour Request is currently waiting approvals from your SLT and CEO.\nAfter approvals, the request will be forwarded to the Catering department.\nTo check on progress, click: {link}\n\nRegards\nSMR-AKHK\n<Auto-generated>"""

                        mail = {
                            "email" : [request.user.email], 
                            "subject" : subject,
                            "message" : msg,
                            "is_html": False
                        }
                        
                        Sendmail.objects.create(**mail)
                    except Exception as e:
                        logger.error(e)

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Meal Request created", f"Meal Request Id: {meal.id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "PUT":

            payload = request.data
            
            serializer = serializers.PutMealSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                department = payload['department']
                am_tea_required = payload['am_tea_required']
                pm_tea_required = payload['pm_tea_required']
                lunch_required = payload['lunch_required']
                dinner_required = payload['dinner_required']
                am_tea = payload['am_tea']
                pm_tea = payload['pm_tea']
                lunch = payload['lunch']
                dinner = payload['dinner']
                date_of_event = payload['date_of_event']
                reason = payload['reason']
                location_of_function = payload['location_of_function']
                number_of_participants = payload['number_of_participants']

                # Get today's date
                today_date = datetime.date.today()

                # find difference in dates / validate dates
                hours = shared_fxns.find_date_difference(str(today_date.strftime('%Y-%m-%d')),date_of_event,'hours')
                if hours < 48:
                    return Response({"details": "Request to be made at least 48hrs before event date"}, status=status.HTTP_400_BAD_REQUEST)



                try:
                    mealInstance = models.Meal.objects.get(id=request_id)
                except Exception as e:
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                
                # try:
                #     slt = get_user_model().objects.get(id=slt)
                # except Exception as e:
                #     return Response({"details": "Unknown SLT"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    department = SRRSDepartment.objects.get(id=department)
                except Exception as e:
                    return Response({"details": "Unknown Department"}, status=status.HTTP_400_BAD_REQUEST)
                
                slt = department.slt    

                def check_items(meal,name):
                    found_meal = True
                    items = 2
                    for k, v in meal.items():
                        if not v:
                            found_meal = False
                            items -= 1
                    if found_meal:
                        meals.append(name)
                    if items == 1:
                        raise ParseError({"details": f"Both Description and time required for {name}"})

                meals =  []
                check_items(am_tea,"AM TEA")
                check_items(pm_tea,"PM TEA")
                check_items(lunch,"LUNCH")
                check_items(dinner,"DINNER")            
                
                with transaction.atomic():
                    raw = {
                        "department": department,
                        "slt": slt,
                        "am_tea": am_tea,
                        "pm_tea": pm_tea,
                        "lunch": lunch,
                        "dinner": dinner,
                        "meals": meals,
                        "created_by": request.user,
                        "date_of_event": date_of_event,
                        "reason": reason,
                        "location_of_function": location_of_function,
                        "number_of_participants": number_of_participants,
                    }  

                    models.Meal.objects.filter(Q(id=request_id)).update(**raw)

                    # create track status change
                    raw = {
                        "meal": mealInstance,
                        "status": "EDITED",
                        "status_for": "/".join(roles),
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)

                user_util.log_account_activity(
                    authenticated_user, authenticated_user, "Meal Request updated", f"Meal Id: {mealInstance.id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

  
        elif request.method == "PATCH":
            # Request approvals
            if not any(role in ['SLT','CEO'] for role in roles):
                return Response({"details": "Permission Denied"}, status=status.HTTP_400_BAD_REQUEST)
            
            payload = request.data
            serializer = serializers.PatchMealSerializer(
                    data=payload, many=False)
            
            if serializer.is_valid():
                request_id = payload['request_id']
                action = payload['action'].upper()

                try:
                    mealInstance = models.Meal.objects.get(id=request_id)
                except Exception as e:
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)

                is_ceo = False
                is_slt = False

                if "SLT" in roles:
                    is_slt = True
                    status_for = 'SLT'
                    if action == 'APPROVED':
                        action = 'SLT APPROVED'

                if "CEO" in roles:
                    is_ceo = True
                    status_for = 'CEO'
                    if action == 'APPROVED' or action == 'SLT APPROVED':
                        action = 'CEO APPROVED'

              
                with transaction.atomic():
                    mealInstance.status = action
                    mealInstance.save()

                    # create track status change
                    raw = {
                        "meal": mealInstance,
                        "status": action,
                        "status_for": status_for,
                        "action_by": authenticated_user
                    }

                    models.StatusChange.objects.create(**raw)

                if is_ceo and is_slt:
                    emails = list(get_user_model().objects.filter(Q(groups__name__in=['SMR_ADMIN'])).values_list('email', flat=True))
                else:
                    if is_ceo:
                        emails = list(get_user_model().objects.filter(Q(groups__name__in=['SMR_ADMIN'])).values_list('email', flat=True))
                    if is_slt:
                        emails = list(get_user_model().objects.filter(Q(groups__name__in=['CEO'])).values_list('email', flat=True))

                subject = f"[SMR] New Meal Request: {mealInstance.uid}"
                message = f"""
                    <table border="1" class='signature-table'>
                        <tr>
                            <th colspan='5'>Meal Details</th>
                        </tr>
                        <tr>
                            <th>Location</th>
                            <td>{mealInstance.location_of_function}</td>
                        </tr>
                        <tr>
                            <th>Date of Event</th>
                            <td>{mealInstance.date_of_event}</td>
                        </tr>
                            <tr>
                            <th>Event Justification</th>
                            <td>{mealInstance.reason}</td>
                        </tr>
                        <tr>
                            <th>Number of Participants</th>
                            <td>{mealInstance.number_of_participants}</td>
                        </tr>
                        <tr>
                            <th>AM Tea</th>
                            <td>
                                <strong>Time: </strong>
                                {mealInstance.am_tea.get('time') or 'N/A'} <br>
                                <strong>Description:</strong><br>
                                {mealInstance.am_tea.get('description') or 'N/A'}
                            </td>
                        </tr>
                        <tr>
                            <th>Lunch</th>
                            <td>
                                <strong>Time: </strong>
                                {mealInstance.lunch.get('time') or 'N/A'} <br>
                                <strong>Description:</strong><br>
                                {mealInstance.lunch.get('description') or 'N/A'}
                            </td>
                        </tr>
                        <tr>
                            <th>PM Tea</th>
                            <td>
                                <strong>Time: </strong>
                                {mealInstance.pm_tea.get('time') or 'N/A'} <br>
                                <strong>Description:</strong><br>
                                {mealInstance.pm_tea.get('description') or 'N/A'}
                            </td>
                        </tr>
                        <tr>
                            <th>Dinner</th>
                            <td>
                                <strong>Time: </strong>
                                {mealInstance.dinner.get('time') or 'N/A'} <br>
                                <strong>Description:</strong><br>
                                {mealInstance.dinner.get('description') or 'N/A'} 
                            </td>
                        </tr>
                    </table>


                """
                uri = f"requests/view/{str(mealInstance.id)}"
                link = "http://172.20.0.42:8010/" + uri
                platform = 'View Meal'

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

                
                # Notify Requestor
                emails = []
                if mealInstance.email:
                    emails.append(mealInstance.email)
                if mealInstance.created_by:
                    emails.append(mealInstance.created_by.email)
                subject = f"[SMR] Meal Request Approved: {mealInstance.uid} ."
                message = f"Hello. \nYour meal request: {mealInstance.uid}, \nhas been Approved by: {request.user.first_name} {request.user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\n\nRegards\nSMR-AKHK"

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

                if action == 'REJECTED':
                    # Notify Requestor
                    emails = []
                    if mealInstance.email:
                        emails.append(mealInstance.email)
                    if mealInstance.created_by:
                        emails.append(mealInstance.created_by.email)
                    subject = f"[SMR] Meal Request Rejected: {mealInstance.uid} ."
                    message = f"Hello. \nYour meal request: {mealInstance.uid}, \nhas been Rejected by: {request.user.first_name} {request.user.last_name} on {str(datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'))}\n\nRegards\nSMR-AKHK"

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
                    authenticated_user, authenticated_user, "Meal Request updated", f"Meal Id: {mealInstance.id}")
                
                return Response('success', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
      
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            query = request.query_params.get('q')
            slim = request.query_params.get('slim')

            if request_id:
                try:
                    resp = models.Meal.objects.get(Q(id=request_id))
                    if slim:
                        resp = serializers.SlimFetchMealSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    else:
                        resp = serializers.FetchMealSerializer(resp, many=False, context={"user_id":request.user.id}).data
                    return Response(resp, status=status.HTTP_200_OK)
                
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    today = timezone.now().date()
                    if "SMR_ADMIN" in roles or "SUPERUSER" in roles:
                        if query == 'pending':
                            resp = models.Meal.objects.filter(
                                    Q(status='REQUESTED'), is_deleted=False
                                ).order_by('-date_created')
                        else:
                            resp = models.Meal.objects.filter(
                                    is_deleted=False
                                ).order_by('-date_created')
                    elif "CEO" in roles:
                        resp = models.Meal.objects.filter(
                                    Q(status='SLT APPROVED') | Q(slt=request.user) | Q(department__slt=request.user)  , is_deleted=False
                                ).exclude(Q(status__in=['EXPIRED','REJECTED','CEO APPROVED'])).order_by('-date_created')
                        # resp = models.Meal.objects.filter(
                        #             Q(status='SLT APPROVED') & Q(date_of_event__gte=today), is_deleted=False
                        #         ).order_by('-date_created')
                    else:
                        resp = models.Meal.objects.filter(
                                Q(email=request.user.email) |
                                Q(created_by=request.user) |
                                Q(slt=request.user) |
                                Q(department__slt=request.user) 
                            ).order_by('-date_created')


                    paginator = PageNumberPagination()
                    paginator.page_size = 50
                    result_page = paginator.paginate_queryset(resp, request)
                    serializer = serializers.SlimFetchMealSerializer(
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
                    recordInstance = models.Meal.objects.get(id=request_id,created_by=request.user)
                    recordInstance.is_deleted = True
                    recordInstance.status = "DELETED"
                    recordInstance.save()
                    # track status change
                    raw = {
                        "meal": recordInstance,
                        "status": "DELETED",
                        "status_for": '/'.join(roles),
                        "action_by": authenticated_user,
                    }
                    models.StatusChange.objects.create(**raw)

                    return Response('200', status=status.HTTP_200_OK)    
                 
                except Exception as e:
                    return Response({"details": "Unknown Request"}, status=status.HTTP_400_BAD_REQUEST)    


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
                assign_role = user_util.award_role('SMR_ADMIN', str(admin.id))
                if not assign_role:
                    return Response({"details": "Unable to assign role SMR_ADMIN"}, status=status.HTTP_400_BAD_REQUEST)
                
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
                    user_util.revoke_role('SMR_ADMIN', str(user.admin.id))
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
            url_path="meals",
            url_name="meals")
    def meals(self, request):
                    
        department = request.query_params.get('department')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        r_status = request.query_params.get('status')
        meal_type = request.query_params.get('meal_type')
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
        e_filters = Q()

        if department:
            q_filters &= Q(department=department)

        if date_from or date_to:
            if not date:
                return Response({"details": "Date From & To Required !"}, status=status.HTTP_400_BAD_REQUEST)
            q_filters &= create_date_range(date_from,date_to)
            
        if r_status:
            q_filters &= Q(status=r_status)

        if meal_type:
            if meal_type == 'AMTEA':
                q_filters &= Q(am_tea__description__isnull=False)
                e_filters &= Q(am_tea__description="")
            if meal_type == 'PMTEA':
                q_filters &= Q(pm_tea__description__isnull=False)
                e_filters &= Q(pm_tea__description="")
            if meal_type == 'LUNCH':
                q_filters &= Q(lunch__description__isnull=False)
                e_filters &= Q(lunch__description="")
            if meal_type == 'DINNER':
                q_filters &= Q(dinner__description__isnull=False)
                e_filters &= Q(dinner__description="")


        if q_filters:
            if e_filters:
                resp = models.Meal.objects.filter(Q(is_deleted=False) & q_filters).exclude(e_filters).order_by('-date_created')
            else:
                resp = models.Meal.objects.filter(Q(is_deleted=False) & q_filters).order_by('-date_created')
            
        else:
            resp = models.Meal.objects.filter(Q(is_deleted=False)).order_by('-date_created')[:50]

        resp = serializers.FetchMealSerializer(resp, many=True, context={"user_id":request.user.id}).data

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
        active_status = ['REQUESTED']

        
        if any(role in ['SMR_ADMIN', 'SUPERUSER'] for role in roles):
            requests = models.Meal.objects.filter(Q(is_deleted=False)).count()
            approved = models.Meal.objects.filter(Q(status="SLT APPROVED"), is_deleted=False).count()
            rejected = models.Meal.objects.filter(status="REJECTED", is_deleted=False).count()
            pending = models.Meal.objects.filter(Q(status__in=active_status), is_deleted=False).count()
        else:
            requests = models.Meal.objects.filter(Q(department=request.user.srrs_department) | Q(created_by=request.user) | Q(slt=request.user), is_deleted=False).count()
            approved = models.Meal.objects.filter(Q(department=request.user.srrs_department) |  Q(created_by=request.user) | Q(slt=request.user) | Q(email=request.user.email), status="SLT APPROVED", is_deleted=False).count()
            rejected = models.Meal.objects.filter(Q(department=request.user.srrs_department) |  Q(created_by=request.user) | Q(slt=request.user) | Q(email=request.user.email), status="REJECTED", is_deleted=False).count()
            pending = models.Meal.objects.filter(Q(department=request.user.srrs_department) |  Q(created_by=request.user) | Q(slt=request.user) | Q(email=request.user.email), status__in=active_status, is_deleted=False).count()

        resp = {
            "requests": requests,
            "approved": approved,
            "rejected": rejected,
            "pending": pending
        }

        return Response(resp, status=status.HTTP_200_OK)