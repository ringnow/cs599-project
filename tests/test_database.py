"""Unit tests for src/storage/database.py — SearchHistory, User, and helpers.

Uses an in-memory SQLite database so tests don't touch the real DB file.
"""
import os
import sys

# Force in-memory SQLite before importing database module
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from src.storage import database as db_mod
from src.storage.database import (
    SearchHistory, User, init_db, SessionLocal,
    save_search, get_recent_searches,
    create_user, get_user_by_username,
)


@pytest.fixture(autouse=True)
def fresh_db():
    """Recreate tables before each test for isolation."""
    init_db()
    yield
    # Clean up after test
    with SessionLocal() as s:
        s.query(SearchHistory).delete()
        s.query(User).delete()
        s.commit()


# ── save_search / get_recent_searches ───────────────────────────────────────

def test_save_search_returns_id():
    with SessionLocal() as s:
        rid = save_search(
            db_session=s, topic="quantum computing",
            sub_questions=["q1", "q2"], num_sources=5,
            num_papers_cited=3, report_preview="preview text",
            duration_seconds=12.5, provider="openai", model="gpt-4",
            username="alice",
        )
    assert isinstance(rid, int)
    assert rid > 0


def test_get_recent_searches_returns_ordered():
    with SessionLocal() as s:
        save_search(s, topic="topic A", sub_questions=[], num_sources=1,
                    num_papers_cited=0, report_preview="", duration_seconds=1,
                    provider="", model="", username="alice")
        save_search(s, topic="topic B", sub_questions=[], num_sources=2,
                    num_papers_cited=0, report_preview="", duration_seconds=2,
                    provider="", model="", username="bob")
    results = get_recent_searches(SessionLocal(), limit=10)
    assert len(results) == 2
    # Most recent first (ordered by created_at desc)
    assert results[0].topic in ("topic A", "topic B")


def test_get_recent_searches_filter_by_username():
    with SessionLocal() as s:
        save_search(s, topic="alice's search", sub_questions=[], num_sources=1,
                    num_papers_cited=0, report_preview="", duration_seconds=1,
                    provider="", model="", username="alice")
        save_search(s, topic="bob's search", sub_questions=[], num_sources=1,
                    num_papers_cited=0, report_preview="", duration_seconds=1,
                    provider="", model="", username="bob")
    # Filter by alice
    results = get_recent_searches(SessionLocal(), username="alice")
    assert len(results) == 1
    assert results[0].topic == "alice's search"


def test_get_recent_searches_none_username_returns_all():
    """username=None should NOT filter (returns all records)."""
    with SessionLocal() as s:
        save_search(s, topic="t1", sub_questions=[], num_sources=1,
                    num_papers_cited=0, report_preview="", duration_seconds=1,
                    provider="", model="", username="alice")
        save_search(s, topic="t2", sub_questions=[], num_sources=1,
                    num_papers_cited=0, report_preview="", duration_seconds=1,
                    provider="", model="", username=None)
    results = get_recent_searches(SessionLocal(), username=None)
    assert len(results) == 2


def test_get_recent_searches_empty_string_username_is_real_filter():
    """Empty string username is NOT None, so it IS a real filter (regression
    for the truthiness bug where '' was treated as 'no filter')."""
    with SessionLocal() as s:
        save_search(s, topic="owned", sub_questions=[], num_sources=1,
                    num_papers_cited=0, report_preview="", duration_seconds=1,
                    provider="", model="", username="alice")
        save_search(s, topic="anonymous", sub_questions=[], num_sources=1,
                    num_papers_cited=0, report_preview="", duration_seconds=1,
                    provider="", model="", username=None)
    # Filter by "" should return 0 matches (no record has username="")
    results = get_recent_searches(SessionLocal(), username="")
    assert len(results) == 0


# ── User management ──────────────────────────────────────────────────────────

def test_create_user_success():
    with SessionLocal() as s:
        ok = create_user(s, "testuser", "hashedpw123", "test@test.com")
    assert ok is True


def test_create_user_duplicate_fails():
    with SessionLocal() as s:
        create_user(s, "dupuser", "hashedpw", "a@test.com")
        ok = create_user(s, "dupuser", "otherpw", "b@test.com")
    assert ok is False


def test_get_user_by_username():
    with SessionLocal() as s:
        create_user(s, "findme", "hashedpw", "")
        user = get_user_by_username(s, "findme")
    assert user is not None
    assert user.username == "findme"


def test_get_user_by_username_not_found():
    with SessionLocal() as s:
        user = get_user_by_username(s, "nonexistent")
    assert user is None


# ── Schema invariants ────────────────────────────────────────────────────────

def test_search_history_has_username_column_not_user_id():
    """Regression: column was renamed from user_id to username with FK."""
    assert hasattr(SearchHistory, "username")
    assert not hasattr(SearchHistory, "user_id")


def test_search_history_username_has_foreign_key():
    """The username column should reference users.username."""
    col = SearchHistory.__table__.c.username
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "users"
    assert fks[0].column.name == "username"
