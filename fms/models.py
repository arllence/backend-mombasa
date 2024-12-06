import uuid
from acl.models import User, SRRSDepartment, SubDepartment, OHC
from django.db import models
from django.conf import settings


class Incident(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="fms_created_by",
       null=True, blank=True
    )
    closed_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="fms_closed_by",
       null=True, blank=True
    )
    assigned_to = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="fms_assigned_to",
       null=True, blank=True
    )
    department = models.ForeignKey(
       SRRSDepartment, on_delete=models.DO_NOTHING, 
       related_name="srrs_fms_department",
       null=True, blank=True
    )
    location = models.ForeignKey(
       SubDepartment, on_delete=models.DO_NOTHING, 
       related_name="srrs_fms_sub_department",
       null=True, blank=True
    )
    ohc = models.ForeignKey(
       OHC, on_delete=models.DO_NOTHING, 
       related_name="srrs_fms_ohc",
       null=True, blank=True
    )

    uid = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=255, default='SUBMITTED')
    type_of_incident = models.CharField(max_length=255)
    priority = models.CharField(max_length=255)
    attachment = models.FileField(upload_to='documents/fms/attachments/', null=True, blank=True)
    person_affected = models.CharField(max_length=255)
    affected_person_name = models.CharField(max_length=255, null=True, blank=True)
    type_of_issue = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    date_of_incident = models.DateField()
    time_of_incident = models.TimeField()
    affected_person_phone = models.CharField(max_length=255, null=True, blank=True)
    ks_number = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    assignee_comment = models.TextField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_closed = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.uid

    class Meta:
        db_table = u'"{}\".\"incidents"'.format(settings.FEEDBACK_MANAGEMENT_SYSTEM)


class Note(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="fms_note_by"
    )
    incident = models.ForeignKey(
        Incident, on_delete=models.DO_NOTHING,
        related_name="note_incident_instance"
    )
    note = models.TextField()
   
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.incident.uid)

    class Meta:
        db_table = u'"{}\".\"notes"'.format(settings.FEEDBACK_MANAGEMENT_SYSTEM)



class StatusChange(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(
        Incident, on_delete=models.DO_NOTHING,
        related_name="status_change_incident_instance"
    )
    status = models.CharField(max_length=255)
    status_for = models.CharField(max_length=255, null=True, blank=True)
    action_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="fms_action_by",
       null=True, blank=True
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.incident.uid)

    class Meta:
        db_table = u'"{}\".\"status_change"'.format(settings.FEEDBACK_MANAGEMENT_SYSTEM)


class PlatformAdmin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    admin = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="fms_admin"
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="fms_admin_created_by"
    )

    status = models.CharField(max_length=255, default='ACTIVE')
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.admin.first_name
    
    class Meta:
        db_table = u'"{}\".\"platform_admins"'.format(settings.FEEDBACK_MANAGEMENT_SYSTEM)


