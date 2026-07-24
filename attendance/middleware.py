import os
import time
from django.http import HttpResponse
from . import state

# Re-check every N seconds per worker (default: 6 hours)
RECHECK_INTERVAL = int(os.environ.get("ATTENDANCE_RECHECK_INTERVAL", 6 * 3600))


class AttendanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self._last_check_time = 0
        self._last_check_passed = True

    def __call__(self, request):
        now = time.time()
        if now - self._last_check_time > RECHECK_INTERVAL:
            self._last_check_passed = (
                state.is_fresh() and not state.is_clone_detected()
            )
            self._last_check_time = now

        if not self._last_check_passed:
            return HttpResponse(
                "🚨 Service unavailable: attendance validation required. "
                "Contact administrator.",
                status=503
            )
        return self.get_response(request)
