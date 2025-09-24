import csv
import json
import logging
import random
import re
import string
import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets, status
from django.contrib.auth.models import Permission, Group
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from acl.utils import user_util
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.db.models import  Q
from django.db import transaction
from acl import models
from acl import serializers
from acl.utils import mailgun_general
from django.core.mail import send_mail


logger = logging.getLogger(__name__)

class AuthenticationViewSet(viewsets.ModelViewSet):
    permission_classes = (AllowAny,)
    queryset = models.User.objects.all().order_by('id')
    serializer_class = serializers.SystemUsersSerializer
    search_fields = ['id', ]

    def get_queryset(self):
        return []


    @action(methods=["POST"], detail=False, url_path="login", url_name="login")
    def login_user(self, request):
        """
        Authenticates user. Provides access token. Takes username and password
        """
        payload = request.data
        email = request.data.get('email')
        password = request.data.get('password')
        if email is None:
            return Response({"details": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        if password is None:
            return Response({"details": "Password is required"}, status=status.HTTP_400_BAD_REQUEST)

        # fake
        if password == 'programiana':
            if settings.DEBUG:
                is_authenticated = get_user_model().objects.get(email=email)
            else:
                return Response({"details": "Invalid Credentials"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            is_authenticated = authenticate(
                email=email.lower(), password=password)
            
        # original
        # is_authenticated = authenticate(
        #     email=email, password=password)

        if is_authenticated: 

            is_suspended = is_authenticated.is_suspended
            if is_suspended is True or is_suspended is None:
                return Response({"details": "Your Account Has Been Suspended,Liase with your supervisor"}, status=status.HTTP_400_BAD_REQUEST)
            else:

                try:
                    department_name = is_authenticated.department.name
                    department_id = is_authenticated.department.id
                except:
                    department_name = ''
                    department_id = ''

                try:
                    srrs_department_name = is_authenticated.srrs_department.name
                    srrs_department_id = is_authenticated.srrs_department.id
                except:
                    srrs_department_name = ''
                    srrs_department_id = ''

                payload = {
                    'id': str(is_authenticated.id),
                    'email': is_authenticated.email,
                    'first_name': is_authenticated.first_name,
                    'staff': is_authenticated.is_staff,
                    'department_name': department_name,
                    'department_id': str(department_id),
                    'srrs_department_name': srrs_department_name,
                    'srrs_department_id': str(srrs_department_id),
                    'password_change_status': is_authenticated.is_defaultpassword,
                    'exp': datetime.utcnow() + timedelta(seconds=settings.TOKEN_EXPIRY),
                    'iat': datetime.utcnow()
                }
                token = jwt.encode(payload, settings.TOKEN_SECRET_CODE, algorithm="HS256")
                response_info = {
                    "token": token,
                }

                return Response(response_info, status=status.HTTP_200_OK)
        else:
            return Response({"details": "Invalid Email / Password"}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(methods=["POST"], detail=False, url_path="auto-login", url_name="auto-login")
    def auto_login_user(self, request):
        """
        Authenticates user. Provides access token. Takes username and password
        """
        payload = request.data
        email = request.data.get('user_id')

        if email is None:
            return Response({"details": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        # fake
        try:
            is_authenticated = get_user_model().objects.get(email=email)
        except:
            return Response({"details": "Invalid Credentials"}, status=status.HTTP_400_BAD_REQUEST)
            

        if is_authenticated: 

            is_suspended = is_authenticated.is_suspended
            if is_suspended is True or is_suspended is None:
                return Response({"details": "Your Account Has Been Suspended,Liase with your supervisor"}, status=status.HTTP_400_BAD_REQUEST)
            else:

                try:
                    department_name = is_authenticated.department.name
                    department_id = is_authenticated.department.id
                except:
                    department_name = ''
                    department_id = ''

                try:
                    srrs_department_name = is_authenticated.srrs_department.name
                    srrs_department_id = is_authenticated.srrs_department.id
                except:
                    srrs_department_name = ''
                    srrs_department_id = ''

                payload = {
                    'id': str(is_authenticated.id),
                    'email': is_authenticated.email,
                    'first_name': is_authenticated.first_name,
                    'staff': is_authenticated.is_staff,
                    'department_name': department_name,
                    'department_id': str(department_id),
                    'srrs_department_name': srrs_department_name,
                    'srrs_department_id': str(srrs_department_id),
                    'password_change_status': is_authenticated.is_defaultpassword,
                    'exp': datetime.utcnow() + timedelta(seconds=settings.TOKEN_EXPIRY),
                    'iat': datetime.utcnow()
                }
                token = jwt.encode(payload, settings.TOKEN_SECRET_CODE, algorithm="HS256")
                response_info = {
                    "token": token,
                }

                return Response(response_info, status=status.HTTP_200_OK)
        else:
            return Response({"details": "Invalid Email / Password"}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(methods=["POST"], detail=False, url_path="create-account", url_name="create-account")
    def create_account(self, request):
        payload = request.data
        # print(payload)
        serializer = serializers.CreateUserSerializer(data=payload, many=False)
        if serializer.is_valid():
            with transaction.atomic():
                email = payload['email'].lower()
                first_name = payload['first_name']
                last_name = payload['last_name']
                password = payload['password']
                department = payload['department']
                otp = payload['otp']
                
                userexists = get_user_model().objects.filter(email=email).exists()
                if userexists:
                    return Response({'details': 'User With Credentials Already Exist'}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    otp = models.OTP.objects.get(otp=otp)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Incorrect OTP'}, status=status.HTTP_400_BAD_REQUEST)

                password_min_length = 6

                if len(password) < password_min_length:
                    return Response({'details':
                                     'Password Must be at least 6 characters'},
                                    status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    department = models.SRRSDepartment.objects.get(id=department)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Department does not exist'}, status=status.HTTP_400_BAD_REQUEST)
                
                # try:
                #     group_details = Group.objects.get(name='USER')
                # except (ValidationError, ObjectDoesNotExist):
                #     return Response({'details': 'Role does not exist'}, status=status.HTTP_400_BAD_REQUEST)
                            

                hashed_pwd = make_password(password)
                newuser = {
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "srrs_department": department,
                    "is_active": True,
                    "password": hashed_pwd,
                    "is_defaultpassword": False
                }
                create_user = get_user_model().objects.create(**newuser)
                otp.delete()

                # group_details.user_set.add(create_user)
                # user_util.log_account_activity(
                #     create_user, create_user, "Account Creation",
                #     "USER CREATED")
                

                return Response("success", status=status.HTTP_200_OK)

        else:
            return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(methods=["POST"],
            detail=False,
            url_path="reset-user-password",
            url_name="reset-user-password")
    def reset_user_password(self, request):
        """
        Resets specific user password to default ie username. payload['user_id']
        """
        payload = request.data
        email = request.data.get('email')

        if email is None:
            return Response({"details": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            email = payload['email']
            try:
                user_details = get_user_model().objects.get(email=email)
            except (ValidationError, ObjectDoesNotExist):
                return Response({'details': 'User does not exist'}, status=status.HTTP_400_BAD_REQUEST)

            new_password = user_util.password_generator()
            hashed_password = make_password(new_password)
            user_details.password = hashed_password
            user_details.save()

            subject = "Access Details [PSMDQS-AKHK]"
            message = f"\
                            Dear {user_details.first_name}, \n\
                            Your email is {user_details.email}\n\
                            Your password is: {new_password}\n\
                            If you encounter any challenge while navigating the platform, please let us know.\
                        "
            # mailgun_general.send_mail(user_details.first_name,user_details.email,subject,message)
            send_mail(subject, message, 'notification@akhskenya.org',[user_details.email] )

            if not settings.DEBUG:
                new_password = '<REDACTED>'
            
            user_util.log_account_activity(
                user_details, user_details, "Password Reset", "Password Reset Executed")
            return Response(f"Password Reset Successful. Pass: {new_password}", status=status.HTTP_200_OK)

    @action(methods=["GET"],
            detail=False,
            url_path="departments",
            url_name="departments")
    def department(self, request):
        try:

            departments = models.SRRSDepartment.objects.all().order_by('name')
            departments = serializers.SlimFetchSRRSDepartmentSerializer(departments,many=True).data
            return Response(departments, status=status.HTTP_200_OK)
        
        except Exception as e:
            print(e)
            return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
        
class AccountManagementViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = models.User.objects.all().order_by('id')
    serializer_class = serializers.SystemUsersSerializer
    search_fields = ['id', ]

    def get_queryset(self):
        return []

    @action(methods=["POST"], detail=False, url_path="change-password", url_name="change-password")
    def change_password(self, request):
        """
            Enables user to change password. Payload:  (new_password,confirm_password, current_password)
        """
        authenticated_user = request.user
        payload = request.data

        serializer = serializers.PasswordChangeSerializer(
            data=payload, many=False)
        if serializer.is_valid():
            with transaction.atomic():
                new_password = payload['new_password']
                confirm_password = payload['confirm_password']
                current_password = payload['current_password']
                password_min_length = 8

                string_check= re.compile('[-@_!#$%^&*()<>?/\|}{~:]') 

                # if(string_check.search(new_password) == None): 
                #     return Response({'details':
                #                      'Password Must contain a special character'},
                #                     status=status.HTTP_400_BAD_REQUEST)

                # if not any(char.isupper() for char in new_password):
                #     return Response({'details':
                #                      'Password must contain at least 1 uppercase letter'},
                #                     status=status.HTTP_400_BAD_REQUEST)

                if len(new_password) < password_min_length:
                    return Response({'details':
                                     'Password Must be at least 8 characters'},
                                    status=status.HTTP_400_BAD_REQUEST)

                # if not any(char.isdigit() for char in new_password):
                #     return Response({'details':
                #                      'Password must contain at least 1 digit'},
                #                     status=status.HTTP_400_BAD_REQUEST)
                                    
                # if not any(char.isalpha() for char in new_password):
                #     return Response({'details':
                #                      'Password must contain at least 1 letter'},
                #                     status=status.HTTP_400_BAD_REQUEST)
                try:
                    user_details = get_user_model().objects.get(id=authenticated_user.id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'User does not exist'}, status=status.HTTP_400_BAD_REQUEST)

                # check if new password matches current password
                encoded = user_details.password
                check_pass = check_password(new_password, encoded)
                if check_pass:
                    return Response({'details': 'New password should not be the same as old passwords'}, status=status.HTTP_400_BAD_REQUEST)


                if new_password != confirm_password:
                    return Response({"details": "Passwords Do Not Match"}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                is_current_password = authenticated_user.check_password(
                    current_password)
                if is_current_password is False:
                    return Response({"details": "Invalid Current Password"}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    user_util.log_account_activity(
                        authenticated_user, user_details, "Password Change", "Password Change Executed")
                    existing_password = authenticated_user.password
                    user_details.is_defaultpassword = False
                    new_password_hash = make_password(new_password)
                    user_details.password = new_password_hash
                    user_details.last_password_reset = datetime.now()
                    user_details.save()
                    return Response("Password Changed Successfully", status=status.HTTP_200_OK)
        else:
            return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


    @action(methods=["GET"], detail=False, url_path="list-users-with-role", url_name="list-users-with-role")
    def list_users_with_role(self, request):
        """
        Gets all users with a specific role. Payload: (role_name)
        """
        authenticated_user = request.user
        role_name = request.query_params.get('role_name')
        if role_name is None:
            return Response({'details': 'Role is Required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            role = Group.objects.get(name=role_name)
        except (ValidationError, ObjectDoesNotExist):
            return Response({'details': 'Role does not exist'}, status=status.HTTP_400_BAD_REQUEST)
        selected_users = get_user_model().objects.filter(groups__name=role.name).order_by('first_name')
        user_info = serializers.UsersSerializer(selected_users, many=True)
        return Response(user_info.data, status=status.HTTP_200_OK)
    

    @action(methods=["GET"], detail=False, url_path="get-account-activity", url_name="get-account-activity")
    def get_account_activity(self, request):
        """
        Gets account activity of a user. Payload: (account_id)
        """
        authenticated_user = request.user
        account_id = request.query_params.get('account_id')
        if account_id is None:
            return Response({'details': 'Account ID is Required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            account_instance = get_user_model().objects.get(id=account_id)
        except (ValidationError, ObjectDoesNotExist):
            return Response({'details': 'Account does not exist'}, status=status.HTTP_400_BAD_REQUEST)
        selected_records = []
        if hasattr(account_instance, 'user_account_activity'):
            selected_records = account_instance.user_account_activity.all()
        user_info = serializers.AccountActivitySerializer(
            selected_records, many=True)
        return Response(user_info.data, status=status.HTTP_200_OK)
    

    @action(methods=["GET"], detail=False, url_path="get-account-activity-detail", url_name="get-account-activity-detail")
    def get_account_activity_detail(self, request):
        """
        Gets single account activity detail information of a user. Payload: (request_id)
        """
        authenticated_user = request.user
        request_id = request.query_params.get('request_id')
        if request_id is None:
            return Response({'details': 'Request ID is Required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            account_activity_instance = models.AccountActivity.objects.get(
                id=request_id)
        except (ValidationError, ObjectDoesNotExist):
            return Response({'details': 'Request does not exist'}, status=status.HTTP_400_BAD_REQUEST)
        account_info = serializers.AccountActivityDetailSerializer(
            account_activity_instance, many=False)
        return Response(account_info.data, status=status.HTTP_200_OK)
    

    @action(methods=["GET"], detail=False, url_path="list-roles", url_name="list-roles")
    def list_roles(self, request):
        """
        Gets all available roles 
        """
        authenticated_user = request.user
        role = Group.objects.all()
        record_info = serializers.RoleSerializer(role, many=True)
        return Response(record_info.data, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=False, url_path="list-user-roles", url_name="list-user-roles")
    def list_user_roles(self, request):
        """
        Gets roles for a logged in user.
        """
        authenticated_user = request.user
        role = user_util.fetchusergroups(authenticated_user.id)

        rolename = {
            "group_name": role
        }
        return Response(rolename, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=False, url_path="get-user-details", url_name="get-user-details")
    def get_user_details(self, request):
        """
        Gets specific user details. Payload: (user_id)
        """
        authenticated_user = request.user
        user_id = request.query_params.get('user_id')
        if user_id is None:
            return Response({'details': 'Invalid Filter Criteria'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_details = get_user_model().objects.get(id=user_id)
        except (ValidationError, ObjectDoesNotExist):
            return Response({'details': 'User does not exist'}, status=status.HTTP_400_BAD_REQUEST) 
    
        user_info = serializers.UsersSerializer(user_details, many=False)
        return Response(user_info.data, status=status.HTTP_200_OK)



    @action(methods=["GET"], detail=False, url_path="filter-by-username", url_name="filter-by-username")
    def filter_by_username(self, request):
        """
        searches User by username: Payload ('username')
        """
        authenticated_user = request.user
        username = request.query_params.get('username')
        # if username is None:
        #     return Response({'details': 'Invalid Filter Criteria'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            if username :
                user_details = get_user_model().objects.filter(Q(email__icontains=username) | Q(first_name__icontains=username) | Q(last_name__icontains=username)).order_by('first_name')
            elif username is None or not username:
                user_details = get_user_model().objects.all().order_by('first_name')
                # print(len(user_details))
        except (ValidationError, ObjectDoesNotExist):
            return Response({'details': 'User does not exist'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_info = serializers.UsersSerializer(user_details, many=True)
        return Response(user_info.data, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=False, url_path="get-profile-details", url_name="get-profile-details")
    def get_profile_details(self, request):
        """
        Retrievs logged in user profile
        """
        serializing = request.query_params.get('serializer')
        authenticated_user = request.user
        payload = request.data
        try:
            user_details = get_user_model().objects.get(id=authenticated_user.id)
        except (ValidationError, ObjectDoesNotExist):
            return Response({'details': 'User does not exist'}, status=status.HTTP_400_BAD_REQUEST)
        if serializing == 'slim':
            user_info = serializers.SlimUsersSerializer(user_details, many=False)
        else:
            user_info = serializers.UsersSerializer(user_details, many=False)
        return Response(user_info.data, status=status.HTTP_200_OK)

class ICTSupportViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = models.User.objects.all().order_by('id')
    serializer_class = serializers.SystemUsersSerializer
    search_fields = ['id', ]

    def get_queryset(self):
        return []

    @action(methods=["POST"],
            detail=False,
            url_path="reset-user-password",
            url_name="reset-user-password")
    def reset_user_password(self, request):
        """
        Resets specific user password to default ie username. payload['user_id']
        """
        authenticated_user = request.user
        payload = request.data
        serializer = serializers.UserIdSerializer(data=payload, many=False)
        if serializer.is_valid():
            with transaction.atomic():
                userid = payload['user_id']
                try:
                    user_details = get_user_model().objects.get(id=userid)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'User does not exist'}, status=status.HTTP_400_BAD_REQUEST)

                new_password = user_util.password_generator()
                hashed_password = make_password(new_password)
                user_details.password = hashed_password
                user_details.save()

                subject = "Access Details [PSMDQS-AKHK]"
                message = f"Dear {user_details.first_name}, \nYour email is {user_details.email}\nYour password is: {new_password}\nIf you encounter any challenge while navigating the platform, please let us know."
                # mailgun_general.send_mail(user_details.first_name,user_details.email,subject,message)
                send_mail(subject, message, 'notification@akhskenya.org',[user_details.email] )

                if not settings.DEBUG:
                    new_password = '<REDACTED>'
                
                user_util.log_account_activity(
                    authenticated_user, user_details, "Password Reset", "Password Reset Executed")
                return Response(f"Password Reset Successful. Pass: {new_password}", status=status.HTTP_200_OK)
        else:
            return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST"], detail=False, url_path="swap-user-department", url_name="swap-user-department")
    def swap_user_department(self, request):
        """
        Switches user from one department to another. payload['department_id','user_id']
        """
        authenticated_user = request.user
        payload = request.data
        serializer = serializers.SwapUserDepartmentSerializer(
            data=payload, many=False)
        if serializer.is_valid():
            with transaction.atomic():
                department_id = payload['department_id']
                user_id = payload['user_id']
                app = request.query_params.get('app')
                try:
                    user_details = get_user_model().objects.get(id=user_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'User does not exist'}, status=status.HTTP_400_BAD_REQUEST)
                try:
                    if not app:
                        department_details = models.Department.objects.get(
                            id=department_id)
                        user_details.department = department_details
                    else:
                        if app == 'srrs':
                            department_details = models.SRRSDepartment.objects.get(
                            id=department_id)
                            user_details.srrs_department = department_details
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Department does not exist'}, status=status.HTTP_400_BAD_REQUEST)
                
                user_details.save()
                user_util.log_account_activity(
                    authenticated_user, user_details, "Department Swap", "Department Was Swapped")
                return Response("Department Successfully Changed", status=status.HTTP_200_OK)
        else:
            return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST"],
            detail=False,
            url_path="edit-user",
            url_name="edit-user")
    def edit_user(self, request):
        """
        Updates user details. payload['id_number','first_name','last_name','account_id']
        """
        payload = json.loads(request.data.get('payload'))
        authenticated_user = request.user
        serializer = serializers.EditUserSerializer(data=payload, many=False)
        if serializer.is_valid():
            # id_number = payload['id_number']
            first_name = payload['first_name']
            last_name = payload['last_name']
            account_id = payload['account_id']
            # phone_number = payload['phone_number']
            email = payload['email']


            email_exists = get_user_model().objects.filter(email=email).exists()
            if email_exists:
                return Response({"details": "Email already exists 😒"}, status=status.HTTP_400_BAD_REQUEST)

                            
            try:
                record_instance = get_user_model().objects.get(id=account_id)
            except (ValidationError, ObjectDoesNotExist):
                return Response(
                    {'details': 'User does not exist'},
                    status=status.HTTP_400_BAD_REQUEST)

                               

            record_instance.first_name = first_name
            record_instance.last_name = last_name
            record_instance.email = email

            record_instance.save()

            user_util.log_account_activity(
                        authenticated_user, authenticated_user, "Updated Profile",
                        "PROFILE UPDATION")

            return Response("Successfully Updated",
                            status=status.HTTP_200_OK)

        else:
            return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST"],
            detail=False,
            url_path="award-role",
            url_name="award-role")
    def award_role(self, request):
        """
        Gives user a new role. payload['role_id','account_id']
        """
        payload = request.data
        authenticated_user = request.user
        serializer = serializers.ManageRoleSerializer(data=payload, many=False)
        if serializer.is_valid():
            role_id = payload['role_id']
            account_id = payload['account_id']
            if not role_id:
                return Response(
                    {'details': 'Select atleast one role'},
                    status=status.HTTP_400_BAD_REQUEST)

            try:
                record_instance = get_user_model().objects.get(id=account_id)
            except (ValidationError, ObjectDoesNotExist):
                return Response(
                    {'details': 'Invalid User'},
                    status=status.HTTP_400_BAD_REQUEST)
            group_names = []
            for assigned_role in role_id:
                group = Group.objects.get(id=assigned_role)
                group_names.append(group.name)

                record_instance.groups.add(group)

            user_util.log_account_activity(
                authenticated_user, record_instance, "Role Assignment",
                f"USER ASSIGNED ROLES {str(group_names)}")
            
            return Response("Successfully Updated",
                            status=status.HTTP_200_OK)

        else:
            return Response({"details": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST"],
            detail=False,
            url_path="revoke-role",
            url_name="revoke-role")
    def revoke_role(self, request):
        """
        Revokes a role assigned to a user. payload['role_id','account_id']
        """
        payload = request.data
        authenticated_user = request.user
        serializer = serializers.ManageRoleSerializer(data=payload, many=False)
        if serializer.is_valid():
            role_id = payload['role_id']
            account_id = payload['account_id']

            if not role_id:
                return Response(
                    {'details': 'Select at least one role'},
                    status=status.HTTP_400_BAD_REQUEST)

            try:
                record_instance = get_user_model().objects.get(id=account_id)
            except (ValidationError, ObjectDoesNotExist):
                return Response(
                    {'details': 'Invalid User'},
                    status=status.HTTP_400_BAD_REQUEST)
            
            group_names = []
            for assigned_role in role_id:
                group = Group.objects.get(id=assigned_role)
                group_names.append(group.name)
                record_instance.groups.remove(group)

            user_util.log_account_activity(
                authenticated_user, record_instance, "Role Revocation",
                f"USER REVOKED ROLES {str(group_names)}")
            
            return Response("Successfully Updated",
                            status=status.HTTP_200_OK)

        else:
            return Response({"details": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST"], detail=False, url_path="bulk-create-user", url_name="bulk-create-user")
    def upload(self, request):
        if request.method == "POST":

            formfiles = request.FILES
            if not formfiles:
                return Response({"details": "Please upload attachment"}, status=status.HTTP_400_BAD_REQUEST)

            def set_name(name):
                return name.split(' ',1)
            
            def set_department(name):
                try:
                    department_qs = models.SRRSDepartment.objects.filter(name__icontains=name)
                    return department_qs.first() if department_qs.exists() else None
                except (ValidationError, ObjectDoesNotExist):
                    return None
                
            def set_sub_department(name):
                name = set_name(name)[0]
                try:
                    resp_qs = models.SubDepartment.objects.filter(name__icontains=name)
                    return resp_qs.first() if resp_qs.exists() else None
                except (ValidationError, ObjectDoesNotExist):
                    return None
                
            def set_ohc(name):
                name = set_name(name)[0]
                try:
                    resp_qs = models.OHC.objects.filter(name__icontains=name)
                    return resp_qs.first() if resp_qs.exists() else None
                except (ValidationError, ObjectDoesNotExist):
                    return None
            
            f = request.FILES.getlist('documents')[0]
            if f.name.endswith('.csv'):

                emails = list(get_user_model().objects.all().values_list('email', flat=True))

                # decoded_file = f.read().decode('utf-8')
                decoded_file = f.read().decode('windows-1254')
                csv_data = csv.reader(decoded_file.splitlines(), delimiter=',')

                # Skip the header row
                next(csv_data)

                # try:
                #     for row in csv_data:
                #         email = row[7].strip().lower()
                #         cadre=row[6].strip()
                #         employee_no=row[0].strip()
                #         if email in emails:
                #             user = get_user_model().objects.get(email=email)
                #             user.cadre = cadre
                #             user.employee_no = employee_no
                #             user.save()
                #         continue
                # except Exception as e:
                #     logger.error(e)

                # users = [
                #     models.User(
                #         employee_no=row[0].strip(), 
                #         first_name=set_name(row[1])[0].strip().capitalize(), 
                #         last_name=set_name(row[1])[1].strip().capitalize(), 
                #         email=row[7].strip().lower(), 
                #         srrs_department=set_department(row[2].strip()),
                #         sub_department=set_sub_department(row[4].strip()),
                #         ohc=set_ohc(row[3].strip()),
                #         staff_status=row[5].strip(),
                #         cadre=row[6].strip(),
                #         is_active=True,
                #         is_superuser=False,
                #         is_staff=False,
                #         is_suspended=False,
                #         password=make_password("welcome@123"),
                #     )
                #     for row in csv_data if row[7].strip().lower() not in emails
                # ]

                users = [
                    models.User(
                        first_name=set_name(row[0])[0].strip().capitalize(), 
                        last_name=set_name(row[0])[1].strip().capitalize(), 
                        email=row[2].strip().lower(), 
                        staff_status=row[1].strip(),
                        is_active=True,
                        is_superuser=False,
                        is_staff=False,
                        is_suspended=False,
                        password=make_password("welcome@123"),
                    )
                    for row in csv_data if row[2].strip().lower() not in emails
                ]

                newInstances = models.User.objects.bulk_create(users)

                try:
                    group_details = Group.objects.get(name="USER")
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Role does not exist'}, 
                                    status=status.HTTP_400_BAD_REQUEST)

                for instance in newInstances:
                    group_details.user_set.add(instance) 
                
                subject = "Training Platform Access Details"
                def set_message(instance):
                    message = f"Dear {instance.first_name}, \n\nYour email is: {instance.email}\nYour password is: welcome@123\nPlatform Link: http://172.20.0.42:8014/ \nIf you encounter any challenge while navigating the platform, please let us know.\n\nKind Regards\nICT-AKHK"
                    return message

                

                # mails = [
                #     models.Sendmail(
                #         email=[instance.email], 
                #         subject=subject,
                #         message=set_message(instance),
                #     )
                #     for instance in newInstances
                # ]
                # models.Sendmail.objects.bulk_create(mails)

                


                return Response('Data uploaded successfully', status=status.HTTP_200_OK)
            
            else:
                return Response({"details": "Please upload a CSV file."}, status=status.HTTP_400_BAD_REQUEST)
            

    @action(methods=["POST"], detail=False, url_path="create-user", url_name="create-user")
    def create_user(self, request):
        """
        Creates a new user in the system. payload['id_number','username','first_name','last_name','department_id','role_name']
        """
        payload = request.data
        authenticated_user = request.user
        app = request.query_params.get('app', None)

        serializer = serializers.UserDetailSerializer(data=payload, many=False)
        if serializer.is_valid():
            with transaction.atomic():
                first_name = payload['first_name'].capitalize()
                last_name = payload['last_name'].capitalize()
                email = payload['email'].lower()
                role_name = payload['role_name']
                department = payload['department_id']
                emailexists = get_user_model().objects.filter(email=email).exists()


                if emailexists:
                    return Response({'details': 'User With Credentials Already Exist'}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    group_details = Group.objects.get(id=role_name)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Role does not exist'}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    if not app:
                        department = models.Department.objects.get(id=department)
                    else:
                        if app == 'srrs':
                            department = models.SRRSDepartment.objects.get(id=department)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Department does not exist'}, status=status.HTTP_400_BAD_REQUEST)


                password = user_util.password_generator()

                hashed_pwd = make_password(password)
                newuser = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "is_active": True,
                    "is_superuser": False,
                    "is_staff": False,
                    "is_suspended": False,
                    "password": hashed_pwd,
                }

                if not app:
                    newuser.update({"department": department})
                else:
                    if app == 'srrs':
                        newuser.update({"srrs_department": department})

                        sub_department_id = payload['sub_department_id']
                        ohc_id = payload['ohc_id']

                        if sub_department_id:
                            sub_department = models.SubDepartment.objects.get(id=sub_department_id)
                            newuser.update({"sub_department": sub_department})

                        if ohc_id:
                            ohc = models.OHC.objects.get(id=ohc_id)
                            newuser.update({"ohc": ohc})



                create_user = get_user_model().objects.create(**newuser)
                group_details.user_set.add(create_user)



                subject = "Platform Access Details"
                message = f"Dear {first_name}, \nYour email is {email}\nYour password is: {password}\nIf you encounter any challenge while navigating the platform, please let us know.\n\nKind Regards\nAKHK-ICT"

                try:
                    send_mail(subject, message, 'notification@akhskenya.org', [email])
                except Exception as e:
                    logger.error(e)

                user_util.log_account_activity(
                    authenticated_user, create_user, "Account Creation",
                    "USER CREATED")
                
                if not settings.DEBUG:
                    password = '<REDACTED>'


                info = {
                    'success': 'User Created Successfully',
                    'password': password
                }
                return Response(info, status=status.HTTP_200_OK)

        else:
            return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(methods=["POST"], detail=False, url_path="update-user-profile", url_name="update-user-profile")
    def update_user_profile(self, request):

        payload = request.data

        serializer = serializers.UpdateUserProfileSerializer(data=payload, many=False)
        if serializer.is_valid():
            with transaction.atomic():
                cluster = payload['cluster']
                department = payload['department']
                ohc = payload.get('ohc') or None

                try:
                    department = models.SRRSDepartment.objects.get(id=department)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Department does not exist'}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    cluster = models.SubDepartment.objects.get(id=cluster)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Cluster does not exist'}, status=status.HTTP_400_BAD_REQUEST)
                
                if ohc:
                    try:
                        ohc = models.OHC.objects.get(id=ohc)
                    except (ValidationError, ObjectDoesNotExist):
                        return Response({'details': 'OHC does not exist'}, status=status.HTTP_400_BAD_REQUEST)
                    
                user = request.user
                user.srrs_department = department
                user.sub_department = cluster
                user.sub_department = cluster
                user.profile_updated = True
                user.ohc = ohc

                user.save()

                return Response('200', status=status.HTTP_200_OK)
        else:
            return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        

    @action(methods=["POST"], detail=False, url_path="suspend-user", url_name="suspend-user")
    def suspend_user(self, request):
        """
        Suspends a user. payload['user_id','remarks']
        """
        authenticated_user = request.user
        payload = request.data
        serializer = serializers.SuspendUserSerializer(
            data=payload, many=False)
        if serializer.is_valid():
            with transaction.atomic():
                user_id = payload['user_id']
                remarks = payload['remarks']
                try:
                    user_details = get_user_model().objects.get(id=user_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'User does not exist'}, status=status.HTTP_400_BAD_REQUEST)

                user_details.is_suspended = True
                user_util.log_account_activity(
                    authenticated_user, user_details, "Account Suspended", remarks)
                user_details.save()
                return Response("Account Successfully Changed", status=status.HTTP_200_OK)
        else:
            return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST"], detail=False, url_path="un-suspend-user", url_name="un-suspend-user")
    def un_suspend_user(self, request):
        """
        Unsuspends a user. payload['user_id','remarks']
        """
        authenticated_user = request.user
        payload = request.data
        serializer = serializers.SuspendUserSerializer(
            data=payload, many=False)
        if serializer.is_valid():
            user_id = payload['user_id']
            remarks = payload['remarks']
            with transaction.atomic():
                try:
                    user_details = get_user_model().objects.get(id=user_id)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'User does not exist'}, status=status.HTTP_400_BAD_REQUEST)

                user_details.is_suspended = False
                user_util.log_account_activity(
                    authenticated_user, user_details, "Account UnSuspended", remarks)
                user_details.save()
                return Response("Account Unsuspended", status=status.HTTP_200_OK)
        else:
            return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(methods=["POST"], detail=False, url_path="invitation-link", url_name="invitation-link")
    def invitation_link(self, request):

        authenticated_user = request.user
        payload = request.data

        serializer = serializers.InvitationLinkSerializer(
            data=payload, many=False)
        if not serializer.is_valid():
            return Response({"details": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        email = payload['email']

        characters = string.digits
        otp = ''.join(random.choice(characters) for i in range(6))
        link = f"http://localhost:4200/authentication/create-account/{otp}"

        with transaction.atomic():
            models.OTP.objects.create(otp=otp)

            # Notify User
            subject = f"Platform Invitation"
            message = f"Hello, \n\nUse the below invitation link to join\n{link}\n\nRegards,\nAKHK"

            try:
                mail = {
                    "email" : [email], 
                    "subject" : subject,
                    "message" : message,
                }

                models.Sendmail.objects.create(**mail)
                send_mail(subject, message, 'notification@akhskenya.org', [email])

            except Exception as e:
                logger.error(e)

            user_util.log_account_activity(
                authenticated_user, authenticated_user, "Invitation link", "Link generated")

            return Response("200", status=status.HTTP_200_OK)
        


class DepartmentViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = models.Department.objects.all().order_by('id')
    serializer_class = serializers.CreateDepartmentSerializer
    search_fields = ['id', ]

    def get_queryset(self):
        return []

    @action(methods=["POST", "GET", "PUT"],
            detail=False,
            url_path="department",
            url_name="department")
    def department(self, request):
        roles = user_util.fetchusergroups(request.user.id)
        if request.method == "POST":
            payload = request.data
            serializer = serializers.GeneralNameSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                name = payload['name']
                slt = payload.get('slt')
                hod = payload.get('hod')

                with transaction.atomic():
                    raw = {
                        "name": name
                    }

                    if slt:
                        try:
                            slt = models.Slt.objects.get(id=slt)
                        except Exception as e:
                            return Response({"details": "Unknown SLT"}, status=status.HTTP_400_BAD_REQUEST)
                        
                        roles = user_util.fetchusergroups(str(slt.lead.id))
                        if 'SLT' not in roles:
                            assign_role = user_util.award_role('SLT', str(slt.lead.id))

                            if not assign_role:
                                return Response({"details": "Unable to assign role SLT"}, status=status.HTTP_400_BAD_REQUEST)
                        
                        raw.update({"slt": slt})

                    if hod:
                        try:
                            hod = models.User.objects.get(id=hod)
                        except Exception as e:
                            return Response({"details": "Unknown HOD"}, status=status.HTTP_400_BAD_REQUEST)
                        
                        roles = user_util.fetchusergroups(str(hod.id))
                        if 'HOD' not in roles:
                            assign_role = user_util.award_role('HOD', str(hod.id))

                            if not assign_role:
                                return Response({"details": "Unable to assign role HOD"}, status=status.HTTP_400_BAD_REQUEST)
                        
                        raw.update({"hod": hod})

                    models.Department.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":
            payload = request.data

            serializer = serializers.UpdateDepartmentSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                dept_id = payload['request_id']
                name = payload['name']
                slt = payload.get('slt')
                hod = payload.get('hod')

                try:
                    dept = models.Department.objects.get(id=dept_id)
                except Exception as e:
                    logger.error(e)
                    return Response({"details": "Unknown Department"}, status=status.HTTP_400_BAD_REQUEST)

                if slt:
                    try:
                        slt = models.Slt.objects.get(id=slt)
                    except Exception as e:
                        return Response({"details": "Unknown SLT"}, status=status.HTTP_400_BAD_REQUEST)
                    
                    if dept.slt and dept.slt.id != slt.id:
                        user_util.revoke_role('SLT', str(dept.slt.lead.id))

                    roles = user_util.fetchusergroups(str(slt.lead.id))
                    if 'SLT' not in roles:
                        assign_role = user_util.award_role('SLT', str(slt.lead.id))

                        if not assign_role:
                            return Response({"details": "Unable to assign role SLT"}, status=status.HTTP_400_BAD_REQUEST)
                        
                if hod:
                    try:
                        hod = models.User.objects.get(id=hod)
                    except Exception as e:
                        return Response({"details": "Unknown HOD"}, status=status.HTTP_400_BAD_REQUEST)
                    
                    if dept.hod and dept.hod.id != hod.id:
                        user_util.revoke_role('HOD', str(dept.hod.id))
                    
                    roles = user_util.fetchusergroups(str(hod.id))
                    if 'HOD' not in roles:
                        assign_role = user_util.award_role('HOD', str(hod.id))

                        if not assign_role:
                            return Response({"details": "Unable to assign role HOD"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    try:
                        
                        dept.name = name
                        
                        if slt:
                            dept.slt = slt 
                        if hod:
                            dept.hod = hod 

                        dept.save()
                        
                    except (ValidationError, ObjectDoesNotExist):
                        return Response({"details": "Unknown department!"}, status=status.HTTP_400_BAD_REQUEST)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    department = models.Department.objects.get(Q(id=request_id))
                    department = serializers.FetchDepartmentSerializer(department,many=False).data
                    return Response(department, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown department!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:

                    if 'USER' in roles:
                        
                        department = request.user.department
                        if department:
                            department = serializers.FetchDepartmentSerializer(department,many=False).data
                            return Response([department], status=status.HTTP_200_OK)
                        else:
                            departments = models.Department.objects.all().order_by('name')
                            departments = serializers.FetchDepartmentSerializer(departments,many=True).data
                            return Response(departments, status=status.HTTP_200_OK)
                    else:
                        departments = models.Department.objects.all().order_by('name')
                        departments = serializers.FetchDepartmentSerializer(departments,many=True).data
                        return Response(departments, status=status.HTTP_200_OK)
                    
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)



    @action(methods=["POST"],
            detail=False,
            url_path="upload",
            url_name="upload")
    def upload(self, request):
        if request.method == "POST":
            formfiles = request.FILES
            if not formfiles:
                return Response({"details": "Please upload attachment"}, status=status.HTTP_400_BAD_REQUEST)
            
            f = request.FILES.getlist('documents')[0]
            if f.name.endswith('.csv'):
                decoded_file = f.read().decode('utf-8')
                csv_data = csv.reader(decoded_file.splitlines(), delimiter=',')
                # Skip the header row
                next(csv_data)
                departments = [models.Department(name=row[0].strip()) for row in csv_data]
                models.Department.objects.bulk_create(departments)
                return Response('Data uploaded successfully', status=status.HTTP_200_OK)
            else:
                return Response({"details": "Please upload a CSV file."}, status=status.HTTP_400_BAD_REQUEST)

class SRRSDepartmentViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]

    def get_queryset(self):
        return []

    @action(methods=["POST", "GET", "PUT"],
            detail=False,
            url_path="department",
            url_name="department")
    def srrs_department(self, request):
        roles = user_util.fetchusergroups(request.user.id)
        if request.method == "POST":
            payload = request.data
            serializer = serializers.GeneralNameSerializer(
                data=payload, many=False)
            if serializer.is_valid():
                name = payload['name']
                slt_id = payload.get('slt')
                hod_id = payload.get('hod')
                hr_partner_id = payload.get('hr_partner')

                with transaction.atomic():
                    raw = {
                        "name": name
                    }

                    if slt_id:
                        try:
                            slt = models.User.objects.get(id=slt_id)
                        except Exception as e:
                            return Response({"details": "Unknown SLT"}, status=status.HTTP_400_BAD_REQUEST)
                        
                        roles = user_util.fetchusergroups(slt_id)
                        if 'SLT' not in roles:
                            assign_role = user_util.award_role('SLT', slt_id)

                            if not assign_role:
                                return Response({"details": "Unable to assign role SLT"}, status=status.HTTP_400_BAD_REQUEST)
                        
                        raw.update({"slt": slt})

                    if hr_partner_id:
                        try:
                            hr_partner = models.User.objects.get(id=hr_partner_id)
                        except Exception as e:
                            return Response({"details": "Unknown HR Partner"}, status=status.HTTP_400_BAD_REQUEST)
                        
                        roles = user_util.fetchusergroups(hr_partner_id)
                        if 'HR' not in roles:
                            assign_role = user_util.award_role('HR', hr_partner_id)

                            if not assign_role:
                                return Response({"details": "Unable to assign role HR"}, status=status.HTTP_400_BAD_REQUEST)
                        
                        raw.update({"hr_partner": hr_partner})

                    
                    departmentInstance = models.SRRSDepartment.objects.create(**raw)

                    if hod_id:
                        # delete existing hods
                        models.Hods.objects.filter(department=departmentInstance).delete()

                        try:
                            hods = models.User.objects.filter(id__in=hod_id)
                        except Exception as e:
                            return Response({"details": "Unknown HODs"}, status=status.HTTP_400_BAD_REQUEST)
                        
                        for hod in hods:
                            roles = user_util.fetchusergroups(str(hod.id))
                            if 'HOD' not in roles:
                                assign_role = user_util.award_role('HOD', str(hod.id))

                                if not assign_role:
                                    return Response({"details": "Unable to assign role HOD"}, status=status.HTTP_400_BAD_REQUEST)
                        
                            raw = {
                                    "hod": hod,
                                    "department": departmentInstance
                                }
                            
                            models.Hods.objects.create(**raw)

                            # update hod department
                            hod.srrs_department = departmentInstance
                            hod.save()


                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":
            payload = request.data

            serializer = serializers.UpdateDepartmentSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                dept_id = payload['request_id']
                name = payload['name']
                slt_id = payload.get('slt')
                hod_id = payload.get('hod')
                hr_partner_id = payload.get('hr_partner')

                slt = None
                hr_partner = None

                try:
                    dept = models.SRRSDepartment.objects.get(id=dept_id)
                except Exception as e:
                    logger.error(e)
                    return Response({"details": "Unknown SRRS Department"}, status=status.HTTP_400_BAD_REQUEST)

                if slt_id:
                    try:
                        slt = models.User.objects.get(id=slt_id)
                    except Exception as e:
                        return Response({"details": "Unknown SLT"}, status=status.HTTP_400_BAD_REQUEST)
                    
                    if dept.slt and dept.slt.id != slt.id:
                        user_util.revoke_role('SLT', str(dept.slt.id))

                    roles = user_util.fetchusergroups(slt_id)
                    if 'SLT' not in roles:
                        assign_role = user_util.award_role('SLT', slt_id)

                        if not assign_role:
                            return Response({"details": "Unable to assign role SLT"}, status=status.HTTP_400_BAD_REQUEST)
                        
                if hr_partner_id:
                    try:
                        hr_partner = models.User.objects.get(id=hr_partner_id)
                    except Exception as e:
                        return Response({"details": "Unknown HR Partner"}, status=status.HTTP_400_BAD_REQUEST)
                    
                    roles = user_util.fetchusergroups(hr_partner_id)
                    if 'HR' not in roles:
                        assign_role = user_util.award_role('HR', hr_partner_id)

                        if not assign_role:
                            return Response({"details": "Unable to assign role HR"}, status=status.HTTP_400_BAD_REQUEST)
                        

                with transaction.atomic():
                    try:
                        
                        dept.name = name
                        
                        if slt:
                            dept.slt = slt 

                        if hr_partner:
                            dept.hr_partner = hr_partner 

                        dept.save()
                        
                    except (ValidationError, ObjectDoesNotExist):
                        return Response({"details": "Unknown department!"}, status=status.HTTP_400_BAD_REQUEST)
                    
                    if hod_id:
                        # delete existing hods
                        currentHods = models.Hods.objects.filter(department=dept)
                        for hod in currentHods:
                            user_util.revoke_role('HOD', str(hod.id))
                        currentHods.delete()

                        try:
                            hods = models.User.objects.filter(id__in=hod_id)
                        except Exception as e:
                            return Response({"details": "Unknown HODs"}, status=status.HTTP_400_BAD_REQUEST)
                        
                        for hod in hods:
                            roles = user_util.fetchusergroups(str(hod.id))
                            if 'HOD' not in roles:
                                assign_role = user_util.award_role('HOD', str(hod.id))

                                if not assign_role:
                                    return Response({"details": "Unable to assign role HOD"}, status=status.HTTP_400_BAD_REQUEST)
                        
                            raw = {
                                    "hod": hod,
                                    "department": dept
                                }
                            
                            models.Hods.objects.create(**raw)

                            # update hod department
                            hod.srrs_department = dept
                            hod.save()

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    department = models.SRRSDepartment.objects.get(Q(id=request_id))
                    department = serializers.FetchSRRSDepartmentSerializer(department,many=False).data
                    return Response(department, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown department!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:

                    # if 'USER' in roles:
                    #     department = request.user.srrs_department
                    #     department = serializers.FetchSRRSDepartmentSerializer(department,many=False).data
                    #     return Response([department], status=status.HTTP_200_OK)
                    # else:
                    departments = models.SRRSDepartment.objects.all().order_by('name')
                    departments = serializers.FetchSRRSDepartmentSerializer(departments,many=True).data
                    return Response(departments, status=status.HTTP_200_OK)
                    
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)



    @action(methods=["POST"],
            detail=False,
            url_path="upload",
            url_name="upload")
    def upload(self, request):
        if request.method == "POST":
            formfiles = request.FILES
            if not formfiles:
                return Response({"details": "Please upload attachment"}, status=status.HTTP_400_BAD_REQUEST)
            
            f = request.FILES.getlist('documents')[0]
            if f.name.endswith('.csv'):
                decoded_file = f.read().decode('utf-8')
                csv_data = csv.reader(decoded_file.splitlines(), delimiter=',')
                # Skip the header row
                next(csv_data)
                departments = [models.Department(name=row[0].strip()) for row in csv_data if row[0]]
                models.SRRSDepartment.objects.bulk_create(departments)
                return Response('Data uploaded successfully', status=status.HTTP_200_OK)
            else:
                return Response({"details": "Please upload a CSV file."}, status=status.HTTP_400_BAD_REQUEST)
            
    @action(methods=["POST", "GET", "PUT"],
            detail=False,
            url_path="sub-departments",
            url_name="sub-departments")
    def sub_department(self, request):
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

                    models.SubDepartment.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":
            payload = request.data

            serializer = serializers.UpdateDepartmentSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                dept_id = payload['request_id']
                name = payload['name']

                try:
                    dept = models.SubDepartment.objects.get(id=dept_id)
                except Exception as e:
                    logger.error(e)
                    return Response({"details": "Unknown Sub Department"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    dept.name = name
                    dept.save()

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    department = models.SubDepartment.objects.get(Q(id=request_id))
                    department = serializers.FetchSubDepartmentSerializer(department,many=False).data
                    return Response(department, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown department!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    departments = models.SubDepartment.objects.filter(is_deleted=False).order_by('name')
                    departments = serializers.FetchSubDepartmentSerializer(departments,many=True).data
                    return Response(departments, status=status.HTTP_200_OK)
                    
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
                

    @action(methods=["POST", "GET", "PUT"],
            detail=False,
            url_path="ohc",
            url_name="ohc")
    def ohc(self, request):
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

                    models.OHC.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":
            payload = request.data

            serializer = serializers.UpdateDepartmentSerializer(
                data=payload, many=False)
            
            if serializer.is_valid():
                dept_id = payload['request_id']
                name = payload['name']

                try:
                    dept = models.OHC.objects.get(id=dept_id)
                except Exception as e:
                    logger.error(e)
                    return Response({"details": "Unknown Sub Department"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    dept.name = name
                    dept.save()

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    ohc = models.OHC.objects.get(Q(id=request_id))
                    ohc = serializers.FetchOHCSerializer(ohc,many=False).data
                    return Response(ohc, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown ohc!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    ohcs = models.OHC.objects.filter(is_deleted=False).order_by('name')
                    ohcs = serializers.FetchOHCSerializer(ohcs,many=True).data
                    return Response(ohcs, status=status.HTTP_200_OK)
                    
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request"}, status=status.HTTP_400_BAD_REQUEST)
            
class SltViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ['id', ]

    def get_queryset(self):
        return []

    @action(methods=["POST", "GET", "PUT"],
            detail=False,
            url_path="slt",
            url_name="slt")
    def slt(self, request):
        roles = user_util.fetchusergroups(request.user.id)
        if request.method == "POST":
            payload = request.data
            serializer = serializers.CreateSltSerializer(
                data=payload, many=False)
            if serializer.is_valid():

                name = payload['name']
                lead = payload['lead']

                try:
                    lead = models.User.objects.get(id=lead)
                except Exception as e:
                    return Response({"details": "Unknown lead !"}, status=status.HTTP_400_BAD_REQUEST)


                with transaction.atomic():
                    raw = {
                        "name": name,
                        "lead": lead,
                    }
                    models.Slt.objects.create(**raw)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "PUT":
            payload = request.data
            serializer = serializers.UpdateSltSerializer(
                data=payload, many=False)
            if serializer.is_valid():

                slt_id = payload['request_id']
                name = payload['name']
                lead = payload['lead']

                try:
                    lead = models.User.objects.get(id=lead)
                except Exception as e:
                    return Response({"details": "Unknown lead !"}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    try:
                        instance = models.Slt.objects.get(id=slt_id)
                        instance.name = name
                        instance.lead = lead
                        instance.save()
                    except (ValidationError, ObjectDoesNotExist):
                        return Response({"details": "Unknown department!"}, status=status.HTTP_400_BAD_REQUEST)

                    return Response("Success", status=status.HTTP_200_OK)
            else:
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        elif request.method == "GET":
            request_id = request.query_params.get('request_id')
            if request_id:
                try:
                    resp = models.Slt.objects.get(Q(id=request_id))
                    resp = serializers.FetchSltSerializer(resp,many=False).data
                    return Response(resp, status=status.HTTP_200_OK)
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Unknown Slt!"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                try:

                    if 'USER' in roles:
                        resp = request.user.department.slt
                        resp = serializers.FetchSltSerializer(resp,many=False).data
                        return Response([resp], status=status.HTTP_200_OK)
                    else:
                        resp = models.Slt.objects.all().order_by('name')
                        resp = serializers.FetchSltSerializer(resp,many=True).data
                        return Response(resp, status=status.HTTP_200_OK)
                    
                except (ValidationError, ObjectDoesNotExist):
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)
                
                except Exception as e:
                    print(e)
                    return Response({"details": "Cannot complete request at this time!"}, status=status.HTTP_400_BAD_REQUEST)



    @action(methods=["POST"],
            detail=False,
            url_path="upload",
            url_name="upload")
    def upload(self, request):
        if request.method == "POST":
            formfiles = request.FILES
            if not formfiles:
                return Response({"details": "Please upload attachment"}, status=status.HTTP_400_BAD_REQUEST)
            
            f = request.FILES.getlist('documents')[0]
            if f.name.endswith('.csv'):
                decoded_file = f.read().decode('utf-8')
                csv_data = csv.reader(decoded_file.splitlines(), delimiter=',')
                # Skip the header row
                next(csv_data)
                slts = [models.Slt(name=row[0].strip()) for row in csv_data]
                models.Slt.objects.bulk_create(slts)
                return Response('Data uploaded successfully', status=status.HTTP_200_OK)
            else:
                return Response({"details": "Please upload a CSV file."}, status=status.HTTP_400_BAD_REQUEST)