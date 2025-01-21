from django.db.models import  Q
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchSRRSDepartmentSerializer, SlimFetchSRRSDepartmentSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from asa import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from asa.utils import shared_fxns


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
    # signature = serializers.CharField(min_length=10)
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

class ApproverSerializer(serializers.Serializer):
    approver = serializers.CharField(max_length=255)

class UpdateApproverSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    approver = serializers.CharField(max_length=255)

class UpdateRequestSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    status = serializers.CharField(max_length=255)


class SlimFetchSystemsSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    class Meta:
        model = models.System
        fields = '__all__'

    def get_roles(self, obj):
        try:
            request = models.Roles.objects.filter(system=obj)
            serializer = SlimFetchRoleSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return []
        except Exception as e:
            print(e)
            # logger.error(e)
            return []
class FetchRequestSerializer(serializers.ModelSerializer):
    department = FetchSRRSDepartmentSerializer()
    access = serializers.SerializerMethodField()
    doctor_info = serializers.SerializerMethodField()
    system_access = serializers.SerializerMethodField()
    additional_system_access = serializers.SerializerMethodField()
    module_access = serializers.SerializerMethodField()
    additional_module_access = serializers.SerializerMethodField()
    approvals = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Employee
        fields = '__all__'

    def get_access(self, obj):
        try:
            request = models.Access.objects.get(employee=obj)
            serializer = SlimFetchAccessSerializer(request, many=False)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 
        
    def get_doctor_info(self, obj):
        try:
            request = models.DoctorInfo.objects.get(employee=obj)
            serializer = SlimFetchDoctorInfoSerializer(request, many=False)
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
    
    def get_additional_system_access(self, obj):
        try:
            request = models.AdditionalSystemAccess.objects.filter(employee=obj,status='REQUESTED')
            serializer = SlimFetchAdditionalSystemAccessSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 
        
    def get_module_access(self, obj):
        try:
            request = models.ModuleAccess.objects.get(employee=obj)
            
            serializer = SlimFetchModuleAccessSerializer(request, many=False)

            modules = serializer.data['modules']

            serialized_modules = []
            for module in modules:
                selected_module = module['module']
                selected_rights = module['rights']

                selected_module = models.Module.objects.get(id=selected_module)
                selected_module = SlimFetchModuleSerializer(selected_module, many=False).data
                
                rights = []
                for right in selected_rights:
                    right = models.Right.objects.get(id=right)
                    right = SlimFetchRightSerializer(right,many=False).data
                    rights.append(right)

                module = {
                    "module" : selected_module,
                    "rights" : rights
                }

                serialized_modules.append(module)

            serializer_data = serializer.data
            serializer_data['modules'] = serialized_modules
            return serializer_data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {}

    def get_additional_module_access(self, obj):
        try:
            request = models.AdditionalModuleAccess.objects.filter(employee=obj,status='REQUESTED')
            serializer = SlimFetchAdditionalModuleAccessSerializer(request, many=True)
            # return serializer.data
            # print(serializer.data)
            requested = shared_fxns.convert_to_json_serializable(serializer.data)
            
            for item in requested:
                modules = item['modules']
                serialized_modules = []
                for module in modules:
                    selected_module = module['module']
                    selected_rights = module['rights']

                    selected_module = models.Module.objects.get(id=selected_module)
                    selected_module = SlimFetchModuleSerializer(selected_module, many=False).data
                    
                    rights = []
                    for right in selected_rights:
                        right = models.Right.objects.get(id=right)
                        right = SlimFetchRightSerializer(right,many=False).data
                        rights.append(right)

                    module = {
                        "module" : selected_module,
                        "rights" : rights
                    }

                    serialized_modules.append(module)
                item['modules'] = serialized_modules

            # serializer_data = serializer.data
            # serializer_data['modules'] = serialized_modules
            return requested
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 
        
    def get_approvals(self, obj):
        try:
            request = models.StatusChange.objects.filter(access__employee=obj)
            serializer = FetchStatusChangeSerializer(request, many=True)
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

class FetchRequestApproverSerializer(serializers.ModelSerializer):
    approver = UsersSerializer()
    created_by = UsersSerializer()
    
    class Meta:
        model = models.RequestApprover
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
    system = SlimFetchSystemsSerializer()
    class Meta:
        model = models.SystemAccess
        fields = '__all__'

class SlimFetchAdditionalSystemAccessSerializer(serializers.ModelSerializer):
    system = SlimFetchSystemsSerializer()
    class Meta:
        model = models.AdditionalSystemAccess
        fields = '__all__'

class SlimFetchModuleAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ModuleAccess
        fields = '__all__'

class SlimFetchAdditionalModuleAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AdditionalModuleAccess
        fields = '__all__'

class FetchApproverSerializer(serializers.ModelSerializer):
    approver = UsersSerializer()
    created_by = UsersSerializer()
    
    class Meta:
        model = models.RequestApprover
        fields = '__all__'

class FetchStatusChangeSerializer(serializers.ModelSerializer):
    action_by = SlimUsersSerializer()
    class Meta:
        model = models.StatusChange
        fields = '__all__'

class IdNumberSerializer(serializers.Serializer):
    id_number = serializers.IntegerField()
    request_id = serializers.CharField(max_length=255)

class SlimFetchRightSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Right
        fields = '__all__'       
class ModuleSerializer(serializers.Serializer):
    system = serializers.CharField(max_length=255)
    modules = serializers.ListField(min_length=1)

class PutModuleSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    system = serializers.CharField(max_length=255)
    modules = serializers.ListField(min_length=1)

class FetchModuleSerializer(serializers.ModelSerializer):
    system = SlimFetchSystemsSerializer()
    rights = serializers.SerializerMethodField()
    class Meta:
        model = models.Module
        fields = '__all__'

    def get_rights(self, obj):
        try:
            request = models.Right.objects.filter(module=obj,is_deleted=False)
            serializer = SlimFetchRightSerializer(request, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 
        
class SlimFetchModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Module
        fields = '__all__'
        
class PutRightSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)

class UpdateAdditionalRequestSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    status = serializers.CharField(max_length=255)
    option = serializers.CharField(max_length=255)

class RoleSerializer(serializers.Serializer):
    system = serializers.CharField(max_length=255)
    roles = serializers.ListField(min_length=1)

class PutRoleSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)

class FetchRoleSerializer(serializers.ModelSerializer):
    system = SlimFetchSystemsSerializer()
    class Meta:
        model = models.Roles
        fields = '__all__' 

class SlimFetchRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Roles
        fields = '__all__' 
