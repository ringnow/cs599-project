"""SQLAlchemy database models and session management for CS599."""
import os
import time
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone

# 环境变量配置，默认用 SQLite（不需要装 MySQL 也能跑）
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///cs599_history.db"  # 本地开发默认用 SQLite
)

# SQLite 需要 check_same_thread=False + timeout 等待锁；
# MySQL/PostgreSQL 需要 connect_timeout 避免启动时长时间卡住
if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False, "timeout": 30}
else:
    # connect_timeout=5：连接握手超过 5 秒即失败，避免启动时无限阻塞
    _connect_args = {"connect_timeout": 5}

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args=_connect_args,
    pool_pre_ping=True,   # 检测断连自动重连
    pool_recycle=3600,    # 连接回收周期
    pool_size=5,          # 连接池大小
    max_overflow=5,       # 突发时最多额外创建 5 个连接
    pool_timeout=10,      # 获取连接超时 10 秒
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# SQLite WAL 模式：允许多个读 + 一个写并发，避免 "database is locked"
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic = Column(String(500), nullable=False, index=True)
    sub_questions = Column(Text)  # JSON string of sub-questions
    num_sources = Column(Integer, default=0)
    num_papers_cited = Column(Integer, default=0)
    report_preview = Column(Text)  # first 500 chars of report
    duration_seconds = Column(Float, default=0.0)
    provider = Column(String(100))  # which LLM provider was used
    model = Column(String(100))     # which model
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    username = Column(String(100), ForeignKey("users.username"), nullable=True)


class User(Base):
    """Persistent user accounts for JWT auth."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(200), nullable=False)
    email = Column(String(200), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db():
    """Create all tables. Safe to call multiple times (won't drop data)."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency: get a DB session, close it after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_search(db_session, topic, sub_questions, num_sources, num_papers_cited,
                report_preview, duration_seconds, provider, model, username=None):
    """Save a search history entry. Returns record.id on success, None on failure."""
    import json
    import logging as _logging
    _log = _logging.getLogger(__name__)
    record = SearchHistory(
        topic=topic,
        sub_questions=json.dumps(sub_questions, ensure_ascii=False),
        num_sources=num_sources,
        num_papers_cited=num_papers_cited,
        report_preview=report_preview[:500] if report_preview else "",
        duration_seconds=round(duration_seconds, 2),
        provider=provider or "",
        model=model or "",
        username=username,
    )
    db_session.add(record)
    try:
        db_session.commit()
        return record.id
    except SQLAlchemyError as e:
        db_session.rollback()
        _log.error("save_search 失败 (topic=%r): %s | __cause__=%s", topic, e, e.__cause__)
        return None


def get_recent_searches(db_session, limit=20, username=None):
    """Get recent search history, optionally filtered by user.

    Use `username is not None` (not truthiness) so an empty string is
    treated as a real filter — returning records with NULL username —
    rather than silently dropping the filter and leaking all users' data.
    """
    query = db_session.query(SearchHistory).order_by(SearchHistory.created_at.desc())
    if username is not None:
        query = query.filter(SearchHistory.username == username)
    return query.limit(limit).all()


# ── User management ──────────────────────────────────────────────────────────

def get_user_by_username(db_session, username: str):
    """Get a user by username. Returns User or None."""
    return db_session.query(User).filter(User.username == username).first()


def create_user(db_session, username: str, hashed_password: str, email: str = ""):
    """Create a new user. Returns True on success, False if username exists."""
    if get_user_by_username(db_session, username):
        return False
    user = User(username=username, hashed_password=hashed_password, email=email)
    db_session.add(user)
    try:
        db_session.commit()
    except SQLAlchemyError:
        db_session.rollback()
        return False
    return True


def ensure_admin_user(db_session):
    """Create default admin user if it doesn't exist.

    The default password is read from the DEFAULT_ADMIN_PASSWORD env var.
    If the env var is unset, no default admin is created — operators must
    register one explicitly via /api/register. This avoids shipping a
    known-weak credential in production.
    """
    import bcrypt as _bcrypt
    from src.api.auth import _BCRYPT_ROUNDS
    default_pw = os.getenv("DEFAULT_ADMIN_PASSWORD")
    if not default_pw:
        # No password configured → skip default admin creation.
        return
    if not get_user_by_username(db_session, "admin"):
        pw = _bcrypt.hashpw(default_pw.encode(), _bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode()
        create_user(db_session, "admin", pw, "admin@cs599.local")
