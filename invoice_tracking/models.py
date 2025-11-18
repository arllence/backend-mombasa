import uuid
from acl.models import User, SRRSDepartment
from django.db import models
from django.conf import settings

from ict_helpdesk.models import Facility


class Tracking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uid = models.CharField(max_length=50, unique=True, null=True, blank=True)
    facility = models.ForeignKey(
       Facility, on_delete=models.DO_NOTHING, 
       related_name="ict_helpdesk_tracking_facility"
    )
    type = models.CharField(max_length=255, null=True, blank=True)
    weigh_bill_no = models.CharField(max_length=255)
    courier = models.CharField(max_length=255)
    collector = models.CharField(max_length=255)
    notes = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, default='PENDING')
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    received_on = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="tracking_created_by"
    )

    class Meta:
        db_table = u'"{}\".\"tracking"'.format(settings.INVOICE_TRACKING)

    def __str__(self):
        return str(self.weigh_bill_no) 
    

class Cancellation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uid = models.CharField(max_length=50, unique=True, null=True, blank=True)
    facility = models.ForeignKey(
       Facility, on_delete=models.DO_NOTHING, 
       related_name="ict_helpdesk_cancellation_facility"
    )
    invoice_no = models.CharField(max_length=255)
    action = models.CharField(max_length=255)
    reason = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, default='PENDING')
    type = models.CharField(max_length=50, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="cancellation_created_by"
    )

    class Meta:
        db_table = u'"{}\".\"cancellation"'.format(settings.INVOICE_TRACKING)

    def __str__(self):
        return str(self.invoice_no) 

class CentralArchive(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uid = models.CharField(max_length=50, unique=True, null=True, blank=True)
    facility = models.ForeignKey(
       Facility, on_delete=models.DO_NOTHING, 
       related_name="ict_helpdesk_archive_facility"
    )
    invoice_no = models.CharField(max_length=255)
    approval_type = models.CharField(max_length=255)
    corporate = models.CharField(max_length=255)
    patient_names = models.CharField(max_length=255)
    date_of_service = models.DateField()
    status = models.CharField(max_length=50, default='UPLOADED')
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="archive_created_by"
    )

    class Meta:
        db_table = u'"{}\".\"central_archive"'.format(settings.INVOICE_TRACKING)

    def __str__(self):
        return str(self.invoice_no)    

class PlatformAdmin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    admin = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="psd_admin"
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="psd_admin_created_by"
    )

    status = models.CharField(max_length=255, default='ACTIVE')
    is_receiver = models.BooleanField(default=False)
    is_approver = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.admin.first_name
    
    class Meta:
        db_table = u'"{}\".\"platform_admins"'.format(settings.INVOICE_TRACKING)


class TrackingStatusChange(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tracked = models.ForeignKey(
        Tracking, on_delete=models.DO_NOTHING,
        related_name="status_change_tracked_instance"
    )
    status = models.CharField(max_length=255)
    action_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="tracking_action_by"
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.tracked.weigh_bill_no)

    class Meta:
        db_table = u'"{}\".\"tracking_status_change"'.format(settings.INVOICE_TRACKING)

    
class CancellationStatusChange(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cancelled = models.ForeignKey(
        Cancellation, on_delete=models.DO_NOTHING,
        related_name="status_change_cancelled_instance"
    )
    status = models.CharField(max_length=255)
    action_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="cancellation_action_by"
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.cancelled.invoice_no)

    class Meta:
        db_table = u'"{}\".\"cancellation_status_change"'.format(settings.INVOICE_TRACKING)


class CentralArchiveStatusChange(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    central_archive = models.ForeignKey(
        CentralArchive, on_delete=models.DO_NOTHING,
        related_name="status_change_archive_instance"
    )
    status = models.CharField(max_length=255)
    action_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="archive_action_by"
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.central_archive.invoice_no)

    class Meta:
        db_table = u'"{}\".\"archive_status_change"'.format(settings.INVOICE_TRACKING)


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    archive = models.ForeignKey(
        CentralArchive,
        on_delete=models.DO_NOTHING,
        related_name='archive_document',
        db_index=True
    )
    
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        related_name="archive_document_uploaded_by",
        db_index=True
    )

    document = models.FileField(upload_to='documents/archives')
    file_name = models.CharField(max_length=500, db_index=True)
    file_type = models.CharField(max_length=255, default='Supporting Document', db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.file_name}"
    
    class Meta:
        db_table = u'"{}"."documents"'.format(settings.INVOICE_TRACKING)
        indexes = [
            # Speeds up queries for active (non-deleted) documents linked to a specific expenditure
            models.Index(fields=['archive', 'is_deleted']),
            
            # Speeds up queries for filtering or ordering by uploader and creation date
            models.Index(fields=['uploaded_by', 'date_created'], name="documents_uploade_fff90de_idx"),
            
            # Helpful for searches or filtering by file type
            models.Index(fields=['file_type'], name="documents_file_ty_4b3ax1_idx"),
        ]
        # Optional: old style for backward compatibility
        index_together = [
            ['archive', 'is_deleted'],
            ['uploaded_by', 'date_created'],
        ]

