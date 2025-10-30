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
    invoice_number = serializers.CharField()
    amount_kes = serializers.CharField()
    department = serializers.CharField()

class UpdateContractSerializer(serializers.Serializer):
    request_id = serializers.CharField()
    reference_no = serializers.CharField()
    description = serializers.CharField()
    invoice_number = serializers.CharField()
    amount_kes = serializers.CharField()
    department = serializers.CharField()

class SlimFetchExpenditureSerializer(serializers.ModelSerializer):
    department = SlimFetchSRRSDepartmentSerializer()
    requested_by = SlimUsersSerializer()
    class Meta:
        model = models.ExpenditureRequest
        fields = '__all__'

class SlimFetchDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Document
        fields = '__all__'

class FetchExpenditureSerializer(serializers.ModelSerializer):
    department = SlimFetchSRRSDepartmentSerializer()
    documents = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()
    approvals = serializers.SerializerMethodField()
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

    def get_can_approve(self, obj):
        try:
            user_id = str(self.context["user_id"])
            roles = get_user_roles(user_id)

            # Only certain roles can approve
            if not any(role in {"CEO", "HOF", "SUPERUSER", "HOD", "FINANCE_MANAGER"} for role in roles):
                return False

            # HOD specific logic
            if "HOD" in roles:
                if not obj.is_hod_approved:
                    return True
                
            # FM specific logic
            if "FINANCE_MANAGER" in roles:
                if obj.is_hod_approved and not obj.is_finance_manager_approved:
                    return True
                
            # HOF specific logic
            if "HOF" in roles:
                if obj.is_finance_manager_approved and not obj.is_hof_approved:
                    return True

            # CEO approval logic
            if "CEO" in roles and obj.is_finance_manager_approved and obj.is_hof_approved:
                if not obj.is_ceo_approved:
                    return True

            return False

        except KeyError:
            print("Missing user_id in context.")
        except Exception as e:
            print(f"Error in get_can_approve: {e}")

        return False  
    
    def get_approvals(self, obj):
        try:
            request = models.StatusChange.objects.filter(expenditure=obj).order_by('date_created')
            serializer = FetchStatusChangeSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 
        
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
    created_by = SlimUsersSerializer()
    class Meta:
        model = models.Note
        fields = '__all__'

class FetchStatusChangeSerializer(serializers.ModelSerializer):
    action_by = SlimUsersSerializer()
    class Meta:
        model = models.StatusChange
        fields = '__all__'