from django.db.models import  Q
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchSRRSDepartmentSerializer, SlimFetchSRRSDepartmentSerializer, FetchSubDepartmentSerializer, FetchOHCSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from mhd import models
from mms.serializers import SlimFetchQuoteSerializer as MMDSlimFetchQuoteSerializer
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    # category = serializers.CharField(max_length=255)

class UpdateGeneralNameSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)
    # category = serializers.CharField(max_length=255)

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

class FetchPrioritySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Priority
        fields = '__all__'

class GenericIssueSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.CharField()
    department = serializers.CharField()
    facility = serializers.CharField()
    # category = serializers.CharField()
    subject = serializers.CharField()
    issue = serializers.CharField(style={'type': 'textarea'})

class PrioritySerializer(serializers.Serializer):
    name = serializers.CharField()
    expected_closure = serializers.IntegerField(min_value=1)

class PutPrioritySerializer(serializers.Serializer):
    request_id = serializers.CharField()
    name = serializers.CharField()
    expected_closure = serializers.IntegerField(min_value=1)

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
    priority = FetchPrioritySerializer()
    facility = FetchFacilitySerializer()
    section = FetchSectionSerializer()
    department = FetchSRRSDepartmentSerializer()
    approvals = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    is_assigned = serializers.SerializerMethodField()
    tat = serializers.SerializerMethodField()
    assignees = serializers.SerializerMethodField()
    quotes = serializers.SerializerMethodField()
    job_card = serializers.SerializerMethodField()
    
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
        
    def get_assignees(self, obj):
        try:
            request = models.Assignees.objects.filter(issue=obj)
            serializer = FetchAssigneesSerializer(request, many=True)
            return serializer.data
        except Exception as e:
            print(e)
            # logger.error(e)
            return []
        
    def get_quotes(self, obj):
        try:
            request = models.Quote.objects.filter(issue=obj)
            serializer = SlimFetchQuoteSerializer(request, many=True)
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
                assigned = models.Assignees.objects.filter(assignee=user_id,issue=obj).exists()
                if not assigned:
                    if obj.assigned_to:
                        if str(obj.assigned_to.id) == user_id:
                            assigned = True                       
            except Exception as e:
                pass

            return assigned
        except Exception as e:
            print(e)
            # logger.error(e)
            return False
        
    def get_tat(self, obj):
        try:
            if obj.date_completed:
                diff = (obj.date_completed - obj.date_assigned).total_seconds() // 3600
            else:
                diff = (obj.date_closed - obj.date_assigned).total_seconds() // 3600
                
            if diff < 1:
                return "1"
            return str(diff)

        except Exception as e:
            print(e)
            # logger.error(e)
            return ""
        
    def get_job_card(self, obj):
        user_id = str(self.context["user_id"])

        try:
            request = models.JobCard.objects.filter(issue=obj).order_by('-date_created').first()
            serializer = FetchJobCardSerializer(request, many=False, context={"user_id":user_id})
            return serializer.data
        except Exception as e:
            print(e)
            # logger.error(e)
            return None
    

class SlimFetchIssueSerializer(serializers.ModelSerializer):
    department = SlimFetchSRRSDepartmentSerializer()
    job_type = FetchJobTypeSerializer()
    equipment_type = FetchEquipmentTypeSerializer()
    section = FetchSectionSerializer()
    facility = FetchFacilitySerializer()
    category = FetchCategorySerializer()
    is_owner = serializers.SerializerMethodField()
    assignees = serializers.SerializerMethodField()
    tat = serializers.SerializerMethodField()

    class Meta:
        model = models.Issue
        fields = '__all__'

    def get_assignees(self, obj):
        try:
            request = models.Assignees.objects.filter(issue=obj)
            serializer = FetchAssigneesSerializer(request, many=True)
            return serializer.data
        except Exception as e:
            print(e)
            # logger.error(e)
            return []
        
    def get_tat(self, obj):
        try:
            if obj.date_completed:
                diff = (obj.date_completed - obj.date_assigned).total_seconds() // 3600
            else:
                diff = (obj.date_closed - obj.date_assigned).total_seconds() // 3600

            if diff < 1:
                return "1 Hour"
            return str(diff) + " Hours"

        except Exception as e:
            print(e)
            # logger.error(e)
            return ""

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
    request_id = serializers.CharField()
    priority = serializers.CharField()
    job_type = serializers.CharField()
    assign_to = serializers.ListField(min_length=1)

