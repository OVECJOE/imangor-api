from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.auth import AuthService
from app.models.user import User
from app.schemas.user import GoogleAuthRequest, AuthResponse, UserResponse
from app.api.dependencies import get_current_user_required

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/google", response_model=AuthResponse)
async def google_auth(
    auth_request: GoogleAuthRequest,
    db: Session = Depends(get_db)
):
    """Authenticate user with Google OAuth token"""
    auth_service = AuthService(db)
    
    # Verify Google token
    google_info = await auth_service.verify_google_token(auth_request.token)
    
    # Get or create user
    user = auth_service.get_or_create_user(google_info)
    
    # Create session token
    access_token = auth_service.create_session_token(user)
    
    return AuthResponse(
        access_token=access_token,
        user=UserResponse.from_orm(user)
    )

@router.post("/regenerate-api-key")
async def regenerate_api_key(
    user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Regenerate user's API key"""
    auth_service = AuthService(db)
    new_api_key = auth_service.regenerate_api_key(str(user.id))
    
    return {"api_key": new_api_key}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: User = Depends(get_current_user_required)
):
    """Get current user information"""
    return UserResponse.model_validate(user, by_alias=True, strict=True)
