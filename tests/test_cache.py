"""Unit tests for src/storage/cache.py — cache key generation and no-Redis path.

Redis-dependent behavior is tested via mock; the pure cache_key function
is tested directly.
"""
import os
import json
from unittest.mock import patch, MagicMock

import pytest

# Ensure no Redis URL is set so _get_redis returns None
os.environ.pop("REDIS_URL", None)

from src.storage import cache as cache_mod


# ── cache_key (pure function) ────────────────────────────────────────────────

def test_cache_key_is_deterministic():
    """Same topic → same key."""
    k1 = cache_mod.cache_key("quantum computing")
    k2 = cache_mod.cache_key("quantum computing")
    assert k1 == k2


def test_cache_key_case_insensitive():
    """Topic casing should not affect the key."""
    k1 = cache_mod.cache_key("Quantum Computing")
    k2 = cache_mod.cache_key("quantum computing")
    assert k1 == k2


def test_cache_key_strips_whitespace():
    k1 = cache_mod.cache_key("  quantum  ")
    k2 = cache_mod.cache_key("quantum")
    assert k1 == k2


def test_cache_key_different_topics_differ():
    k1 = cache_mod.cache_key("quantum computing")
    k2 = cache_mod.cache_key("classical computing")
    assert k1 != k2


def test_cache_key_has_prefix():
    k = cache_mod.cache_key("test")
    assert k.startswith("cs599:search:")


# ── No-Redis path ────────────────────────────────────────────────────────────

def test_get_cached_returns_none_without_redis():
    """When Redis is unavailable, get_cached should return None (cache miss)."""
    with patch.object(cache_mod, "_get_redis", return_value=None):
        result = cache_mod.get_cached("any topic")
    assert result is None


def test_set_cached_noop_without_redis():
    """When Redis is unavailable, set_cached should silently do nothing."""
    with patch.object(cache_mod, "_get_redis", return_value=None):
        # Should not raise
        cache_mod.set_cached("topic", {"data": 1})


def test_cache_stats_disabled_without_redis():
    with patch.object(cache_mod, "_get_redis", return_value=None):
        stats = cache_mod.cache_stats()
    assert stats["enabled"] is False


# ── With mocked Redis ────────────────────────────────────────────────────────

def test_get_cached_hit():
    """When Redis has the key, get_cached should return the parsed value."""
    fake_redis = MagicMock()
    fake_redis.get.return_value = json.dumps({"report": "hello"})
    with patch.object(cache_mod, "_get_redis", return_value=fake_redis):
        result = cache_mod.get_cached("test topic")
    assert result == {"report": "hello"}


def test_get_cached_miss():
    """When Redis returns None, get_cached should return None."""
    fake_redis = MagicMock()
    fake_redis.get.return_value = None
    with patch.object(cache_mod, "_get_redis", return_value=fake_redis):
        result = cache_mod.get_cached("test topic")
    assert result is None


def test_set_cached_writes_to_redis():
    fake_redis = MagicMock()
    with patch.object(cache_mod, "_get_redis", return_value=fake_redis):
        cache_mod.set_cached("topic", {"data": 1}, ttl=60)
    fake_redis.setex.assert_called_once()
    # Verify the TTL and key
    args = fake_redis.setex.call_args
    assert args[0][0].startswith("cs599:search:")
    # timedelta is the second positional arg
    assert args[0][1].total_seconds() == 60
