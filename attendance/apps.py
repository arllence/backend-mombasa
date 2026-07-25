import os
import sys
import time
from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured


class AttendanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "attendance"
    verbose_name = "Attendance Guard"

    def ready(self):
        # Bypass for tests, CI, etc.
        if os.environ.get("ATTENDANCE_BYPASS") == "1":
            return

        # Don't block Django's own management commands
        SKIP_COMMANDS = {
            "migrate", "makemigrations", "collectstatic", "shell",
            "createsuperuser", "test", "showmigrations", "dbshell",
        }
        if len(sys.argv) > 1 and sys.argv[1] in SKIP_COMMANDS:
            return

        from . import state
        from . import bootstrap

        last = state.get_last_success()
        now = time.time()

        # --- Case 1: We have a prior successful ping --------------------
        if last is not None:
            age = now - last
            if state.is_clone_detected():
                raise ImproperlyConfigured(
                    "🚨 ATTENDANCE: Clone detected. Deployment locked."
                )
            if age > state.MAX_AGE_SECONDS:
                hours = age / 3600
                max_hours = state.MAX_AGE_SECONDS / 3600
                raise ImproperlyConfigured(
                    f"🚨 ATTENDANCE: Last successful ping was {hours:.1f}h ago "
                    f"(max: {max_hours:.1f}h). "
                    f"Run `python manage.py mark_attendance` to renew."
                )
            return  # ✅ Fresh, continue

        # --- Case 2: First ever run (no record yet) ---------------------
        boot_ts = bootstrap.get_bootstrap_timestamp()
        if boot_ts is None:
            raise ImproperlyConfigured(
                "🚨 ATTENDANCE: No attendance record found. "
                "Set ATTENDANCE_BOOTSTRAP_TIMESTAMP=<unix_time> on first deploy, "
                "or run `python manage.py mark_attendance` first."
            )

        grace = bootstrap.seconds_until_bootstrap_expires()
        if grace <= 0:
            raise ImproperlyConfigured(
                "🚨 ATTENDANCE: Bootstrap grace period expired. "
                "Run `python manage.py mark_attendance` to register."
            )
        # ✅ Within grace period — allow startup
