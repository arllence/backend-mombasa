import uuid
from acl.models import User, SRRSDepartment
from django.db import models
from django.conf import settings
from django.utils import timezone


class ShiftStatus(models.TextChoices):
    DRAFT = "DRAFT", "DRAFT"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION", "AWAITING CONFIRMATION"
    COMPLETED = "COMPLETED", "COMPLETED"


class ShiftType(models.TextChoices):
    MORNING = "MORNING", "MorMORNINGning"
    EVENING = "EVENING", "EVENING"
    NIGHT = "NIGHT", "NIGHT"


class RoomStatusChoice(models.TextChoices):
    OPERATIONAL = "OPERATIONAL", "OPERATIONAL"
    CLOSED = "CLOSED", "CLOSED"
    MAINTENANCE = "MAINTENANCE", "MAINTENANCE"
    CLEANING = "CLEANING", "CLEANING"


class EquipmentStatusChoice(models.TextChoices):
    OK = "OK", "OK"
    FAULTY = "FAULTY", "FAULTY"


class PriorityChoice(models.TextChoices):
    ROUTINE = "ROUTINE", "ROUTINE"
    URGENT = "URGENT", "URGENT"
    EMERGENCY = "EMERGENCY", "EMERGENCY"


class Shift(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    date = models.DateField()
    shift_type = models.CharField(max_length=20, choices=ShiftType.choices)

    outgoing_officer = models.ForeignKey(
        User,
        related_name="outgoing_shifts",
        on_delete=models.PROTECT
    )

    incoming_officer = models.ForeignKey(
        User,
        related_name="incoming_shifts",
        on_delete=models.PROTECT
    )

    radiologist_on_call = models.ForeignKey(
        User,
        related_name="radiologist_on_call_shifts",
        on_delete=models.PROTECT
    )

    status = models.CharField(
        max_length=30,
        choices=ShiftStatus.choices,
        default=ShiftStatus.DRAFT
    )

    signed_out_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def sign_out(self):
        if self.status != ShiftStatus.DRAFT:
            raise ValueError("Shift must be in DRAFT state to sign out.")
        self.status = ShiftStatus.AWAITING_CONFIRMATION
        self.signed_out_at = timezone.now()
        self.save()

    def confirm(self):
        if self.status != ShiftStatus.AWAITING_CONFIRMATION:
            raise ValueError("Shift not awaiting confirmation.")
        self.status = ShiftStatus.COMPLETED
        self.confirmed_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.date} - {self.shift_type}"
    
    class Meta:
        db_table = u'"{}\".\"shifts"'.format(settings.RADIOLOGY_SYSTEM)


class RoomStatus(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    shift = models.ForeignKey(
        Shift,
        related_name="rooms",
        on_delete=models.CASCADE
    )

    room_type = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20,
        choices=RoomStatusChoice.choices
    )
    remarks = models.TextField(blank=True)

    def clean(self):
        if self.status == RoomStatusChoice.MAINTENANCE and not self.remarks:
            raise ValueError("Remarks required for maintenance status.")

    def __str__(self):
        return f"{self.room_type} - {self.status}"
    
    class Meta:
        db_table = u'"{}\".\"room_status"'.format(settings.RADIOLOGY_SYSTEM)


class EquipmentStatus(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    shift = models.ForeignKey(
        Shift,
        related_name="equipment",
        on_delete=models.CASCADE
    )

    equipment_name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=EquipmentStatusChoice.choices
    )
    remarks = models.TextField(blank=True)
    escalated = models.BooleanField(default=False)

    def clean(self):
        if self.status == EquipmentStatusChoice.FAULTY and not self.remarks:
            raise ValueError("Remarks required if equipment is faulty.")

    def __str__(self):
        return f"{self.equipment_name} - {self.status}"
    
    class Meta:
        db_table = u'"{}\".\"equipment_status"'.format(settings.RADIOLOGY_SYSTEM)


