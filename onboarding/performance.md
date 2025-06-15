# Performance Guide 🚀

Welcome to the performance guide! This document will help you understand our performance optimization practices, monitoring strategies, and how to maintain a high-performing application. Whether you're developing new features or optimizing existing ones, this guide will be your reference.

## Table of Contents

1. [Performance Overview](#performance-overview)
2. [Performance Metrics](#performance-metrics)
3. [Database Optimization](#database-optimization)
4. [Caching Strategies](#caching-strategies)
5. [API Optimization](#api-optimization)
6. [Background Tasks](#background-tasks)
7. [Monitoring and Profiling](#monitoring-and-profiling)
8. [Performance Testing](#performance-testing)

## Performance Overview

Our performance optimization approach focuses on:

- Response time optimization
- Resource utilization
- Scalability
- Throughput
- Latency reduction

### Performance Goals

1. **Response Time**
   - API endpoints: < 200ms
   - Database queries: < 100ms
   - Background tasks: < 5s

2. **Resource Usage**
   - CPU: < 70% average
   - Memory: < 80% of allocated
   - Database connections: < 80% of pool

3. **Scalability**
   - Horizontal scaling
   - Load distribution
   - Resource elasticity

## Performance Metrics

### 1. Key Metrics

```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Response time metrics
request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'status']
)

# Resource usage metrics
cpu_usage = Gauge(
    'cpu_usage_percent',
    'CPU usage in percent'
)

memory_usage = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes'
)

# Database metrics
db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type']
)

db_connections = Gauge(
    'db_connections_total',
    'Total number of database connections'
)

# Cache metrics
cache_hits = Counter(
    'cache_hits_total',
    'Total number of cache hits',
    ['cache_type']
)

cache_misses = Counter(
    'cache_misses_total',
    'Total number of cache misses',
    ['cache_type']
)
```

### 2. Metric Collection

```python
# app/core/middleware.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        request_duration.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).observe(duration)
        
        return response

# Usage in main.py
app.add_middleware(MetricsMiddleware)
```

## Database Optimization

### 1. Query Optimization

```python
# app/crud/base.py
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import select

class CRUDBase:
    def get_with_relations(self, db: Session, id: int):
        # Use selectinload for one-to-many relationships
        query = (
            select(self.model)
            .options(
                selectinload(self.model.related_items),
                joinedload(self.model.owner)
            )
            .where(self.model.id == id)
        )
        return db.execute(query).scalar_one_or_none()
    
    def get_multi_optimized(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict = None
    ):
        query = select(self.model)
        
        if filters:
            for key, value in filters.items():
                query = query.where(getattr(self.model, key) == value)
        
        # Use offset/limit for pagination
        query = query.offset(skip).limit(limit)
        
        # Add index hints if needed
        # query = query.with_hint(self.model, 'USE INDEX (idx_field)')
        
        return db.execute(query).scalars().all()
```

### 2. Indexing Strategy

```sql
-- migrations/versions/xxx_add_indexes.py
"""Add performance indexes

Revision ID: xxx
Revises: previous_revision
Create Date: 2024-03-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add indexes for frequently queried fields
    op.create_index(
        'idx_user_email',
        'users',
        ['email'],
        unique=True
    )
    
    op.create_index(
        'idx_resource_owner',
        'resources',
        ['owner_id', 'created_at']
    )
    
    # Add composite indexes for common query patterns
    op.create_index(
        'idx_resource_status_created',
        'resources',
        ['status', 'created_at']
    )

def downgrade():
    op.drop_index('idx_user_email')
    op.drop_index('idx_resource_owner')
    op.drop_index('idx_resource_status_created')
```

## Caching Strategies

### 1. Redis Caching

```python
# app/core/cache.py
from redis import Redis
from functools import wraps
import json
import pickle

redis_client = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

def cache_response(ttl: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached_value = redis_client.get(cache_key)
            if cached_value:
                cache_hits.labels(cache_type='response').inc()
                return json.loads(cached_value)
            
            # Cache miss, execute function
            cache_misses.labels(cache_type='response').inc()
            result = await func(*args, **kwargs)
            
            # Cache the result
            redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result)
            )
            
            return result
        return wrapper
    return decorator

# Usage in endpoints
@router.get("/api/resources")
@cache_response(ttl=300)
async def get_resources(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    return crud.resource.get_multi(db, skip=skip, limit=limit)
```

### 2. Query Result Caching

```python
# app/crud/base.py
from app.core.cache import redis_client

class CRUDBase:
    def get_cached(
        self,
        db: Session,
        id: int,
        ttl: int = 300
    ):
        cache_key = f"{self.model.__name__}:{id}"
        
        # Try to get from cache
        cached_value = redis_client.get(cache_key)
        if cached_value:
            cache_hits.labels(cache_type='query').inc()
            return pickle.loads(cached_value)
        
        # Cache miss, query database
        cache_misses.labels(cache_type='query').inc()
        result = db.query(self.model).get(id)
        
        if result:
            redis_client.setex(
                cache_key,
                ttl,
                pickle.dumps(result)
            )
        
        return result
```

## API Optimization

### 1. Response Compression

```python
# app/main.py
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(
    GZipMiddleware,
    minimum_size=1000  # Compress responses larger than 1KB
)
```

### 2. Pagination and Filtering

```python
# app/schemas/common.py
from pydantic import BaseModel
from typing import Optional, List

class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20
    max_page_size: int = 100

class FilterParams(BaseModel):
    sort_by: Optional[str] = None
    sort_order: Optional[str] = None
    filters: Optional[dict] = None

# Usage in endpoints
@router.get("/api/resources")
async def get_resources(
    pagination: PaginationParams = Depends(),
    filters: FilterParams = Depends(),
    db: Session = Depends(get_db)
):
    skip = (pagination.page - 1) * pagination.page_size
    limit = min(pagination.page_size, pagination.max_page_size)
    
    query = crud.resource.get_multi_query(db)
    
    if filters.sort_by:
        sort_column = getattr(Resource, filters.sort_by)
        if filters.sort_order == "desc":
            sort_column = sort_column.desc()
        query = query.order_by(sort_column)
    
    if filters.filters:
        for field, value in filters.filters.items():
            query = query.filter(getattr(Resource, field) == value)
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return {
        "items": items,
        "total": total,
        "page": pagination.page,
        "page_size": limit,
        "pages": (total + limit - 1) // limit
    }
```

## Background Tasks

### 1. Task Queue

```python
# app/core/celery_app.py
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.task_routes = {
    "app.worker.*": {"queue": "main-queue"},
    "app.worker.high_priority.*": {"queue": "high-priority-queue"}
}

celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.result_expires = 3600
celery_app.conf.task_acks_late = True
celery_app.conf.task_reject_on_worker_lost = True
```

### 2. Task Implementation

```python
# app/worker/tasks.py
from app.core.celery_app import celery_app
from app.core.metrics import task_duration

@celery_app.task(bind=True)
@task_duration.labels(task_type='process_data').time()
def process_data(self, data_id: int):
    try:
        # Process data
        result = process_data_impl(data_id)
        
        # Update metrics
        task_success.labels(task_type='process_data').inc()
        
        return result
    except Exception as e:
        # Update metrics
        task_failure.labels(
            task_type='process_data',
            error_type=type(e).__name__
        ).inc()
        
        # Retry with exponential backoff
        raise self.retry(
            exc=e,
            countdown=2 ** self.request.retries,
            max_retries=3
        )
```

## Monitoring and Profiling

### 1. Application Profiling

```python
# app/core/profiling.py
import cProfile
import pstats
import io
from functools import wraps
import time

def profile_function(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()
        
        result = func(*args, **kwargs)
        
        pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats()
        
        # Log profiling results
        logger.info(f"Profile for {func.__name__}:\n{s.getvalue()}")
        
        return result
    return wrapper

# Usage in development
@profile_function
def expensive_operation():
    # Operation to profile
    pass
```

### 2. Performance Monitoring

```python
# app/core/monitoring.py
from prometheus_client import start_http_server
import psutil
import threading
import time

def monitor_resources():
    while True:
        # Monitor CPU usage
        cpu_usage.set(psutil.cpu_percent())
        
        # Monitor memory usage
        memory = psutil.Process().memory_info()
        memory_usage.set(memory.rss)
        
        # Monitor database connections
        db_connections.set(get_db_connection_count())
        
        time.sleep(5)

# Start monitoring in a separate thread
monitoring_thread = threading.Thread(
    target=monitor_resources,
    daemon=True
)
monitoring_thread.start()

# Start Prometheus metrics server
start_http_server(8000)
```

## Performance Testing

### 1. Load Testing

```python
# tests/performance/test_load.py
import locust
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def get_resources(self):
        self.client.get("/api/resources")
    
    @task(1)
    def create_resource(self):
        self.client.post(
            "/api/resources",
            json={
                "name": "Test Resource",
                "description": "Test Description"
            }
        )
    
    @task(2)
    def update_resource(self):
        self.client.put(
            f"/api/resources/{self.resource_id}",
            json={"name": "Updated Resource"}
        )

# Run with: locust -f test_load.py
```

### 2. Benchmark Testing

```python
# tests/performance/test_benchmark.py
import pytest
import time
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def benchmark_endpoint(endpoint: str, method: str = "GET", **kwargs):
    start_time = time.time()
    
    if method == "GET":
        response = client.get(endpoint, **kwargs)
    elif method == "POST":
        response = client.post(endpoint, **kwargs)
    elif method == "PUT":
        response = client.put(endpoint, **kwargs)
    
    duration = time.time() - start_time
    
    assert response.status_code == 200
    return duration

@pytest.mark.performance
def test_get_resources_performance():
    durations = []
    for _ in range(100):
        duration = benchmark_endpoint("/api/resources")
        durations.append(duration)
    
    avg_duration = sum(durations) / len(durations)
    assert avg_duration < 0.2  # 200ms threshold
```

## Need Help?

If you need assistance with performance:
1. Check the performance documentation
2. Review performance metrics
3. Ask in the performance channel
4. Schedule a performance review
5. Run performance tests

Remember: Performance is a feature! 🚀 