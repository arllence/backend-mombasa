import uuid
from acl.models import User, SRRSDepartment, SubDepartment, OHC
from django.db import models
from django.conf import settings

    

class Recruit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="srrs_created_by",
       null=True, blank=True
    )
    closed_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="srrs_closed_by",
       null=True, blank=True
    )
    rejected_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="srrs_rejected_by",
       null=True, blank=True
    )
    department = models.ForeignKey(
       SRRSDepartment, on_delete=models.DO_NOTHING, 
       related_name="srrs_department",
       null=True, blank=True
    )
    sub_department = models.ForeignKey(
       SubDepartment, on_delete=models.DO_NOTHING, 
       related_name="srrs_sub_department",
       null=True, blank=True
    )
    ohc = models.ForeignKey(
       OHC, on_delete=models.DO_NOTHING, 
       related_name="srrs_ohc",
       null=True, blank=True
    )
    hr_partner = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="srrs_hr_partner",
       null=True, blank=True
    )
    preferred_slt = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="srrs_preferred_slt",
       null=True, blank=True
    )
    uid = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=255, default='REQUESTED')
    position_title = models.CharField(max_length=255)
    position_type = models.CharField(max_length=255)
    qualifications = models.TextField(null=True, blank=True)
    job_description = models.FileField(upload_to='documents/srrs/job_description/', null=True, blank=True)
    nature_of_hiring = models.CharField(max_length=255)
    existing_staff_same_title = models.JSONField(null=True, blank=True)
    justification = models.TextField(null=True, blank=True)
    reasons_for_not_sharing_tasks = models.TextField(null=True, blank=True)
    filling_date = models.DateField(null=True, blank=True)
    period_from = models.DateField(null=True, blank=True)
    period_to = models.DateField(null=True, blank=True)
    temporary_task_assignment_to = models.CharField(max_length=255)
    replacement_details = models.JSONField(null=True, blank=True)
    rejection_reasons = models.JSONField(null=True, blank=True)
    proposed_salary = models.BigIntegerField(default=0)
    budget_approval_file = models.FileField(upload_to='documents/srrs/budget_approval/', null=True, blank=True)
    slt_comments = models.TextField(null=True, blank=True)
    hhr_comments = models.TextField(null=True, blank=True)
    hof_comments = models.TextField(null=True, blank=True)
    ceo_comments = models.TextField(null=True, blank=True)
    is_slt_approved = models.BooleanField(default=False)
    is_hhr_approved = models.BooleanField(default=False)
    is_hof_approved = models.BooleanField(default=False)
    is_ceo_approved = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_closed = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.uid

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
        return str(self.traveler.uid)

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
       related_name="srrs_action_by",
       null=True, blank=True
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.recruit.uid)

    class Meta:
        db_table = u'"{}\".\"status_change"'.format(settings.STAFF_REQUISITION_SYSTEM)

class Employee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recruit = models.ForeignKey(
        Recruit, on_delete=models.DO_NOTHING,
        related_name="employee_recruit_instance"
    )

    name = models.CharField(max_length=500)
    email = models.EmailField(max_length=500, null=True, blank=True)
    employee_no = models.CharField(max_length=255)
    reporting_date = models.DateField()
    reporting_station = models.CharField(max_length=500)
    working_station = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(max_length=255, default='ACTIVE')

    action_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="employee_action_by"
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.recruit.uid)

    class Meta:
        db_table = u'"{}\".\"employees"'.format(settings.STAFF_REQUISITION_SYSTEM)

class LocumAttendance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee, on_delete=models.DO_NOTHING,
        related_name="employee_attendance",
        null=True, blank=True
    )
    month = models.IntegerField()
    year = models.IntegerField()
    data = models.JSONField()
    action_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="attendance_action_by",
       null=True, blank=True
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.employee.name)

    class Meta:
        db_table = u'"{}\".\"locum_attendance"'.format(settings.STAFF_REQUISITION_SYSTEM)

class MonthlyLocumAttendance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee, on_delete=models.DO_NOTHING,
        related_name="employee_monthly_attendance"
    )
    month = models.IntegerField()
    year = models.IntegerField()
    hours_worked = models.IntegerField(default=0)
    days_worked = models.IntegerField(default=0)
    action_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="monthly_attendance_action_by"
    )
    updated_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="monthly_attendance_updated_by",
       null=True, blank=True
    )
    reason_for_extra_hours = models.TextField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.employee.name)

    class Meta:
        db_table = u'"{}\".\"monthly_locum_attendance"'.format(settings.STAFF_REQUISITION_SYSTEM)