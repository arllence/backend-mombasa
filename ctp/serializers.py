from django.db.models import  Q
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchSRRSDepartmentSerializer, SlimFetchSRRSDepartmentSerializer
from srrs.serializers import FetchOHCSerializer, FetchSubDepartmentSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from ctp import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

class UpdateGeneralNameSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)

class CreateTrainingMaterialSerializer(serializers.Serializer):
    title = serializers.CharField()
    type = serializers.CharField()
    description = serializers.CharField()
    department = serializers.CharField(max_length=255)

class UpdateTrainingMaterialSerializer(serializers.Serializer):
    request_id = serializers.CharField()
    title = serializers.CharField()
    type = serializers.CharField()
    description = serializers.CharField()
    department = serializers.CharField(max_length=255)

class SlimFetchTrainingMaterialSerializer(serializers.ModelSerializer):
    department = SlimFetchSRRSDepartmentSerializer()
    class Meta:
        model = models.TrainingMaterial
        fields = '__all__'

class SlimFetchDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Document
        fields = '__all__'

class FetchTrainingMaterialSerializer(serializers.ModelSerializer):
    department = SlimFetchSRRSDepartmentSerializer()
    documents = serializers.SerializerMethodField()
    created_by = SlimUsersSerializer()
    
    class Meta:
        model = models.TrainingMaterial
        fields = '__all__'

    def get_documents(self, obj):
        try:
            request = models.Document.objects.filter(training=obj, is_deleted=False)
            serializer = SlimFetchDocumentSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return [] 
        
        
class UploadFileSerializer(serializers.Serializer):
    training_id = serializers.CharField()

# TrainingAssignment

class CreateTrainingAssignmentSerializer(serializers.Serializer):
    assign_to = serializers.CharField()
    training = serializers.CharField()

class UpdateTrainingAssignmentSerializer(serializers.Serializer):
    request_id = serializers.CharField()
    user = serializers.CharField()
    training = serializers.CharField()

class SlimFetchTrainingAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TrainingAssignment
        fields = '__all__'

class FetchTrainingAssignmentSerializer(serializers.ModelSerializer):
    training = SlimFetchTrainingMaterialSerializer()
    # documents = serializers.SerializerMethodField()
    user = SlimUsersSerializer()
    assigned_by = SlimUsersSerializer()
    
    class Meta:
        model = models.TrainingAssignment
        fields = '__all__'
        
# PlatformAdmin

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