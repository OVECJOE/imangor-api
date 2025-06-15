# API Development Guide 🚀

## Table of Contents
- [Overview](#overview)
- [API Structure](#api-structure)
- [Endpoint Patterns](#endpoint-patterns)
- [Request/Response Handling](#requestresponse-handling)
- [Error Handling](#error-handling)
- [Authentication & Authorization](#authentication--authorization)
- [Rate Limiting & Caching](#rate-limiting--caching)
- [Testing](#testing)

## Overview

Our API follows RESTful principles and is built with FastAPI. This guide covers our API development patterns and best practices.

## API Structure

### Directory Layout
```
app/
├── api/
│   ├── v1/
│   │   ├── endpoints/
│   │   │   ├── users.py
│   │   │   ├── items.py
│   │   │   └── orders.py
│   │   ├── deps.py
│   │   └── router.py
│   └── deps.py
├── core/
│   ├── config.py
│   └── security.py
└── schemas/
    ├── user.py
    ├── item.py
    └── order.py
```

### Versioning
We use URL-based versioning (e.g., `/api/v1/users`). Each version has its own router and dependencies.

## Endpoint Patterns

### 1. CRUD Endpoints
```python
# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException
from app.crud import user as crud_user
from app.schemas.user import UserCreate, UserUpdate, UserResponse

router = APIRouter()

@router.post("/", response_model=UserResponse)
async def create_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
    current_user: User = Depends(get_current_active_superuser)
) -> UserResponse:
    """Create new user."""
    user = crud_user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    return crud_user.create(db, obj_in=user_in)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """Get user by ID."""
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

### 2. Search & Filter Endpoints
```python
# app/api/v1/endpoints/items.py
from app.schemas.item import ItemFilter, ItemListResponse

@router.get("/search", response_model=ItemListResponse)
async def search_items(
    *,
    db: Session = Depends(get_db),
    filter: ItemFilter = Depends(),
    skip: int = 0,
    limit: int = 100
) -> ItemListResponse:
    """Search items with filters."""
    items = crud_item.get_multi(
        db,
        skip=skip,
        limit=limit,
        filter_params=filter.dict(exclude_unset=True)
    )
    total = crud_item.count(
        db,
        filter_params=filter.dict(exclude_unset=True)
    )
    return ItemListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )
```

### 3. Action Endpoints
```python
# app/api/v1/endpoints/orders.py
@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    *,
    db: Session = Depends(get_db),
    order_id: int,
    current_user: User = Depends(get_current_active_user)
) -> OrderResponse:
    """Cancel an order."""
    order = crud_order.get(db, id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    if order.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Can only cancel pending orders"
        )
    
    return crud_order.cancel(db, db_obj=order)
```

## Request/Response Handling

### 1. Request Validation
```python
# app/schemas/order.py
from pydantic import BaseModel, Field, validator
from typing import List

class OrderItemCreate(BaseModel):
    item_id: int
    quantity: int = Field(gt=0, le=100)
    
    @validator('quantity')
    def validate_quantity(cls, v, values):
        if v > 100:
            raise ValueError("Quantity cannot exceed 100")
        return v

class OrderCreate(BaseModel):
    items: List[OrderItemCreate]
    shipping_address: str = Field(min_length=10)
    
    @validator('items')
    def validate_items(cls, v):
        if not v:
            raise ValueError("Order must contain at least one item")
        return v
```

### 2. Response Models
```python
# app/schemas/common.py
from typing import Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    skip: int
    limit: int
    
    class Config:
        orm_mode = True

# Usage
class UserListResponse(PaginatedResponse[UserResponse]):
    pass
```

## Error Handling

### 1. Custom Exceptions
```python
# app/core/exceptions.py
from fastapi import HTTPException

class BusinessException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)

class NotFoundException(HTTPException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=404, detail=detail)

# Usage
@router.get("/items/{item_id}")
async def get_item(item_id: int):
    item = crud_item.get(db, id=item_id)
    if not item:
        raise NotFoundException(f"Item {item_id} not found")
    return item
```

### 2. Error Middleware
```python
# app/core/middleware.py
from fastapi import Request
from fastapi.responses import JSONResponse

@app.middleware("http")
async def error_handler(request: Request, call_next):
    try:
        return await call_next(request)
    except BusinessException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        )
    except Exception as e:
        logger.exception("Unhandled error")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
```

## Authentication & Authorization

### 1. JWT Authentication
```python
# app/api/deps.py
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401)
    except JWTError:
        raise HTTPException(status_code=401)
    
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=401)
    return user
```

### 2. Role-Based Access
```python
# app/api/deps.py
from functools import wraps
from fastapi import HTTPException

def require_roles(roles: List[str]):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if not any(role in current_user.roles for role in roles):
                raise HTTPException(
                    status_code=403,
                    detail="Not enough permissions"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

# Usage
@router.post("/admin/users")
@require_roles(["admin"])
async def create_admin_user():
    pass
```

## Rate Limiting & Caching

### 1. Rate Limiting
```python
# app/core/rate_limit.py
from fastapi import HTTPException
from redis import Redis

async def rate_limit(
    key: str,
    limit: int,
    window: int,
    redis: Redis = Depends(get_redis)
):
    """Rate limit decorator."""
    current = await redis.get(key)
    if current and int(current) >= limit:
        raise HTTPException(
            status_code=429,
            detail="Too many requests"
        )
    
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    await pipe.execute()

# Usage
@router.post("/login")
@rate_limit(key="login", limit=5, window=300)
async def login():
    pass
```

### 2. Response Caching
```python
# app/core/cache.py
from functools import wraps
from fastapi import Response

def cache_response(ttl: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key = f"{func.__name__}:{args}:{kwargs}"
            
            # Try cache
            cached = await redis.get(key)
            if cached:
                return Response(
                    content=cached,
                    media_type="application/json"
                )
            
            # Get fresh response
            response = await func(*args, **kwargs)
            
            # Cache response
            await redis.setex(
                key,
                ttl,
                response.json()
            )
            
            return response
        return wrapper
    return decorator

# Usage
@router.get("/items/featured")
@cache_response(ttl=3600)
async def get_featured_items():
    pass
```

## Testing

### 1. Endpoint Testing
```python
# tests/api/test_items.py
from fastapi.testclient import TestClient

def test_create_item(client: TestClient, admin_token: str):
    response = client.post(
        "/api/v1/items/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Test Item",
            "price": 10.99,
            "description": "Test description"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Item"
    assert "id" in data

def test_get_item_not_found(client: TestClient):
    response = client.get("/api/v1/items/999")
    assert response.status_code == 404
```

### 2. Integration Testing
```python
# tests/integration/test_orders.py
async def test_order_flow(
    client: TestClient,
    user_token: str,
    db: Session
):
    # Create item
    item = create_test_item(db)
    
    # Create order
    response = await client.post(
        "/api/v1/orders/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "items": [{"item_id": item.id, "quantity": 1}],
            "shipping_address": "123 Test St"
        }
    )
    assert response.status_code == 201
    order_id = response.json()["id"]
    
    # Cancel order
    response = await client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
```

## Need Help?

If you need assistance with API development:
1. Check our API documentation
2. Review existing endpoints
3. Ask in team channels
4. Schedule a code review

Remember: Follow our patterns for consistent, maintainable APIs! 🎯 