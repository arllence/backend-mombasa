import uuid
from acl.models import User, Department
from django.db import models
from django.conf import settings

    

class Recruit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="created_by",
       null=True, blank=True
    )
    closed_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="closed_by",
       null=True, blank=True
    )
    rejected_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="rejected_by",
       null=True, blank=True
    )
    department = models.ForeignKey(
       Department, on_delete=models.DO_NOTHING, 
       related_name="department",
       null=True, blank=True
    )
    uid = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=255, default='REQUESTED')
    position_title = models.CharField(max_length=255)
    position_type = models.CharField(max_length=255)
    qualifications = models.JSONField()
    job_description = models.TextField()
    nature_of_hiring = models.CharField(max_length=255)
    existing_staff_same_title = models.JSONField(null=True, blank=True)
    reasons_for_not_sharing_tasks = models.TextField(null=True, blank=True)
    filling_period_from = models.DateField()
    filling_period_to = models.DateField()
    temporary_task_assignment_to = models.CharField(max_length=255)
    replacement_details = models.JSONField(null=True, blank=True)
    proposed_salary = models.BigIntegerField(default=0)
    budget_approval_file = models.FileField(upload_to='documents/srrs/budget_approval/', null=True, blank=True)
    hhr_comments = models.TextField(null=True, blank=True)
    hof_comments = models.TextField(null=True, blank=True)
    ceo_comments = models.TextField(null=True, blank=True)
    is_slt_approved = models.BooleanField(default=False)
    is_hof_approved = models.BooleanField(default=False)
    is_ceo_approved = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_closed = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.tid

    class Meta:
        db_table = u'"{}\".\"recruits"'.format(settings.STAFF_REQUISITION_SYSTEM)


class RecruitHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uid = models.CharField(max_length=50)
    data = models.JSONField()
    triggered_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="triggered_by",
       null=True, blank=True
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.traveler.tid)

    class Meta:
        db_table = u'"{}\".\"recruit_history"'.format(settings.STAFF_REQUISITION_SYSTEM)


class StatusChange(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recruit = models.ForeignKey(
        Recruit, on_delete=models.DO_NOTHING,
        related_name="status_change_recruit_instance"
    )
    status = models.CharField(max_length=255)
    status_for = models.CharField(max_length=255, null=True, blank=True)
    action_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="action_by",
       null=True, blank=True
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.traveler.tid)

    class Meta:
        db_table = u'"{}\".\"status_change"'.format(settings.STAFF_REQUISITION_SYSTEM)