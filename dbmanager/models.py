import uuid
from acl.models import User, SRRSDepartment
from django.db import models
from django.conf import settings


class BackupLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    action_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="log_added_by"
    )

    type = models.CharField(max_length=500)
    date = models.DateField()
    status = models.CharField(max_length=100)
    size = models.IntegerField(default=0)
    unit = models.CharField(max_length=100)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.type}"
    
    class Meta:
        db_table = u'"{}\".\"backup_logs"'.format(settings.DB_MANAGER)


class SystemRecoveryVerification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    verified_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="verified_by"
    )

    module_verified = models.CharField(max_length=500)
    date = models.DateField()
    comments = models.TextField()
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.module_verified}"
    
    class Meta:
        db_table = u'"{}\".\"system_recovery_verifications"'.format(settings.DB_MANAGER)


class RemoteBackupLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    action_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="remote_log_added_by"
    )

    type = models.CharField(max_length=500)
    date = models.DateField()
    status = models.CharField(max_length=100)
    remote_location = models.CharField(max_length=500)
    size = models.IntegerField(default=0)
    unit = models.CharField(max_length=100)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.type}"
    
    class Meta:
        db_table = u'"{}\".\"remote_backup_logs"'.format(settings.DB_MANAGER)

