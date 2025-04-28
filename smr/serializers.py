from django.db.models import  Q
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchSRRSDepartmentSerializer, SlimFetchSRRSDepartmentSerializer, FetchSubDepartmentSerializer, FetchOHCSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from smr import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

class UpdateGeneralNameSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)

class GenericMealSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.CharField()
    # slt = serializers.CharField()
    department = serializers.CharField()
    date_of_event = serializers.DateField()
    number_of_participants = serializers.CharField()

class MealSerializer(serializers.Serializer):
    department = serializers.CharField()
    # slt = serializers.CharField()
    department = serializers.CharField()
    date_of_event = serializers.DateField()
    number_of_participants = serializers.CharField()
    reason = serializers.CharField()

class PutMealSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    # slt = serializers.CharField()
    department = serializers.CharField()
    date_of_event = serializers.DateField()
    number_of_participants = serializers.CharField()
    reason = serializers.CharField()

class PatchMealSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    action = serializers.CharField(max_length=500)

class FetchMealSerializer(serializers.ModelSerializer):
    created_by = UsersSerializer()
    slt = UsersSerializer()
    department = FetchSRRSDepartmentSerializer()
    approvals = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Meal
        fields = '__all__'

    def get_approvals(self, obj):
        try:
            request = models.StatusChange.objects.filter(meal=obj)
            serializer = FetchStatusChangeSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 
        
    def get_is_owner(self, obj):
        try:
            user_id = str(self.context["user_id"])
            # roles = get_user_roles(user_id)

            edit = False

            try:
                if str(obj.created_by.id) == user_id:
                    edit = True
            except Exception as e:
                pass

            return edit
        except Exception as e:
            print(e)
            # logger.error(e)
            return False
        
    def get_can_approve(self, obj):
        try:
            user_id = str(self.context["user_id"])
            roles = get_user_roles(user_id)

            approve = False

            if "SLT" in  roles and "CEO" in  roles:
                if obj.status != 'CEO APPROVED':
                    approve = True
            else:

                if "SLT" in  roles:
                    try:
                        if str(obj.department.slt.id) == user_id:
                            if obj.status == 'REQUESTED':
                                approve = True
                            else: 
                                approve = False
                    except Exception as e:
                        pass

                
                if "CEO" in  roles:
                    if obj.status == 'SLT APPROVED':
                        approve = True
                    else: 
                        approve = False

            return approve
        except Exception as e:
            print(e)
            # logger.error(e)
            return False
    

class SlimFetchMealSerializer(serializers.ModelSerializer):
    department = SlimFetchSRRSDepartmentSerializer()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = models.Meal
        fields = '__all__'

    def get_is_owner(self, obj):
        try:
            user_id = str(self.context["user_id"])
            # roles = get_user_roles(user_id)

            edit = False

            try:
                if str(obj.created_by.id) == user_id:
                    edit = True
            except Exception as e:
                pass

            return edit
        except Exception as e:
            print(e)
            # logger.error(e)
            return False


class FetchStatusChangeSerializer(serializers.ModelSerializer):
    action_by = SlimUsersSerializer()
    class Meta:
        model = models.StatusChange
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


