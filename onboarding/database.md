# Database Guide 🗄️

## Table of Contents
- [Overview](#overview)
- [Models & Schemas](#models--schemas)
- [CRUD Operations](#crud-operations)
- [Query Patterns](#query-patterns)
- [Migrations](#migrations)
- [Performance](#performance)
- [Testing](#testing)

## Overview

We use PostgreSQL with SQLAlchemy ORM. This guide covers our database patterns and best practices.

## Models & Schemas

### 1. Base Model
```python
# app/models/base.py
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from app.db.base_class import Base

class BaseModel(Base):
    """Base model with common fields."""
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
```

### 2. Model Relationships
```python
# app/models/user.py
from sqlalchemy import Column, String, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship

class User(BaseModel):
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    items = relationship("Item", back_populates="owner")
    orders = relationship("Order", back_populates="user")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_email_active', 'email', 'is_active'),
    )

# app/models/item.py
class Item(BaseModel):
    title = Column(String(255), index=True, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    owner_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="items")
    order_items = relationship("OrderItem", back_populates="item")
```

## CRUD Operations

### 1. Generic CRUD Base
```python
# app/crud/base.py
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        filter_params: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        query = db.query(self.model)
        if filter_params:
            for field, value in filter_params.items():
                if value is not None:
                    query = query.filter(getattr(self.model, field) == value)
        return query.offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
```

### 2. Custom CRUD Operations
```python
# app/crud/user.py
class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        db_obj = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            is_active=obj_in.is_active,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def authenticate(
        self,
        db: Session,
        *,
        email: str,
        password: str
    ) -> Optional[User]:
        user = self.get_by_email(db, email=email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

user = CRUDUser(User)
```

## Query Patterns

### 1. Complex Queries
```python
# app/crud/item.py
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import joinedload

class CRUDItem(CRUDBase[Item, ItemCreate, ItemUpdate]):
    def get_user_items(
        self,
        db: Session,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        search: Optional[str] = None
    ) -> List[Item]:
        query = db.query(Item).filter(Item.owner_id == user_id)
        
        if min_price is not None:
            query = query.filter(Item.price >= min_price)
        if max_price is not None:
            query = query.filter(Item.price <= max_price)
        if search:
            query = query.filter(
                or_(
                    Item.title.ilike(f"%{search}%"),
                    Item.description.ilike(f"%{search}%")
                )
            )
        
        return query.offset(skip).limit(limit).all()

    def get_items_with_orders(
        self,
        db: Session,
        *,
        item_id: int
    ) -> Optional[Item]:
        return db.query(Item).options(
            joinedload(Item.order_items).joinedload(OrderItem.order)
        ).filter(Item.id == item_id).first()
```

### 2. Bulk Operations
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

## Migrations

### 1. Creating Migrations
```bash
# Create a new migration
alembic revision --autogenerate -m "Add user table"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### 2. Migration Example
```python
# alembic/versions/xxxx_add_user_table.py
def upgrade():
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'ix_user_email',
        'user',
        ['email'],
        unique=True
    )

def downgrade():
    op.drop_index('ix_user_email', table_name='user')
    op.drop_table('user')
```

## Performance

### 1. Query Optimization
```python
# app/crud/order.py
from sqlalchemy import select
from sqlalchemy.orm import selectinload

class CRUDOrder(CRUDBase[Order, OrderCreate, OrderUpdate]):
    def get_order_with_items(
        self,
        db: Session,
        *,
        order_id: int
    ) -> Optional[Order]:
        """Optimized query with eager loading."""
        stmt = select(Order).options(
            selectinload(Order.items).selectinload(OrderItem.item)
        ).where(Order.id == order_id)
        return db.execute(stmt).scalar_one_or_none()
```

### 2. Indexing Strategy
```python
# app/models/order.py
class Order(BaseModel):
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    status = Column(String(50), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    
    # Composite indexes for common queries
    __table_args__ = (
        Index('idx_order_user_status', 'user_id', 'status'),
        Index('idx_order_created_status', 'created_at', 'status'),
    )
```

## Testing

### 1. Model Testing
```python
# tests/models/test_user.py
def test_create_user():
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        is_active=True
    )
    assert user.email == "test@example.com"
    assert user.is_active is True

def test_user_relationships(db_session):
    # Create user and item
    user = create_test_user(db_session)
    item = Item(
        title="Test Item",
        price=10.99,
        owner_id=user.id
    )
    db_session.add(item)
    db_session.commit()
    
    # Test relationship
    assert len(user.items) == 1
    assert user.items[0].title == "Test Item"
```

### 2. CRUD Testing
```python
# tests/crud/test_user.py
def test_create_user(db_session):
    user_in = UserCreate(
        email="test@example.com",
        password="testpass123"
    )
    user = crud_user.create(db_session, obj_in=user_in)
    assert user.email == user_in.email
    assert hasattr(user, "hashed_password")

def test_authenticate_user(db_session):
    user = create_test_user(db_session)
    authenticated = crud_user.authenticate(
        db_session,
        email=user.email,
        password="testpass123"
    )
    assert authenticated is not None
    assert authenticated.id == user.id
```

## Need Help?

If you need assistance with database operations:
1. Check our model examples
2. Review existing queries
3. Ask in team channels
4. Schedule a code review

Remember: Follow our patterns for efficient, maintainable database code! 🎯 