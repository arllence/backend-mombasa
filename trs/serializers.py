import math
from urllib import request
from django.db.models import  Q
from acl.serializers import UsersSerializer, FetchDepartmentSerializer
from trs import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError




class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)


class FetchTravelerSerializer(serializers.ModelSerializer):
    traveler = UsersSerializer()
    trip = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Traveler
        fields = '__all__'

    def get_trip(self, obj):
        try:
            trip = models.Trip.objects.get(Q(traveler=obj))
            serializer = FetchTripSerializer(trip, many=False)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []

class TravelerSerializer(serializers.Serializer):
    employee_no = serializers.CharField(max_length=500)
    position = serializers.CharField(max_length=500)
    purpose = serializers.CharField(max_length=500)
    description = serializers.CharField(max_length=5000)

    route = serializers.CharField(max_length=5000)
    departure_date = serializers.CharField(max_length=255)
    return_date = serializers.CharField(max_length=255)

class PutTravelerSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=500)
    employee_no = serializers.CharField(max_length=500)
    position = serializers.CharField(max_length=500)
    purpose = serializers.CharField(max_length=500)
    description = serializers.CharField(max_length=5000)

    route = serializers.CharField(max_length=5000)
    departure_date = serializers.CharField(max_length=255)
    return_date = serializers.CharField(max_length=255)

class PatchTravelerSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=500)
    traveler_id = serializers.CharField(max_length=500)

class FetchTripSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Trip
        fields = '__all__'

class FetchApprovalSerializer(serializers.ModelSerializer):
    approved_by = UsersSerializer()

    class Meta:
        model = models.Approval
        fields = '__all__'

class FetchCostingSerializer(serializers.ModelSerializer):
    created_by = UsersSerializer()
    
    class Meta:
        model = models.Costing
        fields = '__all__'

class ApprovalSerializer(serializers.Serializer):
    traveler = serializers.CharField(max_length=500)




