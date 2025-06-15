import time
from typing import Optional

import redis
from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.security import verify_token


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_url: Optional[str] = None):
        super().__init__(app)
        self.redis_client = redis.from_url(redis_url or settings.REDIS_URL)

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip rate limiting for certain paths
        if request.url.path in ["/health", "/metrics", "/docs", "/redoc"]:
            return await call_next(request)

        # Determine rate limit based on authentication
        user_id = self.get_user_from_request(request)
        if user_id:
            limit = settings.AUTHENTICATED_RATE_LIMIT
            key = f"rate_limit:user:{user_id}"
        else:
            limit = settings.ANONYMOUS_RATE_LIMIT
            # Use IP address for anonymous users
            client_ip = self.get_client_ip(request)
            key = f"rate_limit:ip:{client_ip}"

        # Check rate limit
        current_time = int(time.time())
        window = 60  # 1 minute window

        # Use sliding window log
        pipe = self.redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, current_time - window)
        pipe.zcard(key)
        pipe.zadd(key, {str(current_time): current_time})
        pipe.expire(key, window)
        results = pipe.execute()

        request_count = results[1]

        if request_count >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {limit} requests per minute.",
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - request_count - 1))
        response.headers["X-RateLimit-Reset"] = str(current_time + window)

        return response

    def get_user_from_request(self, request: Request) -> Optional[str]:
        """Extract user ID from JWT token or API key"""
        # Check Authorization header for JWT
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            user_id = verify_token(token)
            if user_id:
                return user_id

        # Check for API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            # TODO: implement API key lookup
            return self.get_user_by_api_key(api_key)

        return None

    def get_user_by_api_key(self, api_key: str) -> Optional[str]:
        """Get user ID by API key - implement caching for performance"""
        # This should be cached in Redis for performance
        cache_key = f"api_key:{api_key}"
        cached_user_id = self.redis_client.get(cache_key)

        if cached_user_id:
            return cached_user_id.decode("utf-8")

        # Fallback to database lookup (implement caching)
        return None

    def get_client_ip(self, request: Request) -> Optional[str]:
        """Get client IP address"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host
        return None
