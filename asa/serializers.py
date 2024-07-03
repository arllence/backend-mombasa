from django.db.models import  Q
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchSRRSDepartmentSerializer, SlimFetchSRRSDepartmentSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from asa import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)


class UpdateGeneralNameSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)

class EmployeeSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=500)
    email = serializers.CharField(max_length=500)
    employee_no = serializers.CharField(max_length=255)
    employee_type = serializers.CharField(max_length=255)
    # title = serializers.CharField(max_length=255)
    department = serializers.CharField(max_length=255)
    is_doctor = serializers.CharField(max_length=10)

class DoctorsSerializer(serializers.Serializer):
    # employee = serializers.CharField(max_length=500)
    type = serializers.CharField(max_length=500)
    specialty = serializers.CharField(max_length=255)
    admitting_rights = serializers.CharField(max_length=255)
    clinic = serializers.CharField(max_length=255)

class SystemAccessSerializer(serializers.Serializer):
    employee = serializers.CharField(max_length=500)
    system = serializers.CharField(max_length=500)

class ModuleAccessSerializer(serializers.Serializer):
    employee = serializers.CharField(max_length=500)
    system = serializers.CharField(max_length=500)
    modules = serializers.CharField(max_length=500)

class FetchRequestSerializer(serializers.ModelSerializer):
    department = FetchSRRSDepartmentSerializer()
    access = serializers.SerializerMethodField()
    doctor_info = serializers.SerializerMethodField()
    system_access = serializers.SerializerMethodField()
    module_access = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Employee
        fields = '__all__'

    def get_access(self, obj):
        try:
            request = models.Access.objects.filter(employee=obj)
            serializer = SlimFetchAccessSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 
        
    def get_doctor_info(self, obj):
        try:
            request = models.DoctorInfo.objects.filter(employee=obj)
            serializer = SlimFetchDoctorInfoSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 
        
    def get_system_access(self, obj):
        try:
            request = models.SystemAccess.objects.filter(employee=obj)
            serializer = SlimFetchSystemAccessSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 
        
    def get_module_access(self, obj):
        try:
            request = models.ModuleAccess.objects.filter(employee=obj)
            serializer = SlimFetchModuleAccessSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 


class SlimFetchEmployeeSerializer(serializers.ModelSerializer):
    department = FetchSRRSDepartmentSerializer()
    
    class Meta:
        model = models.Employee
        fields = '__all__'

    

# class FetchAccessSerializer(serializers.ModelSerializer):
#     employee = serializers.SerializerMethodField()
#     class Meta:
#         model = models.Access
#         fields = '__all__'

#     def get_employee(self, obj):
#         try:
#             request = models.ModuleAccess.objects.filter(employee=obj)
#             serializer = SlimFetchModuleAccessSerializer(request, many=True)
#             return serializer.data
#         except (ValidationError, ObjectDoesNotExist):
#             return {}
#         except Exception as e:
#             print(e)
#             # logger.error(e)
#             return {} 
        
class SlimFetchAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Access
        fields = '__all__'

class SlimFetchDoctorInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DoctorInfo
        fields = '__all__'

class SlimFetchSystemAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SystemAccess
        fields = '__all__'

class SlimFetchModuleAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ModuleAccess
        fields = '__all__'

class SlimFetchSystemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.System
        fields = '__all__'

