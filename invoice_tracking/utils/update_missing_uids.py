from invoice_tracking.models import Tracking, Cancellation
from django.db import transaction
import string
import random
# from invoice_tracking.utils.update_missing_uids import update_missing_tracking_uids

def generate_unique_identifier(existing_uids):
    characters = string.ascii_uppercase + string.digits
    while True:
        uid = ''.join(random.choices(characters, k=6))
        if uid not in existing_uids:
            return uid

@transaction.atomic
def update_missing_tracking_uids():
    # Get all existing UIDs across both models
    existing_uids = set(
        Tracking.objects.exclude(uid__isnull=True).values_list('uid', flat=True)
    ) | set(
        Cancellation.objects.exclude(uid__isnull=True).values_list('uid', flat=True)
    )

    # Find all Tracking records without UID
    missing_uid_trackings = Tracking.objects.filter(uid__isnull=True)

    print(f"Found {missing_uid_trackings.count()} records without UID.")

    for tracking in missing_uid_trackings:
        uid = generate_unique_identifier(existing_uids)
        tracking.uid = uid
        tracking.save(update_fields=['uid'])
        existing_uids.add(uid)  # Avoid future collisions

    print("All Tracking missing UIDs assigned.")

    # Find all cancellation records without UID
    missing_uid_trackings = Cancellation.objects.filter(uid__isnull=True)

    print(f"Found {missing_uid_trackings.count()} records without UID.")

    for tracking in missing_uid_trackings:
        uid = generate_unique_identifier(existing_uids)
        tracking.uid = uid
        tracking.save(update_fields=['uid'])
        existing_uids.add(uid)  # Avoid future collisions

    print("All Cancellation missing UIDs assigned.")
