import uuid
from acl.models import User
from django.db import models
from django.conf import settings


class QuickLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="directory_link_created_by"
    )

    title = models.CharField(max_length=500)
    link = models.URLField()
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title}"
    
    class Meta:
        db_table = u'"{}\".\"links"'.format(settings.SYSTEM_DIRECTORY)
