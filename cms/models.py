import uuid
from acl.models import User, SRRSDepartment
from django.db import models
from django.conf import settings


class Contract(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    department = models.ForeignKey(
        SRRSDepartment, on_delete=models.DO_NOTHING,
        related_name="contract_department"
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="contract_created_by"
    )

    uid = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    commencement_date = models.DateField()
    expiry_date = models.DateField()
    previous = models.CharField(max_length=255,null=True, blank=True)
    is_expired = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.title)

    class Meta:
        db_table = u'"{}\".\"contracts"'.format(settings.CONTRACT_MANAGEMENT_SYSTEM)


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    contract = models.ForeignKey(
        Contract, on_delete=models.DO_NOTHING, 
        related_name='contract_document')
    
    uploaded_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="contract_document_uploaded_by"
    )

    document = models.FileField(upload_to='documents/contracts')
    file_name = models.CharField(max_length=500)
    file_type = models.CharField(max_length=255, default='contract')
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file_name}"
    
    class Meta:
        db_table = u'"{}\".\"documents"'.format(settings.CONTRACT_MANAGEMENT_SYSTEM)


class PlatformAdmin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    admin = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="cms_admin"
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="cms_admin_created_by"
    )

    status = models.CharField(max_length=255, default='ACTIVE')
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.admin.first_name
    
    class Meta:
        db_table = u'"{}\".\"platform_admins"'.format(settings.CONTRACT_MANAGEMENT_SYSTEM)


class TrackNotification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    contract = models.ForeignKey(
       Contract, on_delete=models.DO_NOTHING, 
       related_name="contract_model"
    )
    recipients = models.JSONField()
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.contract.uid
    
    class Meta:
        db_table = u'"{}\".\"track_notifications"'.format(settings.CONTRACT_MANAGEMENT_SYSTEM)