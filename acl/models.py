import os
import uuid
import datetime
from django.db import models
from django.conf import settings
from .managers import UserManager
from django.contrib.auth.models import Group, PermissionsMixin
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser


class Slt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    lead = models.ForeignKey(
        'User', related_name='slts', 
        null=True, blank=True,
        on_delete=models.DO_NOTHING
    )
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "slts"
        

class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slt = models.ForeignKey(
        Slt, related_name='departments', 
        null=True, blank=True,
        on_delete=models.DO_NOTHING
    )
    hod = models.ForeignKey(
        'User', related_name='department_hod', 
        null=True, blank=True,
        on_delete=models.DO_NOTHING
    )
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "departments"

class SRRSDepartment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slt = models.ForeignKey(
        'User', related_name='srrs_department_slt', 
        null=True, blank=True,
        on_delete=models.DO_NOTHING
    )
    # hod = models.ForeignKey(
    #     'User', related_name='srrs_department_hod', 
    #     null=True, blank=True,
    #     on_delete=models.DO_NOTHING
    # )
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "srrs_departments"


class SubDepartment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "sub_departments"


class OHC(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "ohcs"


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.CharField(max_length=100, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    employee_no = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    is_defaultpassword = models.BooleanField(default=True)
    date_created = models.DateTimeField(auto_now_add=True)
    department = models.ForeignKey(
        Department, related_name="user_department", 
        null=True, blank=True,
        on_delete=models.DO_NOTHING
    )
    srrs_department = models.ForeignKey(
        SRRSDepartment, related_name="srrs_user_department", 
        null=True, blank=True,
        on_delete=models.DO_NOTHING
    )
    sub_department = models.ForeignKey(
        SubDepartment, related_name="srrs_user_sub_department", 
        null=True, blank=True,
        on_delete=models.DO_NOTHING
    )
    ohc = models.ForeignKey(
        OHC, related_name="srrs_user_ohc", 
        null=True, blank=True,
        on_delete=models.DO_NOTHING
    )
    objects = UserManager()

    USERNAME_FIELD = "email"

    def __str__(self):
        return '%s' % (str(self.id))

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    class Meta:
        db_table = "systemusers"


class Hods(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hod = models.ForeignKey(
        User, related_name='hod', 
        on_delete=models.DO_NOTHING
    )
    department = models.ForeignKey(
        SRRSDepartment, related_name='hod_department', 
        on_delete=models.DO_NOTHING
    )
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.hod.first_name} {self.hod.last_name}"

    class Meta:
        db_table = "hods"


class AccountActivity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        User, related_name="user_account_activity", on_delete=models.DO_NOTHING
    )
    actor = models.ForeignKey(
        User, related_name="activity_actor", on_delete=models.DO_NOTHING
    )
    activity = models.TextField(null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    action_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "account_activities"

    def __str__(self):
        return str(self.id)


class Sendmail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.JSONField()
    subject = models.CharField(max_length=500)
    message = models.TextField()
    status = models.CharField(max_length=55, default="PENDING")
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "send_mail"

    def __str__(self):
        return str(self.email)