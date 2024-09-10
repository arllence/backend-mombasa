from django.db.models import  Q
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchSRRSDepartmentSerializer, SlimFetchSRRSDepartmentSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
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

class QipsCategorySerializer(serializers.Serializer):
    category = serializers.CharField(max_length=500)
    sub_topic = serializers.CharField(max_length=500)

class UpdateQipsCategorySerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    category = serializers.CharField(max_length=500)

class SlimFetchQipsCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.QipsCategory
        fields = '__all__'