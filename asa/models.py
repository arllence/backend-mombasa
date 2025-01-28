import uuid
from acl.models import User, SRRSDepartment
from django.db import models
from django.conf import settings


class System(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = u'"{}\".\"systems"'.format(settings.ACCESS_SERVICE_AGREEMENT)


class Employee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    department = models.ForeignKey(
        SRRSDepartment, on_delete=models.DO_NOTHING,
        related_name="asa_employee_department"
    )

    name = models.CharField(max_length=500)
    email = models.EmailField(max_length=500)
    employee_no = models.CharField(max_length=255, unique=True)
    employee_type = models.CharField(max_length=255)
    contract_expire_date = models.DateField(null=True, blank=True)
    warehouse = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(max_length=255, default='INACTIVE')
    signature = models.TextField(null=True, blank=True)
    is_doctor = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        db_table = u'"{}\".\"employees"'.format(settings.ACCESS_SERVICE_AGREEMENT)

class Access(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee, on_delete=models.DO_NOTHING,
        related_name="asa_employee",
        null=True, blank=True
    )
    granted_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="asa_granted_by",
       null=True, blank=True
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="asa_created_for",
       null=True, blank=True
    )
    created_for = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="asa_created_by",
       null=True, blank=True
    )
    is_hod_approved = models.BooleanField(default=False)
    is_ict_approved = models.BooleanField(default=False)
    agreement_accepted = models.BooleanField(default=False)
    agreement_details = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=255, default='PENDING')
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.employee.name

    class Meta:
        db_table = u'"{}\".\"access"'.format(settings.ACCESS_SERVICE_AGREEMENT)


class DoctorInfo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee, on_delete=models.DO_NOTHING,
        related_name="asa_employee_doctor_info"
    )
    type = models.CharField(max_length=255)
    specialty = models.CharField(max_length=255)
    admitting_rights = models.CharField(max_length=255)
    pc_rate = models.CharField(max_length=255, null=True, blank=True)
    clinic = models.CharField(max_length=255)
    services = models.JSONField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.employee.name

    class Meta:
        db_table = u'"{}\".\"doctor_info"'.format(settings.ACCESS_SERVICE_AGREEMENT)


class SystemAccess(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee, on_delete=models.DO_NOTHING,
        related_name="asa_employee_system_access"
    )
    system = models.ForeignKey(
        System, on_delete=models.DO_NOTHING,
        related_name="asa_system"
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.name} -- {self.system.name}"

    class Meta:
        db_table = u'"{}\".\"system_access"'.format(settings.ACCESS_SERVICE_AGREEMENT)


class ModuleAccess(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee, on_delete=models.DO_NOTHING,
        related_name="asa_module_employee"
    )
    modules = models.JSONField()
    remarks = models.TextField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.name}"

    class Meta:
        db_table = u'"{}\".\"module_access"'.format(settings.ACCESS_SERVICE_AGREEMENT)

class RoleAccess(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee, on_delete=models.DO_NOTHING,
        related_name="asa_role_employee"
    )
    roles = models.JSONField()
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.name}"

    class Meta:
        db_table = u'"{}\".\"role_access"'.format(settings.ACCESS_SERVICE_AGREEMENT)


class AdditionalSystemAccess(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee, on_delete=models.DO_NOTHING,
        related_name="asa_additional_employee_system_access"
    )
    system = models.ForeignKey(
        System, on_delete=models.DO_NOTHING,
        related_name="asa_additional_system"
    )
    status = models.CharField(max_length=20, default='REQUESTED')
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.name} -- {self.system.name}"

    class Meta:
        db_table = u'"{}\".\"additional_system_access"'.format(settings.ACCESS_SERVICE_AGREEMENT)


class AdditionalModuleAccess(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee, on_delete=models.DO_NOTHING,
        related_name="asa_additional_module_employee"
    )
    modules = models.JSONField()
    status = models.CharField(max_length=20, default='REQUESTED')
    remarks = models.TextField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.name}"

    class Meta:
        db_table = u'"{}\".\"additional_module_access"'.format(settings.ACCESS_SERVICE_AGREEMENT)

class RequestApprover(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    approver = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="asa_request_approver"
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="asa_approver_created_by"
    )

    status = models.CharField(max_length=255, default='ACTIVE')
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.approver.first_name
    
    class Meta:
        db_table = u'"{}\".\"approvers"'.format(settings.ACCESS_SERVICE_AGREEMENT)
    

class StatusChange(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    access = models.ForeignKey(
        Access, on_delete=models.DO_NOTHING,
        related_name="status_change_access_instance"
    )
    status = models.CharField(max_length=255)
    status_for = models.CharField(max_length=500, null=True, blank=True)
    action_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="asa_action_by"
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.access.uid)

    class Meta:
        db_table = u'"{}\".\"status_change"'.format(settings.ACCESS_SERVICE_AGREEMENT)


class RequestHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee, on_delete=models.DO_NOTHING,
        related_name="asa_employee_history"
    )
    data = models.JSONField()
    triggered_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="action_triggered_by"
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.employee.name)

    class Meta:
        db_table = u'"{}\".\"request_history"'.format(settings.ACCESS_SERVICE_AGREEMENT)



class Module(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    system = models.ForeignKey(
        System, on_delete=models.DO_NOTHING,
        related_name="asa_module_system"
    )
    name = models.CharField(max_length=255)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} -- {self.system.name}"

    class Meta:
        db_table = u'"{}\".\"modules"'.format(settings.ACCESS_SERVICE_AGREEMENT)

class Right(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(
        Module, on_delete=models.DO_NOTHING,
        related_name="asa_module"
    )
    name = models.CharField(max_length=255)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} -- {self.module.name}"

    class Meta:
        db_table = u'"{}\".\"rights"'.format(settings.ACCESS_SERVICE_AGREEMENT)


class Roles(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    system = models.ForeignKey(
        System, on_delete=models.DO_NOTHING,
        related_name="asa_system_role"
    )
    name = models.CharField(max_length=255)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} -- {self.system.name}"

    class Meta:
        db_table = u'"{}\".\"roles"'.format(settings.ACCESS_SERVICE_AGREEMENT)


class Verifications(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    access = models.ForeignKey(
        Access, on_delete=models.DO_NOTHING,
        related_name="asa_access"
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="asa_access_created_for"
    )
    is_hod_verified = models.BooleanField(default=False)
    is_ict_verified = models.BooleanField(default=False)
    hod_status = models.CharField(max_length=255)
    ict_status = models.CharField(max_length=255)
    year = models.IntegerField()
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.access.employee.name

    class Meta:
        db_table = u'"{}\".\"verifications"'.format(settings.ACCESS_SERVICE_AGREEMENT)

    
class VerificationStatusChange(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    access = models.ForeignKey(
        Access, on_delete=models.DO_NOTHING,
        related_name="asa_status_change_access_instance"
    )
    status = models.CharField(max_length=255)
    status_for = models.CharField(max_length=500, null=True, blank=True)
    action_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="verification_action_by"
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.access.employee.name)

    class Meta:
        db_table = u'"{}\".\"verifications_status_change"'.format(settings.ACCESS_SERVICE_AGREEMENT)