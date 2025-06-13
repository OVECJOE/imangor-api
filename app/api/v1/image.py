from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import (
    get_current_user, get_user_by_api_key, get_device_fingerprint_data
)
from app.services.device_tracking import DeviceTrackingService
from app.services.credit_management import CreditService
from app.services.image_processing import ImageProcessingService
from app.models.image import ImageJob, ProcessingStatus
from app.models.transaction import TransactionType
from app.models.user import User
from app.schemas.image import ImageJobResponse, SupportedLanguage
from app.core.exceptions import *
from app.core.config import settings
from typing import Optional, List
import uuid

router = APIRouter(prefix="/images", tags=["Image Processing"])

@router.post("/upload", response_model=ImageJobResponse)
async def upload_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_language: SupportedLanguage = Form(...),
    target_language: SupportedLanguage = Form(...),
    webhook_url: Optional[str] = Form(None),
    fingerprint_data: dict = Depends(get_device_fingerprint_data),
    user: Optional[User] = Depends(get_current_user),
    api_user: Optional[User] = Depends(get_user_by_api_key),
    db: Session = Depends(get_db)
):
    """Upload image for text translation"""
    
    # Determine the authenticated user (session or API key)
    authenticated_user = user or api_user
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise InvalidFileFormatException(file_ext)
    
    # Read file content
    file_content = await file.read()
    file_size = len(file_content)
    credit_cost = 0.0
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE / 1024 / 1024:.1f}MB"
        )
    
    # Initialize services
    device_service = DeviceTrackingService(db)
    credit_service = CreditService(db)
    image_service = ImageProcessingService()
    
    # Handle anonymous vs authenticated users
    if not authenticated_user:
        # Anonymous user - check device fingerprint limit
        device_fingerprint = device_service.get_or_create_fingerprint(fingerprint_data)
        
        if device_service.check_anonymous_limit(device_fingerprint):
            raise AnonymousLimitExceededException()
        
        user_id = None
        device_fingerprint_id = device_fingerprint.id
        
        # Increment usage for anonymous user
        device_service.increment_usage(device_fingerprint)
    else:
        # Authenticated user - check credits
        user_id = authenticated_user.id
        device_fingerprint_id = None
        
        # Calculate credit cost
        credit_cost = credit_service.calculate_image_cost(file_size)
        available_credits = credit_service.get_user_credits(str(user_id))
        
        if available_credits < credit_cost:
            raise InsufficientCreditsException(credit_cost, available_credits)
    
    # Upload image to storage
    input_path = image_service.upload_to_gcs(file_content, file.filename)
    
    # Create image job
    job = ImageJob(
        user_id=user_id,
        device_fingerprint_id=device_fingerprint_id,
        original_filename=file.filename,
        file_size_bytes=file_size,
        content_type=file.content_type,
        input_image_path=input_path,
        source_language=source_language.value,
        target_language=target_language.value,
        credits_used=credit_cost if authenticated_user else 0,
        webhook_url=webhook_url
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Deduct credits for authenticated users
    if authenticated_user:
        credit_service.deduct_credits(
            str(user_id),
            credit_cost,
            f"Image translation: {file.filename}",
            TransactionType.USAGE
        )
    
    # Process image asynchronously
    background_tasks.add_task(
        image_service.process_image_async,
        str(job.id),
        input_path,
        source_language.value,
        target_language.value,
        webhook_url
    )
    
    return ImageJobResponse.from_orm(job)

@router.get("/jobs/{job_id}", response_model=ImageJobResponse)
async def get_job_status(
    job_id: uuid.UUID,
    user: Optional[User] = Depends(get_current_user),
    api_user: Optional[User] = Depends(get_user_by_api_key),
    fingerprint_data: dict = Depends(get_device_fingerprint_data),
    db: Session = Depends(get_db)
):
    """Get image processing job status"""
    
    authenticated_user = user or api_user
    
    job = db.query(ImageJob).filter(ImageJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check access permissions
    if authenticated_user:
        if job.user_id != authenticated_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        # For anonymous users, verify device fingerprint
        device_service = DeviceTrackingService(db)
        device_fingerprint = device_service.get_or_create_fingerprint(fingerprint_data)
        if job.device_fingerprint_id != device_fingerprint.id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Add download URL if processing is completed
    job_response = ImageJobResponse.from_orm(job)
    if job.processing_status == ProcessingStatus.COMPLETED and job.output_image_path:
        job_response.download_url = f"https://storage.googleapis.com/{settings.GOOGLE_CLOUD_STORAGE_BUCKET}/{job.output_image_path}"
    
    return job_response

@router.get("/jobs", response_model=List[ImageJobResponse])
async def get_user_jobs(
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get user's image processing jobs"""
    
    jobs = db.query(ImageJob).filter(
        ImageJob.user_id == user.id
    ).order_by(ImageJob.created_at.desc()).offset(skip).limit(limit).all()
    
    job_responses = []
    for job in jobs:
        job_response = ImageJobResponse.from_orm(job)
        if job.processing_status == ProcessingStatus.COMPLETED and job.output_image_path:
            job_response.download_url = f"https://storage.googleapis.com/{settings.GOOGLE_CLOUD_STORAGE_BUCKET}/{job.output_image_path}"
        job_responses.append(job_response)
    
    return job_responses
