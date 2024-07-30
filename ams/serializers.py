from django.db.models import  Q
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchSRRSDepartmentSerializer, SlimFetchSRRSDepartmentSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from ams import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

class UpdateGeneralNameSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)

class AssetSerializer(serializers.Serializer):
    barcode = serializers.CharField(max_length=500)
    serial_no = serializers.CharField(max_length=500)
    asset_description = serializers.CharField(max_length=255)
    asset_type = serializers.CharField(max_length=255)
    asset_count = serializers.IntegerField()
    main_location = serializers.CharField(max_length=255)
    sub_location = serializers.CharField(max_length=255)
    building = serializers.CharField(max_length=255)
    room = serializers.CharField(max_length=255)
    department = serializers.CharField(max_length=255)
    person = serializers.CharField(max_length=255)
    condition = serializers.CharField(max_length=255)

class UpdateAssetSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    barcode = serializers.CharField(max_length=500)
    serial_no = serializers.CharField(max_length=500)
    asset_description = serializers.CharField(max_length=255)
    asset_type = serializers.CharField(max_length=255)
    asset_count = serializers.IntegerField()
    main_location = serializers.CharField(max_length=255)
    sub_location = serializers.CharField(max_length=255)
    building = serializers.CharField(max_length=255)
    room = serializers.CharField(max_length=255)
    department = serializers.CharField(max_length=255)
    person = serializers.CharField(max_length=255)
    condition = serializers.CharField(max_length=255)

class SlimFetchAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Asset
        fields = '__all__'

class FetchAssetSerializer(serializers.ModelSerializer):
    department = FetchSRRSDepartmentSerializer()
    created_by = UsersSerializer()
    
    class Meta:
        model = models.Asset
        fields = '__all__'

    

