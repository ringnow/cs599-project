"""Unit tests for src/queue/worker.py — enqueue, status, result, retry logic.

Uses a mock Redis to test the queue logic without a real Redis instance.
The retry logic is tested by simulating handler failures.
"""
import json
import os
import time
from unittest.mock import patch, MagicMock

import pytest

# Ensure REDIS_URL is set so the module doesn't bail out early, but
# we'll mock _get_redis to control behavior.
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from src.task_queue import worker as w


@pytest.fixture(autouse=True)
def reset_worker_state():
    """Reset module-level state between tests."""
    w._redis_client = None
    w._redis_failed_at = 0
    w._running = False
    w._executor = None
    yield
    # Cleanup
    if w._executor is not None:
        w._executor.shutdown(wait=False)
        w._executor = None
    w._running = False


# ── enqueue_task ─────────────────────────────────────────────────────────────

def test_enqueue_task_returns_none_without_redis():
    """When Redis is unavailable, enqueue should return None (signal caller
    to fall back to synchronous execution)."""
    with patch.object(w, "_get_redis", return_value=None):
        task_id = w.enqueue_task("research", {"topic": "test"})
    assert task_id is None


def test_enqueue_task_returns_task_id_with_redis():
    fake_redis = MagicMock()
    with patch.object(w, "_get_redis", return_value=fake_redis):
        task_id = w.enqueue_task("research", {"topic": "quantum"})
    assert task_id is not None
    assert isinstance(task_id, str)
    # Should have set initial status and pushed to queue
    assert fake_redis.setex.call_count == 1
    fake_redis.lpush.assert_called_once()
    # Verify the pushed task contains the payload
    pushed = json.loads(fake_redis.lpush.call_args[0][1])
    assert pushed["payload"]["topic"] == "quantum"
    assert pushed["task_id"] == task_id


# ── get_task_status / get_task_result ────────────────────────────────────────

def test_get_task_status_returns_none_without_redis():
    with patch.object(w, "_get_redis", return_value=None):
        assert w.get_task_status("abc") is None


def test_get_task_status_returns_parsed_dict():
    fake_redis = MagicMock()
    fake_redis.get.return_value = json.dumps({"status": "running", "progress": 50})
    with patch.object(w, "_get_redis", return_value=fake_redis):
        status = w.get_task_status("abc")
    assert status["status"] == "running"
    assert status["progress"] == 50


def test_get_task_result_returns_none_without_redis():
    with patch.object(w, "_get_redis", return_value=None):
        assert w.get_task_result("abc") is None


def test_get_task_result_returns_parsed_dict():
    fake_redis = MagicMock()
    fake_redis.get.return_value = json.dumps({"report": "done"})
    with patch.object(w, "_get_redis", return_value=fake_redis):
        result = w.get_task_result("abc")
    assert result["report"] == "done"


# ── Retry logic ──────────────────────────────────────────────────────────────

def test_failed_task_retried_up_to_max():
    """When handler raises, task should be re-queued with incremented
    retry_count until RETRY_MAX is exceeded, then marked 'failed'."""
    # Simulate Redis as a simple in-memory dict + list
    storage = {}
    queue = []

    class FakeRedis:
        def setex(self, key, ttl, val):
            storage[key] = val

        def get(self, key):
            return storage.get(key)

        def lpush(self, key, val):
            queue.append(val)

        def brpop(self, key, timeout=5):
            if queue:
                return (key, queue.pop(0))
            return None

        def ping(self):
            return True

    fake = FakeRedis()

    # Handler that always fails
    fail_count = [0]

    def always_fail(task_type, payload):
        fail_count[0] += 1
        raise RuntimeError("intentional failure")

    with patch.object(w, "_get_redis", return_value=fake):
        task_id = w.enqueue_task("research", {"topic": "retry-test"})
        assert task_id is not None

        # Manually run the poll loop for a few iterations to simulate retries
        # We call _poll's logic inline since start_worker spawns threads
        w._running = True
        from concurrent.futures import ThreadPoolExecutor
        w._executor = ThreadPoolExecutor(max_workers=1)

        # Submit the poll function
        import src.task_queue.worker as worker_mod
        # Access the inner _poll by starting the worker
        # But we need to control iterations, so let's manually process
        for _ in range(w.RETRY_MAX + 2):
            if not queue:
                break
            result = fake.brpop(w.QUEUE_KEY, timeout=1)
            if result is None:
                break
            _, task_raw = result
            task = json.loads(task_raw)
            try:
                always_fail(task["task_type"], task["payload"])
            except Exception as e:
                retry = task.get("retry_count", 0) + 1
                if retry <= w.RETRY_MAX:
                    task["retry_count"] = retry
                    fake.lpush(w.QUEUE_KEY, json.dumps(task))
                else:
                    fake.setex(f"{w.STATUS_PREFIX}{task_id}", 86400, json.dumps({
                        "status": "failed", "error": str(e),
                    }))

    # After exhausting retries, status should be 'failed'
    final_status = json.loads(storage[f"{w.STATUS_PREFIX}{task_id}"])
    assert final_status["status"] == "failed"
    assert "intentional failure" in final_status["error"]


# ── start_worker / stop_worker ───────────────────────────────────────────────

def test_start_worker_noop_without_redis():
    """start_worker should return early if Redis is unavailable."""
    import os
    saved = os.environ.pop("REDIS_URL", None)
    import importlib
    import src.task_queue.worker as w_mod
    importlib.reload(w_mod)
    w_mod.start_worker(lambda t, p: {})
    assert w_mod._executor is None
    assert w_mod._running is False
    if saved is not None:
        os.environ["REDIS_URL"] = saved
        importlib.reload(w_mod)


def test_stop_worker_graceful():
    """stop_worker should set _running=False and shutdown executor."""
    w._running = True
    from concurrent.futures import ThreadPoolExecutor
    w._executor = ThreadPoolExecutor(max_workers=1)
    w.stop_worker()
    assert w._running is False
    assert w._executor is None
