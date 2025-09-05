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
    type = serializers.CharField()

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
    uid = serializers.SerializerMethodField()
    is_creator = serializers.SerializerMethodField()
    can_receive = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    received_by = serializers.SerializerMethodField()
    
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
        
    def get_can_receive(self, obj):
        try:
            user_id = str(self.context["user_id"])
            is_receiver = models.PlatformAdmin.objects.filter(
                Q(admin=user_id) & Q(is_receiver=True)).exists()

            return is_receiver
        except Exception as e:
            print(e)
            # logger.error(e)
            return False
        
    def get_uid(self, obj):
        try:
            user_id = str(self.context["user_id"])
            if str(obj.created_by.id) == user_id:
                return obj.uid
            else:
                if obj.status == 'RECEIVED':
                    return obj.uid
                else:
                    return '-'
        except Exception as e:
            print(e)
            # logger.error(e)
            return False
        
    def get_received_by(self, obj):
        try:
            record = models.TrackingStatusChange.objects.get(tracked=obj,status='RECEIVED')
            serializer = FetchStatusChangeSerializer(record, many=False)
            return serializer.data
        except Exception as e:
            return {}
        
class CreateCancellationSerializer(serializers.Serializer):
    facility = serializers.CharField()
    invoice_no = serializers.CharField()
    action = serializers.CharField()
    reason = serializers.CharField()
    type = serializers.CharField()

class UpdateCancellationSerializer(serializers.Serializer):
    request_id = serializers.CharField()
    facility = serializers.CharField()
    invoice_no = serializers.CharField()
    action = serializers.CharField()
    reason = serializers.CharField()
    type = serializers.CharField()

class SlimFetchCancellationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Cancellation
        fields = '__all__'

class FetchCancellationSerializer(serializers.ModelSerializer):
    facility = FetchFacilitySerializer()
    created_by = UsersSerializer()
    is_creator = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()
    approved_by = serializers.SerializerMethodField()
    
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
        
    def get_can_approve(self, obj):
        try:
            user_id = str(self.context["user_id"])
            is_approver = models.PlatformAdmin.objects.filter(
                Q(admin=user_id) & Q(is_approver=True)).exists()

            return is_approver
        except Exception as e:
            print(e)
            # logger.error(e)
            return False
        
    def get_approved_by(self, obj):
        try:
            record = models.CancellationStatusChange.objects.get(cancelled=obj,status='APPROVED')
            serializer = FetchStatusChangeSerializer(record, many=False)
            return serializer.data
        except Exception as e:
            return {}
        
        
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

