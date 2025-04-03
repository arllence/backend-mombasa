from django.db.models import  Q
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchSRRSDepartmentSerializer, SlimFetchSRRSDepartmentSerializer
from srrs.serializers import FetchOHCSerializer, FetchSubDepartmentSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from cms import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

class UpdateGeneralNameSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)

class CreateContractSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField()
    commencement_date = serializers.DateField()
    expiry_date = serializers.DateField()
    department = serializers.CharField(max_length=255)

class UpdateContractSerializer(serializers.Serializer):
    request_id = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    commencement_date = serializers.DateField()
    expiry_date = serializers.DateField()
    department = serializers.CharField(max_length=255)

class SlimFetchContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Contract
        fields = '__all__'

class SlimFetchDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Document
        fields = '__all__'

class FetchContractSerializer(serializers.ModelSerializer):
    department = FetchSRRSDepartmentSerializer()
    documents = serializers.SerializerMethodField()
    previous = serializers.SerializerMethodField()
    created_by = SlimUsersSerializer()
    
    class Meta:
        model = models.Contract
        fields = '__all__'

    def get_documents(self, obj):
        try:
            request = models.Document.objects.filter(contract=obj, is_deleted=False)
            serializer = SlimFetchDocumentSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return [] 
        
    def get_previous(self, obj):
        try:
            request = models.Contract.objects.get(id=obj.previous, is_deleted=False)
            serializer = FetchContractSerializer(request, many=False)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 
        
class UploadFileSerializer(serializers.Serializer):
    contract_id = serializers.CharField()
    file_type = serializers.CharField()



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