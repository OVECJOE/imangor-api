from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.transaction import TransactionType
from app.core.security import generate_api_key, create_access_token
from datetime import datetime, timezone
from app.core.config import settings
from app.core.exceptions import CustomException
from typing import Dict, Any

class AuthService:
    def __init__(self, db: Session):
        self.db = db
    
    async def verify_google_token(self, token: str) -> Dict[str, Any]:
        """Verify Google OAuth token"""
        try:
            idinfo = id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )
            
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
            
            return idinfo
        except ValueError as e:
            raise CustomException(f"Invalid Google token: {str(e)}", 401)
    
    def get_or_create_user(self, google_info: Dict[str, Any]) -> User:
        """Get existing user or create new one from Google info"""
        user = self.db.query(User).filter(
            User.google_id == google_info['sub']
        ).first()
        
        if not user:
            # Check if user exists with same email
            user = self.db.query(User).filter(
                User.email == google_info['email']
            ).first()
            
            if user:
                # Link Google account to existing user
                user.google_id = google_info['sub']
            else:
                # Create new user
                user = User(
                    email=google_info['email'],
                    google_id=google_info['sub'],
                    name=google_info.get('name', google_info['email']),
                    avatar_url=google_info.get('picture'),
                    api_key=generate_api_key(),
                    api_key_created_at=datetime.utcnow(),
                    credits_balance=settings.FREE_CREDITS_NEW_USER
                )
                self.db.add(user)
                
                # Add free credits transaction
                from app.services.credit_management import CreditService
                credit_service = CreditService(self.db)
                credit_service.add_credits(
                    str(user.id),
                    settings.FREE_CREDITS_NEW_USER,
                    "Welcome bonus - free credits for new user",
                    expires_months=settings.CREDIT_EXPIRY_MONTHS,
                    transaction_type=TransactionType.BONUS
                )
        
        user.last_login = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def create_session_token(self, user: User) -> str:
        """Create JWT session token"""
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "type": "access"
        }
        return create_access_token(token_data)
    
    def regenerate_api_key(self, user_id: str) -> str:
        """Regenerate user's API key"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise CustomException("User not found", 404)
        
        user.api_key = generate_api_key()
        user.api_key_created_at = datetime.now(timezone.utc)
        self.db.commit()
        
        return user.api_key
