import math
from urllib import request
from django.db.models import  Q
from acl.serializers import UsersSerializer, FetchDepartmentSerializer
from mms import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError




class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)


class FetchDocumentSerializer(serializers.ModelSerializer):
    uploader = UsersSerializer()
    
    class Meta:
        model = models.Document
        fields = '__all__'

class QuoteSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=500)
    description = serializers.CharField(max_length=5000)
    department = serializers.CharField(max_length=500)

class PutQuoteSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=500)
    subject = serializers.CharField(max_length=500)
    description = serializers.CharField(max_length=5000)
    department = serializers.CharField(max_length=500)

class PatchQuoteSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=500)
    quote_id = serializers.CharField(max_length=500)

class CloseQuoteSerializer(serializers.Serializer):
    quote = serializers.CharField(max_length=500)

class FetchQuoteSerializer(serializers.ModelSerializer):
    uploader = UsersSerializer()
    department = FetchDepartmentSerializer()
    attachment = FetchDocumentSerializer()
    class Meta:
        model = models.Quote
        fields = '__all__'


class AssignQuoteSerializer(serializers.Serializer):
    quote = serializers.CharField(max_length=500)
    staff = serializers.CharField(max_length=500)


class FetchAssignQuoteSerializer(serializers.ModelSerializer):
    assigned = UsersSerializer()
    quote = FetchQuoteSerializer()

    class Meta:
        model = models.QuoteAssignee
        fields = '__all__'



