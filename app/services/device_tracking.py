from sqlalchemy.orm import Session
from app.models.user import DeviceFingerprint
from app.core.security import create_device_fingerprint
from app.core.config import settings

class DeviceTrackingService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_fingerprint(self, fingerprint_data: dict) -> DeviceFingerprint:
        """Get existing fingerprint or create new one"""
        fingerprint_hash = create_device_fingerprint(fingerprint_data)
        
        fingerprint = self.db.query(DeviceFingerprint).filter(
            DeviceFingerprint.fingerprint_hash == fingerprint_hash
        ).first()
        
        if not fingerprint:
            fingerprint = DeviceFingerprint(
                fingerprint_hash=fingerprint_hash,
                user_agent=fingerprint_data.get('user_agent'),
                screen_resolution=fingerprint_data.get('screen_resolution'),
                timezone=fingerprint_data.get('timezone'),
                language=fingerprint_data.get('language'),
                platform=fingerprint_data.get('platform'),
            )
            self.db.add(fingerprint)
            self.db.commit()
            self.db.refresh(fingerprint)
        
        return fingerprint
    
    def check_anonymous_limit(self, fingerprint: DeviceFingerprint) -> bool:
        """Check if anonymous user has exceeded image limit"""
        return fingerprint.images_processed >= settings.ANONYMOUS_IMAGE_LIMIT
    
    def increment_usage(self, fingerprint: DeviceFingerprint):
        """Increment usage count for fingerprint"""
        fingerprint.images_processed += 1
        self.db.commit()
