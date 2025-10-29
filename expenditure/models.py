import uuid
from acl.models import User, SRRSDepartment
from django.db import models
from django.conf import settings


class ExpenditureRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uid = models.CharField(max_length=50, unique=True)
    reference_no = models.CharField(max_length=20, unique=True, db_index=True)
    department = models.ForeignKey(
        SRRSDepartment,
        on_delete=models.DO_NOTHING,
        related_name='expenditure_department',
        db_index=True
    )
    description = models.TextField()
    invoice_number = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    amount_kes = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, default='REQUESTED', db_index=True)

    requested_by = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        related_name='requisition_by',
        db_index=True
    )
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.reference_no} - {self.department.name}"

    class Meta:
        db_table = u'"{}"."expenditures"'.format(settings.EXPENDITURE_SYSTEM)
        indexes = [
            models.Index(fields=['department', 'status']),
            models.Index(fields=['requested_by', 'date_created']),
            models.Index(fields=['invoice_number']),
        ]
        # Optional: if you often query combinations of these fields
        index_together = [
            ['department', 'status'],
            ['requested_by', 'date_created'],
        ]


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    expenditure = models.ForeignKey(
        ExpenditureRequest,
        on_delete=models.DO_NOTHING,
        related_name='expenditure_document',
        db_index=True
    )
    
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        related_name="expenditure_document_uploaded_by",
        db_index=True
    )

    document = models.FileField(upload_to='documents/expenditures')
    file_name = models.CharField(max_length=500, db_index=True)
    file_type = models.CharField(max_length=255, default='Supporting Document', db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.file_name}"
    
    class Meta:
        db_table = u'"{}"."documents"'.format(settings.EXPENDITURE_SYSTEM)
        indexes = [
            # Speeds up queries for active (non-deleted) documents linked to a specific expenditure
            models.Index(fields=['expenditure', 'is_deleted']),
            
            # Speeds up queries for filtering or ordering by uploader and creation date
            models.Index(fields=['uploaded_by', 'date_created']),
            
            # Helpful for searches or filtering by file type
            models.Index(fields=['file_type']),
        ]
        # Optional: old style for backward compatibility
        index_together = [
            ['expenditure', 'is_deleted'],
            ['uploaded_by', 'date_created'],
        ]


class StatusChange(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expenditure = models.ForeignKey(
        ExpenditureRequest, on_delete=models.DO_NOTHING,
        related_name="status_change_expenditure_instance"
    )
    status = models.CharField(max_length=255)
    action_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="expenditure_action_by",
       null=True, blank=True
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.expenditure.reference_no)

    class Meta:
        db_table = u'"{}\".\"status_change"'.format(settings.EXPENDITURE_SYSTEM)


class PlatformAdmin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    admin = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="expenditure_admin"
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="expenditure_admin_created_by"
    )

    status = models.CharField(max_length=255, default='ACTIVE')
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.admin.first_name
    
    class Meta:
        db_table = u'"{}\".\"platform_admins"'.format(settings.EXPENDITURE_SYSTEM)


class Note(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="expenditure_note_by"
    )
    expenditure = models.ForeignKey(
        ExpenditureRequest, on_delete=models.DO_NOTHING,
        related_name="note_expenditure_instance"
    )
    note = models.TextField()
   
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.expenditure.uid)

    class Meta:
        db_table = u'"{}\".\"notes"'.format(settings.EXPENDITURE_SYSTEM)