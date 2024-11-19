import uuid
from acl.models import User
from django.db import models
from django.conf import settings


class BackupLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    action_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="log_added_by"
    )

    type = models.ForeignKey(
       'System', on_delete=models.DO_NOTHING, 
       related_name="system_log_added_by",
       null=True, blank=True
    )

    date = models.DateField()
    status = models.CharField(max_length=100)
    size = models.FloatField(default=0.0)
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
    
    uploaded_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="verified_by", 
       null=True, blank=True
    )

    module_verified = models.CharField(max_length=500)
    verified_by = models.CharField(max_length=500, null=True, blank=True)
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

    type = models.ForeignKey(
       'System', on_delete=models.DO_NOTHING, 
       related_name="remote_system_log_added_by",
       null=True, blank=True
    )

    remote_location = models.ForeignKey(
       'RemoteLocations', on_delete=models.DO_NOTHING, 
       related_name="remote_location_added_by",
       null=True, blank=True
    )

    date = models.DateField()
    status = models.CharField(max_length=100)
    size = models.FloatField(default=0.0)
    unit = models.CharField(max_length=100)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.type}"
    
    class Meta:
        db_table = u'"{}\".\"remote_backup_logs"'.format(settings.DB_MANAGER)


class System(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = u'"{}\".\"systems"'.format(settings.DB_MANAGER)


class RemoteLocations(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = u'"{}\".\"remote_locations"'.format(settings.DB_MANAGER)