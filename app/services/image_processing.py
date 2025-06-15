import asyncio
import io
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import httpx
from google.cloud import storage
from google.cloud import translate_v2 as translate
from google.cloud import vision
from PIL import Image, ImageDraw, ImageFont

from app.core.config import settings
from app.models.image import ImageJob, ProcessingStatus
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


class ImageProcessingService:
    """Service for processing and translating text in images.

    This service handles:
    - Image upload/download to/from Google Cloud Storage
    - Text detection using Google Vision API
    - Text translation using Google Translate API
    - Image manipulation with PIL
    - Webhook notifications
    """

    def __init__(self):
        """Initialize the image processing service with Google Cloud clients."""
        self.vision_client = vision.ImageAnnotatorClient()
        self.translate_client = translate.Client()
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(settings.GOOGLE_CLOUD_STORAGE_BUCKET)

    def upload_to_gcs(self, file_content: bytes, filename: str) -> str:
        """Upload file to Google Cloud Storage"""
        blob_name = f"images/{uuid.uuid4()}/{filename}"
        blob = self.bucket.blob(blob_name)
        blob.upload_from_string(file_content)
        return blob_name

    def download_from_gcs(self, blob_name: str) -> bytes:
        """Download file from Google Cloud Storage"""
        blob = self.bucket.blob(blob_name)
        return blob.download_as_bytes()

    def detect_text(self, image_content: bytes) -> Tuple[List[dict], float]:
        """Detect text in image using Google Vision API"""
        image = vision.Image(content=image_content)
        response = self.vision_client.text_detection(image=image)
        if response.error.message:
            raise Exception(f"Google Vision API error: {response.error.message}")

        text_annotations = response.text_annotations
        if not text_annotations:
            return [], 0.0

        # Calculate average confidence
        confidences = [annotation.confidence for annotation in text_annotations if hasattr(annotation, "confidence")]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Process text blocks
        text_blocks = []
        for annotation in text_annotations[1:]:  # Skip the first one (full text)
            vertices = [(vertex.x, vertex.y) for vertex in annotation.bounding_poly.vertices]
            text_blocks.append(
                {
                    "text": annotation.description,
                    "vertices": vertices,
                    "confidence": getattr(annotation, "confidence", 0.0),
                }
            )

        return text_blocks, avg_confidence

    def translate_text(self, text: str, target_language: str, source_language: Optional[str] = None) -> str:
        """Translate text using Google Translate API"""
        result = self.translate_client.translate(text, target_language=target_language, source_language=source_language)
        return result["translatedText"]

    def create_translated_image(
        self,
        original_image: bytes,
        text_blocks: List[dict],
        target_language: str,
        source_language: Optional[str] = None,
    ) -> bytes:
        """Create new image with translated text"""
        # Open original image
        image = Image.open(io.BytesIO(original_image))
        draw = ImageDraw.Draw(image)

        # Process each text block
        for block in text_blocks:
            # Translate the text
            translated_text = self.translate_text(block["text"], target_language, source_language)

            # Calculate bounding box
            vertices = block["vertices"]
            x_coords = [v[0] for v in vertices]
            y_coords = [v[1] for v in vertices]
            x_min, x_max = min(x_coords), max(x_coords)
            y_min, y_max = min(y_coords), max(y_coords)

            # Clear original text area (fill with white or background color)
            draw.rectangle([x_min, y_min, x_max, y_max], fill="white")

            # Calculate font size based on bounding box
            box_width = x_max - x_min
            box_height = y_max - y_min
            font_size = min(box_height - 4, box_width // len(translated_text) * 2)
            font_size = max(12, min(font_size, 72))  # Reasonable bounds

            try:
                # Try to use a basic font
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
            except Exception:
                # Fallback to default font
                font = ImageFont.load_default()

            # Draw translated text
            text_color = "black"  # You might want to detect original text color
            draw.text((x_min + 2, y_min + 2), translated_text, fill=text_color, font=font)

        # Save to bytes
        output_buffer = io.BytesIO()
        image.save(output_buffer, format="PNG")
        return output_buffer.getvalue()

    async def process_image_async(
        self,
        job_id: str,
        input_path: str,
        source_lang: str,
        target_lang: str,
        user_id: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ):
        """Async image processing for webhook support"""
        db = SessionLocal()

        try:
            # Create job record
            job = ImageJob(
                user_id=user_id,
                status=ProcessingStatus.PROCESSING,
                target_language=target_lang,
                source_language=source_lang,
                webhook_url=webhook_url,
            )
            db.add(job)
            db.commit()

            # Download and process image
            image_content = self.download_from_gcs(input_path)
            text_blocks, confidence = self.detect_text(image_content)

            if not text_blocks:
                # No text detected - apply penalty
                job.processing_status = ProcessingStatus.FAILED
                job.error_message = "No text detected in image"
                db.commit()

                if webhook_url:
                    await self.send_webhook(
                        webhook_url,
                        {
                            "job_id": str(job_id),
                            "status": "failed",
                            "error": "No text detected in image",
                        },
                    )
                return

            # Translate image
            translated_image = self.create_translated_image(image_content, text_blocks, target_lang, source_lang)

            # Upload result
            output_filename = f"translated_{uuid.uuid4()}.png"
            output_path = self.upload_to_gcs(translated_image, output_filename)

            # Update job
            job.processing_status = ProcessingStatus.COMPLETED
            job.processing_completed_at = datetime.now(timezone.utc)
            job.output_image_path = output_path
            job.text_blocks_detected = len(text_blocks)
            job.text_blocks_translated = len(text_blocks)
            job.ocr_confidence = confidence
            db.commit()

            # Send webhook if provided
            if webhook_url:
                await self.send_webhook(
                    webhook_url,
                    {
                        "job_id": str(job_id),
                        "status": "completed",
                        "output_url": (
                            "https://storage.googleapis.com/"
                            + settings.GOOGLE_CLOUD_STORAGE_BUCKET
                            + "/"
                            + output_path
                        ),
                        "text_blocks_detected": len(text_blocks),
                        "confidence": confidence,
                    },
                )

        except Exception as e:
            # Update job with error
            job = db.query(ImageJob).filter(ImageJob.id == job_id).first()
            job.processing_status = ProcessingStatus.FAILED
            job.error_message = str(e)
            db.commit()

            if webhook_url:
                await self.send_webhook(
                    webhook_url,
                    {"job_id": str(job_id), "status": "failed", "error": str(e)},
                )

        finally:
            db.close()

    async def send_webhook(self, webhook_url: str, data: dict):
        """Send webhook notification"""
        try:
            async with httpx.AsyncClient(timeout=settings.WEBHOOK_TIMEOUT) as client:
                for attempt in range(settings.WEBHOOK_MAX_RETRIES):
                    try:
                        response = await client.post(webhook_url, json=data)
                        if response.status_code == 200:
                            break
                    except Exception as e:
                        if attempt == settings.WEBHOOK_MAX_RETRIES - 1:
                            logger.error("Webhook failed after %d attempts: %s", settings.WEBHOOK_MAX_RETRIES, str(e))
                        else:
                            await asyncio.sleep(2**attempt)  # Exponential backoff
        except Exception as e:
            logging.error(f"Webhook error: {e}")
