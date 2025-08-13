from django.db.models import  Q
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchSRRSDepartmentSerializer, SlimFetchSRRSDepartmentSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from ams import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from ict_helpdesk.serializers import FetchFacilitySerializer


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

class UpdateGeneralNameSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)

class AssetSerializer(serializers.Serializer):
    # asset_no = serializers.CharField(max_length=500)
    type = serializers.CharField(max_length=500)
    status = serializers.CharField(max_length=255)
    facility = serializers.CharField(max_length=255)
    department = serializers.UUIDField()

class UpdateAssetSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    # asset_no = serializers.CharField(max_length=500)
    type = serializers.CharField(max_length=500)
    status = serializers.CharField(max_length=255)
    facility = serializers.CharField(max_length=255)
    department = serializers.UUIDField()

class SlimFetchAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Asset
        fields = '__all__'

class FetchAssetSerializer(serializers.ModelSerializer):
    department = FetchSRRSDepartmentSerializer()
    facility = FetchFacilitySerializer()
    created_by = UsersSerializer()
    
    class Meta:
        model = models.Asset
        fields = '__all__'

    

