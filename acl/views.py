import re
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
        username = request.data.get('username')
        password = request.data.get('password')
        if username is None:
            return Response({"details": "Username is required"}, status=status.HTTP_400_BAD_REQUEST)
        if password is None:
            return Response({"details": "Password is required"}, status=status.HTTP_400_BAD_REQUEST)
        input_username = payload['username']
        input_password = payload['password']
        is_authenticated = authenticate(
            username=input_username, password=input_password)

        if is_authenticated: 

            is_suspended = is_authenticated.is_suspended
            if is_suspended is True or is_suspended is None:
                return Response({"details": "Your Account Has Been Suspended,Liase with your supervisor"}, status=status.HTTP_400_BAD_REQUEST)
            else:

                payload = {
                    'id': str(is_authenticated.id),
                    'username': is_authenticated.username,
                    'staff': is_authenticated.is_staff,
                    'exp': datetime.utcnow() + timedelta(seconds=settings.TOKEN_EXPIRY),
                    'iat': datetime.utcnow()
                }
                token = jwt.encode(payload, settings.TOKEN_SECRET_CODE)
                response_info = {
                    "token": token,
                }
                return Response(response_info, status=status.HTTP_200_OK)
        else:
            return Response({"details": "Invalid Username / Password"}, status=status.HTTP_400_BAD_REQUEST)
        
        
    @action(methods=["POST"], detail=False, url_path="create-account", url_name="create-account")
    def create_account(self, request):
        payload = request.data
        # print(payload)
        serializer = serializers.CreateUserSerializer(data=payload, many=False)
        if serializer.is_valid():
            with transaction.atomic():
                email = payload['email']
                first_name = payload['first_name']
                last_name = payload['last_name']
                password = payload['password']
                confirm_password = payload['confirm_password']
                
                userexists = get_user_model().objects.filter(email=email).exists()

                if userexists:
                    return Response({'details': 'User With Credentials Already Exist'}, status=status.HTTP_400_BAD_REQUEST)

               
                password_min_length = 8

                string_check= re.compile('[-@_!#$%^&*()<>?/\|}{~:;]') 

                if(password != confirm_password): 
                    return Response({'details':
                                     'Passwords Not Matching'},
                                    status=status.HTTP_400_BAD_REQUEST)

                if(string_check.search(password) == None): 
                    return Response({'details':
                                     'Password Must contain a special character, choose one from these: [-@_!#$%^&*()<>?/\|}{~:;]'},
                                    status=status.HTTP_400_BAD_REQUEST)

                if not any(char.isupper() for char in password):
                    return Response({'details':
                                     'Password must contain at least 1 uppercase letter'},
                                    status=status.HTTP_400_BAD_REQUEST)

                if len(password) < password_min_length:
                    return Response({'details':
                                     'Password Must be atleast 8 characters'},
                                    status=status.HTTP_400_BAD_REQUEST)

                if not any(char.isdigit() for char in password):
                    return Response({'details':
                                     'Password must contain at least 1 digit'},
                                    status=status.HTTP_400_BAD_REQUEST)
                                    
                if not any(char.isalpha() for char in password):
                    return Response({'details':
                                     'Password must contain at least 1 letter'},
                                    status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    group_details = Group.objects.get(name='USER')
                except (ValidationError, ObjectDoesNotExist):
                    return Response({'details': 'Role does not exist'}, status=status.HTTP_400_BAD_REQUEST)
                            

                hashed_pwd = make_password(password)
                newuser = {
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_active": True,
                    "password": hashed_pwd,
                }
                create_user = get_user_model().objects.create(**newuser)

                group_details.user_set.add(create_user)
                user_util.log_account_activity(
                    create_user, create_user, "Account Creation",
                    "USER CREATED")
                

                return Response("success", status=status.HTTP_200_OK)

        else:
            return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    