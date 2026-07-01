"""Auth middleware: extracts and validates JWT from Authorization header.

Routes are split into three categories:
- Whitelisted: always allowed without auth (login, register, docs, assets).
- Protected: require a valid JWT; missing/invalid token → 401.
- Default: token is parsed if present and user info is injected into
  request.state, but unauthenticated access is still allowed (backward
  compatible for endpoints that gracefully degrade to anonymous).
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from src.api.auth import decode_access_token

# 不需要认证的路径前缀
AUTH_WHITELIST = [
    "/api/health",
    "/api/login",
    "/api/register",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/providers/health",
    "/assets/",
    "/favicon.ico",
]

# 受保护路径前缀：必须携带有效 JWT 才能访问
PROTECTED_PATHS = [
    "/api/queue/research",   # 异步任务提交需登录，便于按用户归属结果
    "/api/queue/result",     # 任务结果只能由提交者查看（粗粒度校验）
]


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that checks JWT for protected routes."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 白名单放行
        for prefix in AUTH_WHITELIST:
            if path.startswith(prefix) or path == "/":
                return await call_next(request)

        # 静态文件放行（非 API 路由）
        if not path.startswith("/api/"):
            return await call_next(request)

        # 检查 Authorization header
        auth_header = request.headers.get("Authorization", "")
        token_payload = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # "Bearer ".length == 7
            token_payload = decode_access_token(token)
            if token_payload:
                # 把用户信息注入 request.state
                request.state.user = token_payload.get("sub", "anonymous")
                request.state.user_email = token_payload.get("email", "")

        # 受保护路径：无有效 token 直接 401
        for prefix in PROTECTED_PATHS:
            if path.startswith(prefix):
                if token_payload is None:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Authentication required for this endpoint"},
                    )
                break

        # 其它路由：无 token 也放行，但 user 为空（向后兼容）
        response = await call_next(request)
        return response
