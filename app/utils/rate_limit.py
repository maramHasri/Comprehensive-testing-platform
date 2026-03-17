"""
In-memory rate limiter for forgot-password (per email).
For production at scale, replace with Redis. Config: RATE_LIMIT_FORGOT_PASSWORD e.g. "5 per hour".
"""
from datetime import datetime, timedelta
from threading import Lock

_store = {}  # email -> list of request timestamps
_lock = Lock()

# Parse "5 per hour" -> (5, 3600)
def _parse_limit(limit_str: str) -> tuple[int, int]:
    parts = limit_str.strip().lower().split()
    if len(parts) != 3 or parts[1] != "per":
        return 5, 3600
    try:
        n = int(parts[0])
    except ValueError:
        return 5, 3600
    unit = parts[2]
    if unit in ("hour", "hours"):
        return n, 3600
    if unit in ("minute", "minutes"):
        return n, 60
    if unit in ("day", "days"):
        return n, 86400
    return n, 3600


def is_rate_limited(key: str, limit_str: str) -> bool:
    """
    Returns True if the key (e.g. email) is over the limit and should be rejected.
    Call this before processing forgot-password; if True, return generic success.
    """
    max_requests, window_seconds = _parse_limit(limit_str)
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=window_seconds)
    with _lock:
        times = _store.get(key, [])
        times = [t for t in times if t > cutoff]
        if len(times) >= max_requests:
            return True
        times.append(now)
        _store[key] = times
    return False
