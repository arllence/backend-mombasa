import uuid
from acl.models import User, SRRSDepartment
from django.db import models
from django.conf import settings


class TrainingMaterial(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(
        SRRSDepartment, on_delete=models.DO_NOTHING, 
        related_name="training_materials", db_index=True
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="training_created_by", db_index=True
    )
    uid = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255, db_index=True)
    type = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    description = models.TextField(blank=True)
    external_url = models.URLField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} - ({self.department.name})"
    
    class Meta:
        db_table = u'"{}\".\"training_materials"'.format(settings.CENTRALIZED_TRAINING_PLATFORM)
        indexes = [
            models.Index(fields=["department"]),
            models.Index(fields=["title"]),
            models.Index(fields=["type"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["department", "title"]),  # composite
        ]


class TrainingAssignment(models.Model):
    """
    Tracks which training a user must complete.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="user_assigned", db_index=True)
    training = models.ForeignKey(TrainingMaterial, on_delete=models.DO_NOTHING, related_name="training_assigned", db_index=True)
    assigned_by = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="assignment_by", db_index=True)
    completion_date = models.DateField(blank=True, null=True)
    date_completed = models.DateField(blank=True, null=True)
    is_completed = models.BooleanField(default=False, db_index=True)
    certificate = models.FileField(upload_to="documents/training/certificates/", blank=True, null=True)
    date_created = models.DateTimeField(blank=True, null=True, db_index=True)
    is_deleted = models.BooleanField(default=False)


    class Meta:
        unique_together = ("user", "training")
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["training"]),
            models.Index(fields=["is_completed"]),
            models.Index(fields=["date_created"]),
            models.Index(fields=["user", "is_completed"]),         # composite
            models.Index(fields=["training", "is_completed"]),     # composite
            models.Index(fields=["user", "training", "is_completed"]),  # composite (reporting)
        ]
        db_table = u'"{}\".\"training_assignments"'.format(settings.CENTRALIZED_TRAINING_PLATFORM)

    def __str__(self):
        return f"{self.user} - {self.training}"

class TrainingResource(models.Model):
    # VIDEO = "video"
    # LINK = "link"
    # SCORM = "scorm"

    # RESOURCE_TYPE_CHOICES = [
    #     (VIDEO, "Video"),
    #     (LINK, "Link"),
    #     (SCORM, "SCORM Package"),
    # ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    training = models.ForeignKey(TrainingMaterial, on_delete=models.CASCADE, related_name="resources", db_index=True)
    resource_type = models.CharField(max_length=20, db_index=True)
    title = models.CharField(max_length=200, db_index=True)
    url = models.URLField()
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.training.title} - {self.title} ({self.resource_type})"

    class Meta:
        db_table = u'"{}\".\"training_recourses"'.format(settings.CENTRALIZED_TRAINING_PLATFORM)
        indexes = [
            models.Index(fields=["training"]),
            models.Index(fields=["resource_type"]),
            models.Index(fields=["title"]),
            models.Index(fields=["training", "resource_type"]),  # composite
        ]


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    training = models.ForeignKey(
        TrainingMaterial, on_delete=models.DO_NOTHING, 
        related_name="training_documents", db_index=True)
    
    uploaded_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="training_document_uploaded_by"
    )

    document = models.FileField(upload_to='documents/training/courses/')
    file_name = models.CharField(max_length=500)
    file_type = models.CharField(max_length=255, default='training')
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.file_name}"
    
    class Meta:
        db_table = u'"{}\".\"documents"'.format(settings.CENTRALIZED_TRAINING_PLATFORM)
        indexes = [
            models.Index(fields=["training"]),
            models.Index(fields=["date_created"]),
            models.Index(fields=["training", "date_created"]),  # composite
        ]


class PlatformAdmin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    admin = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="ctp_admin"
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="ctp_admin_created_by"
    )

    status = models.CharField(max_length=255, default='ACTIVE')
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.admin.first_name
    
    class Meta:
        db_table = u'"{}\".\"platform_admins"'.format(settings.CENTRALIZED_TRAINING_PLATFORM)


class TrackNotification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="user_model"
    )
    recipients = models.JSONField()
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.email
    
    class Meta:
        db_table = u'"{}\".\"track_notifications"'.format(settings.CENTRALIZED_TRAINING_PLATFORM)