"""Redis-backed task queue for async research execution.

Uses Redis LIST (lpush/rpop) as a simple message queue.
No external dependency beyond redis-py.
"""
import json
import os
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Callable

REDIS_URL = os.getenv("REDIS_URL", "")
MAX_WORKERS = int(os.getenv("QUEUE_WORKERS", "2"))
RETRY_MAX = int(os.getenv("QUEUE_RETRY_MAX", "3"))
# Max seconds a single handler() call may run before being force-killed.
# Prevents a stuck provider/MCP call from blocking the worker forever.
HANDLER_TIMEOUT = int(os.getenv("QUEUE_HANDLER_TIMEOUT", "600"))  # 10 min
QUEUE_KEY = "cs599:task_queue"
RESULT_PREFIX = "cs599:task_result:"
STATUS_PREFIX = "cs599:task_status:"

# Module-level cached Redis client (lazy-init, reused across calls).
# Falls back to None when REDIS_URL is empty or connection fails.
_redis_client: Optional[object] = None
_redis_failed_at: float = 0
_REDIS_RETRY_INTERVAL = 5  # seconds between reconnect attempts after failure

_executor: Optional[ThreadPoolExecutor] = None
_running = False


def _get_redis():
    """Lazy-init Redis connection with module-level caching.

    Returns None if REDIS_URL is unset or the connection cannot be
    established. On failure, retries every _REDIS_RETRY_INTERVAL seconds
    so transient outages self-heal without restarting the process.
    """
    global _redis_client, _redis_failed_at
    import time as _time

    # Fast path: cached and alive
    if _redis_client is not None:
        try:
            _redis_client.ping()
            return _redis_client
        except Exception:
            _redis_client = None
            _redis_failed_at = _time.time()
            return None

    # Throttle reconnect attempts
    if _redis_failed_at and (_time.time() - _redis_failed_at < _REDIS_RETRY_INTERVAL):
        return None

    if not REDIS_URL:
        return None
    try:
        import redis
        _redis_client = redis.from_url(REDIS_URL, socket_connect_timeout=2, decode_responses=True)
        _redis_client.ping()
        _redis_failed_at = 0
        return _redis_client
    except Exception:
        _redis_client = None
        _redis_failed_at = _time.time()
        return None


def enqueue_task(task_type: str, payload: dict) -> Optional[str]:
    """Push a task to the queue. Returns task_id, or None when Redis is
    unavailable (caller must run synchronously as fallback).

    Args:
        task_type: 'research' | 'paper' | 'survey'
        payload: parameters for the task (topic, provider, etc.)
    """
    task_id = str(uuid.uuid4())
    task = json.dumps({
        "task_id": task_id,
        "task_type": task_type,
        "payload": payload,
        "created_at": time.time(),
        "retry_count": 0,
    }, ensure_ascii=False)

    r = _get_redis()
    if r:
        # Store initial status
        r.setex(f"{STATUS_PREFIX}{task_id}", 86400, json.dumps({
            "status": "queued",
            "task_id": task_id,
            "task_type": task_type,
            "progress": 0,
        }, ensure_ascii=False))
        # Push to queue
        r.lpush(QUEUE_KEY, task)
        return task_id

    # No Redis available: callers should fall back to synchronous execution.
    # Returning None signals the router to either reject the request (503)
    # or run inline depending on the endpoint's policy.
    return None


def get_task_status(task_id: str) -> Optional[dict]:
    """Get current status of a task."""
    r = _get_redis()
    if not r:
        return None
    raw = r.get(f"{STATUS_PREFIX}{task_id}")
    if raw:
        return json.loads(raw)
    return None


def get_task_result(task_id: str) -> Optional[dict]:
    """Get completed task result."""
    r = _get_redis()
    if not r:
        return None
    raw = r.get(f"{RESULT_PREFIX}{task_id}")
    if raw:
        return json.loads(raw)
    return None


