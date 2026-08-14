import hashlib

from redis import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True)
        self.limit = settings.rate_limit_requests_per_minute

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.rate_limit_enabled or request.url.path in {"/api/v1/health", "/api/v1/ready"}:
            return await call_next(request)

        identity = _identity(request)
        key = f"rate-limit:{identity}:{request.url.path}"
        try:
            count = self.redis.incr(key)
            if count == 1:
                self.redis.expire(key, 60)
            if count > self.limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": "60"},
                )
        except Exception:
            return await call_next(request)
        return await call_next(request)


def _identity(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth:
        return hashlib.sha256(auth.encode("utf-8")).hexdigest()[:24]
    if request.client:
        return request.client.host
    return "unknown"

