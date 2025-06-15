import logging
import time
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.exceptions import (
    APIException, ErrorCode, ValidationException, AuthenticationException,
    ResourceException, ProcessingException, ExternalServiceException, SystemException
)
from app.middleware.rate_limiting import RateLimitMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.tracing import RequestTracingMiddleware, RequestTimingMiddleware
from app.schemas.error import ErrorResponse

# Metrics
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_DURATION = Histogram("http_request_duration_seconds", "HTTP request duration")
ERROR_COUNT = Counter("http_errors_total", "Total HTTP errors", ["error_code", "status_code"])

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.ENVIRONMENT == "development" else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("imangor-api")

@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup
    logger.info("Starting up Imangor API...")
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    logger.info("Shutting down Imangor API...")

app = FastAPI(
    title="Imangor API",
    description="Production-grade SaaS API for image text translation with credit-based billing",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan,
)

# Security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
app.add_middleware(RateLimitMiddleware)

# Tracing middleware (add before other middleware)
app.add_middleware(RequestTracingMiddleware)
app.add_middleware(RequestTimingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    REQUEST_DURATION.observe(process_time)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status=response.status_code).inc()

    logging.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")

    return response


# Exception handlers
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    ERROR_COUNT.labels(error_code=exc.error_code, status_code=exc.status_code).inc()
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code=exc.error_code,
            message=str(exc.detail),
            details=exc.details,
            trace_id=UUID(request.state.trace_id),
            timestamp=time.time()
        ).dict()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    ERROR_COUNT.labels(error_code="HTTP_ERROR", status_code=exc.status_code).inc()
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(exc.detail),
            trace_id=UUID(request.state.trace_id),
            timestamp=time.time()
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    ERROR_COUNT.labels(error_code="UNHANDLED_ERROR", status_code=500).inc()
    logger.exception("Unhandled exception occurred")
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred",
            trace_id=UUID(request.state.trace_id),
            timestamp=time.time()
        ).dict()
    )

# Health check with detailed status
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0"
    }

# Enhanced metrics endpoint
@app.get("/metrics")
async def get_metrics():
    return generate_latest()


# Include API router
app.include_router(api_router, prefix="/api")

# Log startup
logger.info(f"Imangor API started in {settings.ENVIRONMENT} mode")
