from django.db.models import  Q
from acl.serializers import UsersSerializer, SlimUsersSerializer, FetchSRRSDepartmentSerializer, SlimFetchSRRSDepartmentSerializer
from acl.utils.user_util import fetchusergroups as get_user_roles
from radiology import models
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction


class GeneralNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

class UpdateGeneralNameSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)

# class ShiftSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = models.Shift
#         fields = "__all__"
#         read_only_fields = (
#             "id",
#             "status",
#             "signed_out_at",
#             "confirmed_at",
#             "created_at",
#             "updated_at",
#         )

# # Room Status Serializer
# class RoomStatusSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = models.RoomStatus
#         fields = "__all__"
#         read_only_fields = ("id",)

#     def validate(self, data):
#         if data["status"] == "MAINTENANCE" and not data.get("remarks"):
#             raise serializers.ValidationError(
#                 "Remarks required for maintenance status."
#             )
#         return data
    
# # Equipment Status Serializer
# class EquipmentStatusSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = models.EquipmentStatus
#         fields = "__all__"
#         read_only_fields = ("id",)

#     def validate(self, data):
#         if data["status"] == "FAULTY" and not data.get("remarks"):
#             raise serializers.ValidationError(
#                 "Remarks required if equipment is faulty."
#             )
#         return data
    
# # Pending Case Serializer
# class PendingCaseSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = models.PendingCase
#         fields = "__all__"
#         read_only_fields = ("id", "created_at")


# # Critical Result Serializer
# class CriticalResultSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = models.CriticalResult
#         fields = "__all__"
#         read_only_fields = ("id", "created_at", "notified_at")


# # Stock Serializer
# class StockEntrySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = models.StockEntry
#         fields = "__all__"
#         read_only_fields = ("id", "used")


# # Infection Control Serializer
# class InfectionControlSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = models.InfectionControl
#         fields = "__all__"
#         read_only_fields = ("id",)

#     def validate(self, data):
#         if data.get("hazmat_issue") and not data.get("hazmat_details"):
#             raise serializers.ValidationError(
#                 "Hazmat details required if issue exists."
#             )
#         return data
    

# # Nurse Handover Serializer
# class NurseHandoverSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = models.NurseHandover
#         fields = "__all__"
#         read_only_fields = ("id", "created_at")



class PlatformAdminSerializer(serializers.Serializer):
    admin = serializers.CharField(max_length=500)

class UpdatePlatformAdminSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=500)
    admin = serializers.CharField(max_length=500)

class FetchPlatformAdminSerializer(serializers.ModelSerializer):
    created_by = SlimUsersSerializer()
    admin = UsersSerializer()
    class Meta:
        model = models.PlatformAdmin
        fields = '__all__'



class RoomStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RoomStatus
        fields = "__all__"
        read_only_fields = ("shift",)


class EquipmentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EquipmentStatus
        fields = "__all__"
        read_only_fields = ("shift",)


class PendingCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PendingCase
        fields = "__all__"
        read_only_fields = ("shift",)


class CriticalResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CriticalResult
        fields = "__all__"
        read_only_fields = ("shift",)


class StockEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StockEntry
        fields = "__all__"
        read_only_fields = ("shift",)


class InfectionControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.InfectionControl
        fields = "__all__"
        read_only_fields = ("shift",)


class NurseHandoverSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.NurseHandover
        fields = "__all__"
        read_only_fields = ("shift",)


class ShiftSerializer(serializers.ModelSerializer):

    rooms = RoomStatusSerializer(many=True, required=False)
    equipment = EquipmentStatusSerializer(many=True, required=False)
    pending_cases = PendingCaseSerializer(many=True, required=False)
    critical_results = CriticalResultSerializer(many=True, required=False)
    stock_entries = StockEntrySerializer(many=True, required=False)
    infection_control = InfectionControlSerializer(required=False)
    nurse_handover = NurseHandoverSerializer(required=False)

    class Meta:
        model = models.Shift
        fields = "__all__"
        read_only_fields = (
            "status",
            "signed_out_at",
            "confirmed_at",
        )

    @transaction.atomic
    def create(self, validated_data):
        print(validated_data)
        rooms = validated_data.pop("rooms", [])
        equipment = validated_data.pop("equipment", [])
        pending_cases = validated_data.pop("pending_cases", [])
        critical_results = validated_data.pop("critical_results", [])
        stock_entries = validated_data.pop("stock_entries", [])
        infection_control = validated_data.pop("infection_control", None)
        nurse_handover = validated_data.pop("nurse_handover", None)

        shift = models.Shift.objects.create(**validated_data)

        for item in rooms:
            models.RoomStatus.objects.create(shift=shift, **item)

        for item in equipment:
            models.EquipmentStatus.objects.create(shift=shift, **item)

        for item in pending_cases:
            models.PendingCase.objects.create(shift=shift, **item)

        for item in critical_results:
            models.CriticalResult.objects.create(shift=shift, **item)

        for item in stock_entries:
            models.StockEntry.objects.create(shift=shift, **item)

        if infection_control:
            models.InfectionControl.objects.create(shift=shift, **infection_control)

        if nurse_handover:
            models.NurseHandover.objects.create(shift=shift, **nurse_handover)

        return shift

    # ----------------------------
    # UPDATE (Replace Strategy)
    # ----------------------------

    @transaction.atomic
    def update(self, instance, validated_data):

        if instance.status == "COMPLETED":
            raise serializers.ValidationError(
                "Completed shift cannot be edited."
            )

        rooms = validated_data.pop("rooms", None)
        equipment = validated_data.pop("equipment", None)
        pending_cases = validated_data.pop("pending_cases", None)
        critical_results = validated_data.pop("critical_results", None)
        stock_entries = validated_data.pop("stock_entries", None)
        infection_control = validated_data.pop("infection_control", None)
        nurse_handover = validated_data.pop("nurse_handover", None)

        # Update base fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        # Replace nested data
        if rooms is not None:
            instance.rooms.all().delete()
            for item in rooms:
                models.RoomStatus.objects.create(shift=instance, **item)

        if equipment is not None:
            instance.equipment.all().delete()
            for item in equipment:
                models.EquipmentStatus.objects.create(shift=instance, **item)

        if pending_cases is not None:
            instance.pending_cases.all().delete()
            for item in pending_cases:
                models.PendingCase.objects.create(shift=instance, **item)

        if critical_results is not None:
            instance.critical_results.all().delete()
            for item in critical_results:
                models.CriticalResult.objects.create(shift=instance, **item)

        if stock_entries is not None:
            instance.stock_entries.all().delete()
            for item in stock_entries:
                models.StockEntry.objects.create(shift=instance, **item)

        if infection_control is not None:
            models.InfectionControl.objects.update_or_create(
                shift=instance,
                defaults=infection_control
            )

        if nurse_handover is not None:
            models.NurseHandover.objects.update_or_create(
                shift=instance,
                defaults=nurse_handover
            )

        return instance







