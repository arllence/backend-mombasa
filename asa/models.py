import uuid
from acl.models import User
from django.db import models
from django.conf import settings
from srrs.models import Employee


class System(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = u'"{}\".\"systems"'.format(settings.ACCESS_SERVICE_AGREEMENT)


class Access(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee, on_delete=models.DO_NOTHING,
        related_name="asa_employee"
    )
    granted_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="asa_granted_by"
    )
    status = models.CharField(max_length=255, default='REQUESTED')
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
        related_name="asa_employee"
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


class CanAccess(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee, on_delete=models.DO_NOTHING,
        related_name="asa_employee"
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
        db_table = u'"{}\".\"can_access"'.format(settings.ACCESS_SERVICE_AGREEMENT)


class StatusChange(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    access = models.ForeignKey(
        Access, on_delete=models.DO_NOTHING,
        related_name="status_change_access_instance"
    )
    status = models.CharField(max_length=255)
    status_for = models.CharField(max_length=255, null=True, blank=True)
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
