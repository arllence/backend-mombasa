import uuid
from acl.models import User, SRRSDepartment
from django.db import models
from django.conf import settings


class Staff(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    department = models.ForeignKey(
        SRRSDepartment, on_delete=models.DO_NOTHING,
        related_name="sss_staff_department"
    )

    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="sss_created_by"
    )
    uid = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    payroll_no = models.CharField(max_length=255)
    supervisor_name = models.CharField(max_length=255)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        db_table = u'"{}\".\"staffs"'.format(settings.STAFF_SICK_SHEET)


class Medical(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff = models.ForeignKey(
        Staff, on_delete=models.DO_NOTHING,
        related_name="sss_medical_staff"
    )

    is_fit_to_work = models.CharField(max_length=5, default='YES')
    days = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    resume_work_on = models.DateField()
    to_be_reviewed_on = models.DateField(null=True, blank=True)
    reason = models.TextField()
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.staff.name

    class Meta:
        db_table = u'"{}\".\"medical"'.format(settings.STAFF_SICK_SHEET)


class Refer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    staff = models.ForeignKey(
        Staff, on_delete=models.DO_NOTHING,
        related_name="sss_refer_staff"
    )

    consultant_name = models.CharField(max_length=255)
    date = models.DateField()
    time = models.TimeField()
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.staff.name

    class Meta:
        db_table = u'"{}\".\"refers"'.format(settings.STAFF_SICK_SHEET)


