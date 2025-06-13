import httpx
import uuid
from app.core.config import settings
from typing import Dict, Any

class PaymentService:
    def __init__(self):
        self.base_url = "https://api.flutterwave.com/v3"
        self.secret_key = settings.FLUTTERWAVE_SECRET_KEY
        self.public_key = settings.FLUTTERWAVE_PUBLIC_KEY
    
    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    
    async def initialize_payment(self, user_id: str, email: str, amount_naira: float, 
                               credits: int, callback_url: str) -> Dict[str, Any]:
        """Initialize Flutterwave payment"""
        tx_ref = f"IMG_CREDITS_{user_id}_{uuid.uuid4()}"
        
        payload = {
            "tx_ref": tx_ref,
            "amount": amount_naira,
            "currency": "NGN",
            "redirect_url": callback_url,
            "payment_options": "card,mobilemoney,ussd",
            "customer": {
                "email": email,
                "name": email.split('@')[0]
            },
            "customizations": {
                "title": "Image Translation Credits",
                "description": f"Purchase {credits} image translation credits",
                "logo": "https://yourdomain.com/logo.png"
            },
            "meta": {
                "user_id": user_id,
                "credits": credits,
                "source": "api"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/payments",
                headers=self.get_headers(),
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Payment initialization failed: {response.text}")
            
            result = response.json()
            if result["status"] != "success":
                raise Exception(f"Payment initialization failed: {result.get('message', 'Unknown error')}")
            
            return {
                "payment_link": result["data"]["link"],
                "tx_ref": tx_ref,
                "amount": amount_naira,
                "credits": credits
            }
    
    async def verify_payment(self, tx_ref: str) -> Dict[str, Any]:
        """Verify Flutterwave payment"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/transactions/verify_by_reference?tx_ref={tx_ref}",
                headers=self.get_headers()
            )
            
            if response.status_code != 200:
                raise Exception(f"Payment verification failed: {response.text}")
            
            result = response.json()
            if result["status"] != "success":
                raise Exception(f"Payment verification failed: {result.get('message', 'Unknown error')}")
            
            return result["data"]
