import logging
from typing import Optional, BinaryIO
from google.cloud import storage
from google.cloud.storage.blob import Blob
from google.cloud.storage.client import Client

from app.core.config import settings

logger = logging.getLogger(__name__)

_storage_client: Optional[Client] = None


def get_storage_client() -> Client:
    """
    Get or create a Google Cloud Storage client.
    
    Returns:
        Client: Google Cloud Storage client instance
    """
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client.from_service_account_json(
            settings.GOOGLE_APPLICATION_CREDENTIALS
        )
    return _storage_client


def upload_file(
    file: BinaryIO,
    destination_blob_name: str,
    content_type: Optional[str] = None,
    bucket_name: Optional[str] = None
) -> str:
    """
    Upload a file to Google Cloud Storage.
    
    Args:
        file: File-like object to upload
        destination_blob_name: Name of the blob in the bucket
        content_type: Content type of the file (optional)
        bucket_name: Name of the bucket (defaults to settings.GOOGLE_CLOUD_STORAGE_BUCKET)
        
    Returns:
        str: Public URL of the uploaded file
    """
    try:
        bucket_name = bucket_name or settings.GOOGLE_CLOUD_STORAGE_BUCKET
        client = get_storage_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        
        # Set content type if provided
        if content_type:
            blob.content_type = content_type
        
        # Upload the file
        blob.upload_from_file(file)
        
        # Make the blob publicly accessible
        blob.make_public()
        
        logger.info(f"File uploaded to {blob.public_url}")
        return blob.public_url
        
    except Exception as e:
        logger.exception(f"Failed to upload file to {destination_blob_name}")
        raise


def delete_file(
    blob_name: str,
    bucket_name: Optional[str] = None
) -> None:
    """
    Delete a file from Google Cloud Storage.
    
    Args:
        blob_name: Name of the blob to delete
        bucket_name: Name of the bucket (defaults to settings.GOOGLE_CLOUD_STORAGE_BUCKET)
    """
    try:
        bucket_name = bucket_name or settings.GOOGLE_CLOUD_STORAGE_BUCKET
        client = get_storage_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        blob.delete()
        logger.info(f"File {blob_name} deleted from bucket {bucket_name}")
        
    except Exception as e:
        logger.exception(f"Failed to delete file {blob_name}")
        raise


def get_file_url(
    blob_name: str,
    bucket_name: Optional[str] = None
) -> str:
    """
    Get the public URL of a file in Google Cloud Storage.
    
    Args:
        blob_name: Name of the blob
        bucket_name: Name of the bucket (defaults to settings.GOOGLE_CLOUD_STORAGE_BUCKET)
        
    Returns:
        str: Public URL of the file
    """
    try:
        bucket_name = bucket_name or settings.GOOGLE_CLOUD_STORAGE_BUCKET
        client = get_storage_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # Ensure the blob is publicly accessible
        blob.make_public()
        
        return blob.public_url
        
    except Exception as e:
        logger.exception(f"Failed to get URL for file {blob_name}")
        raise 