import uuid
from acl.models import User, SRRSDepartment
from django.db import models
from django.conf import settings


class Patient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uid = models.CharField(max_length=50, unique=True)
    admission_no = models.CharField(max_length=255)
    status = models.CharField(max_length=255, default='PENDING')
    illness_severity = models.CharField(max_length=255)
    patient_summary = models.TextField(null=True, blank=True)
    action_list = models.TextField(null=True, blank=True)
    # situation_awareness = models.JSONField()
    synthesis_by_receiver = models.TextField(null=True, blank=True)
    acknowledgement = models.JSONField(null=True, blank=True)
    bio = models.JSONField()
    handover_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="handover_by"
    )
    handover_to = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="handover_to"
    )
    handover_acceptance_date = models.DateTimeField(null=True, blank=True)
    attestation = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = u'"{}\".\"patients"'.format(settings.IPASS)

    def __str__(self):
        return str(self.admission_no) 
    

class PlatformDoctor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    doctor = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="ipass_doctor"
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="ipass_doctor_created_by"
    )

    status = models.CharField(max_length=255, default='ACTIVE')
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.doctor.first_name
    
    class Meta:
        db_table = u'"{}\".\"platform_doctors"'.format(settings.IPASS)


class EmailExempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    doctor = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="ipass_email_exempt",
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="ipass_email_exempt_created_by"
    )

    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.doctor.first_name
    
    class Meta:
        db_table = u'"{}\".\"email_exempts"'.format(settings.IPASS)


class StatusChange(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient, on_delete=models.DO_NOTHING,
        related_name="status_change_patient_instance"
    )
    status = models.CharField(max_length=255)
    status_for = models.CharField(max_length=255, null=True, blank=True)
    action_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="ipass_action_by",
       null=True, blank=True
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.patient.admission_no)

    class Meta:
        db_table = u'"{}\".\"status_change"'.format(settings.IPASS)

