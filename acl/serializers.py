from django.db.models import  Q
from acl import models as acl_models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group


class UserDetailSerializer(serializers.Serializer):
    username = serializers.CharField()
    id_number = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


class SystemUsersSerializer(serializers.Serializer):
    UserId = serializers.CharField()
    email = serializers.CharField()
    firstname = serializers.CharField()
    lastname = serializers.CharField()

class GroupSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()

class UsersSerializer(serializers.ModelSerializer):
    id = serializers.CharField()
    email = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    is_active = serializers.CharField()
    is_suspended = serializers.CharField()
    user_groups = serializers.SerializerMethodField(read_only=True)
    user_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = get_user_model()
        fields = [
            'id', 'email', 'first_name', 'last_name', 'is_active', 'is_suspended','user_groups','date_created'
        ]

    def get_user_groups(self, obj):
        allgroups = Group.objects.filter(user=obj)
        serializer = GroupSerializer(allgroups, many=True)
        return serializer.data
    

class CreateUserSerializer(serializers.Serializer):
    email = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    password = serializers.CharField()
    confirm_password = serializers.CharField()