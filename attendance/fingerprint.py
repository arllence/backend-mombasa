import hashlib
import platform
import uuid
import subprocess
import os
import requests
from django.conf import settings

def get_machine_fingerprint():
    """
    Builds a unique fingerprint from hardware-level identifiers.
    Stealing the code won't work because this won't match on another machine.
    """
    pieces = []

    # 1. MAC address (most reliable on Linux servers)
    try:
        mac = ':'.join(
            f'{(uuid.getnode() >> i) & 0xff:02x}' 
            for i in range(0, 48, 8)
        )
        pieces.append(mac)
    except Exception:
        pass

    # 2. Machine-id (Linux only — works great on VPS/dedicated servers)
    try:
        if os.path.exists("/etc/machine-id"):
            with open("/etc/machine-id") as f:
                pieces.append(f.read().strip())
    except Exception:
        pass

    # 3. CPU info
    try:
        pieces.append(platform.processor())
    except Exception:
        pass

    # 4. Hostname
    pieces.append(platform.node())

    # 5. A "salt" you control (from env var)
    pieces.append(os.environ.get("ATTENDANCE_SALT", "default-salt-change-me"))

    combined = "|".join(pieces)
    return hashlib.sha256(combined.encode()).hexdigest()
