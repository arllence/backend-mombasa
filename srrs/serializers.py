from django.db.models import  Q
from acl.serializers import UsersSerializer, FetchDepartmentSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from srrs import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

class SlimFetchRecruitSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Recruit
        fields = '__all__'

class FetchRecruitSerializer(serializers.ModelSerializer):
    created_by = UsersSerializer()
    closed_by = UsersSerializer()
    department = FetchDepartmentSerializer()
    
    class Meta:
        model = models.Recruit
        fields = '__all__'
   
class RecruitSerializer(serializers.Serializer):
    position_title = serializers.CharField(max_length=500)
    position_type = serializers.CharField(max_length=500)
    qualifications = serializers.JSONField()
    job_description = serializers.CharField(max_length=5000)
    nature_of_hiring = serializers.CharField(max_length=500)
    filling_period_from = serializers.DateField()
    filling_period_to = serializers.DateField()
    temporary_task_assignment_to = serializers.CharField(max_length=255)

class PutRecruitSerializer(serializers.Serializer):
    record_id = serializers.CharField(max_length=500)
    position_title = serializers.CharField(max_length=500)
    position_type = serializers.CharField(max_length=500)
    qualifications = serializers.JSONField()
    job_description = serializers.CharField(max_length=5000)
    nature_of_hiring = serializers.CharField(max_length=500)
    filling_period_from = serializers.CharField(max_length=5000)
    filling_period_to = serializers.CharField(max_length=255)
    temporary_task_assignment_to = serializers.CharField(max_length=255)
