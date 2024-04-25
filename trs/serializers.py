import math
from urllib import request
from django.db.models import  Q
from acl.serializers import UsersSerializer, FetchDepartmentSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from trs import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError




class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

class SlimFetchTravelerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Traveler
        fields = '__all__'

class FetchTravelerSerializer(serializers.ModelSerializer):
    traveler = UsersSerializer()
    created_by = UsersSerializer()
    closed_by = UsersSerializer()
    department = FetchDepartmentSerializer()
    trip = serializers.SerializerMethodField()
    salary_advance = serializers.SerializerMethodField()
    administration = serializers.SerializerMethodField()
    approvals = serializers.SerializerMethodField()
    cash_office = serializers.SerializerMethodField()
    transport_office = serializers.SerializerMethodField()
    is_slt_and_hof = serializers.SerializerMethodField()
    forwardings = serializers.SerializerMethodField()
    is_department_slt = serializers.SerializerMethodField()
    is_creator = serializers.SerializerMethodField()
    
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
            request = models.StatusChange.objects.filter(traveler=obj)
            serializer = FetchStatusChangeSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 
        
    def get_cash_office(self, obj):
        try:
            approval_msg = models.Approval.objects.filter(
                traveler=obj,approval_for='CASH_OFFICE').order_by('-date_created').first().approval_msg
            
            if isinstance(approval_msg, list):
                return approval_msg
            elif isinstance(approval_msg, dict):
                return [approval_msg]
            else:
                return []
            
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []
    
    def get_transport_office(self, obj):
        try:
            approval_msg = models.Approval.objects.filter(
                traveler=obj,approval_for='TRANSPORT').order_by('-date_created').first().approval_msg
            
            return approval_msg
            
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []
        
    def get_forwardings(self, obj):
        try:
            request = models.TravelForwarding.objects.filter(traveler=obj)
            serializer = FetchTravelForwardingSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 
        
    def get_is_slt_and_hof(self, obj):
        try:
            user_id = str(self.context["user_id"])
            roles = get_user_roles(user_id)

            if "SLT" in roles and "HOF" in roles:
                return True
            return False
        except Exception as e:
            print(e)
            # logger.error(e)
            return False
        
    def get_is_department_slt(self, obj):
        try:
            user_id = str(self.context["user_id"])
            roles = get_user_roles(user_id)

            if "SLT" in  roles:
                try:
                    if obj.department.slt.lead.id == user_id:
                        return True
                except Exception as e:
                    pass
            return False
        except Exception as e:
            print(e)
            # logger.error(e)
            return False
        
    def get_is_creator(self, obj):
        try:
            user_id = str(self.context["user_id"])

            if str(obj.created_by.id) == user_id:
                return True
            return False
        except Exception as e:
            print(e)
            # logger.error(e)
            return False

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
    type_of_travel = serializers.CharField(max_length=255)
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
    action_by = UsersSerializer()
    class Meta:
        model = models.StatusChange
        fields = '__all__'

class FetchTravelForwardingSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.TravelForwarding
        fields = '__all__'

class PatchAdvanceSalaryRequestsSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=500)
    request_id = serializers.CharField(max_length=500)

class FetchApprovalSerializer(serializers.ModelSerializer):
    approved_by = UsersSerializer()

    class Meta:
        model = models.Approval
        fields = '__all__'

class FullFetchApprovalSerializer(serializers.ModelSerializer):
    approved_by = UsersSerializer()
    traveler = SlimFetchTravelerSerializer()

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

class TravelForwardingSerializer(serializers.Serializer):
    traveler = serializers.CharField(max_length=500)
    send_to = serializers.CharField(max_length=500)

class CostingSerializer(serializers.Serializer):
    traveler = serializers.CharField(max_length=500)
    bill_settlement_by = serializers.CharField(max_length=500)
    




