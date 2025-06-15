import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Middleware for request tracing and correlation IDs."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.trace_header = "X-Request-ID"
        self.trace_id_context_var = "request_id"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get or generate trace ID
        trace_id = request.headers.get(self.trace_header)
        if not trace_id:
            trace_id = str(uuid.uuid4())
        
        # Store trace ID in request state
        request.state.trace_id = trace_id
        
        # Add trace ID to response headers
        response = await call_next(request)
        response.headers[self.trace_header] = trace_id
        
        # Add trace ID to logs if in development
        if settings.ENVIRONMENT == "development":
            import logging
            logging.info(f"Request {trace_id}: {request.method} {request.url.path}")
        
        return response


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware for request timing and performance monitoring."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate timing
        process_time = time.time() - start_time
        
        # Add timing headers
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log slow requests
        if process_time > 1.0:  # Log requests taking more than 1 second
            import logging
            logging.warning(
                f"Slow request detected: {request.method} {request.url.path} "
                f"took {process_time:.2f}s (trace_id: {request.state.trace_id})"
            )
        
        return response 