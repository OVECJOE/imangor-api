# Core Concepts Guide 🎯

Welcome to our core concepts guide! This document serves as your primary reference for understanding the fundamental patterns, principles, and technical decisions that form the foundation of our codebase. Think of this as your technical bible - a comprehensive resource that will help you understand not just what we do, but why we do it.

## Table of Contents

1. [Overview](#overview)
2. [API Design](#api-design)
3. [Database Patterns](#database-patterns)
4. [Authentication & Authorization](#authentication--authorization)
5. [Caching & Performance](#caching--performance)
6. [Background Tasks](#background-tasks)
7. [Error Handling](#error-handling)
8. [Monitoring & Observability](#monitoring--observability)

## Overview

Our codebase is built on several core concepts that guide our development. Understanding these concepts is crucial for writing maintainable, scalable, and secure code.

### Core Technologies
- **FastAPI**: Our web framework of choice, providing async support, automatic OpenAPI documentation, and type safety
- **SQLAlchemy**: Our ORM, handling database operations with a focus on type safety and query optimization
- **Redis**: Our caching layer, used for session storage, rate limiting, and performance optimization
- **Celery**: Our task queue, managing background jobs and async processing
- **Prometheus**: Our metrics collection system, enabling monitoring and alerting
- **Structured Logging**: Our logging system, providing consistent, searchable logs
- **Security-First**: Our approach to development, ensuring security at every layer

### Why These Choices?
1. **FastAPI**: Chosen for its performance, modern async support, and automatic API documentation
2. **SQLAlchemy**: Selected for its powerful ORM capabilities and type safety
3. **Redis**: Used for its speed and versatility in caching and rate limiting
4. **Celery**: Implemented for reliable background task processing
5. **Prometheus**: Adopted for its powerful metrics collection and querying capabilities

## API Design

### 1. FastAPI Patterns

FastAPI is the backbone of our API layer. Here's how we use it effectively:

#### Dependency Injection
We use FastAPI's dependency injection system extensively to:
- Manage database sessions
- Handle authentication
- Validate requests
- Share common functionality

```python
# app/core/deps.py
from typing import Generator
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.db.session import SessionLocal
from app.core.config import settings
from app.models.user import User

def get_db() -> Generator:
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """User authentication dependency."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401)
    except JWTError:
        raise HTTPException(status_code=401)
        
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401)
    return user
```

#### Type Safety
We leverage FastAPI's type system for:
- Request/response validation
- Automatic API documentation
- Better IDE support
- Runtime type checking

```python
# app/schemas/user.py
from pydantic import BaseModel, EmailStr, constr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: constr(min_length=8)

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

#### API Endpoints
Our endpoints follow a consistent pattern:
- Clear route definitions
- Proper response models
- Dependency injection
- Error handling
- Documentation

```python
# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.deps import get_db, get_current_user
from app.schemas.user import UserCreate, UserResponse
from app.crud import user as user_crud

router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Create new user."""
    user = user_crud.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = user_crud.create(db, obj_in=user_in)
    return user

@router.get("/me", response_model=UserResponse)
async def read_user_me(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Get current user."""
    return current_user
```

### 2. Common API Patterns

#### Pagination
We implement consistent pagination across all list endpoints:

```python
# app/schemas/common.py
from typing import Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar('T')

class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int

# app/api/v1/endpoints/items.py
@router.get("/", response_model=Page[ItemResponse])
async def list_items(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
) -> Page[ItemResponse]:
    """List items with pagination."""
    items = crud.item.get_multi(db, skip=skip, limit=limit)
    total = crud.item.count(db)
    
    return Page(
        items=items,
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )
```

#### Filtering
We implement flexible filtering using query parameters:

```python
# app/api/v1/endpoints/items.py
@router.get("/")
async def list_items(
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
) -> Page[ItemResponse]:
    """List items with filtering."""
    query = db.query(Item)
    
    if category:
        query = query.filter(Item.category == category)
    if min_price is not None:
        query = query.filter(Item.price >= min_price)
    if max_price is not None:
        query = query.filter(Item.price <= max_price)
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return Page(
        items=items,
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )
```

## Database Patterns

### 1. SQLAlchemy Models

Our database models follow a consistent pattern with a base model that provides common fields and functionality:

```python
# app/models/base.py
from datetime import datetime
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, DateTime

class Base(DeclarativeBase):
    """Base model class that all models inherit from."""
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        return cls.__name__.lower()

# Example model
# app/models/user.py
from sqlalchemy import String, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base

class User(Base):
    """User model."""
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    items = relationship("Item", back_populates="owner", cascade="all, delete-orphan")
```

### 2. CRUD Operations

We use a base CRUD class to provide common database operations:

```python
# app/crud/base.py
from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.base_class import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base class for CRUD operations."""
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    def get(self, db: Session, id: int) -> Optional[ModelType]:
        """Get a single record by ID."""
        return db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records with pagination."""
        return db.query(self.model).offset(skip).limit(limit).all()
    
    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        db_obj = self.model(**obj_in.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
```

### 3. Database Migrations

We use Alembic for database migrations:

```python
# migrations/versions/xxx_add_user_table.py
"""Add user table"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_users_email', 'users', ['email'], unique=True)

def downgrade():
    op.drop_index('idx_users_email', table_name='users')
    op.drop_table('users')
```

## Authentication & Authorization

### 1. JWT Authentication

We use JWT for stateless authentication:

```python
# app/core/security.py
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=30)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
```

### 2. Role-Based Access Control

We implement RBAC using FastAPI dependencies:

```python
# app/core/auth.py
from enum import Enum
from typing import List
from fastapi import Depends, HTTPException

class Role(str, Enum):
    """User roles."""
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"

def require_roles(required_roles: List[Role]):
    """Role-based access control dependency."""
    async def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if not any(role in current_user.roles for role in required_roles):
            raise HTTPException(status_code=403)
        return current_user
    return role_checker

# Usage in endpoints
@router.get("/admin/users")
async def list_users(
    current_user: User = Depends(require_roles([Role.ADMIN]))
) -> List[UserResponse]:
    """List all users. Requires admin role."""
    return crud.user.get_multi(db)
```

## Caching & Performance

### 1. Redis Caching

We use Redis for caching API responses:

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
    """Cache decorator for API responses."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try cache
            cached_value = redis_client.get(cache_key)
            if cached_value:
                return json.loads(cached_value)
            
            # Cache miss
            result = await func(*args, **kwargs)
            redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator
```

### 2. Rate Limiting

We implement rate limiting using Redis:

```python
# app/core/rate_limit.py
def rate_limit(key: str, limit: int, window: int):
    """Rate limiting middleware."""
    current = redis_client.get(key)
    if current and int(current) >= limit:
        raise HTTPException(status_code=429)
    
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    pipe.execute()
```

## Background Tasks

### 1. Celery Tasks

We use Celery for background tasks:

```python
# app/core/celery_app.py
from celery import Celery

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

@celery_app.task(bind=True)
def process_data(self, data_id: int):
    """Process data in background."""
    try:
        result = process_data_impl(data_id)
        return result
    except Exception as e:
        raise self.retry(
            exc=e,
            countdown=2 ** self.request.retries,
            max_retries=3
        )
```

## Error Handling

### 1. Custom Exceptions

We use custom exceptions for better error handling:

```python
# app/core/exceptions.py
class AppException(Exception):
    """Base exception for application errors."""
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)

class ValidationException(AppException):
    """Validation error."""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR"
        )
```

### 2. Error Middleware

We use middleware for consistent error handling:

```python
# app/core/middleware.py
@app.middleware("http")
async def error_handling_middleware(
    request: Request,
    call_next
) -> JSONResponse:
    """Global error handling middleware."""
    try:
        return await call_next(request)
    except AppException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "error": {
                    "code": e.error_code,
                    "message": e.message
                }
            }
        )
```

## Monitoring & Observability

### 1. Prometheus Metrics

We use Prometheus for metrics collection:

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
```

### 2. Structured Logging

We use structured logging for better observability:

```python
# app/core/logging.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Setup application logging."""
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # File handler
    file_handler = RotatingFileHandler(
        'app.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
```

## Real-World Scenarios

### 1. User Management Flow

Here's how our core concepts come together in a real-world scenario - user management:

```python
# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.core.cache import cache_response
from app.core.rate_limit import rate_limit
from app.worker.tasks import send_welcome_email

router = APIRouter()

@router.post("/register", response_model=UserResponse)
@rate_limit(key="register", limit=5, window=3600)  # 5 attempts per hour
async def register_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
    background_tasks: BackgroundTasks
) -> UserResponse:
    """
    Register a new user.
    
    This endpoint demonstrates several core concepts:
    - Input validation (Pydantic models)
    - Rate limiting
    - Background tasks
    - Error handling
    - Database operations
    """
    # Validate email uniqueness
    if crud.user.get_by_email(db, email=user_in.email):
        raise ValidationException("Email already registered")
    
    # Create user
    user = crud.user.create(db, obj_in=user_in)
    
    # Send welcome email in background
    background_tasks.add_task(
        send_welcome_email,
        user_id=user.id,
        email=user.email
    )
    
    # Track metrics
    metrics.user_registrations.inc()
    
    return user

@router.get("/profile", response_model=UserProfileResponse)
@cache_response(ttl=300)  # Cache for 5 minutes
async def get_user_profile(
    current_user: User = Depends(get_current_user)
) -> UserProfileResponse:
    """
    Get user profile with cached response.
    
    Demonstrates:
    - Authentication
    - Response caching
    - Profile aggregation
    """
    # Get user's recent activity
    recent_activity = crud.activity.get_recent(
        db,
        user_id=current_user.id,
        limit=5
    )
    
    # Get user's preferences
    preferences = crud.preferences.get(db, user_id=current_user.id)
    
    return UserProfileResponse(
        user=current_user,
        recent_activity=recent_activity,
        preferences=preferences
    )
```

### 2. Order Processing Flow

Another real-world example showing how we handle complex business logic:

```python
# app/api/v1/endpoints/orders.py
from app.core.celery_app import celery_app
from app.core.exceptions import BusinessException

@router.post("/orders", response_model=OrderResponse)
async def create_order(
    *,
    db: Session = Depends(get_db),
    order_in: OrderCreate,
    current_user: User = Depends(get_current_user)
) -> OrderResponse:
    """
    Create a new order.
    
    Demonstrates:
    - Transaction management
    - Background processing
    - Error handling
    - Business logic
    """
    try:
        # Start transaction
        with db.begin():
            # Validate inventory
            for item in order_in.items:
                if not crud.inventory.check_availability(
                    db,
                    item_id=item.id,
                    quantity=item.quantity
                ):
                    raise BusinessException(
                        f"Insufficient inventory for item {item.id}"
                    )
            
            # Create order
            order = crud.order.create_with_items(
                db,
                obj_in=order_in,
                user_id=current_user.id
            )
            
            # Update inventory
            for item in order_in.items:
                crud.inventory.decrease(
                    db,
                    item_id=item.id,
                    quantity=item.quantity
                )
            
            # Create payment intent
            payment = crud.payment.create_intent(
                db,
                order_id=order.id,
                amount=order.total_amount
            )
            
            # Schedule background tasks
            celery_app.send_task(
                "app.worker.tasks.process_order",
                args=[order.id],
                countdown=300  # Process after 5 minutes
            )
            
            return order
            
    except BusinessException as e:
        # Rollback transaction
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
```

## Common Pitfalls and Solutions

### 1. Database Pitfalls

#### N+1 Query Problem
❌ **Wrong Way**:
```python
# This will execute N+1 queries
users = db.query(User).all()
for user in users:
    print(user.items)  # Executes a query for each user
```

✅ **Correct Way**:
```python
# This executes just 1 query
users = db.query(User).options(
    joinedload(User.items)
).all()
for user in users:
    print(user.items)  # No additional queries
```

#### Missing Indexes
❌ **Wrong Way**:
```python
# No index on frequently queried field
class User(Base):
    email = Column(String(255))  # Missing index
```

✅ **Correct Way**:
```python
# Add index for frequently queried field
class User(Base):
    email = Column(String(255), index=True)
    
    # Add composite index for common queries
    __table_args__ = (
        Index('idx_user_status_created', 'is_active', 'created_at'),
    )
```

### 2. Caching Pitfalls

#### Cache Invalidation
❌ **Wrong Way**:
```python
@cache_response(ttl=3600)
async def get_user(user_id: int):
    return crud.user.get(user_id)

# Update user without invalidating cache
async def update_user(user_id: int, data: dict):
    crud.user.update(user_id, data)
    # Cache is now stale!
```

✅ **Correct Way**:
```python
@cache_response(ttl=3600, key_prefix="user")
async def get_user(user_id: int):
    return crud.user.get(user_id)

async def update_user(user_id: int, data: dict):
    crud.user.update(user_id, data)
    # Invalidate cache
    redis_client.delete(f"user:{user_id}")
```

#### Cache Key Collisions
❌ **Wrong Way**:
```python
@cache_response(ttl=3600)
async def get_user_data(user_id: int, data_type: str):
    # Same cache key for different data types!
    return crud.user.get_data(user_id, data_type)
```

✅ **Correct Way**:
```python
@cache_response(ttl=3600, key_prefix="user_data")
async def get_user_data(user_id: int, data_type: str):
    # Include data_type in cache key
    return crud.user.get_data(user_id, data_type)
```

### 3. Authentication Pitfalls

#### Token Management
❌ **Wrong Way**:
```python
# No token expiration
def create_token(user_id: int) -> str:
    return jwt.encode({"sub": user_id}, SECRET_KEY)
```

✅ **Correct Way**:
```python
def create_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=30)
    return jwt.encode(
        {
            "sub": user_id,
            "exp": expire,
            "type": "access"
        },
        SECRET_KEY
    )
```

#### Password Security
❌ **Wrong Way**:
```python
# Plain text password storage
class User(Base):
    password = Column(String(255))
```

✅ **Correct Way**:
```python
class User(Base):
    hashed_password = Column(String(255))
    
    def set_password(self, password: str):
        self.hashed_password = get_password_hash(password)
    
    def verify_password(self, password: str) -> bool:
        return verify_password(password, self.hashed_password)
```

## Performance Considerations

### 1. Database Optimization

#### Query Optimization
```python
# app/crud/base.py
class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def get_optimized(
        self,
        db: Session,
        *,
        filters: dict,
        joins: list = None,
        select: list = None
    ) -> List[ModelType]:
        """
        Optimized query with selective loading.
        
        Parameters:
        - filters: Dictionary of filter conditions
        - joins: List of relationships to join
        - select: List of columns to select
        """
        query = db.query(self.model)
        
        # Apply joins
        if joins:
            for join in joins:
                query = query.join(join)
        
        # Apply filters
        for field, value in filters.items():
            if value is not None:
                query = query.filter(getattr(self.model, field) == value)
        
        # Select specific columns
        if select:
            query = query.with_entities(*select)
        
        return query.all()
```

#### Bulk Operations
```python
# app/crud/base.py
def bulk_create(
    self,
    db: Session,
    *,
    objects_in: List[CreateSchemaType]
) -> List[ModelType]:
    """Efficient bulk creation."""
    db_objects = [
        self.model(**obj.dict())
        for obj in objects_in
    ]
    db.bulk_save_objects(db_objects)
    db.commit()
    return db_objects
```

### 2. Caching Strategies

#### Multi-Level Caching
```python
# app/core/cache.py
class MultiLevelCache:
    """Two-level cache with memory and Redis."""
    def __init__(self):
        self.memory_cache = {}
        self.redis_client = Redis()
    
    async def get(self, key: str) -> Any:
        # Try memory cache first
        if key in self.memory_cache:
            return self.memory_cache[key]
        
        # Try Redis
        value = await self.redis_client.get(key)
        if value:
            # Update memory cache
            self.memory_cache[key] = value
            return value
        
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 300
    ):
        # Set in both caches
        self.memory_cache[key] = value
        await self.redis_client.setex(key, ttl, value)
```

#### Cache Warming
```python
# app/core/cache.py
async def warm_cache():
    """Pre-warm frequently accessed data."""
    # Warm user profiles
    users = crud.user.get_multi(db, limit=1000)
    for user in users:
        await cache.set(
            f"user_profile:{user.id}",
            user.dict(),
            ttl=3600
        )
    
    # Warm product listings
    products = crud.product.get_featured(db)
    await cache.set(
        "featured_products",
        [p.dict() for p in products],
        ttl=1800
    )
```

## Testing Examples

### 1. Unit Testing

#### Testing API Endpoints
```python
# tests/api/test_users.py
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)

def test_create_user():
    """Test user creation endpoint."""
    response = client.post(
        "/api/v1/users/",
        json={
            "email": "test@example.com",
            "password": "testpass123",
            "full_name": "Test User"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

def test_get_user_profile():
    """Test user profile endpoint with authentication."""
    # Create test user
    user = create_test_user()
    token = create_access_token(user.id)
    
    response = client.get(
        "/api/v1/users/profile",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["id"] == user.id
```

#### Testing Database Operations
```python
# tests/crud/test_user.py
from app.crud import user as user_crud
from app.models.user import User

def test_create_user(db_session):
    """Test user creation."""
    user_in = UserCreate(
        email="test@example.com",
        password="testpass123"
    )
    user = user_crud.create(db_session, obj_in=user_in)
    assert user.email == user_in.email
    assert user.id is not None

def test_get_user_by_email(db_session):
    """Test user retrieval by email."""
    # Create test user
    user = create_test_user(db_session)
    
    # Test retrieval
    found = user_crud.get_by_email(
        db_session,
        email=user.email
    )
    assert found.id == user.id
```

### 2. Integration Testing

#### Testing Authentication Flow
```python
# tests/integration/test_auth.py
async def test_login_flow():
    """Test complete login flow."""
    # Register user
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpass123"
        }
    )
    assert response.status_code == 201
    
    # Login
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpass123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    
    # Access protected endpoint
    response = await client.get(
        "/api/v1/users/me",
        headers={
            "Authorization": f"Bearer {data['access_token']}"
        }
    )
    assert response.status_code == 200
```

#### Testing Background Tasks
```python
# tests/integration/test_tasks.py
from app.worker.tasks import process_order
from app.core.celery_app import celery_app

def test_order_processing():
    """Test order processing task."""
    # Create test order
    order = create_test_order()
    
    # Process order
    result = process_order.delay(order.id)
    assert result.id is not None
    
    # Wait for result
    task_result = result.get(timeout=10)
    assert task_result["status"] == "completed"
    
    # Verify order status
    order = crud.order.get(db, id=order.id)
    assert order.status == "processed"
```

### 3. Performance Testing

#### Load Testing
```python
# tests/performance/test_load.py
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login before starting tasks."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpass123"
            }
        )
        self.token = response.json()["access_token"]
    
    @task(3)
    def get_user_profile(self):
        """Test profile endpoint under load."""
        self.client.get(
            "/api/v1/users/profile",
            headers={"Authorization": f"Bearer {self.token}"}
        )
    
    @task(1)
    def create_order(self):
        """Test order creation under load."""
        self.client.post(
            "/api/v1/orders",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "items": [
                    {"id": 1, "quantity": 1}
                ]
            }
        )
```

#### Benchmark Testing
```python
# tests/performance/test_benchmark.py
import pytest
from time import time

@pytest.mark.benchmark
def test_database_performance(benchmark):
    """Benchmark database operations."""
    def create_users():
        users = [
            UserCreate(
                email=f"test{i}@example.com",
                password="testpass123"
            )
            for i in range(100)
        ]
        return crud.user.bulk_create(db, objects_in=users)
    
    # Run benchmark
    result = benchmark(create_users)
    assert len(result) == 100

@pytest.mark.benchmark
def test_cache_performance(benchmark):
    """Benchmark cache operations."""
    def cache_operations():
        # Set cache
        cache.set("test_key", "test_value")
        # Get cache
        return cache.get("test_key")
    
    # Run benchmark
    result = benchmark(cache_operations)
    assert result == "test_value"
```

## Need Help?

If you need assistance understanding our core concepts:
1. Review the specific concept's documentation
2. Check our code examples
3. Ask in team channels
4. Schedule a knowledge sharing session

Remember: Understanding these concepts helps you write better code! 🎯 