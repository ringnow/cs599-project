"""Redis cache layer for CS599 search results.

环境变量：
    REDIS_URL: Redis 连接地址，例如 redis://127.0.0.1:6379/0
        未设置时缓存功能自动禁用（get_cached 返回 None，set_cached 静默跳过）。
        要启用 Redis 缓存，必须在启动前设置此环境变量，例如：
            set REDIS_URL=redis://127.0.0.1:6379/0   (Windows CMD)
            $env:REDIS_URL="redis://127.0.0.1:6379/0"  (PowerShell)
        或写入项目根目录的 .env 文件。
"""
import os
import json
import hashlib
import time
import logging
from typing import Optional, Any
from datetime import timedelta

logger = logging.getLogger(__name__)

# 注意：REDIS_URL 不在 import 时读取，而是每次 _get_redis() 调用时懒读取，
# 确保 server.py 的 load_dotenv() 加载 .env 后能读取到正确值。
DEFAULT_TTL = int(os.getenv("CACHE_TTL_SECONDS", "3600"))  # 1 hour

_cache_enabled = False
_redis_client = None
_redis_failed_at = 0  # timestamp of last failure; retry after 30s
_RETRY_INTERVAL = 30
# Health-check interval: only ping at most once every _HEALTH_CHECK_INTERVAL
# seconds instead of on every get/set call, to avoid per-op round-trip cost.
_last_health_check = 0.0
_HEALTH_CHECK_INTERVAL = 10


def _get_redis():
    """Lazy-init Redis connection. Returns None if unavailable.

    If Redis was previously connected but went down, retries every
    _RETRY_INTERVAL seconds instead of returning a stale connection forever.
    Connection liveness is checked at most once per _HEALTH_CHECK_INTERVAL
    seconds (not on every call) to avoid adding a ping round-trip to every
    cache operation.
    """
    global _redis_client, _cache_enabled, _redis_failed_at, _last_health_check

    # 每次调用都重新读取 REDIS_URL（懒加载，确保 .env 已加载）
    redis_url = os.getenv("REDIS_URL", "").strip()

    # Fast path: still connected (skip ping unless health check is due)
    if _cache_enabled and _redis_client:
        now = time.time()
        if now - _last_health_check < _HEALTH_CHECK_INTERVAL:
            return _redis_client
        # Periodic health check
        try:
            _redis_client.ping()
            _last_health_check = now
            return _redis_client
        except Exception as e:
            # Connection went stale, fall through to reconnect
            logger.warning("Redis 健康检查失败，将尝试重连: %s", e)
            _cache_enabled = False
            _redis_client = None
            _redis_failed_at = now
            return None

    # Don't retry too frequently after a failure
    if _redis_failed_at and (time.time() - _redis_failed_at < _RETRY_INTERVAL):
        return None

    if not redis_url:
        # 首次调用时记录一次，避免日志刷屏
        if not _redis_failed_at:
            logger.info("REDIS_URL 未配置，Redis 缓存已禁用。设置 REDIS_URL=redis://host:port/db 以启用。")
            _redis_failed_at = time.time()  # 标记已记录过，避免重复日志
        return None
    try:
        import redis
        _redis_client = redis.from_url(redis_url, socket_connect_timeout=2, decode_responses=True, protocol=2)
        _redis_client.ping()
        _cache_enabled = True
        _redis_failed_at = 0
        _last_health_check = time.time()
        logger.info("Redis 连接成功: %s", redis_url)
        return _redis_client
    except Exception as e:
        _cache_enabled = False
        _redis_failed_at = time.time()
        logger.warning("Redis 连接失败 (%s): %s", redis_url, e)
        return None


def cache_key(topic: str, provider: str = "", model: str = "") -> str:
    """Generate a deterministic cache key from topic + provider + model.

    Including provider and model prevents cross-model cache collisions:
    a GPT-4o result for "transformers" must not be served to a user
    querying via Ollama/llama3.
    """
    raw = f"{topic.strip().lower()}|{provider.lower()}|{model.lower()}"
    return "cs599:search:" + hashlib.md5(raw.encode()).hexdigest()


def get_cached(topic: str, provider: str = "", model: str = "") -> Optional[dict]:
    """Try to retrieve cached search result. Returns None on miss."""
    r = _get_redis()
    if not r:
        return None
    try:
        raw = r.get(cache_key(topic, provider, model))
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.warning("Redis get_cached 失败 (topic=%r): %s", topic, e)
    return None


def set_cached(topic: str, result: dict, ttl: int = DEFAULT_TTL,
               provider: str = "", model: str = ""):
    """Cache a search result."""
    r = _get_redis()
    if not r:
        return
    try:
        r.setex(cache_key(topic, provider, model), timedelta(seconds=ttl),
                json.dumps(result, ensure_ascii=False))
    except Exception as e:
        logger.warning("Redis set_cached 失败 (topic=%r): %s", topic, e)


def cache_stats() -> dict:
    """Return cache statistics for monitoring."""
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        return {
            "enabled": False,
            "reason": "REDIS_URL 未配置。设置环境变量 REDIS_URL=redis://host:port/db 以启用 Redis 缓存。",
            "configured": False,
        }
    r = _get_redis()
    if not r:
        return {
            "enabled": False,
            "reason": f"REDIS_URL 已配置 ({redis_url}) 但连接失败，请检查 Redis 服务是否运行。",
            "configured": True,
        }
    try:
        info = r.info("memory")
        dbsize = r.dbsize()
        return {
            "enabled": True,
            "cached_keys": dbsize,
            "memory_used_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
            "redis_url": redis_url,
        }
    except Exception as e:
        logger.warning("Redis cache_stats 获取信息失败: %s", e)
        return {"enabled": True, "error": f"unable to fetch stats: {e}"}
