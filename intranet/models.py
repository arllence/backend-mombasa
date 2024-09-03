import uuid
from acl.models import User, SRRSDepartment
from django.db import models
from django.conf import settings


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    department = models.ForeignKey(
        SRRSDepartment, on_delete=models.DO_NOTHING, 
        related_name='intranet_document_department')
    
    uploaded_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="document_uploaded_by"
    )

    document = models.FileField(upload_to='documents/intranet')
    title = models.CharField(max_length=500, null=True, blank=True)
    original_file_name = models.CharField(max_length=500)
    downloads = models.IntegerField(default=0)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title}"
    
    class Meta:
        db_table = u'"{}\".\"documents"'.format(settings.INTRANET)
    

class QuickLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="link_created_by"
    )

    title = models.CharField(max_length=500)
    link = models.URLField()
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title}"
    
    class Meta:
        db_table = u'"{}\".\"quick_links"'.format(settings.INTRANET)