class FetchAssigneesSerializer(serializers.ModelSerializer):
    assignee = SlimUsersSerializer()
    class Meta:
        model = models.Assignees
        fields = '__all__'

class AcknowledgementSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    action = serializers.CharField(max_length=500)

class MarkAsCompleteSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)

class QuoteSerializer(serializers.Serializer):
    issue_id = serializers.CharField()
    quote_id = serializers.CharField()

class FetchQuoteSerializer(serializers.ModelSerializer):
    issue = SlimFetchIssueSerializer()
    quote = MMDSlimFetchQuoteSerializer()
    class Meta:
        model = models.Quote
        fields = '__all__'

class SlimFetchQuoteSerializer(serializers.ModelSerializer):
    quote = MMDSlimFetchQuoteSerializer()
    class Meta:
        model = models.Quote
        fields = '__all__'

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

class FetchJobCardNoteSerializer(serializers.ModelSerializer):
    owner = SlimUsersSerializer()
    class Meta:
        model = models.JobCardNote
        fields = '__all__'

class PlatformAdminSerializer(serializers.Serializer):
    admin = serializers.CharField(max_length=500)
    category = serializers.CharField(max_length=500)
    is_hod = serializers.CharField(max_length=500)
    is_slt = serializers.CharField(max_length=500)

class UpdatePlatformAdminSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    admin = serializers.CharField(max_length=500)

class FetchPlatformAdminSerializer(serializers.ModelSerializer):
    created_by = SlimUsersSerializer()
    admin = UsersSerializer()
    category = FetchCategorySerializer()
    class Meta:
        model = models.PlatformAdmin
        fields = '__all__'


class JobCardSerializer(serializers.Serializer):
    issue = serializers.CharField(max_length=500)
    materials = serializers.ListField(min_length=1)
    supplier = serializers.CharField(max_length=500)
    material_cost = serializers.FloatField()
    labour_cost = serializers.FloatField()
    contract_type = serializers.CharField(max_length=500)
    contract_to = serializers.CharField(max_length=500)

class UpdateJobCardSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    issue = serializers.CharField(max_length=500)
    materials = serializers.ListField(min_length=1)
    supplier = serializers.CharField(max_length=500)
    material_cost = serializers.FloatField()
    labour_cost = serializers.FloatField()
    contract_type = serializers.CharField(max_length=500)
    contract_to = serializers.CharField(max_length=500)

class FetchJobCardSerializer(serializers.ModelSerializer):
    requested_by = SlimUsersSerializer()
    materials = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()

    def get_materials(self, obj):
        try:
            request = models.MaterialItem.objects.filter(job_card=obj)
            serializer = MaterialItemSerializer(request, many=True)
            return serializer.data
        except Exception as e:
            print(e)
            # logger.error(e)
            return []
        
    def get_can_approve(self, obj):
        try:
            user_id = str(self.context["user_id"])
            roles = get_user_roles(user_id)

            # Only certain roles can approve
            if not any(role in {"CEO", "HOF", "SUPERUSER", "MHD_ADMIN"} for role in roles):
                return False

            # MHD_ADMIN specific logic
            if "MHD_ADMIN" in roles:
                try:
                    approver = models.PlatformAdmin.objects.filter(admin=user_id).first()
                except models.PlatformAdmin.DoesNotExist:
                    return False

                if approver.is_hod and not obj.is_hod_approved:
                    return True

                if approver.is_slt and obj.is_hod_approved and not obj.is_slt_approved:
                    return True

            # # CEO approval logic
            if ("CEO" in roles or "HOF" in roles) and obj.is_hod_approved and obj.is_slt_approved:
                if not obj.is_ceo_approved and not obj.is_hof_approved:
                    return True
                
            # if "CEO" in roles and obj.is_hod_approved and obj.is_slt_approved:
            #     if not obj.is_ceo_approved or not obj.is_hof_approved:
            #         return True
            

            return False

        except KeyError:
            print("Missing user_id in context.")
        except Exception as e:
            print(f"Error in get_can_approve: {e}")

        return False

    class Meta:
        model = models.JobCard
        fields = '__all__'

class MaterialItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MaterialItem
        fields = '__all__'

class PatchJobCardSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    status = serializers.CharField(max_length=500)

class UploadFileSerializer(serializers.Serializer):
    job_card_id = serializers.CharField()
    file_type = serializers.CharField()

class SlimFetchDocumentSerializer(serializers.ModelSerializer):
    uploaded_by = SlimUsersSerializer()
    class Meta:
        model = models.JobCardDocument
        fields = '__all__'