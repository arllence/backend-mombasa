import uuid
from acl.models import User, SRRSDepartment, SubDepartment, OHC
from django.db import models
from django.conf import settings
from mms.models import Quote as MMDQuote

class Section(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = u'"{}\".\"sections"'.format(settings.MAINTENANCE_HELPDESK_SYSTEM)


class JobType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = u'"{}\".\"job_types"'.format(settings.MAINTENANCE_HELPDESK_SYSTEM)


class EquipmentType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = u'"{}\".\"equipment_types"'.format(settings.MAINTENANCE_HELPDESK_SYSTEM)

class Facility(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=255, default='OHC')
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = u'"{}\".\"facilities"'.format(settings.MAINTENANCE_HELPDESK_SYSTEM)

class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = u'"{}\".\"categories"'.format(settings.MAINTENANCE_HELPDESK_SYSTEM)

class Priority(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    expected_closure = models.IntegerField()
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = u'"{}\".\"priority"'.format(settings.MAINTENANCE_HELPDESK_SYSTEM)

class Issue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="mhs_created_by", 
       null=True, blank=True
    )
    closed_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="mhs_closed_by",
       null=True, blank=True
    )
    assigned_to = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="mhs_assigned_to",
       null=True, blank=True
    )
    priority = models.ForeignKey(
       Priority, on_delete=models.DO_NOTHING, 
       related_name="mhs_priority",
       null=True, blank=True
    )
    department = models.ForeignKey(
       SRRSDepartment, on_delete=models.DO_NOTHING, 
       related_name="srrs_mhs_department",
       null=True, blank=True
    )
    section = models.ForeignKey(
       Section, on_delete=models.DO_NOTHING, 
       related_name="mhs_section",
       null=True, blank=True
    )
    job_type = models.ForeignKey(
       JobType, on_delete=models.DO_NOTHING, 
       related_name="mhs_job_type",
       null=True, blank=True
    )
    equipment_type = models.ForeignKey(
       EquipmentType, on_delete=models.DO_NOTHING, 
       related_name="mhs_equipment_type",
       null=True, blank=True
    )
    facility = models.ForeignKey(
       Facility, on_delete=models.DO_NOTHING, 
       related_name="mhs_facility",
       null=True, blank=True
    )
    category = models.ForeignKey(
       Category, on_delete=models.DO_NOTHING, 
       related_name="mhs_category",
       null=True, blank=True
    )

    uid = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=255, default='SUBMITTED')
    attachment = models.FileField(upload_to='documents/mhd/attachments/', null=True, blank=True)
    issue = models.TextField()
    subject = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    is_acknowledged = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    date_assigned = models.DateTimeField(null=True, blank=True)
    date_completed = models.DateTimeField(null=True, blank=True)
    date_reopened = models.DateTimeField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_closed = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.uid

    class Meta:
        db_table = u'"{}\".\"issues"'.format(settings.MAINTENANCE_HELPDESK_SYSTEM)


class Assignees(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignee = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="mhd_assignee"
    )
    assigned_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="mhd_assigned_by",
       null=True, blank=True
    )
    issue = models.ForeignKey(
        Issue, on_delete=models.DO_NOTHING,
        related_name="assignee_issue_instance"
    )
   
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.issue.uid)

    class Meta:
        db_table = u'"{}\".\"assignees"'.format(settings.MAINTENANCE_HELPDESK_SYSTEM)


class Note(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="mhs_note_by"
    )
    issue = models.ForeignKey(
        Issue, on_delete=models.DO_NOTHING,
        related_name="note_issue_instance"
    )
    note = models.TextField()
   
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.issue.uid)

    class Meta:
        db_table = u'"{}\".\"notes"'.format(settings.MAINTENANCE_HELPDESK_SYSTEM)


class Quote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    issue = models.ForeignKey(
        Issue, on_delete=models.DO_NOTHING,
        related_name="quote_issue_instance"
    )
    quote = models.ForeignKey(
        MMDQuote, on_delete=models.DO_NOTHING,
        related_name="mmd_quote_issue_instance"
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.issue.uid)

    class Meta:
        db_table = u'"{}\".\"quotes"'.format(settings.MAINTENANCE_HELPDESK_SYSTEM)

class StatusChange(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    issue = models.ForeignKey(
        Issue, on_delete=models.DO_NOTHING,
        related_name="status_change_issue_instance"
    )
    status = models.CharField(max_length=255)
    status_for = models.CharField(max_length=255, null=True, blank=True)
    action_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="mhs_action_by",
       null=True, blank=True
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.issue.uid)

    class Meta:
        db_table = u'"{}\".\"status_changes"'.format(settings.MAINTENANCE_HELPDESK_SYSTEM)


class PlatformAdmin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    admin = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="mhs_admin"
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="mhs_admin_created_by"
    )
    category = models.ForeignKey(
       Category, on_delete=models.DO_NOTHING, 
       related_name="mhs_admin_category",
       null=True, blank=True
    )

    status = models.CharField(max_length=255, default='ACTIVE')
    location = models.CharField(max_length=255, null=True, blank=True)
    is_hod = models.BooleanField(default=False)
    is_slt = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.admin.first_name
    
    class Meta:
        db_table = u'"{}\".\"platform_admins"'.format(settings.MAINTENANCE_HELPDESK_SYSTEM)
