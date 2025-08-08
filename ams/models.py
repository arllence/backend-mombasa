import uuid
from acl.models import User, SRRSDepartment
from django.db import models
from django.conf import settings
from ict_helpdesk.models import Facility




class Asset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset_no = models.CharField(max_length=500, unique=True, null=True, blank=True)
    type = models.CharField(max_length=100, null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=100, null=True, blank=True)
    custodian = models.CharField(max_length=500, null=True, blank=True)
    specific_location = models.CharField(max_length=500, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    properties = models.JSONField()
    department = models.ForeignKey(
        SRRSDepartment, on_delete=models.DO_NOTHING,
        related_name="asset_department"
    )
    facility = models.ForeignKey(
       Facility, on_delete=models.DO_NOTHING, 
       related_name="ams_facility", null=True, blank=True
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="asset_created_by"
    )
    procurement_date = models.DateField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.asset_no)

    class Meta:
        indexes = [
            models.Index(fields=['asset_no', 'type']),  # multi-field index
        ]
        db_table = u'"{}\".\"assets"'.format(settings.ASSET_MANAGEMENT_SYSTEM)
