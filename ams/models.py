import uuid
from acl.models import User, SRRSDepartment
from django.db import models
from django.conf import settings




class Asset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    barcode = models.CharField(max_length=500, unique=True)
    serial_no = models.CharField(max_length=500, unique=True)
    data = models.JSONField()
    department = models.ForeignKey(
        SRRSDepartment, on_delete=models.DO_NOTHING,
        related_name="asset_department"
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="asset_created_by"
    )
    is_deleted = models.BooleanField(default=False)
    last_updated = models.DateTimeField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.data__barcode)

    class Meta:
        db_table = u'"{}\".\"assets"'.format(settings.ASSET_MANAGEMENT_SYSTEM)
