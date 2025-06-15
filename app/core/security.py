import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.

    Args:
        data: Dictionary containing the data to encode in the token
        expires_delta: Optional timedelta for token expiration. If not provided,
            uses settings.ACCESS_TOKEN_EXPIRE_MINUTES

    Returns:
        str: The encoded JWT token

    Note:
        The token will include an 'exp' claim for expiration time.
    """
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
        return payload
    except JWTError:
        return None


def generate_api_key() -> str:
    """Generate a secure random API key.

    Returns:
        str: A secure random string of length settings.API_KEY_LENGTH

    Note:
        Uses secrets module for cryptographically secure random generation.
    """
    return secrets.token_urlsafe(settings.API_KEY_LENGTH)


def hash_string(value: str) -> str:
    """Create a SHA256 hash of a string.

    Args:
        value: The string to hash

    Returns:
        str: The hexadecimal representation of the SHA256 hash

    Note:
        This is used for creating device fingerprints and other non-cryptographic
        hashing needs. For password hashing, use pwd_context instead.
    """
    return hashlib.sha256(value.encode()).hexdigest()


def create_device_fingerprint(request_data: dict) -> str:
    """Create device fingerprint hash from request data"""
    fingerprint_data = (
        f"{request_data.get('user_agent', '')}"
        f"{request_data.get('screen_resolution', '')}"
        f"{request_data.get('timezone', '')}"
        f"{request_data.get('language', '')}"
        f"{request_data.get('platform', '')}"
    )
    return hash_string(fingerprint_data)
