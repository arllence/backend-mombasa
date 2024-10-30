from django.db.models import  Q
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchSRRSDepartmentSerializer, SlimFetchSRRSDepartmentSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from acl.models import SRRSDepartment
from dbmanager import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

class UpdateGeneralNameSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)



class FetchBackupLogSerializer(serializers.ModelSerializer):
    action_by = UsersSerializer()
    
    class Meta:
        model = models.BackupLog
        fields = '__all__'

class UpdateBackupLogSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    type = serializers.CharField(max_length=500)
    date = serializers.CharField(max_length=500)
    status = serializers.CharField(max_length=500)
    size = serializers.IntegerField()
    unit = serializers.CharField(max_length=100)

class BackupLogSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=500)
    date = serializers.CharField(max_length=500)
    status = serializers.CharField(max_length=500)
    size = serializers.IntegerField()
    unit = serializers.CharField(max_length=100)


class FetchRemoteBackupLogSerializer(serializers.ModelSerializer):
    action_by = UsersSerializer()
    
    class Meta:
        model = models.RemoteBackupLog
        fields = '__all__'

class UpdateRemoteBackupLogSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    type = serializers.CharField(max_length=500)
    date = serializers.CharField(max_length=500)
    status = serializers.CharField(max_length=500)
    size = serializers.IntegerField()
    unit = serializers.CharField(max_length=100)

class RemoteBackupLogSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=500)
    date = serializers.CharField(max_length=500)
    status = serializers.CharField(max_length=500)
    size = serializers.IntegerField()
    unit = serializers.CharField(max_length=100)


class FetchSystemRecoveryVerificationSerializer(serializers.ModelSerializer):
    verified_by = UsersSerializer()
    
    class Meta:
        model = models.SystemRecoveryVerification
        fields = '__all__'

class UpdateSystemRecoveryVerificationSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    module_verified = serializers.CharField(max_length=500)
    date = serializers.CharField(max_length=500)
    comments = serializers.CharField(style={'type': 'textarea'})

class SystemRecoveryVerificationSerializer(serializers.Serializer):
    module_verified = serializers.CharField(max_length=500)
    date = serializers.CharField(max_length=500)
    comments = serializers.CharField(style={'type': 'textarea'})

