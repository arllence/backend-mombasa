from django.db.models import  Q
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchSRRSDepartmentSerializer, SlimFetchSRRSDepartmentSerializer, FetchSubDepartmentSerializer, FetchOHCSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from mhd import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

class UpdateGeneralNameSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)

class FetchSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Section
        fields = '__all__'

class FetchJobTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.JobType
        fields = '__all__'

class FetchEquipmentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EquipmentType
        fields = '__all__'

class FetchFacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Facility
        fields = '__all__'

class FetchCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Category
        fields = '__all__'

class GenericIssueSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.CharField()
    department = serializers.CharField()
    facility = serializers.CharField()
    category = serializers.CharField()
    subject = serializers.CharField()
    issue = serializers.CharField(style={'type': 'textarea'})


class IssueSerializer(serializers.Serializer):
    department = serializers.CharField()
    facility = serializers.CharField()
    category = serializers.CharField()
    subject = serializers.CharField()
    issue = serializers.CharField(style={'type': 'textarea'})

class PutIssueSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    department = serializers.CharField()
    facility = serializers.CharField()
    subject = serializers.CharField()
    category = serializers.CharField()
    issue = serializers.CharField(style={'type': 'textarea'})


class PatchIssueSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)

class FetchIssueSerializer(serializers.ModelSerializer):
    created_by = UsersSerializer()
    closed_by = UsersSerializer()
    assigned_to = UsersSerializer()
    job_type = FetchJobTypeSerializer()
    equipment_type = FetchEquipmentTypeSerializer()
    category = FetchCategorySerializer()
    facility = FetchFacilitySerializer()
    section = FetchSectionSerializer()
    department = FetchSRRSDepartmentSerializer()
    approvals = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    is_assigned = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Issue
        fields = '__all__'

    def get_approvals(self, obj):
        try:
            request = models.StatusChange.objects.filter(issue=obj)
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
        
    def get_is_assigned(self, obj):
        try:
            user_id = str(self.context["user_id"])
            # roles = get_user_roles(user_id)

            assigned = False

            try:
                if str(obj.assigned_to.id) == user_id:
                    assigned = True
            except Exception as e:
                pass

            return assigned
        except Exception as e:
            print(e)
            # logger.error(e)
            return False
    

class SlimFetchIssueSerializer(serializers.ModelSerializer):
    department = SlimFetchSRRSDepartmentSerializer()
    job_type = FetchJobTypeSerializer()
    equipment_type = FetchEquipmentTypeSerializer()
    section = FetchSectionSerializer()
    facility = FetchFacilitySerializer()
    section = FetchSectionSerializer()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = models.Issue
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


class AssignSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    assign_to = serializers.CharField(max_length=500)

class MarkAsCompleteSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)

class FetchStatusChangeSerializer(serializers.ModelSerializer):
    action_by = SlimUsersSerializer()
    class Meta:
        model = models.StatusChange
        fields = '__all__'


class NoteSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    comments = serializers.CharField(style={'type': 'textarea'})


class FetchNoteSerializer(serializers.ModelSerializer):
    owner = SlimUsersSerializer()
    class Meta:
        model = models.Note
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


