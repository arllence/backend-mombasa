import uuid
from acl.models import User, SRRSDepartment
from django.db import models
from django.conf import settings

class Meal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="meal_created_by", 
       null=True, blank=True
    )
    slt = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="meal_slt"
    )
    department = models.ForeignKey(
       SRRSDepartment, on_delete=models.DO_NOTHING, 
       related_name="srrs_smr_department"
    )
   
    uid = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=255, default='REQUESTED')
    reason = models.TextField(null=True, blank=True)
    location_of_function = models.CharField(max_length=500)
    date_of_event = models.DateField()
    number_of_participants = models.IntegerField()
    am_tea = models.JSONField(null=True, blank=True)
    pm_tea = models.JSONField(null=True, blank=True)
    lunch = models.JSONField(null=True, blank=True)
    dinner = models.JSONField(null=True, blank=True)
    meals = models.JSONField(null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_closed = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.uid

    class Meta:
        db_table = u'"{}\".\"meals"'.format(settings.STAFF_MEAL_REQUEST)


class StatusChange(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meal = models.ForeignKey(
        Meal, on_delete=models.DO_NOTHING,
        related_name="status_change_issue_instance"
    )
    status = models.CharField(max_length=255)
    status_for = models.CharField(max_length=255, null=True, blank=True)
    action_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="smr_action_by",
       null=True, blank=True
    )
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.meal.uid)

    class Meta:
        db_table = u'"{}\".\"status_changes"'.format(settings.STAFF_MEAL_REQUEST)


class PlatformAdmin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    admin = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="smr_admin"
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="smr_admin_created_by"
    )

    status = models.CharField(max_length=255, default='ACTIVE')
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.admin.first_name
    
    class Meta:
        db_table = u'"{}\".\"platform_admins"'.format(settings.STAFF_MEAL_REQUEST)