def start_worker(handler: Callable[[str, dict], dict]):
    """Start background worker(s) that poll the queue.

    Spawns MAX_WORKERS consumer threads, each running a blocking BRPOP
    loop. Redis LIST is thread-safe so multiple consumers dequeue
    distinct tasks concurrently.

    Args:
        handler: function(task_type, payload) -> result_dict
    """
    global _executor, _running
    if _running:
        return

    if not REDIS_URL:
        return

    _executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    _running = True

    def _poll():
        """One consumer loop. Re-fetches the Redis client on disconnect so
        transient Redis outages don't kill the worker permanently."""
        while _running:
            r = _get_redis()
            if r is None:
                time.sleep(_REDIS_RETRY_INTERVAL)
                continue
            try:
                # BRPOP: blocking pop, timeout 5s
                result = r.brpop(QUEUE_KEY, timeout=5)
                if result is None:
                    continue
                _, task_raw = result
                task = json.loads(task_raw)
                task_id = task["task_id"]

                # Update status to running
                r.setex(f"{STATUS_PREFIX}{task_id}", 86400, json.dumps({
                    "status": "running",
                    "task_id": task_id,
                    "task_type": task["task_type"],
                    "progress": 10,
                }, ensure_ascii=False))

                # Execute with timeout — a stuck handler must not block
                # the worker forever. We run handler() in a sub-thread
                # and enforce HANDLER_TIMEOUT via Future.result().
                try:
                    import concurrent.futures as _cf
                    with _cf.ThreadPoolExecutor(max_workers=1) as _tx:
                        future = _tx.submit(handler, task["task_type"], task["payload"])
                        try:
                            result_data = future.result(timeout=HANDLER_TIMEOUT)
                        except _cf.TimeoutError:
                            # future.cancel() 无法停止已运行的线程；
                            # 通过 mark_cancelled 让 skill 代码协作式退出
                            _payload = task.get("payload", {}) or {}
                            _rid = _payload.get("request_id", "")
                            if _rid:
                                try:
                                    from src.api.cancel import mark_cancelled
                                    mark_cancelled(_rid)
                                except Exception:
                                    pass
                            future.cancel()
                            raise TimeoutError(
                                f"Handler exceeded {HANDLER_TIMEOUT}s timeout (已标记 request_id={_rid} 为取消)"
                            )
                    # Re-fetch r in case the handler took a long time and
                    # the connection went stale mid-execution.
                    r2 = _get_redis() or r
                    r2.setex(f"{STATUS_PREFIX}{task_id}", 86400, json.dumps({
                        "status": "completed",
                        "task_id": task_id,
                        "task_type": task["task_type"],
                        "progress": 100,
                    }, ensure_ascii=False))
                    r2.setex(f"{RESULT_PREFIX}{task_id}", 86400, json.dumps(result_data, ensure_ascii=False))
                except Exception as e:
                    retry = task.get("retry_count", 0) + 1
                    r2 = _get_redis() or r
                    if retry <= RETRY_MAX:
                        # Re-queue with incremented retry count
                        task["retry_count"] = retry
                        r2.setex(f"{STATUS_PREFIX}{task_id}", 86400, json.dumps({
                            "status": "retrying",
                            "task_id": task_id,
                            "task_type": task["task_type"],
                            "progress": 0,
                            "retry": retry,
                        }, ensure_ascii=False))
                        r2.lpush(QUEUE_KEY, json.dumps(task, ensure_ascii=False))
                    else:
                        r2.setex(f"{STATUS_PREFIX}{task_id}", 86400, json.dumps({
                            "status": "failed",
                            "task_id": task_id,
                            "task_type": task["task_type"],
                            "error": str(e),
                            "traceback": traceback.format_exc(),
                            "progress": 100,
                        }, ensure_ascii=False))
            except Exception:
                # Redis error mid-brpop: drop the stale client and retry
                # on the next loop iteration after backoff.
                global _redis_client
                _redis_client = None
                time.sleep(1)

    # Spawn MAX_WORKERS consumer threads for concurrent task processing.
    for _ in range(MAX_WORKERS):
        _executor.submit(_poll)


def stop_worker():
    """Gracefully stop the worker pool."""
    global _running, _executor
    _running = False
    if _executor is not None:
        # Don't wait forever — BRPOP has a 5s timeout, so workers exit
        # within ~5s. cancel_futures=False lets in-flight tasks finish.
        _executor.shutdown(wait=True, cancel_futures=False)
        _executor = None
