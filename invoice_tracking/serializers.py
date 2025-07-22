from django.db.models import  Q
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchSRRSDepartmentSerializer, FetchDepartmentSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from ict_helpdesk.serializers import FetchFacilitySerializer
from invoice_tracking import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

class CreateTrackingSerializer(serializers.Serializer):
    facility = serializers.CharField()
    weigh_bill_no = serializers.CharField()
    courier = serializers.CharField()
    collector = serializers.CharField()

class UpdateTrackingSerializer(serializers.Serializer):
    request_id = serializers.CharField()
    facility = serializers.CharField()
    weigh_bill_no = serializers.CharField()
    courier = serializers.CharField()
    collector = serializers.CharField()

class SlimFetchTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Tracking
        fields = '__all__'

class FetchTrackingSerializer(serializers.ModelSerializer):
    facility = FetchFacilitySerializer()
    created_by = SlimUsersSerializer()
    is_creator = serializers.SerializerMethodField()
    # is_assigned = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Tracking
        fields = '__all__'

    def get_status(self, obj):
        try:
            request = models.TrackingStatusChange.objects.filter(tracked=obj)
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
            if str(obj.created_by.id) == user_id:
                return True
            return False
        except Exception as e:
            print(e)
            # logger.error(e)
            return False
        
    def get_can_edit(self, obj):
        try:
            user_id = str(self.context["user_id"])
            if str(obj.created_by.id) == user_id and obj.status == 'PENDING':
                return True
            return False
        except Exception as e:
            print(e)
            # logger.error(e)
            return False
        
class CreateCancellationSerializer(serializers.Serializer):
    facility = serializers.CharField()
    invoice_no = serializers.CharField()
    action = serializers.CharField()
    reason = serializers.CharField()


class UpdateCancellationSerializer(serializers.Serializer):
    request_id = serializers.CharField()
    facility = serializers.CharField()
    invoice_no = serializers.CharField()
    action = serializers.CharField()
    reason = serializers.CharField()

class SlimFetchCancellationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Cancellation
        fields = '__all__'

class FetchCancellationSerializer(serializers.ModelSerializer):
    facility = FetchFacilitySerializer()
    created_by = UsersSerializer()
    is_creator = serializers.SerializerMethodField()
    is_assigned = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Cancellation
        fields = '__all__'

    def get_status(self, obj):
        try:
            request = models.CancellationStatusChange.objects.filter(tracked=obj)
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
            if str(obj.created_by.id) == user_id:
                return True
            return False
        except Exception as e:
            print(e)
            # logger.error(e)
            return False
        
    def get_can_edit(self, obj):
        try:
            user_id = str(self.context["user_id"])
            if str(obj.created_by.id) == user_id and obj.status == 'PENDING':
                return True
            return False
        except Exception as e:
            print(e)
            # logger.error(e)
            return False
        
        
class FetchStatusChangeSerializer(serializers.ModelSerializer):
    action_by = UsersSerializer()
    class Meta:
        model = models.TrackingStatusChange
        fields = '__all__'
    

class PlatformAdminSerializer(serializers.Serializer):
    admin = serializers.CharField(max_length=500)

class UpdatePlatformAdminSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    admin = serializers.CharField(max_length=500)

class FetchPlatformAdminSerializer(serializers.ModelSerializer):
    created_by = SlimUsersSerializer()
    admin = UsersSerializer()
    class Meta:
        model = models.PlatformAdmin
        fields = '__all__'

