import uuid
from acl.models import User, SRRSDepartment, SubDepartment, OHC
from django.db import models
from django.conf import settings


class Staff(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    department = models.ForeignKey(
        SRRSDepartment, on_delete=models.DO_NOTHING,
        related_name="sss_staff_department"
    )

    location = models.ForeignKey(
        SubDepartment, on_delete=models.DO_NOTHING,
        related_name="sss_staff_location",
        null=True, blank=True
    )

    ohc = models.ForeignKey(
        OHC, on_delete=models.DO_NOTHING,
        related_name="sss_staff_location_ohc",
        null=True, blank=True
    )

    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="sss_created_by"
    )
    uid = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    payroll_no = models.CharField(max_length=255)
    # location = models.CharField(max_length=255, null=True, blank=True)
    # ohc = models.CharField(max_length=255, null=True, blank=True)
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
    days = models.IntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    resume_work_on = models.DateField(null=True, blank=True)
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

    consultant_name = models.CharField(max_length=255,null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.staff.name

    class Meta:
        db_table = u'"{}\".\"refers"'.format(settings.STAFF_SICK_SHEET)


