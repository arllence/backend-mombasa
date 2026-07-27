# attendance/management/commands/mark_attendance.py
import hmac
import hashlib
import time
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from attendance.fingerprint import get_machine_fingerprint
from attendance import state


class Command(BaseCommand):
    help = "Marks daily attendance with the license server"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would happen without contacting the server"
        )

    def handle(self, *args, **options):
        license_url = settings.ATTENDANCE_LICENSE_URL
        secret = settings.ATTENDANCE_HMAC_SECRET
        fingerprint = get_machine_fingerprint()
        timestamp = str(int(time.time()))

        signature = hmac.new(
            secret.encode(),
            timestamp.encode(),
            hashlib.sha256
        ).hexdigest()

        payload = {"fp": fingerprint, "sig": signature, "ts": timestamp}

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(
                f"Would ping {license_url} with fingerprint {fingerprint[:16]}..."
            ))
            self.stdout.write(f"Current local state: {state._read()}")
            return

        self.stdout.write(f"📡 Pinging {license_url}...")
        try:
            r = requests.post(license_url, json=payload, timeout=10)
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"❌ Network error: {e}"))
            state.mark_failure()
            return

        if r.status_code == 200:
            state.mark_success()
            self.stdout.write(self.style.SUCCESS("✅ Attendance marked"))
            self.stdout.write(f"   Local timestamp updated.")
        elif r.status_code in {400, 403}:
            self.stdout.write(self.style.ERROR("🚨 CLONE DETECTED by license server"))
            # Keep the old success timestamp so the app doesn't crash immediately,
            # but flag it as a clone (the middleware will block requests).
            data = state._read() or {}
            data["clone_detected"] = True
            data["last_attempt"] = int(time.time())
            state._write(data)
        else:
            self.stdout.write(self.style.WARNING(f"⚠️ Unexpected status {r.status_code}"))
            state.mark_failure()
