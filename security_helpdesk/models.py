import uuid
from acl.models import User, SRRSDepartment, SubDepartment, OHC
from django.db import models
from django.conf import settings
from mms.models import Quote as MMDQuote
from ict_helpdesk.models import Facility


# class JobType(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     name = models.CharField(max_length=255)
#     is_deleted = models.BooleanField(default=False)
#     date_created = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.name

#     class Meta:
#         db_table = u'"{}\".\"job_types"'.format(settings.SECURITY_HELPDESK)


# class Category(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     name = models.CharField(max_length=255)
#     is_deleted = models.BooleanField(default=False)
#     date_created = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.name

#     class Meta:
#         db_table = u'"{}\".\"categories"'.format(settings.SECURITY_HELPDESK)

class Priority(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    expected_closure = models.IntegerField()
    numbering = models.IntegerField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['numbering'] 
        db_table = u'"{}\".\"priority"'.format(settings.SECURITY_HELPDESK)

class Issue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING, 
        related_name="security_helpdesk_created_by", 
        null=True, blank=True, db_index=True
    )
    closed_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING, 
        related_name="security_helpdesk_closed_by",
        null=True, blank=True, db_index=True
    )
    assigned_to = models.ForeignKey(
        User, on_delete=models.DO_NOTHING, 
        related_name="security_helpdesk_assigned_to",
        null=True, blank=True, db_index=True
    )
    priority = models.ForeignKey(
        Priority, on_delete=models.DO_NOTHING, 
        related_name="security_helpdesk_priority",
        null=True, blank=True, db_index=True
    )
    department = models.ForeignKey(
        SRRSDepartment, on_delete=models.DO_NOTHING, 
        related_name="security_helpdesk_department",
        null=True, blank=True, db_index=True
    )
    # job_type = models.ForeignKey(
    #     JobType, on_delete=models.DO_NOTHING, 
    #     related_name="security_helpdesk_job_type",
    #     null=True, blank=True, db_index=True
    # )
    facility = models.ForeignKey(
        Facility, on_delete=models.DO_NOTHING, 
        related_name="security_helpdesk_facility",
        null=True, blank=True, db_index=True
    )
    # category = models.ForeignKey(
    #     Category, on_delete=models.DO_NOTHING, 
    #     related_name="security_helpdesk_category",
    #     null=True, blank=True, db_index=True
    # )

    uid = models.CharField(max_length=50, unique=True, db_index=True)
    status = models.CharField(max_length=255, default='SUBMITTED', db_index=True)
    attachment = models.FileField(upload_to='documents/security_helpdesk/attachments/', null=True, blank=True)
    issue = models.TextField()
    subject = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    telephone = models.CharField(max_length=255, null=True, blank=True)
    is_acknowledged = models.BooleanField(default=False, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    date_assigned = models.DateTimeField(null=True, blank=True, db_index=True)
    date_completed = models.DateTimeField(null=True, blank=True, db_index=True)
    date_reopened = models.DateTimeField(null=True, blank=True, db_index=True)
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)
    date_closed = models.DateTimeField(null=True, blank=True, db_index=True)

    def __str__(self):
        return self.uid

    class Meta:
        db_table = u'"{}"."issues"'.format(settings.SECURITY_HELPDESK)
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['priority']),
            models.Index(fields=['department']),
            models.Index(fields=['date_created']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['is_acknowledged']),
        ]
        index_together = [
            ('assigned_to', 'status'),
            ('priority', 'status'),
            ('department', 'status'),
        ]

class Assignees(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignee = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="security_issue_assignee"
    )
    assigned_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="security_issue_assigned_by",
       null=True, blank=True
    )
    issue = models.ForeignKey(
        Issue, on_delete=models.DO_NOTHING,
        related_name="security_assignee_issue_instance"
    )
   
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.issue.uid)

    class Meta:
        db_table = u'"{}\".\"assignees"'.format(settings.SECURITY_HELPDESK)


class Note(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="security_helpdesk_note_by"
    )
    issue = models.ForeignKey(
        Issue, on_delete=models.DO_NOTHING,
        related_name="security_note_issue_instance"
    )
    note = models.TextField()
   
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.issue.uid)

    class Meta:
        db_table = u'"{}\".\"notes"'.format(settings.SECURITY_HELPDESK)


class Quote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    issue = models.ForeignKey(
        Issue, on_delete=models.DO_NOTHING,
        related_name="security_quote_issue_instance"
    )
    quote = models.ForeignKey(
        MMDQuote, on_delete=models.DO_NOTHING,
        related_name="security_mmd_quote_issue_instance"
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.issue.uid)

    class Meta:
        db_table = u'"{}\".\"quotes"'.format(settings.SECURITY_HELPDESK)

class StatusChange(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    issue = models.ForeignKey(
        Issue, on_delete=models.DO_NOTHING,
        related_name="security_status_change_issue_instance"
    )
    status = models.CharField(max_length=255)
    status_for = models.CharField(max_length=255, null=True, blank=True)
    action_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="security_helpdesk_action_by",
       null=True, blank=True
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.issue.uid)

    class Meta:
        db_table = u'"{}\".\"status_changes"'.format(settings.SECURITY_HELPDESK)


class PlatformAdmin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    admin = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="security_helpdesk_admin"
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="security_helpdesk_admin_created_by"
    )
    # category = models.ForeignKey(
    #    Category, on_delete=models.DO_NOTHING, 
    #    related_name="security_helpdesk_admin_category",
    #    null=True, blank=True
    # )

    status = models.CharField(max_length=255, default='ACTIVE')
    is_hod = models.BooleanField(default=False)
    is_slt = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.admin.first_name
    
    class Meta:
        db_table = u'"{}\".\"platform_admins"'.format(settings.SECURITY_HELPDESK)



class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    issue = models.ForeignKey(
        Issue, on_delete=models.DO_NOTHING, 
        related_name="security_ticket_documents", db_index=True)
    
    uploaded_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="security_ticket_document_uploaded_by"
    )

    document = models.FileField(upload_to='documents/security_helpdesk/uploads/')
    file_name = models.CharField(max_length=500)
    file_type = models.CharField(max_length=255)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file_name}"
    
    class Meta:
        db_table = u'"{}\".\"documents"'.format(settings.SECURITY_HELPDESK)
        indexes = [
            models.Index(fields=["issue"], name='security_issue_idx')
        ]