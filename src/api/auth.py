"""JWT authentication utilities for CS599."""
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional
import jwt
import bcrypt
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# 密钥：优先环境变量，否则用固定值（仅本地开发）
_DEFAULT_SECRET = "cs599-dev-jwt-secret-key-change-in-real-production-2026-a1b2c3"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", _DEFAULT_SECRET)
if SECRET_KEY == _DEFAULT_SECRET:
    logger.warning(
        "⚠️ JWT_SECRET_KEY 未设置，正在使用不安全的默认密钥。"
        "生产环境请通过环境变量 JWT_SECRET_KEY 配置强随机密钥。"
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
# OWASP 推荐 bcrypt work factor >= 10。可通过 env var 降低用于压测。
_BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "10"))
_DB_RETRY_MAX = 3
_DB_RETRY_DELAY = 0.1


def _hash_pw(password: str) -> str:
    """Hash a password with bcrypt (fast rounds for dev)."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode()


def _verify_pw(plain: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _verify_pw(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return _hash_pw(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate user against database with retry on lock.
    
    SQLite can return 'database is locked' under concurrent access.
    We retry up to 3 times with a short delay.
    """
    from src.storage.database import SessionLocal, get_user_by_username
    for attempt in range(_DB_RETRY_MAX):
        db = SessionLocal()
        try:
            user = get_user_by_username(db, username)
            if not user:
                return None
            if not _verify_pw(password, user.hashed_password):
                return None
            return {"username": user.username, "email": user.email or ""}
        except SQLAlchemyError:
            if attempt < _DB_RETRY_MAX - 1:
                time.sleep(_DB_RETRY_DELAY)
                continue
            return None
        except Exception:
            return None
        finally:
            db.close()
    return None


def register_user(username: str, password: str, email: str = "") -> bool:
    """Register a new user in the database. Returns True on success."""
    from src.storage.database import SessionLocal, create_user
    for attempt in range(_DB_RETRY_MAX):
        db = SessionLocal()
        try:
            return create_user(db, username, _hash_pw(password), email)
        except SQLAlchemyError:
            if attempt < _DB_RETRY_MAX - 1:
                time.sleep(_DB_RETRY_DELAY)
                continue
            return False
        except Exception:
            return False
        finally:
            db.close()
    return False
