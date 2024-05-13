import uuid
from acl.models import User, Department
from django.db import models



class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uploader = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="document_uploader"
    )
    document = models.FileField(upload_to='mms_documents')
    original_file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50,default='FILE')
    title = models.CharField(max_length=255, default='QUOTE')
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mms_documents"

    def __str__(self):
        return str(self.original_file_name)
    

class Quote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(
       Department, on_delete=models.DO_NOTHING, 
       related_name="from_department"
    )
    attachment = models.ForeignKey(
       Document, on_delete=models.DO_NOTHING, 
       related_name="document_attached",
       null=True, blank=True
    )
    uploader = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="quote_uploader"
    )
    status = models.CharField(max_length=500, default='REQUESTED')
    subject = models.CharField(max_length=500)
    qid = models.CharField(max_length=50, null=True, blank=True, unique=True)
    description = models.TextField()
    content = models.JSONField(null=True, blank=True)
    reasons = models.JSONField(null=True, blank=True)
    close_attachments = models.JSONField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_closed = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.subject

    class Meta:
        db_table = "quotes"


class QuoteAssignee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quote = models.ForeignKey(
       Quote, on_delete=models.DO_NOTHING, 
       related_name="quote_assigned"
    )
    assigned = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="quote_assignee"
    )
    status = models.CharField(max_length=500, default='ASSIGNED')
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.quote.subject

    class Meta:
        db_table = "quote_assignees"

