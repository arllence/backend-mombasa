from django.db.models import  Q
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchDepartmentSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from srrs import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

class SlimFetchRecruitSerializer(serializers.ModelSerializer):
    department = FetchDepartmentSerializer()
    class Meta:
        model = models.Recruit
        fields = '__all__'

class SuperSlimFetchRecruitSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Recruit
        fields = '__all__'
class FetchRecruitSerializer(serializers.ModelSerializer):
    created_by = UsersSerializer()
    closed_by = UsersSerializer()
    department = FetchDepartmentSerializer()
    can_approve = serializers.SerializerMethodField()
    approvals = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Recruit
        fields = '__all__'

    def get_approvals(self, obj):
        try:
            request = models.StatusChange.objects.filter(recruit=obj)
            serializer = FetchStatusChangeSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 

    def get_can_approve(self, obj):
        try:
            user_id = str(self.context["user_id"])
            roles = get_user_roles(user_id)

            approve = False

            if "SLT" in  roles:
                try:
                    if str(obj.department.slt.lead.id) == user_id:
                        if obj.is_slt_approved:
                            approve = False
                        else: 
                            approve = True
                except Exception as e:
                    pass

            if "HHR" in  roles:
                if obj.is_slt_approved:
                    if obj.is_hhr_approved:
                        approve = False
                    else: 
                        approve = True

            if "HOF" in  roles:
                if obj.is_hhr_approved:
                    if obj.is_hof_approved:
                        approve = False
                    else: 
                        approve = True
            
            if "CEO" in  roles:
                if obj.is_hof_approved:
                    if obj.is_ceo_approved:
                        approve = False
                    else: 
                        approve = True

            return approve
        except Exception as e:
            print(e)
            # logger.error(e)
            return False
   
class RecruitSerializer(serializers.Serializer):
    position_title = serializers.CharField(max_length=500)
    position_type = serializers.CharField(max_length=500)
    qualifications = serializers.JSONField()
    nature_of_hiring = serializers.CharField(max_length=500)
    filling_date = serializers.DateField()
    temporary_task_assignment_to = serializers.CharField(max_length=255)

class PutRecruitSerializer(serializers.Serializer):
    record_id = serializers.CharField(max_length=500)
    position_title = serializers.CharField(max_length=500)
    position_type = serializers.CharField(max_length=500)
    qualifications = serializers.JSONField()
    nature_of_hiring = serializers.CharField(max_length=500)
    filling_date = serializers.CharField(max_length=255)
    temporary_task_assignment_to = serializers.CharField(max_length=255)

class PatchRecruitSerializer(serializers.Serializer):
    recruit_id = serializers.CharField(max_length=500)
    status = serializers.CharField(max_length=500)

class ApprovalSerializer(serializers.Serializer):
    recruit_id = serializers.CharField(max_length=500)

class PostHRDetailsSerializer(serializers.Serializer):
    recruit_id = serializers.CharField(max_length=500)
    proposed_salary = serializers.ImageField(max_length=500)

class FetchStatusChangeSerializer(serializers.ModelSerializer):
    action_by = SlimUsersSerializer()
    class Meta:
        model = models.StatusChange
        fields = '__all__'

class SlimFetchLocumAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.LocumAttendance
        fields = '__all__'

class AttendanceSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    month = serializers.IntegerField()
    year = serializers.IntegerField()
    day = serializers.IntegerField()
    hours_worked = serializers.IntegerField()
    overtime_hours = serializers.IntegerField()