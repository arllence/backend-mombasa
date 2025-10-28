from django.db.models import  Q
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchSRRSDepartmentSerializer, SlimFetchSRRSDepartmentSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from acl.models import SRRSDepartment
from intranet import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

class UpdateGeneralNameSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)

class UploadDocumentSerializer(serializers.Serializer):
    # title = serializers.CharField(max_length=500)
    department = serializers.CharField(max_length=500)

class UploadGeneralDocumentSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=500)

class UpdateUploadGeneralDocumentSerializer(serializers.Serializer):
    tag = serializers.CharField(max_length=500)
class FetchGeneralDocumentSerializer(serializers.ModelSerializer):
    uploaded_by = UsersSerializer()
    class Meta:
        model = models.GeneralDocument
        fields = '__all__'
class SlimFetchDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Document
        fields = '__all__'


class FetchDocumentSerializer(serializers.ModelSerializer):
    department = SlimFetchSRRSDepartmentSerializer()
    uploaded_by = UsersSerializer()
    
    class Meta:
        model = models.Document
        fields = '__all__'

class UpdateDocumentSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=500)
 
class QuickLinkSerializer(serializers.Serializer):
    link = serializers.CharField(max_length=500)
    title = serializers.CharField(max_length=100)

class UpdateQuickLinkSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    link = serializers.CharField(max_length=500)
    title = serializers.CharField(max_length=100)

class SlimFetchQuickLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.QuickLink
        fields = '__all__'


class FetchQuickLinkSerializer(serializers.ModelSerializer):
    created_by = UsersSerializer()
    
    class Meta:
        model = models.QuickLink
        fields = '__all__'

class QipsSerializer(serializers.Serializer):
    topic = serializers.ListField(min_length=1)

class UpdateQipsSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    topic = serializers.CharField(max_length=500)

class SlimFetchQipsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Qips
        fields = '__all__'

class FullFetchQipsSerializer(serializers.ModelSerializer):
    sub_topics = serializers.SerializerMethodField()
    class Meta:
        model = models.Qips
        fields = '__all__'

    def get_sub_topics(self, obj):
        try:
            request = models.QipsSubTopic.objects.filter(qips=obj,is_deleted=False)
            serializer = FetchQipsSubTopicSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 

class QipsSubTopicSerializer(serializers.Serializer):
    topic = serializers.CharField(max_length=500)
    sub_topic = serializers.ListField(min_length=1)

class UpdateQipsSubTopicSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    sub_topic = serializers.CharField(max_length=500)

class SlimFetchQipsSubTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.QipsSubTopic
        fields = '__all__'

class FetchQipsSubTopicSerializer(serializers.ModelSerializer):
    qips = SlimFetchQipsSerializer()
    categories = serializers.SerializerMethodField()
    class Meta:
        model = models.QipsSubTopic
        fields = '__all__'

    def get_categories(self, obj):
        try:
            request = models.QipsCategory.objects.filter(sub_topic=obj,is_deleted=False)
            serializer = SlimFetchQipsCategorySerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 

class QipsCategorySerializer(serializers.Serializer):
    category = serializers.ListField(min_length=1)
    sub_topic = serializers.CharField(max_length=500)

class UpdateQipsCategorySerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    category = serializers.CharField(max_length=500)

class SlimFetchQipsCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.QipsCategory
        fields = '__all__'

class FetchQipsCategorySerializer(serializers.ModelSerializer):
    sub_topic = SlimFetchQipsSubTopicSerializer()
    class Meta:
        model = models.QipsCategory
        fields = '__all__'

class UploadQipsDocumentSerializer(serializers.Serializer):
    topic = serializers.CharField(max_length=500)

class FetchQipsDocumentSerializer(serializers.ModelSerializer):
    topic = SlimFetchQipsSerializer()
    sub_topic = SlimFetchQipsSubTopicSerializer()
    category = SlimFetchQipsCategorySerializer()
    uploaded_by = SlimUsersSerializer()
    
    class Meta:
        model = models.QipsDocument
        fields = '__all__'

class SlimFetchQipsDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.QipsDocument
        fields = '__all__'

class SlimFetchGeneralDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.GeneralDocument
        fields = '__all__'

class SubDepartmentSerializer(serializers.Serializer):
    department_id = serializers.CharField(max_length=255)
    sub_departments = serializers.ListField(min_length=1)

class UpdateSubDepartmentSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    sub_department = serializers.CharField(max_length=500)

class SubDepartmentCategoriesSerializer(serializers.Serializer):
    sub_department_id = serializers.CharField(max_length=255)
    category = serializers.ListField(min_length=1)

class UpdateSubDepartmentCategoriesSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    category = serializers.CharField(max_length=500)  

class SlimFetchSubDepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SubDepartment
        fields = '__all__'

