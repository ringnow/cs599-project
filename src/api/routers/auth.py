"""Authentication API routes."""
import logging
import time
from collections import defaultdict, deque
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.api.auth import authenticate_user, create_access_token, register_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])

# ── In-process login rate limiting ──────────────────────────────────────────
# Simple sliding-window limiter: max LOGIN_MAX_ATTEMPTS per LOGIN_WINDOW_SECONDS
# per client IP. In-memory (per-worker) — sufficient for single-process deploys.
# For multi-worker production, swap for Redis-backed limiter.
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 60
_login_attempts: dict[str, deque] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    """Extract client IP, honoring X-Forwarded-For when present."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(ip: str) -> None:
    """Raise 429 if the IP has exceeded login attempt limits."""
    now = time.time()
    attempts = _login_attempts[ip]
    # Evict timestamps outside the sliding window
    while attempts and now - attempts[0] > LOGIN_WINDOW_SECONDS:
        attempts.popleft()
    if len(attempts) >= LOGIN_MAX_ATTEMPTS:
        retry_after = int(LOGIN_WINDOW_SECONDS - (now - attempts[0])) + 1
        raise HTTPException(
            status_code=429,
            detail=f"登录尝试过多，请 {retry_after} 秒后重试",
            headers={"Retry-After": str(retry_after)},
        )
    attempts.append(now)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=100)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=4, max_length=100)
    email: str = Field(default="", max_length=200)


@router.post("/api/login", response_model=LoginResponse)
def login(req: LoginRequest, request: Request):
    """Authenticate and get a JWT token.

    Rate-limited to LOGIN_MAX_ATTEMPTS per LOGIN_WINDOW_SECONDS per client IP
    to mitigate brute-force attacks.
    """
    ip = _client_ip(request)
    _check_rate_limit(ip)
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(data={"sub": user["username"], "email": user.get("email", "")})
    return LoginResponse(access_token=token, username=user["username"])


@router.post("/api/register")
def register(req: RegisterRequest):
    """Register a new user."""
    success = register_user(req.username, req.password, req.email)
    if not success:
        raise HTTPException(status_code=409, detail="用户名已存在")
    logger.info("New user registered: %s", req.username)
    return {"message": "注册成功", "username": req.username}


@router.get("/api/me")
def get_current_user(request: Request):
    """Get current user info from JWT token."""
    user = getattr(request.state, "user", None)
    if not user:
        return {"username": "anonymous", "message": "未登录"}
    return {"username": user, "email": getattr(request.state, "user_email", "")}
