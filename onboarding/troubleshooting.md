# Troubleshooting Guide 🔧

Welcome to the troubleshooting guide! This document will help you identify, diagnose, and resolve common issues in our codebase. Whether you're debugging a problem or helping others, this guide will be your reference.

## Table of Contents

1. [Common Issues](#common-issues)
2. [Debugging Tools](#debugging-tools)
3. [Logging and Monitoring](#logging-and-monitoring)
4. [Database Issues](#database-issues)
5. [API Issues](#api-issues)
6. [Deployment Issues](#deployment-issues)
7. [Performance Issues](#performance-issues)
8. [Security Issues](#security-issues)

## Common Issues

### 1. Application Startup Issues

#### Symptoms
- Application fails to start
- Environment variables missing
- Database connection errors
- Port conflicts

#### Solutions
```bash
# Check environment variables - This helps verify if all required environment variables are set
cat .env

# Verify database connection - This tests if the application can connect to the database
python -c "from app.db.session import engine; engine.connect()"

# Check port availability - This shows if port 8000 is already in use by another process
sudo lsof -i :8000

# View application logs - This shows the application's startup logs and any errors
docker logs imangor-api

# Check service status - This shows the status of all services in docker-compose
docker-compose ps
```

### 2. Dependency Issues

#### Symptoms
- Import errors
- Version conflicts
- Missing packages
- Incompatible dependencies

#### Solutions
```bash
# Update dependencies - This updates all packages to their latest compatible versions
pip install -r requirements.txt --upgrade

# Check for conflicts - This identifies any package version conflicts
pip check

# Clean and reinstall - This performs a clean installation of all dependencies
# Useful when you have corrupted packages or version conflicts
rm -rf venv/
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Verify installed packages - This shows all installed packages and their versions
pip freeze
```

## Debugging Tools

### 1. Python Debugger

```python
# app/core/debug.py
import pdb
import logging
from functools import wraps

def debug_function(func):
    """
    A decorator that helps debug functions by:
    1. Catching any exceptions
    2. Logging the error with function name
    3. Dropping into the Python debugger (pdb)
    4. Re-raising the exception after debugging
    
    Usage:
    @debug_function
    def your_function():
        # Your code here
        pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log the error with function name for context
            logging.error(f"Error in {func.__name__}: {str(e)}")
            # Drop into debugger to inspect variables
            pdb.set_trace()
            raise
    return wrapper

# Example usage:
@debug_function
def problematic_function():
    # When this function raises an exception:
    # 1. The error will be logged
    # 2. You'll enter the debugger
    # 3. You can inspect variables using pdb commands:
    #    - n: next line
    #    - s: step into function
    #    - c: continue execution
    #    - p variable: print variable value
    #    - l: list source code
    #    - q: quit debugger
    pass
```

### 2. Logging Configuration

```python
# app/core/logging.py
import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logging():
    """
    Sets up a comprehensive logging system with:
    1. Console output for immediate feedback (INFO level)
    2. File output for detailed debugging (DEBUG level)
    3. Log rotation to manage file sizes
    4. Formatted log messages with timestamps
    
    The logger will:
    - Show INFO and above in console (less verbose)
    - Show DEBUG and above in files (more detailed)
    - Rotate logs at 10MB
    - Keep 5 backup files
    """
    # Create logger with application name
    logger = logging.getLogger("imangor-api")
    logger.setLevel(logging.DEBUG)  # Capture all levels
    
    # Console handler for immediate feedback
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)  # Less verbose in console
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    
    # File handler for detailed logs
    file_handler = RotatingFileHandler(
        'app.log',
        maxBytes=10485760,  # 10MB per file
        backupCount=5       # Keep 5 backup files
    )
    file_handler.setLevel(logging.DEBUG)  # More verbose in files
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_format)
    
    # Add both handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Create logger instance
logger = setup_logging()

# Usage examples:
# logger.debug("Detailed information for debugging")
# logger.info("General information about program execution")
# logger.warning("Warning messages for potentially problematic situations")
# logger.error("Error messages for serious problems")
# logger.critical("Critical messages for fatal errors")
```

## Logging and Monitoring

### 1. Log Analysis

```bash
# View recent logs - Shows the latest log entries in real-time
# Useful for monitoring current application behavior
tail -f app.log

# Search for errors - Finds all error messages in the log
# Useful for identifying patterns in errors
grep -i "error" app.log

# Filter by date - Shows logs for the current date
# Useful for daily log analysis
grep "$(date +%Y-%m-%d)" app.log

# Count occurrences - Counts how many times an error appears
# Useful for identifying most common issues
grep -c "error" app.log

# Export logs for analysis - Saves error logs to a separate file
# Useful for sharing with team or further analysis
cat app.log | grep "error" > errors.log
```

### 2. Monitoring Tools

```python
# app/core/monitoring.py
from prometheus_client import Counter, Histogram
import time

# Error tracking - Counts different types of errors
# Labels help categorize errors by type and endpoint
error_counter = Counter(
    'app_errors_total',
    'Total number of application errors',
    ['error_type', 'endpoint']
)

# Request tracking - Measures request duration
# Labels help analyze performance by method, endpoint, and status
request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'status']
)

def track_error(error_type: str, endpoint: str):
    """
    Tracks application errors with:
    - Error type (e.g., 'validation_error', 'database_error')
    - Endpoint where error occurred
    - Increments counter for monitoring
    """
    error_counter.labels(
        error_type=error_type,
        endpoint=endpoint
    ).inc()

def track_request(method: str, endpoint: str, status: int, duration: float):
    """
    Tracks request performance with:
    - HTTP method (GET, POST, etc.)
    - Endpoint path
    - Response status code
    - Request duration
    """
    request_duration.labels(
        method=method,
        endpoint=endpoint,
        status=status
    ).observe(duration)

# Usage example:
# try:
#     result = process_request()
#     track_request('GET', '/api/users', 200, 0.15)
# except ValidationError as e:
#     track_error('validation_error', '/api/users')
#     raise
```

## Database Issues

### 1. Connection Problems

#### Symptoms
- Connection timeouts
- Connection pool exhaustion
- Database locks
- Slow queries

#### Solutions
```python
# app/core/db.py
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time

# Monitor query execution time
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """
    Called before each query execution.
    Stores the start time for performance measurement.
    """
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """
    Called after each query execution.
    Calculates and logs slow queries (> 1 second).
    Helps identify performance bottlenecks.
    """
    total = time.time() - conn.info['query_start_time'].pop(-1)
    if total > 1.0:  # Log slow queries (> 1 second)
        logger.warning(
            f"Slow query detected ({total:.2f}s): {statement}"
        )

def check_connection_pool():
    """
    Monitors database connection pool status:
    - size: total number of connections
    - checkedin: available connections
    - checkedout: in-use connections
    - overflow: connections beyond pool size
    """
    pool = engine.pool
    return {
        "size": pool.size(),
        "checkedin": pool.checkedin(),
        "checkedout": pool.checkedout(),
        "overflow": pool.overflow()
    }

# Usage example:
# pool_status = check_connection_pool()
# if pool_status["checkedout"] > pool_status["size"] * 0.8:
#     logger.warning("Connection pool near capacity")
```

### 2. Query Optimization

```python
# app/core/db.py
from sqlalchemy import text

def explain_query(query: str, params: dict = None):
    """
    Analyzes query execution plan using EXPLAIN ANALYZE.
    Helps identify:
    - Index usage
    - Table scan operations
    - Join performance
    - Query bottlenecks
    
    Usage:
    results = explain_query("SELECT * FROM users WHERE email = :email", 
                          {"email": "user@example.com"})
    """
    with engine.connect() as conn:
        result = conn.execute(
            text(f"EXPLAIN ANALYZE {query}"),
            params or {}
        )
        return result.fetchall()

def analyze_table(table_name: str):
    """
    Updates table statistics for better query planning.
    Should be run:
    - After bulk data changes
    - When query performance degrades
    - Periodically for large tables
    """
    with engine.connect() as conn:
        conn.execute(text(f"ANALYZE {table_name}"))

# Usage example:
# # Analyze slow query
# plan = explain_query("""
#     SELECT u.*, p.* 
#     FROM users u 
#     JOIN profiles p ON u.id = p.user_id 
#     WHERE u.email = :email
# """, {"email": "user@example.com"})
# 
# # Update statistics
# analyze_table("users")
```

## API Issues

### 1. Request Validation

```python
# app/core/validation.py
from fastapi import HTTPException
from pydantic import ValidationError

def validate_request_data(data: dict, model_class):
    """
    Validates request data against a Pydantic model.
    Provides:
    - Type checking
    - Data validation
    - Custom error messages
    - Consistent error format
    
    Usage:
    @router.post("/users")
    async def create_user(data: dict = Body(...)):
        user_data = validate_request_data(data, UserCreate)
        return create_user_in_db(user_data)
    """
    try:
        return model_class(**data)
    except ValidationError as e:
        # Convert validation errors to HTTP response
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Validation error",
                "errors": e.errors()
            }
        )

# Example usage in endpoint:
@router.post("/resources")
async def create_resource(
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # Validate request data
        resource_data = validate_request_data(data, ResourceCreate)
        # Create resource if validation passes
        return crud.resource.create(db, obj_in=resource_data)
    except HTTPException as e:
        # Log validation errors
        logger.error(f"Validation error: {str(e)}")
        raise
```

### 2. Error Handling

```python
# app/core/errors.py
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Union

class APIError(Exception):
    """
    Custom API error class for consistent error handling.
    Provides:
    - Standardized error format
    - HTTP status codes
    - Error codes for client handling
    - Detailed error messages
    """
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code

async def error_handler(
    request: Request,
    exc: Union[APIError, HTTPException]
) -> JSONResponse:
    """
    Global error handler for consistent error responses.
    Handles:
    - Custom API errors
    - FastAPI HTTP exceptions
    - Standardized JSON responses
    
    Usage:
    app.add_exception_handler(APIError, error_handler)
    app.add_exception_handler(HTTPException, error_handler)
    """
    if isinstance(exc, APIError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message
                }
            }
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"message": exc.detail}}
    )

# Example usage:
# try:
#     if not user.has_permission("admin"):
#         raise APIError(
#             message="Insufficient permissions",
#             status_code=403,
#             error_code="PERMISSION_DENIED"
#         )
# except APIError as e:
#     # Will be handled by error_handler
#     raise
```

## Deployment Issues

### 1. Container Issues

#### Symptoms
- Container fails to start
- Container crashes
- Resource constraints
- Network issues

#### Solutions
```bash
# Check container status - Shows all containers and their states
# Running, exited, or error states
docker ps -a

# View container logs - Shows container output and errors
# Useful for debugging startup issues
docker logs <container_id>

# Check container resources - Shows real-time resource usage
# CPU, memory, network, and disk I/O
docker stats <container_id>

# Inspect container - Shows detailed container configuration
# Network settings, mounts, environment variables
docker inspect <container_id>

# Check container network - Shows network configuration
# Connected networks, IP addresses, ports
docker network inspect <network_name>
```

### 2. Kubernetes Issues

```bash
# Check pod status - Shows all pods and their states
# Running, pending, or error states
kubectl get pods -n imangor-api

# View pod logs - Shows container logs
# Useful for debugging application issues
kubectl logs <pod_name> -n imangor-api

# Describe pod - Shows detailed pod information
# Events, container status, resource usage
kubectl describe pod <pod_name> -n imangor-api

# Check pod events - Shows pod-related events
# Scheduling, pulling images, starting containers
kubectl get events -n imangor-api

# Check service status - Shows service configuration
# Endpoints, ports, selectors
kubectl get svc -n imangor-api
```

## Performance Issues

### 1. Profiling

```python
# app/core/profiling.py
import cProfile
import pstats
import io
from functools import wraps

def profile_endpoint(func):
    """
    Profiles endpoint performance using cProfile.
    Measures:
    - Function call counts
    - Time spent in each function
    - Cumulative time
    - Memory usage
    
    Usage:
    @router.get("/api/resources")
    @profile_endpoint
    async def get_resources():
        # Your endpoint code
        pass
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Start profiling
        pr = cProfile.Profile()
        pr.enable()
        
        # Execute endpoint
        result = await func(*args, **kwargs)
        
        # Stop profiling and analyze
        pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats()
        
        # Log profiling results
        logger.info(f"Profile for {func.__name__}:\n{s.getvalue()}")
        
        return result
    return wrapper

# Example usage:
@router.get("/api/resources")
@profile_endpoint
async def get_resources():
    """
    This endpoint will be profiled:
    - Each request will be measured
    - Results will be logged
    - Performance bottlenecks will be visible
    """
    # Endpoint implementation
    pass
```

### 2. Performance Analysis

```python
# app/core/performance.py
from prometheus_client import Histogram
import time

# Track endpoint performance
endpoint_duration = Histogram(
    'endpoint_duration_seconds',
    'Endpoint execution duration',
    ['endpoint']
)

def analyze_performance(endpoint: str):
    """
    Decorator for endpoint performance analysis.
    Measures:
    - Request duration
    - Slow request detection
    - Performance trends
    
    Usage:
    @router.get("/api/users")
    @analyze_performance("/api/users")
    async def get_users():
        # Your endpoint code
        pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Measure execution time
            start_time = time.time()
            
            # Execute endpoint
            result = await func(*args, **kwargs)
            
            # Calculate and record duration
            duration = time.time() - start_time
            endpoint_duration.labels(endpoint=endpoint).observe(duration)
            
            # Log slow requests
            if duration > 1.0:  # Log slow endpoints
                logger.warning(
                    f"Slow endpoint detected: {endpoint} ({duration:.2f}s)"
                )
            
            return result
        return wrapper
    return decorator

# Example usage:
@router.get("/api/users")
@analyze_performance("/api/users")
async def get_users():
    """
    This endpoint will be monitored for:
    - Response time
    - Slow request detection
    - Performance metrics
    """
    # Endpoint implementation
    pass
```

## Security Issues

### 1. Security Scanning

```bash
# Run security scan - Checks for known vulnerabilities
# Scans all installed packages
safety check

# Check for known vulnerabilities - Alternative to safety
# More detailed vulnerability information
pip-audit

# Scan dependencies - Static code analysis
# Checks for common security issues
bandit -r app/

# Check for secrets - Prevents accidental secret commits
# Scans for API keys, passwords, etc.
git-secrets --scan

# Run security tests - Custom security test suite
# Tests authentication, authorization, etc.
pytest tests/security/
```

### 2. Security Monitoring

```python
# app/core/security.py
from prometheus_client import Counter
import logging

# Track security events
security_events = Counter(
    'security_events_total',
    'Total number of security events',
    ['event_type', 'severity']
)

def track_security_event(event_type: str, severity: str, details: dict):
    """
    Tracks security-related events for:
    - Monitoring
    - Alerting
    - Analysis
    - Incident response
    
    Usage:
    track_security_event(
        "failed_login",
        "high",
        {"user": "user@example.com", "ip": "192.168.1.1"}
    )
    """
    # Increment counter for monitoring
    security_events.labels(
        event_type=event_type,
        severity=severity
    ).inc()
    
    # Log event with details
    logger.warning(
        f"Security event: {event_type} ({severity})",
        extra={"details": details}
    )

# Example usage:
# try:
#     authenticate_user(username, password)
# except AuthenticationError:
#     track_security_event(
#         "failed_login",
#         "high",
#         {
#             "user": username,
#             "ip": request.client.host,
#             "attempt": login_attempts[username]
#         }
#     )
#     raise
```

## Need Help?

If you need assistance with troubleshooting:
1. Check the error logs
2. Review the monitoring dashboards
3. Ask in the troubleshooting channel
4. Create a detailed bug report
5. Schedule a debugging session

Remember: Good debugging is a skill that improves with practice! 🔧 