class SubSlimFetchSubDepartmentSerializer(serializers.ModelSerializer):
    categories = serializers.SerializerMethodField()

    def get_categories(self, obj):
        try:
            request = models.SubDepartmentCategory.objects.filter(sub_department=obj,is_deleted=False)
            serializer = SlimFetchSubDepartmentCategorySerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 
    class Meta:
        model = models.SubDepartment
        fields = '__all__'

class FetchSubDepartmentSerializer(serializers.ModelSerializer):
    department = SlimFetchSRRSDepartmentSerializer()
    categories = serializers.SerializerMethodField()

    def get_categories(self, obj):
        try:
            request = models.SubDepartmentCategory.objects.filter(sub_department=obj)
            serializer = SlimFetchSubDepartmentCategorySerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 
    class Meta:
        model = models.SubDepartment
        fields = '__all__'

class SlimFetchSubDepartmentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SubDepartmentCategory
        fields = '__all__'

class FetchSubDepartmentCategorySerializer(serializers.ModelSerializer):
    sub_department = SlimFetchSubDepartmentSerializer()
    class Meta:
        model = models.SubDepartmentCategory
        fields = '__all__'

class FullFetchDepartmentSerializer(serializers.ModelSerializer):
    sub_departments = serializers.SerializerMethodField()
    class Meta:
        model = models.SRRSDepartment
        fields = '__all__'

    def get_sub_departments(self, obj):
        try:
            request = models.SubDepartment.objects.filter(department=obj,is_deleted=False)
            serializer = SubSlimFetchSubDepartmentSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []
        
# privileges
class SlimFetchPrivilegeSubDepartmentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PrivilegeSubDepartmentCategory
        fields = '__all__'
class SubSlimFetchPrivilegeSubDepartmentSerializer(serializers.ModelSerializer):
    categories = serializers.SerializerMethodField()

    def get_categories(self, obj):
        try:
            request = models.PrivilegeSubDepartmentCategory.objects.filter(sub_department=obj,is_deleted=False)
            serializer = SlimFetchPrivilegeSubDepartmentCategorySerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 
    class Meta:
        model = models.PrivilegeSubDepartment
        fields = '__all__'

class FullFetchPrivilegesDepartmentSerializer(serializers.ModelSerializer):
    sub_departments = serializers.SerializerMethodField()
    class Meta:
        model = models.SRRSDepartment
        fields = '__all__'

    def get_sub_departments(self, obj):
        try:
            request = models.PrivilegeSubDepartment.objects.filter(department=obj,is_deleted=False)
            serializer = SubSlimFetchPrivilegeSubDepartmentSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []
        

# survey
class SurveySerializer(serializers.Serializer):
    topic = serializers.ListField(min_length=1)

class UpdateSurveySerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    # topic = serializers.CharField(max_length=500)
    link = serializers.CharField(max_length=500)

class SlimFetchSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Survey
        fields = '__all__'

class FullFetchSurveySerializer(serializers.ModelSerializer):
    sub_topics = serializers.SerializerMethodField()
    link = serializers.SerializerMethodField()
    class Meta:
        model = models.Survey
        fields = '__all__'

    def get_sub_topics(self, obj):
        try:
            request = models.SurveySubTopic.objects.filter(survey=obj,is_deleted=False)
            serializer = FetchSurveySubTopicSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []
        
    def get_link(self, obj):
        try:
            request = models.SurveyLink.objects.filter(topic=obj).order_by('-date_created').first()
            if request:
                return request.link 
            return ""
        except (ValidationError, ObjectDoesNotExist):
            return ""
        except Exception as e:
            print(e)
            # logger.error(e)
            return ""

class SurveySubTopicSerializer(serializers.Serializer):
    topic = serializers.CharField(max_length=500)
    sub_topic = serializers.ListField(min_length=1)

class UpdateSurveySubTopicSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    sub_topic = serializers.CharField(max_length=500)

class SlimFetchSurveySubTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SurveySubTopic
        fields = '__all__'

class FetchSurveySubTopicSerializer(serializers.ModelSerializer):
    survey = SlimFetchSurveySerializer()
    categories = serializers.SerializerMethodField()
    link = serializers.SerializerMethodField()
    class Meta:
        model = models.SurveySubTopic
        fields = '__all__'

    def get_categories(self, obj):
        try:
            request = models.SurveyCategory.objects.filter(sub_topic=obj,is_deleted=False)
            serializer = SlimFetchSurveyCategorySerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return [] 
        
    def get_link(self, obj):
        try:
            request = models.SurveyLink.objects.filter(sub_topic=obj,is_deleted=False).order_by('-date_created').first()
            if request:
                return request.link 
            return ""
        except (ValidationError, ObjectDoesNotExist):
            return ""
        except Exception as e:
            print(e)
            # logger.error(e)
            return "" 

class SurveyCategorySerializer(serializers.Serializer):
    category = serializers.ListField(min_length=1)
    sub_topic = serializers.CharField(max_length=500)

class UpdateSurveyCategorySerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    category = serializers.CharField(max_length=500)

