from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy.orm import Session
from app.models.user import User, UserStatus
from app.core.security import create_access_token, generate_api_key
from app.core.config import settings
from app.services.credit_management import CreditService
from datetime import datetime, timezone
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    async def verify_google_token(self, token: str) -> Dict:
        """Verify Google OAuth token and return user info"""
        try:
            # Verify the token
            idinfo = id_token.verify_oauth2_token(
                token, 
                requests.Request(), 
                settings.GOOGLE_CLIENT_ID
            )
            
            # Check if token is valid
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
            
            return {
                'google_id': idinfo['sub'],
                'email': idinfo['email'],
                'name': idinfo['name'],
                'avatar_url': idinfo.get('picture', '')
            }
            
        except ValueError as e:
            logger.error(f"Google token verification failed: {str(e)}")
            raise ValueError("Invalid Google token")

    def get_or_create_user(self, google_info: Dict) -> User:
        """Get existing user or create new one"""
        
        # Check if user exists by Google ID
        user = self.db.query(User).filter(
            User.google_id == google_info['google_id']
        ).first()
        
        if user:
            # Update user info and last login
            user.name = google_info['name']
            user.avatar_url = google_info['avatar_url']
            user.last_login = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(user)
            return user
        
        # Check if user exists by email (for account linking)
        user = self.db.query(User).filter(
            User.email == google_info['email']
        ).first()
        
        if user:
            # Link Google account to existing user
            user.google_id = google_info['google_id']
            user.name = google_info['name']
            user.avatar_url = google_info['avatar_url']
            user.last_login = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(user)
            return user
        
        # Create new user
        user = User(
            email=google_info['email'],
            google_id=google_info['google_id'],
            name=google_info['name'],
            avatar_url=google_info['avatar_url'],
            status=UserStatus.ACTIVE,
            api_key=generate_api_key(),
            api_key_created_at=datetime.now(timezone.utc),
            last_login=datetime.now(timezone.utc)
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        # Give new user free credits
        credit_service = CreditService(self.db)
        credit_service.add_credits(
            str(user.id),
            settings.FREE_CREDITS_NEW_USER,
            "Welcome bonus for new user"
        )
        
        logger.info(f"New user created: {user.email}")
        return user

    def create_session_token(self, user: User) -> str:
        """Create JWT session token for user"""
        return create_access_token(data={"sub": str(user.id)})

    def regenerate_api_key(self, user_id: str) -> str:
        """Generate new API key for user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        new_api_key = generate_api_key()
        user.api_key = new_api_key
        user.api_key_created_at = datetime.now(timezone.utc)
        
        self.db.commit()
        return new_api_key