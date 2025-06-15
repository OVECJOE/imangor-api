from typing import Optional

from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Get current authenticated user from JWT token"""
    if not credentials:
        return None

    user_id = verify_token(credentials.credentials)
    if not user_id:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    return user


def get_current_user_required(user: User = Depends(get_current_user)) -> User:
    """Require authenticated user"""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def get_user_by_api_key(x_api_key: str = Header(None), db: Session = Depends(get_db)) -> Optional[User]:
    """Get user by API key"""
    if not x_api_key:
        return None

    user = db.query(User).filter(User.api_key == x_api_key).first()
    return user


def get_user_by_api_key_required(user: User = Depends(get_user_by_api_key)) -> User:
    """Require valid API key"""
    if not user:
        raise HTTPException(status_code=401, detail="Valid API key required")
    return user


def get_device_fingerprint_data(request: Request) -> dict:
    """Extract device fingerprint data from request"""
    return {
        "user_agent": request.headers.get("User-Agent", ""),
        "screen_resolution": request.headers.get("X-Screen-Resolution", ""),
        "timezone": request.headers.get("X-Timezone", ""),
        "language": request.headers.get("Accept-Language", ""),
        "platform": request.headers.get("X-Platform", ""),
    }
