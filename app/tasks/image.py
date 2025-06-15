import logging
from typing import Dict, List, Optional
from uuid import UUID

from celery import Task
from google.cloud import vision, translate_v2 as translate
from PIL import Image
import io

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.exceptions import ProcessingException, ErrorCode
from app.models.job import JobStatus
from app.schemas.image import ImageTranslationRequest
from app.services.storage import get_storage_client
from app.services.credit_management import CreditService

logger = logging.getLogger(__name__)

# Initialize Google Cloud clients
vision_client = vision.ImageAnnotatorClient()
translate_client = translate.Client()
storage_client = get_storage_client()


class ImageProcessingTask(Task):
    """Base task class with error handling and logging."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Task {task_id} failed: {exc}", exc_info=einfo)
        # Update job status in database
        job_id = kwargs.get("job_id")
        if job_id:
            from app.crud.job import update_job_status
            update_job_status(job_id, JobStatus.FAILED, str(exc))
    
    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        logger.info(f"Task {task_id} completed successfully")
        # Update job status in database
        job_id = kwargs.get("job_id")
        if job_id:
            from app.crud.job import update_job_status
            update_job_status(job_id, JobStatus.COMPLETED)


@celery_app.task(base=ImageProcessingTask, bind=True)
def process_image_translation(
    self,
    job_id: UUID,
    request: Dict,  # ImageTranslationRequest as dict
    image_data: bytes,
    target_language: str,
    source_language: Optional[str] = None,
) -> Dict:
    """
    Process image translation task.
    
    Args:
        job_id: Unique job identifier
        request: ImageTranslationRequest as dictionary
        image_data: Raw image data
        target_language: Target language code
        source_language: Optional source language code
    
    Returns:
        Dict containing processing results
    """
    try:
        # Convert request dict back to Pydantic model
        translation_request = ImageTranslationRequest(**request)
        
        # Update job status
        from app.crud.job import update_job_status
        update_job_status(job_id, JobStatus.PROCESSING)
        
        # Perform OCR
        image = vision.Image(content=image_data)
        response = vision_client.text_detection(image=image)
        
        if response.error.message:
            raise ProcessingException(
                error_code=ErrorCode.OCR_FAILED,
                message=f"OCR failed: {response.error.message}"
            )
        
        # Extract text and bounding boxes
        texts = []
        for text in response.text_annotations[1:]:  # Skip first (full image) annotation
            texts.append({
                "text": text.description,
                "bounds": [
                    {"x": vertex.x, "y": vertex.y}
                    for vertex in text.bounding_poly.vertices
                ]
            })
        
        if not texts:
            raise ProcessingException(
                error_code=ErrorCode.OCR_FAILED,
                message="No text detected in image"
            )
        
        # Translate text
        translations = []
        for text in texts:
            result = translate_client.translate(
                text["text"],
                target_language=target_language,
                source_language=source_language
            )
            translations.append({
                "original": text["text"],
                "translated": result["translatedText"],
                "bounds": text["bounds"]
            })
        
        # Create translated image
        pil_image = Image.open(io.BytesIO(image_data))
        # TODO: Implement text overlay with translated text
        # This would use PIL to draw the translated text on the image
        
        # Save translated image
        output_buffer = io.BytesIO()
        pil_image.save(output_buffer, format="PNG")
        output_buffer.seek(0)
        
        # Upload to cloud storage
        bucket = storage_client.bucket(settings.GCS_BUCKET_NAME)
        blob = bucket.blob(f"translations/{job_id}/output.png")
        blob.upload_from_file(output_buffer)
        
        # Return results
        return {
            "job_id": str(job_id),
            "status": "completed",
            "translations": translations,
            "output_url": blob.public_url
        }
        
    except Exception as e:
        logger.exception("Image processing failed")
        raise ProcessingException(
            error_code=ErrorCode.PROCESSING_FAILED,
            message=str(e)
        ) 