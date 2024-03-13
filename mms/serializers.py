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
    closure_files = serializers.SerializerMethodField()
    assigned = serializers.SerializerMethodField()
    class Meta:
        model = models.Quote
        fields = '__all__'

    def get_closure_files(self, obj):
        try:
            # quote_file = obj.close_attachments['quote_file']
            # comparative_analysis_file = obj.close_attachments['comparative_analysis_file']

            # quote_file = models.Document.objects.get(Q(id=quote_file))
            # comparative_analysis_file = models.Document.objects.get(Q(id=comparative_analysis_file))
            # serializer = FetchDocumentSerializer(plans, many=True)
            files = {
                "quote_file": FetchDocumentSerializer(models.Document.objects.get(Q(id=obj.close_attachments['quote_file'])), many=False).data,
                # "comparative_analysis_file": FetchDocumentSerializer(models.Document.objects.get(Q(id=obj.close_attachments['comparative_analysis_file'])), many=False).data
            }
            return files
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {}
    
    def get_assigned(self, obj):
        try:
            user_id = str(self.context["user_id"])
            return models.QuoteAssignee.objects.filter(Q(assigned=user_id) & Q(quote=obj)).exists()
            
        except (ValidationError, ObjectDoesNotExist):
            return False
        except Exception as e:
            print(e)
            # logger.error(e)
            return False


class AssignQuoteSerializer(serializers.Serializer):
    quote = serializers.CharField(max_length=500)
    staff = serializers.CharField(max_length=500)


class FetchAssignQuoteSerializer(serializers.ModelSerializer):
    assigned = UsersSerializer()
    quote = FetchQuoteSerializer()

    class Meta:
        model = models.QuoteAssignee
        fields = '__all__'



