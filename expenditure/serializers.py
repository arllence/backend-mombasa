from django.db.models import  Q
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchSRRSDepartmentSerializer, SlimFetchSRRSDepartmentSerializer
from srrs.serializers import FetchOHCSerializer, FetchSubDepartmentSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from expenditure import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

class UpdateGeneralNameSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)

class CreateExpenditureSerializer(serializers.Serializer):
    reference_no = serializers.CharField()
    description = serializers.CharField()
    invoice_number = serializers.DateField()
    amount_kes = serializers.DateField()
    department = serializers.CharField()

class UpdateContractSerializer(serializers.Serializer):
    request_id = serializers.CharField()
    reference_no = serializers.CharField()
    description = serializers.CharField()
    invoice_number = serializers.DateField()
    amount_kes = serializers.DateField()
    department = serializers.CharField()

class SlimFetchExpenditureSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ExpenditureRequest
        fields = '__all__'

class SlimFetchDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Document
        fields = '__all__'

class FetchExpenditureSerializer(serializers.ModelSerializer):
    department = FetchSRRSDepartmentSerializer()
    documents = serializers.SerializerMethodField()
    requested_by = SlimUsersSerializer()
    
    class Meta:
        model = models.ExpenditureRequest
        fields = '__all__'

    def get_documents(self, obj):
        try:
            request = models.Document.objects.filter(expenditure=obj, is_deleted=False)
            serializer = SlimFetchDocumentSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []         
        
class UploadFileSerializer(serializers.Serializer):
    request_id = serializers.CharField()
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

class NoteSerializer(serializers.Serializer):
    request_id = serializers.CharField()
    comments = serializers.CharField(style={'type': 'textarea'})


class FetchNoteSerializer(serializers.ModelSerializer):
    owner = SlimUsersSerializer()
    class Meta:
        model = models.Note
        fields = '__all__'