class PendingCase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    shift = models.ForeignKey(
        Shift,
        related_name="pending_cases",
        on_delete=models.CASCADE
    )

    patient_identifier = models.CharField(max_length=255)
    examination = models.CharField(max_length=255)
    priority = models.CharField(
        max_length=20,
        choices=PriorityChoice.choices
    )
    reason = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient_identifier} - {self.priority}"
    
    class Meta:
        db_table = u'"{}\".\"pending_cases"'.format(settings.RADIOLOGY_SYSTEM)


class CriticalResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    shift = models.ForeignKey(
        Shift,
        related_name="critical_results",
        on_delete=models.CASCADE
    )

    patient_identifier = models.CharField(max_length=255)
    findings = models.TextField()
    physician_notified = models.CharField(max_length=255)
    notified_at = models.DateTimeField(default=timezone.now)
    feedback = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-notified_at"]

    def __str__(self):
        return f"{self.patient_identifier} - Critical"
    
    class Meta:
        db_table = u'"{}\".\"critical_results"'.format(settings.RADIOLOGY_SYSTEM)


class StockEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    shift = models.ForeignKey(
        Shift,
        related_name="stock_entries",
        on_delete=models.CASCADE
    )

    item_name = models.CharField(max_length=255)
    opening_stock = models.PositiveIntegerField()
    closing_stock = models.PositiveIntegerField()
    used = models.PositiveIntegerField(editable=False)

    def save(self, *args, **kwargs):
        self.used = self.opening_stock - self.closing_stock
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_name} - Used: {self.used}"
    
    class Meta:
        db_table = u'"{}\".\"stock_entries"'.format(settings.RADIOLOGY_SYSTEM)


class InfectionControl(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    shift = models.OneToOneField(
        Shift,
        related_name="infection_control",
        on_delete=models.CASCADE
    )

    cleaning_checklist = models.BooleanField(default=False)
    temperature_checks = models.BooleanField(default=False)
    equipment_disinfection = models.BooleanField(default=False)

    hazmat_issue = models.BooleanField(default=False)
    hazmat_details = models.TextField(blank=True)

    def clean(self):
        if self.hazmat_issue and not self.hazmat_details:
            raise ValueError("Hazmat details required if issue exists.")

    def __str__(self):
        return f"Infection Control - {self.shift.date}"
    
    class Meta:
        db_table = u'"{}\".\"infection_control"'.format(settings.RADIOLOGY_SYSTEM)


class NurseHandover(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    shift = models.OneToOneField(
        Shift,
        related_name="nurse_handover",
        on_delete=models.CASCADE
    )

    hazmat_checklist_status = models.BooleanField(default=False)
    spill_kit_status = models.BooleanField(default=False)
    booked_procedures = models.TextField(blank=True)
    concerns = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Nurse Handover - {self.shift.date}"
    
    class Meta:
        db_table = u'"{}\".\"nurse_handover"'.format(settings.RADIOLOGY_SYSTEM)


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    shift = models.ForeignKey(
        Shift,
        on_delete=models.CASCADE,
        related_name="audit_logs"
    )

    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.action} - {self.timestamp}"
    
    class Meta:
        db_table = u'"{}\".\"audit_logs"'.format(settings.RADIOLOGY_SYSTEM)



class PlatformAdmin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    admin = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="radiology_admin"
    )
    created_by = models.ForeignKey(
       User, on_delete=models.DO_NOTHING, 
       related_name="radiology_admin_created_by"
    )

    status = models.CharField(max_length=255, default='ACTIVE')
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.admin.first_name
    
    class Meta:
        db_table = u'"{}\".\"platform_admins"'.format(settings.RADIOLOGY_SYSTEM)


class TrackNotification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    shift = models.ForeignKey(
       Shift, on_delete=models.DO_NOTHING, 
       related_name="shift_model"
    )
    recipients = models.JSONField()
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.shift.uid
    
    class Meta:
        db_table = u'"{}\".\"track_notifications"'.format(settings.RADIOLOGY_SYSTEM)