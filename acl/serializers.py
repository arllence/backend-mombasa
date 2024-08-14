from django.db.models import  Q
from acl import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

class CreateDepartmentSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

class UpdateDepartmentSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)

class SlimUsersSerializer(serializers.ModelSerializer):
    id = serializers.CharField()
    email = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    employee_no = serializers.CharField()

    class Meta:
        model = get_user_model()
        fields = [
            'id', 'email', 'first_name', 'last_name', 'employee_no', 
        ]

class SlimFetchSltSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Slt
        fields = '__all__'
    
class FetchDepartmentSerializer(serializers.ModelSerializer):
    slt = SlimFetchSltSerializer()
    hod = SlimUsersSerializer()
    class Meta:
        model = models.Department
        fields = '__all__'


class FetchSRRSDepartmentSerializer(serializers.ModelSerializer):
    slt = SlimUsersSerializer()
    hr_partner = SlimUsersSerializer()
    hods = serializers.SerializerMethodField()
    class Meta:
        model = models.SRRSDepartment
        fields = '__all__'


    def get_hods(self, obj):
        try:
            hods = models.Hods.objects.filter(department=obj)
            serializer = FetchHODsSerializer(hods, many=True)
            return serializer.data
        except (ValidationError, ObjectDoesNotExist):
            return {}
        except Exception as e:
            print(e)
            # logger.error(e)
            return {} 

class SlimFetchSRRSDepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SRRSDepartment
        fields = '__all__'

class FetchSubDepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SubDepartment
        fields = '__all__'

class FetchOHCSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OHC
        fields = '__all__'

class FetchHODsSerializer(serializers.ModelSerializer):
    hod = SlimUsersSerializer()
    department = SlimFetchSRRSDepartmentSerializer()
    class Meta:
        model = models.Hods
        fields = '__all__'

class UserDetailSerializer(serializers.Serializer):
    email = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    department_id = serializers.CharField()

class UserIdSerializer(serializers.Serializer):
    user_id = serializers.CharField()

class SystemUsersSerializer(serializers.Serializer):
    UserId = serializers.CharField()
    email = serializers.CharField()
    firstname = serializers.CharField()
    lastname = serializers.CharField()
    phone_number = serializers.CharField()

class SuspendUserSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    remarks = serializers.CharField()

class GroupSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()

class RoleSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()

class ManageRoleSerializer(serializers.Serializer):
    role_id = serializers.ListField(required=True)
    account_id = serializers.CharField()

class EditUserSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    # id_number = serializers.CharField()
    account_id = serializers.CharField()


class UsersSerializer(serializers.ModelSerializer):
    id = serializers.CharField()
    email = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    is_active = serializers.CharField()
    is_suspended = serializers.CharField()
    department = FetchDepartmentSerializer()
    srrs_department = FetchSRRSDepartmentSerializer()
    sub_department = FetchSubDepartmentSerializer()
    ohc = FetchOHCSerializer()
    user_groups = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = get_user_model()
        fields = [
            'id', 'email', 'first_name', 'last_name', 'employee_no', 'is_active', 'is_suspended','department', 'srrs_department', 'sub_department', 'ohc','user_groups', 'date_created'
        ]

    def get_user_groups(self, obj):
        allgroups = Group.objects.filter(user=obj)
        serializer = GroupSerializer(allgroups, many=True)
        return serializer.data
    
class SlimUsersSerializer(serializers.ModelSerializer):
    id = serializers.CharField()
    email = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    class Meta:
        model = get_user_model()
        fields = [
            'id', 'email', 'first_name', 'last_name'
        ]

class CreateUserSerializer(serializers.Serializer):
    email = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    password = serializers.CharField()
    department = serializers.CharField()
    otp = serializers.CharField()

class InvitationLinkSerializer(serializers.Serializer):
    email = serializers.CharField()

class SwapUserDepartmentSerializer(serializers.Serializer):
    department_id = serializers.CharField()
    user_id = serializers.CharField()
class PasswordChangeSerializer(serializers.Serializer):
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()
    current_password = serializers.CharField()

class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

class CreateSltSerializer(serializers.Serializer):
    name = serializers.CharField()
    lead = serializers.CharField()

class UpdateSltSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)
    lead = serializers.CharField(max_length=255)

class FetchSltSerializer(serializers.ModelSerializer):
    lead = UsersSerializer()
    class Meta:
        model = models.Slt
        fields = '__all__'