class SlimFetchSurveyCategorySerializer(serializers.ModelSerializer):
    link = serializers.SerializerMethodField()
    def get_link(self, obj):
        try:
            request = models.SurveyLink.objects.get(category=obj)
            if request.link:
                return request.link 
            return ""
        except (ValidationError, ObjectDoesNotExist):
            return ""
        except Exception as e:
            print(e)
            # logger.error(e)
            return "" 
    class Meta:
        model = models.SurveyCategory
        fields = '__all__'

class FetchSurveyCategorySerializer(serializers.ModelSerializer):
    sub_topic = SlimFetchSurveySubTopicSerializer()
    class Meta:
        model = models.SurveyCategory
        fields = '__all__'

class SurveyLinkSerializer(serializers.Serializer):
    topic = serializers.CharField(max_length=500)
    link = serializers.CharField(max_length=500)

class FetchSurveyLinkSerializer(serializers.ModelSerializer):
    topic = SlimFetchSurveySerializer()
    sub_topic = SlimFetchSurveySubTopicSerializer()
    category = SlimFetchSurveyCategorySerializer()
    created_by = SlimUsersSerializer()
    
    class Meta:
        model = models.SurveyLink
        fields = '__all__'

class SlimFetchSurveyLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SurveyLink
        fields = '__all__'


# Module
class ModuleSerializer(serializers.Serializer):
    topic = serializers.ListField(min_length=1)

class UpdateModuleSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    link = serializers.CharField(max_length=500)

class SlimFetchModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Module
        fields = '__all__'

class FullFetchModuleSerializer(serializers.ModelSerializer):
    sub_topics = serializers.SerializerMethodField()
    link = serializers.SerializerMethodField()
    class Meta:
        model = models.Module
        fields = '__all__'

    def get_sub_topics(self, obj):
        try:
            request = models.ModuleSubTopic.objects.filter(module=obj,is_deleted=False)
            serializer = FetchModuleSubTopicSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []
        
    def get_link(self, obj):
        try:
            request = models.ModuleLink.objects.filter(topic=obj).order_by('-date_created').first()
            if request:
                return request.link 
            return ""
        except (ValidationError, ObjectDoesNotExist):
            return ""
        except Exception as e:
            print(e)
            # logger.error(e)
            return ""

class ModuleSubTopicSerializer(serializers.Serializer):
    topic = serializers.CharField(max_length=500)
    sub_topic = serializers.ListField(min_length=1)

class UpdateModuleSubTopicSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    sub_topic = serializers.CharField(max_length=500)

class SlimFetchModuleSubTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ModuleSubTopic
        fields = '__all__'

class FetchModuleSubTopicSerializer(serializers.ModelSerializer):
    module = SlimFetchModuleSerializer()
    categories = serializers.SerializerMethodField()
    link = serializers.SerializerMethodField()
    class Meta:
        model = models.ModuleSubTopic
        fields = '__all__'

    def get_categories(self, obj):
        try:
            request = models.ModuleCategory.objects.filter(sub_topic=obj,is_deleted=False)
            serializer = SlimFetchModuleCategorySerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return [] 
        
    def get_link(self, obj):
        try:
            request = models.ModuleLink.objects.get(sub_topic=obj,is_deleted=False)
            if request.link:
                return request.link 
            return ""
        except (ValidationError, ObjectDoesNotExist):
            return ""
        except Exception as e:
            print(e)
            # logger.error(e)
            return "" 

class ModuleCategorySerializer(serializers.Serializer):
    category = serializers.ListField(min_length=1)
    sub_topic = serializers.CharField(max_length=500)

class UpdateModuleCategorySerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    category = serializers.CharField(max_length=500)

class SlimFetchModuleCategorySerializer(serializers.ModelSerializer):
    link = serializers.SerializerMethodField()
    def get_link(self, obj):
        try:
            request = models.ModuleLink.objects.get(category=obj)
            if request.link:
                return request.link 
            return ""
        except (ValidationError, ObjectDoesNotExist):
            return ""
        except Exception as e:
            print(e)
            # logger.error(e)
            return "" 
    class Meta:
        model = models.ModuleCategory
        fields = '__all__'

class FetchModuleCategorySerializer(serializers.ModelSerializer):
    sub_topic = SlimFetchModuleSubTopicSerializer()
    class Meta:
        model = models.ModuleCategory
        fields = '__all__'

class ModuleLinkSerializer(serializers.Serializer):
    topic = serializers.CharField(max_length=500)
    link = serializers.CharField(max_length=500)

class FetchModuleLinkSerializer(serializers.ModelSerializer):
    topic = SlimFetchModuleSerializer()
    sub_topic = SlimFetchModuleSubTopicSerializer()
    category = SlimFetchModuleCategorySerializer()
    created_by = SlimUsersSerializer()
    
    class Meta:
        model = models.ModuleLink
        fields = '__all__'

class SlimFetchModuleLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ModuleLink
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