"""Rate limit middleware / FastAPI dependency.

Enforces per-key rate limits by consulting the token bucket and
adding X-RateLimit-* headers to every response.
"""

import structlog
from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = structlog.get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces rate limits on every request.

    Placeholder — fully wired with token bucket and auth in Step 6.
    Currently passes all requests through with default headers.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Add rate limit headers to every response."""
        response = await call_next(request)

        # Default headers (overridden with real values in Step 6)
        response.headers["X-RateLimit-Limit"] = "60"
        response.headers["X-RateLimit-Remaining"] = "59"
        response.headers["X-RateLimit-Reset"] = "0"

        return response
