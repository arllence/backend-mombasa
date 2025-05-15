from django.db.models import  Q
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchSRRSDepartmentSerializer, FetchDepartmentSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from ipass import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

class CreatePatientSerializer(serializers.Serializer):
    admission_no = serializers.CharField()

class SlimFetchPatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Patient
        fields = '__all__'

class FetchPatientSerializer(serializers.ModelSerializer):
    handover_by = SlimUsersSerializer()
    handover_to = SlimUsersSerializer()
    approvals = serializers.SerializerMethodField()
    is_creator = serializers.SerializerMethodField()
    is_assigned = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Patient
        fields = '__all__'

    def get_approvals(self, obj):
        try:
            request = models.StatusChange.objects.filter(patient=obj)
            serializer = FetchStatusChangeSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 
           
    def get_is_creator(self, obj):
        try:
            user_id = str(self.context["user_id"])
            if str(obj.handover_by.id) == user_id:
                return True
            return False
        except Exception as e:
            print(e)
            # logger.error(e)
            return False
        
    def get_is_assigned(self, obj):
        try:
            user_id = str(self.context["user_id"])
            if str(obj.handover_to.id) == user_id:
                return True
            return False
        except Exception as e:
            print(e)
            # logger.error(e)
            return False
        

        
class FetchStatusChangeSerializer(serializers.ModelSerializer):
    action_by = UsersSerializer()
    class Meta:
        model = models.StatusChange
        fields = '__all__'
    


class PlatformDoctorSerializer(serializers.Serializer):
    doctor = serializers.CharField(max_length=500)

class UpdatePlatformDoctorSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    doctor = serializers.CharField(max_length=500)

class FetchPlatformDoctorSerializer(serializers.ModelSerializer):
    created_by = SlimUsersSerializer()
    doctor = UsersSerializer()
    class Meta:
        model = models.PlatformDoctor
        fields = '__all__'

