"""Shared cancellation tracking for long-running requests.

Provides a lightweight mechanism to signal cancellation of an in-flight
request across async/sync boundaries.  Each request carries a `request_id`
string; checking `is_cancelled(id)` periodically allows cooperative
cancellation from within skill execution code.
"""

import threading

_lock = threading.Lock()
_cancelled: dict[str, bool] = {}


def mark_cancelled(request_id: str) -> None:
    """Mark *request_id* as cancelled."""
    with _lock:
        _cancelled[request_id] = True


def is_cancelled(request_id: str) -> bool:
    """Return True if *request_id* has been cancelled."""
    with _lock:
        return _cancelled.get(request_id, False)


def clear(request_id: str) -> None:
    """Remove *request_id* from the cancelled set (cleanup)."""
    with _lock:
        _cancelled.pop(request_id, None)
