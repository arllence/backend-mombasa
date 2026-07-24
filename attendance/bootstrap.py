import os
import time


def get_bootstrap_timestamp():
    """
    Set ATTENDANCE_BOOTSTRAP_TIMESTAMP=<unix_time> on first deploy.
    This gives you a grace period to run the first ping.
    """
    val = os.environ.get("ATTENDANCE_BOOTSTRAP_TIMESTAMP")
    if not val:
        return None
    try:
        return float(val)
    except ValueError:
        return None


def seconds_until_bootstrap_expires():
    """
    Returns seconds remaining before the bootstrap window closes.
    Negative = already expired.
    """
    from . import state
    ts = get_bootstrap_timestamp()
    if ts is None:
        return float("inf")
    age = time.time() - ts
    return state.MAX_AGE_SECONDS - age
