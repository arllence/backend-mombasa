import json
import os
import time
from pathlib import Path
from threading import Lock

_state_lock = Lock()

# You can override these via env vars
STATE_FILE = Path(os.environ.get(
    "ATTENDANCE_STATE_FILE",
    "/var/lib/myapp/.attendance_state"
))
MAX_AGE_SECONDS = int(os.environ.get("ATTENDANCE_MAX_AGE", 86400))  # 24h default


def _read():
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _write(data):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Write atomically: write to temp file, then rename
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    os.replace(tmp, STATE_FILE)


# --- Public API ----------------------------------------------------------

def mark_success():
    """Call after a successful remote ping."""
    with _state_lock:
        _write({
            "last_success": int(time.time()),
            "last_attempt": int(time.time()),
            "failures": 0,
            "clone_detected": False,
        })


def mark_failure():
    """Call when a ping attempt fails."""
    with _state_lock:
        data = _read() or {}
        data["last_attempt"] = int(time.time())
        data["failures"] = data.get("failures", 0) + 1
        _write(data)


def get_last_success():
    data = _read()
    return data.get("last_success") if data else None


def is_fresh():
    last = get_last_success()
    if last is None:
        return False
    return (time.time() - last) <= MAX_AGE_SECONDS


def seconds_since_success():
    last = get_last_success()
    if last is None:
        return float("inf")
    return time.time() - last


def is_clone_detected():
    data = _read()
    return bool(data and data.get("clone_detected"))
