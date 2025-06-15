# Technology Stack Guide 🛠️

Welcome to our technology stack guide! This document explains the technologies we use, why we chose them, and how they work together to create our robust backend system.

## Table of Contents

1. [Overview](#overview)
2. [Core Technologies](#core-technologies)
3. [Development Tools](#development-tools)
4. [Infrastructure](#infrastructure)
5. [Monitoring and Observability](#monitoring-and-observability)
6. [Security Tools](#security-tools)

## Overview

Our technology stack is designed to provide:
- High performance and scalability
- Developer productivity
- Maintainability and reliability
- Security and compliance
- Easy deployment and operations

## Core Technologies

### 1. FastAPI

**Why FastAPI?**
- Modern, fast web framework built on Starlette and Pydantic
- Automatic API documentation with OpenAPI/Swagger
- Type hints and validation
- Async support for high concurrency
- Easy to learn and use

**Key Features We Use:**
```python
# app/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Imangor API",
    description="Backend API for Imangor Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Dependency injection for database sessions
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Example endpoint with automatic validation
@app.post("/users/", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    return crud.user.create(db, obj_in=user)
```

### 2. PostgreSQL

**Why PostgreSQL?**
- Robust, production-ready database
- Advanced features (JSONB, full-text search)
- Strong data integrity
- Excellent performance
- Rich ecosystem

**Key Features We Use:**
```sql
-- Example of JSONB usage for flexible data
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    attributes JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Full-text search example
CREATE INDEX products_search_idx ON products 
USING GIN (to_tsvector('english', name || ' ' || attributes->>'description'));

-- Complex query example
SELECT 
    p.name,
    p.attributes->>'category' as category,
    COUNT(o.id) as order_count
FROM products p
LEFT JOIN orders o ON o.product_id = p.id
WHERE p.attributes->>'category' = 'electronics'
GROUP BY p.id, p.name, p.attributes->>'category'
HAVING COUNT(o.id) > 0;
```

### 3. Redis

**Why Redis?**
- In-memory data store for caching
- Message broker for Celery
- Session storage
- Rate limiting
- Real-time features

**Key Features We Use:**
```python
# app/core/cache.py
from redis import Redis
from functools import wraps

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
                return json.loads(cached_value)
            
            # Cache miss, execute function
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

# Rate limiting example
def rate_limit(key: str, limit: int, window: int):
    current = redis_client.get(key)
    if current and int(current) >= limit:
        raise HTTPException(
            status_code=429,
            detail="Too many requests"
        )
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    pipe.execute()
```

### 4. Celery

**Why Celery?**
- Distributed task queue
- Background job processing
- Scheduled tasks
- Task monitoring
- Scalable worker processes

**Key Features We Use:**
```python
# app/core/celery_app.py
from celery import Celery

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Task configuration
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

# Example task
@celery_app.task(bind=True)
def process_data(self, data_id: int):
    try:
        # Process data
        result = process_data_impl(data_id)
        return result
    except Exception as e:
        # Retry with exponential backoff
        raise self.retry(
            exc=e,
            countdown=2 ** self.request.retries,
            max_retries=3
        )
```

## Development Tools

### 1. Docker

**Why Docker?**
- Consistent development environments
- Easy deployment
- Service isolation
- Resource management
- Reproducible builds

**Key Features We Use:**
```dockerfile
# Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=1.4.0

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry==${POETRY_VERSION} \
    && poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY . .

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Alembic

**Why Alembic?**
- Database migrations
- Version control for schema
- Safe schema updates
- Data migrations
- Rollback support

**Key Features We Use:**
```python
# migrations/versions/xxx_add_user_table.py
"""Add user table

Revision ID: xxx
Revises: previous_revision
Create Date: 2024-03-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    
    # Create indexes
    op.create_index(
        'idx_users_email',
        'users',
        ['email']
    )

def downgrade():
    op.drop_index('idx_users_email')
    op.drop_table('users')
```

### 3. SQLAlchemy

**Why SQLAlchemy?**
- Powerful ORM
- Type safety
- Query building
- Relationship management
- Database abstraction

**Key Features We Use:**
```python
# app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    items = relationship("Item", back_populates="owner")
    
    # Query methods
    @classmethod
    def get_by_email(cls, db: Session, email: str):
        return db.query(cls).filter(cls.email == email).first()
    
    @classmethod
    def get_multi(
        cls,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict = None
    ):
        query = db.query(cls)
        if filters:
            for key, value in filters.items():
                query = query.filter(getattr(cls, key) == value)
        return query.offset(skip).limit(limit).all()
```

## Infrastructure

### 1. Google Cloud Platform

**Why GCP?**
- Scalable infrastructure
- Managed services
- Global presence
- Security features
- Cost-effective

**Services We Use:**
- Cloud Run for containerized applications
- Cloud SQL for managed PostgreSQL
- Cloud Storage for file storage
- Cloud Monitoring for observability
- Cloud IAM for access control

### 2. Kubernetes

**Why Kubernetes?**
- Container orchestration
- Auto-scaling
- Service discovery
- Load balancing
- Rolling updates

**Key Features We Use:**
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: imangor-api
  namespace: imangor-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: imangor-api:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            cpu: "100m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Monitoring and Observability

### 1. Prometheus

**Why Prometheus?**
- Metrics collection
- Alerting
- Time series data
- Service discovery
- Query language

**Key Features We Use:**
```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'status']
)

# Error metrics
error_counter = Counter(
    'app_errors_total',
    'Total number of application errors',
    ['error_type', 'endpoint']
)

# Resource metrics
cpu_usage = Gauge(
    'cpu_usage_percent',
    'CPU usage in percent'
)

memory_usage = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes'
)
```

### 2. Grafana

**Why Grafana?**
- Metrics visualization
- Dashboard creation
- Alert management
- Data exploration
- Team collaboration

**Key Dashboards:**
- API Performance
- Error Rates
- Resource Usage
- Database Metrics
- Business Metrics

## Security Tools

### 1. Security Scanning

**Tools We Use:**
- Safety for dependency scanning
- Bandit for Python code analysis
- Git-secrets for credential detection
- OWASP ZAP for API security testing

**Implementation:**
```bash
# Run security checks
safety check
bandit -r app/
git-secrets --scan
```

### 2. Authentication and Authorization

**Tools We Use:**
- JWT for token-based auth
- OAuth2 for third-party auth
- Role-based access control
- API key management

**Implementation:**
```python
# app/core/security.py
from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)
```

## Need Help?

If you need assistance with our technology stack:
1. Check the specific technology's documentation
2. Review our internal guides
3. Ask in the team's communication channels
4. Schedule a knowledge sharing session

Remember: Understanding our technology choices helps you make better decisions! 🛠️ 