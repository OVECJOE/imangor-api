from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import secrets
import hashlib
from typing import Optional
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except JWTError:
        return None

def generate_api_key() -> str:
    """Generate a secure API key"""
    return secrets.token_urlsafe(settings.API_KEY_LENGTH)

def hash_string(value: str) -> str:
    """Create SHA256 hash of string"""
    return hashlib.sha256(value.encode()).hexdigest()

def create_device_fingerprint(request_data: dict) -> str:
    """Create device fingerprint hash from request data"""
    fingerprint_data = f"{request_data.get('user_agent', '')}" \
                      f"{request_data.get('screen_resolution', '')}" \
                      f"{request_data.get('timezone', '')}" \
                      f"{request_data.get('language', '')}" \
                      f"{request_data.get('platform', '')}"
    return hash_string(fingerprint_data)
