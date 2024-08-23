from django.db.models import  Q
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchSRRSDepartmentSerializer, SlimFetchSRRSDepartmentSerializer
from srrs.serializers import FetchOHCSerializer, FetchSubDepartmentSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from sls import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

class UpdateGeneralNameSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)

class StaffSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=500)
    email = serializers.CharField(max_length=500)
    payroll_no = serializers.CharField(max_length=255)
    supervisor_name = serializers.CharField(max_length=255)
    department = serializers.CharField(max_length=255)
    location = serializers.CharField(max_length=255)

class MedicalSerializer(serializers.Serializer):
    days = serializers.IntegerField(allow_null=True)
    start_date = serializers.CharField(max_length=255, allow_null=True)
    end_date = serializers.CharField(max_length=255, allow_null=True)
    resume_work_on = serializers.CharField(max_length=255, allow_null=True)
    reason = serializers.CharField(style={'type': 'textarea'})

class ReferSerializer(serializers.Serializer):
    consultant_name = serializers.CharField(max_length=255, allow_null=True)
    date = serializers.CharField(max_length=255, allow_null=True)
    time = serializers.CharField(max_length=255, allow_null=True)


class SlimFetchStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Staff
        fields = '__all__'

class SlimFetchMedicalSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Medical
        fields = '__all__'

class SlimFetchReferSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Refer
        fields = '__all__'

class FetchStaffSerializer(serializers.ModelSerializer):
    department = FetchSRRSDepartmentSerializer()
    medical = serializers.SerializerMethodField()
    refer = serializers.SerializerMethodField()
    location = FetchSubDepartmentSerializer()
    ohc = FetchOHCSerializer()
    
    class Meta:
        model = models.Staff
        fields = '__all__'

    def get_medical(self, obj):
        try:
            request = models.Medical.objects.get(staff=obj)
            serializer = SlimFetchMedicalSerializer(request, many=False)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 
        
    def get_refer(self, obj):
        try:
            request = models.Refer.objects.get(staff=obj)
            serializer = SlimFetchReferSerializer(request, many=False)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 
        
