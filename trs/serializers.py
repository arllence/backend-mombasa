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
    created_by = UsersSerializer()
    closed_by = UsersSerializer()
    department = FetchDepartmentSerializer()
    trip = serializers.SerializerMethodField()
    salary_advance = serializers.SerializerMethodField()
    administration = serializers.SerializerMethodField()
    approvals = serializers.SerializerMethodField()
    
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
    
    def get_salary_advance(self, obj):
        try:
            request = models.AdvanceSalaryRequests.objects.get(traveler=obj)
            serializer = FetchAdvanceSalaryRequestsSerializer(request, many=False)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 

    def get_administration(self, obj):
        try:
            request = models.Costing.objects.get(traveler=obj)
            serializer = FetchCostingSerializer(request, many=False)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 

    def get_approvals(self, obj):
        try:
            request = models.StatusChange.objects.get(traveler=obj)
            serializer = FetchStatusChangeSerializer(request, many=False)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 

class TravelerSerializer(serializers.Serializer):
    # employee_no = serializers.CharField(max_length=500)
    # position = serializers.CharField(max_length=500)
    purpose = serializers.CharField(max_length=500)
    department = serializers.CharField(max_length=500)
    description = serializers.CharField(max_length=5000)

    route = serializers.CharField(max_length=5000)
    departure_date = serializers.CharField(max_length=255)
    return_date = serializers.CharField(max_length=255)

    mode_of_transport = serializers.CharField(max_length=255)
    requesting_for = serializers.CharField(max_length=255)

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

class FetchAdvanceSalaryRequestsSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.AdvanceSalaryRequests
        fields = '__all__'


class FetchStatusChangeSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.StatusChange
        fields = '__all__'

class PatchAdvanceSalaryRequestsSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=500)
    request_id = serializers.CharField(max_length=500)

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
    status = serializers.CharField(max_length=500)

class CostingSerializer(serializers.Serializer):
    traveler = serializers.CharField(max_length=500)
    bill_settlement_by = serializers.CharField(max_length=500)
    




