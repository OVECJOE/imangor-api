from sqlalchemy.orm import Session
from app.models.user import DeviceFingerprint
from app.core.security import create_device_fingerprint
from app.core.config import settings
from datetime import datetime, timedelta, timezone
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class DeviceTrackingService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_fingerprint(self, fingerprint_data: Dict) -> DeviceFingerprint:
        """Get or create device fingerprint for anonymous tracking"""
        
        # Create fingerprint hash
        fingerprint_hash = create_device_fingerprint(fingerprint_data)
        
        # Check if fingerprint exists
        fingerprint = self.db.query(DeviceFingerprint).filter(
            DeviceFingerprint.fingerprint_hash == fingerprint_hash
        ).first()
        
        if fingerprint:
            # Update last seen
            fingerprint.last_seen = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(fingerprint)
            return fingerprint
        
        # Create new fingerprint
        fingerprint = DeviceFingerprint(
            fingerprint_hash=fingerprint_hash,
            user_agent=fingerprint_data.get('user_agent', ''),
            screen_resolution=fingerprint_data.get('screen_resolution', ''),
            timezone=fingerprint_data.get('timezone', ''),
            language=fingerprint_data.get('language', ''),
            platform=fingerprint_data.get('platform', ''),
            images_processed=0
        )
        
        self.db.add(fingerprint)
        self.db.commit()
        self.db.refresh(fingerprint)
        
        logger.info(f"New device fingerprint created: {fingerprint_hash[:16]}...")
        return fingerprint

    def check_anonymous_limit(self, fingerprint: DeviceFingerprint) -> bool:
        """Check if anonymous user has exceeded their limit"""
        return fingerprint.images_processed >= settings.ANONYMOUS_IMAGE_LIMIT

    def increment_usage(self, fingerprint: DeviceFingerprint):
        """Increment usage count for device fingerprint"""
        fingerprint.images_processed += 1
        fingerprint.last_seen = datetime.now(timezone.utc)
        self.db.commit()
        
        logger.info(f"Incremented usage for fingerprint {fingerprint.fingerprint_hash[:16]}... to {fingerprint.images_processed}")

    def get_usage_stats(self, fingerprint: DeviceFingerprint) -> Dict:
        """Get usage statistics for a device fingerprint"""
        return {
            "images_processed": fingerprint.images_processed,
            "remaining_free_images": max(0, settings.ANONYMOUS_IMAGE_LIMIT - fingerprint.images_processed),
            "first_seen": fingerprint.first_seen,
            "last_seen": fingerprint.last_seen
        }

    def cleanup_old_fingerprints(self, days_old: int = 90):
        """Clean up old device fingerprints (should be run as periodic task)"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        old_fingerprints = self.db.query(DeviceFingerprint).filter(
            DeviceFingerprint.last_seen < cutoff_date
        ).all()
        
        for fingerprint in old_fingerprints:
            self.db.delete(fingerprint)
        
        if old_fingerprints:
            self.db.commit()
            logger.info(f"Cleaned up {len(old_fingerprints)} old device fingerprints")
        
        return len(old_fingerprints)
