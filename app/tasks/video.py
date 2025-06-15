import logging
import subprocess
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from celery import Task
from google.cloud.speech import SpeechClient
from google.cloud import translate_v2 as translate
import ffmpeg

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.exceptions import ProcessingException, ErrorCode
from app.models.job import JobStatus
from app.schemas.video import VideoTranslationRequest
from app.services.storage import get_storage_client

logger = logging.getLogger(__name__)

# Initialize Google Cloud clients
speech_client = SpeechClient()
translate_client = translate.Client()
storage_client = get_storage_client()


class VideoProcessingTask(Task):
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


def extract_audio(video_path: str) -> str:
    """Extract audio from video file."""
    audio_path = video_path.rsplit(".", 1)[0] + ".wav"
    try:
        stream = ffmpeg.input(video_path)
        stream = ffmpeg.output(stream, audio_path, acodec="pcm_s16le", ac=1, ar="16k")
        ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
        return audio_path
    except ffmpeg.Error as e:
        raise ProcessingException(
            error_code=ErrorCode.VIDEO_PROCESSING_FAILED,
            message=f"Failed to extract audio: {e.stderr.decode()}"
        )


def transcribe_audio(audio_path: str, language_code: str) -> List[Dict]:
    """Transcribe audio using Google Speech-to-Text."""
    try:
        with open(audio_path, "rb") as audio_file:
            content = audio_file.read()

        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=language_code,
            enable_automatic_punctuation=True,
        )

        response = speech_client.recognize(config=config, audio=audio)
        
        segments = []
        for result in response.results:
            for alternative in result.alternatives:
                segments.append({
                    "text": alternative.transcript,
                    "confidence": alternative.confidence,
                    "start_time": alternative.words[0].start_time.total_seconds() if alternative.words else 0,
                    "end_time": alternative.words[-1].end_time.total_seconds() if alternative.words else 0
                })
        
        return segments
    except Exception as e:
        raise ProcessingException(
            error_code=ErrorCode.VIDEO_PROCESSING_FAILED,
            message=f"Speech recognition failed: {str(e)}"
        )


def translate_segments(segments: List[Dict], target_language: str, source_language: Optional[str] = None) -> List[Dict]:
    """Translate text segments."""
    try:
        translations = []
        for segment in segments:
            result = translate_client.translate(
                segment["text"],
                target_language=target_language,
                source_language=source_language
            )
            translations.append({
                **segment,
                "translated_text": result["translatedText"]
            })
        return translations
    except Exception as e:
        raise ProcessingException(
            error_code=ErrorCode.TRANSLATION_FAILED,
            message=f"Translation failed: {str(e)}"
        )


def create_subtitles(translations: List[Dict], format: str = "srt") -> str:
    """Create subtitle file from translations."""
    if format == "srt":
        return create_srt(translations)
    elif format == "vtt":
        return create_vtt(translations)
    else:
        raise ProcessingException(
            error_code=ErrorCode.VIDEO_PROCESSING_FAILED,
            message=f"Unsupported subtitle format: {format}"
        )


def create_srt(translations: List[Dict]) -> str:
    """Create SRT format subtitles."""
    srt_content = []
    for i, segment in enumerate(translations, 1):
        start = format_timestamp(segment["start_time"])
        end = format_timestamp(segment["end_time"])
        srt_content.extend([
            str(i),
            f"{start} --> {end}",
            segment["translated_text"],
            ""
        ])
    return "\n".join(srt_content)


def create_vtt(translations: List[Dict]) -> str:
    """Create WebVTT format subtitles."""
    vtt_content = ["WEBVTT", ""]
    for segment in translations:
        start = format_timestamp(segment["start_time"], vtt=True)
        end = format_timestamp(segment["end_time"], vtt=True)
        vtt_content.extend([
            f"{start} --> {end}",
            segment["translated_text"],
            ""
        ])
    return "\n".join(vtt_content)


def format_timestamp(seconds: float, vtt: bool = False) -> str:
    """Format timestamp for subtitles."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    if vtt:
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{int((seconds % 1) * 1000):03d}"


def burn_subtitles(video_path: str, subtitles_path: str, output_path: str) -> None:
    """Burn subtitles into video."""
    try:
        stream = ffmpeg.input(video_path)
        stream = ffmpeg.filter(stream, "subtitles", subtitles_path)
        stream = ffmpeg.output(stream, output_path)
        ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as e:
        raise ProcessingException(
            error_code=ErrorCode.VIDEO_PROCESSING_FAILED,
            message=f"Failed to burn subtitles: {e.stderr.decode()}"
        )


@celery_app.task(base=VideoProcessingTask, bind=True)
def process_video_translation(
    self,
    job_id: UUID,
    request: Dict,  # VideoTranslationRequest as dict
    video_data: bytes,
    target_language: str,
    source_language: Optional[str] = None,
) -> Dict:
    """
    Process video translation task.
    
    Args:
        job_id: Unique job identifier
        request: VideoTranslationRequest as dictionary
        video_data: Raw video data
        target_language: Target language code
        source_language: Optional source language code
    
    Returns:
        Dict containing processing results
    """
    try:
        # Convert request dict back to Pydantic model
        translation_request = VideoTranslationRequest(**request)
        
        # Update job status
        from app.crud.job import update_job_status
        update_job_status(job_id, JobStatus.PROCESSING)
        
        # Save video to temporary file
        temp_video_path = f"/tmp/{job_id}_input.mp4"
        with open(temp_video_path, "wb") as f:
            f.write(video_data)
        
        # Extract audio
        audio_path = extract_audio(temp_video_path)
        
        # Transcribe audio
        segments = transcribe_audio(audio_path, source_language or "auto")
        
        if not segments:
            raise ProcessingException(
                error_code=ErrorCode.VIDEO_PROCESSING_FAILED,
                message="No speech detected in video"
            )
        
        # Translate segments
        translations = translate_segments(segments, target_language, source_language)
        
        # Create subtitles
        subtitle_format = translation_request.subtitle_format
        subtitles = create_subtitles(translations, subtitle_format)
        
        # Save subtitles
        subtitle_path = f"/tmp/{job_id}_subtitles.{subtitle_format}"
        with open(subtitle_path, "w") as f:
            f.write(subtitles)
        
        # Upload subtitles to cloud storage
        bucket = storage_client.bucket(settings.GCS_BUCKET_NAME)
        subtitle_blob = bucket.blob(f"translations/{job_id}/subtitles.{subtitle_format}")
        subtitle_blob.upload_from_filename(subtitle_path)
        
        # Handle video output
        if translation_request.burn_subtitles:
            output_path = f"/tmp/{job_id}_output.{translation_request.output_format}"
            burn_subtitles(temp_video_path, subtitle_path, output_path)
            
            # Upload processed video
            video_blob = bucket.blob(f"translations/{job_id}/output.{translation_request.output_format}")
            video_blob.upload_from_filename(output_path)
            output_url = video_blob.public_url
        else:
            output_url = None
        
        # Clean up temporary files
        import os
        os.remove(temp_video_path)
        os.remove(audio_path)
        os.remove(subtitle_path)
        if translation_request.burn_subtitles:
            os.remove(output_path)
        
        # Return results
        return {
            "job_id": str(job_id),
            "status": "completed",
            "subtitles_url": subtitle_blob.public_url,
            "output_url": output_url,
            "segments": translations
        }
        
    except Exception as e:
        logger.exception("Video processing failed")
        raise ProcessingException(
            error_code=ErrorCode.PROCESSING_FAILED,
            message=str(e)
        ) 