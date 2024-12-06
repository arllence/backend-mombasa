from django.db.models import  Q
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchSRRSDepartmentSerializer, SlimFetchSRRSDepartmentSerializer, FetchSubDepartmentSerializer, FetchOHCSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from fms import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)


class GenericIncidentSerializer(serializers.Serializer):
    type_of_incident = serializers.CharField(max_length=500)
    priority = serializers.CharField(max_length=500)
    department = serializers.CharField()
    location = serializers.CharField(max_length=500)
    affected_person_name = serializers.CharField()
    person_affected = serializers.CharField(max_length=255)
    date_of_incident = serializers.DateField()
    time_of_incident = serializers.CharField(max_length=255)
    subject = serializers.CharField(max_length=255)
    message = serializers.CharField(max_length=255)

class IncidentSerializer(serializers.Serializer):
    type_of_incident = serializers.CharField(max_length=500)
    priority = serializers.CharField(max_length=500)
    department = serializers.CharField()
    location = serializers.CharField(max_length=500)
    affected_person_name = serializers.CharField()
    person_affected = serializers.CharField(max_length=255)
    date_of_incident = serializers.DateField()
    time_of_incident = serializers.CharField(max_length=255)
    type_of_issue = serializers.CharField(max_length=255)
    subject = serializers.CharField(max_length=255)
    message = serializers.CharField(max_length=255)

class PutIncidentSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    type_of_incident = serializers.CharField(max_length=500)
    priority = serializers.CharField(max_length=500)
    department = serializers.CharField(max_length=500)
    location = serializers.CharField(max_length=500)
    affected_person_name = serializers.CharField(max_length=500)
    person_affected = serializers.CharField(max_length=255)
    date_of_incident = serializers.DateField()
    time_of_incident = serializers.CharField(max_length=255)
    type_of_issue = serializers.CharField(max_length=255)
    subject = serializers.CharField(max_length=255)
    message = serializers.CharField(max_length=255)


class PatchIncidentSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)

class FetchIncidentSerializer(serializers.ModelSerializer):
    created_by = UsersSerializer()
    closed_by = UsersSerializer()
    assigned_to = UsersSerializer()
    department = FetchSRRSDepartmentSerializer()
    location = FetchSubDepartmentSerializer()
    approvals = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    is_assigned = serializers.SerializerMethodField()
    ohc = FetchOHCSerializer()
    
    class Meta:
        model = models.Incident
        fields = '__all__'

    def get_approvals(self, obj):
        try:
            request = models.StatusChange.objects.filter(incident=obj)
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
    

class SlimFetchIncidentSerializer(serializers.ModelSerializer):
    department = SlimFetchSRRSDepartmentSerializer()
    location = FetchSubDepartmentSerializer()
    is_owner = serializers.SerializerMethodField()
    ohc = FetchOHCSerializer()

    class Meta:
        model = models.Incident
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