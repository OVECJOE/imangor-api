import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    name: str


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: uuid.UUID
    avatar_url: Optional[str] = None
    credits_balance: float
    total_credits_purchased: float
    total_credits_used: float
    api_key: str
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class GoogleAuthRequest(BaseModel):
    token: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
