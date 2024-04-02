import uuid
from acl.models import User, Department
from django.db import models
from django.conf import settings

    

class Traveler(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    traveler = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="traveler",
       null=True, blank=True
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="created_by",
       null=True, blank=True
    )
    department = models.ForeignKey(
       Department, on_delete=models.DO_NOTHING, 
       related_name="department",
       null=True, blank=True
    )
    employee_no = models.CharField(max_length=50)
    employees = models.JSONField(null=True, blank=True)
    requesting_for = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=255, default='REQUESTED')
    mode_of_transport = models.CharField(max_length=255, null=True, blank=True)
    group = models.CharField(max_length=255, null=True, blank=True)
    position = models.CharField(max_length=255)
    tid = models.CharField(max_length=50, unique=True)
    purpose = models.CharField(max_length=50)
    description = models.TextField()
    budget_code = models.CharField(max_length=255, null=True, blank=True)
    travel_order_no = models.CharField(max_length=255, null=True, blank=True)
    travel_cost = models.BigIntegerField(default=0)
    salary_advance_required = models.BooleanField(default=False)
    is_hod_approved = models.BooleanField(default=False)
    is_slt_approved = models.BooleanField(default=False)
    is_ceo_approved = models.BooleanField(default=False)
    is_transport_dpt_approved = models.BooleanField(default=False)
    is_administrator_approved = models.BooleanField(default=False)
    requires_ceo_approval = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_closed = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.tid

    class Meta:
        db_table = u'"{}\".\"traveler"'.format(settings.TRAVEL_REQUEST_SYSTEM)

# class TravelGroup(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     traveler = models.ForeignKey(
#         Traveler, on_delete=models.DO_NOTHING,
#         related_name="group_travel_instance"
#     )
#     group_id = models.CharField(max_length=255)
#     is_deleted = models.BooleanField(default=False)
#     date_created = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return str(self.group_id)

#     class Meta:
#         db_table = u'"{}\".\"travel_group"'.format(settings.TRAVEL_REQUEST_SYSTEM)

class Trip(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    traveler = models.ForeignKey(
        Traveler, on_delete=models.DO_NOTHING,
        related_name="traveler_instance"
    )
    route = models.TextField()
    departure_date = models.DateField()
    return_date = models.DateField()
    accommodation = models.BooleanField(default=False)
    visa_required_date = models.DateField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return str(self.traveler.tid)

    class Meta:
        db_table = u'"{}\".\"trip"'.format(settings.TRAVEL_REQUEST_SYSTEM)


class Approval(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    traveler = models.ForeignKey(
       Traveler, on_delete=models.DO_NOTHING, 
       related_name="approval_traveler_instance"
    )
    approved_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="approver"
    )
    approval_for = models.CharField(max_length=255)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.traveler.tid

    class Meta:
        db_table = u'"{}\".\"approvals"'.format(settings.TRAVEL_REQUEST_SYSTEM)


class AdvanceSalaryRequests(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    traveler = models.ForeignKey(
       Traveler, on_delete=models.DO_NOTHING, 
       related_name="advance_salary_requestor"
    )
    approved_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="advance_salary_approver",
       null=True, blank=True
    )
    status = models.CharField(max_length=255, default='REQUESTED')
    amount = models.CharField(max_length=255)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.traveler.tid

    class Meta:
        db_table = u'"{}\".\"advance_salary_requests"'.format(settings.TRAVEL_REQUEST_SYSTEM)


class Costing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    traveler = models.ForeignKey(
       Traveler, on_delete=models.DO_NOTHING, 
       related_name="costing_traveler_instance"
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="costing_approver"
    )
    cost = models.JSONField()
    accommodation = models.JSONField()
    bill_settlement_by = models.CharField(max_length=255)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.traveler.tid

    class Meta:
        db_table = u'"{}\".\"costings"'.format(settings.TRAVEL_REQUEST_SYSTEM)