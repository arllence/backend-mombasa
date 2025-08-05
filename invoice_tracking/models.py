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
