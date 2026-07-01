"""Unit tests for src/api/auth.py — JWT token and password hashing.

These tests don't require a database connection; they test the pure
crypto functions (hash_pw, verify_pw, create_access_token,
decode_access_token) and the register/authenticate flow with a mocked
DB session.
"""
import os
import time
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture(autouse=True)
def set_test_secret():
    """Use a fixed secret for deterministic token tests."""
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-pytest"
    # Re-import to pick up the new secret
    import importlib
    import src.api.auth as auth_mod
    importlib.reload(auth_mod)
    yield auth_mod
    # Restore default after tests
    os.environ.pop("JWT_SECRET_KEY", None)
    importlib.reload(auth_mod)


# ── Password hashing ─────────────────────────────────────────────────────────

def test_hash_and_verify_password(set_test_secret):
    auth = set_test_secret
    hashed = auth._hash_pw("mysecret123")
    assert hashed != "mysecret123"
    assert auth._verify_pw("mysecret123", hashed) is True


def test_verify_wrong_password_fails(set_test_secret):
    auth = set_test_secret
    hashed = auth._hash_pw("correctpassword")
    assert auth._verify_pw("wrongpassword", hashed) is False


def test_hash_is_unique_per_call(set_test_secret):
    """bcrypt salt ensures different hashes for the same password."""
    auth = set_test_secret
    h1 = auth._hash_pw("samepassword")
    h2 = auth._hash_pw("samepassword")
    assert h1 != h2  # different salts
    # Both should verify against the same password
    assert auth._verify_pw("samepassword", h1)
    assert auth._verify_pw("samepassword", h2)


# ── JWT token ────────────────────────────────────────────────────────────────

def test_create_and_decode_token(set_test_secret):
    auth = set_test_secret
    token = auth.create_access_token(data={"sub": "alice", "email": "a@b.com"})
    payload = auth.decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "alice"
    assert payload["email"] == "a@b.com"


def test_decode_invalid_token_returns_none(set_test_secret):
    auth = set_test_secret
    assert auth.decode_access_token("not-a-real-token") is None


def test_decode_token_with_wrong_secret_returns_none(set_test_secret):
    """Token signed with a different secret should fail verification."""
    auth = set_test_secret
    token = auth.create_access_token(data={"sub": "alice"})
    # Decode with a different secret
    import jwt
    try:
        jwt.decode(token, "wrong-secret", algorithms=[auth.ALGORITHM])
        assert False, "Should have raised"
    except jwt.InvalidTokenError:
        pass  # Expected


def test_token_contains_expiry(set_test_secret):
    auth = set_test_secret
    token = auth.create_access_token(data={"sub": "bob"})
    payload = auth.decode_access_token(token)
    assert "exp" in payload
    # Expiry should be in the future
    assert payload["exp"] > int(time.time())


# ── register_user / authenticate_user (mocked DB) ────────────────────────────

def test_register_user_success(set_test_secret):
    auth = set_test_secret
    with patch.object(auth, "SessionLocal") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        with patch.object(auth, "create_user", return_value=True) as mock_create:
            result = auth.register_user("newuser", "password123", "e@b.com")
    assert result is True
    mock_create.assert_called_once()


def test_register_user_duplicate_returns_false(set_test_secret):
    auth = set_test_secret
    with patch.object(auth, "SessionLocal"):
        with patch.object(auth, "create_user", return_value=False):
            result = auth.register_user("existing", "pw", "")
    assert result is False


def test_authenticate_user_success(set_test_secret):
    auth = set_test_secret
    fake_user = {"username": "alice", "hashed_password": auth._hash_pw("pw123")}
    with patch.object(auth, "SessionLocal"):
        with patch.object(auth, "get_user_by_username", return_value=fake_user):
            result = auth.authenticate_user("alice", "pw123")
    assert result is not None
    assert result["username"] == "alice"


def test_authenticate_user_wrong_password(set_test_secret):
    auth = set_test_secret
    fake_user = {"username": "alice", "hashed_password": auth._hash_pw("correct")}
    with patch.object(auth, "SessionLocal"):
        with patch.object(auth, "get_user_by_username", return_value=fake_user):
            result = auth.authenticate_user("alice", "wrong")
    assert result is None


def test_authenticate_user_not_found(set_test_secret):
    auth = set_test_secret
    with patch.object(auth, "SessionLocal"):
        with patch.object(auth, "get_user_by_username", return_value=None):
            result = auth.authenticate_user("ghost", "anything")
    assert result is None
