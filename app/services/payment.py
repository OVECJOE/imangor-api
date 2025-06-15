import logging
import uuid
from typing import Dict

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self):
        self.base_url = "https://api.flutterwave.com/v3"
        self.headers = {
            "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
            "Content-Type": "application/json",
        }

    async def initialize_payment(
        self, user_id: str, email: str, amount: float, credits: int, callback_url: str
    ) -> Dict:
        """Initialize payment with Flutterwave"""

        tx_ref = f"credit_purchase_{user_id}_{uuid.uuid4().hex[:8]}"

        payload = {
            "tx_ref": tx_ref,
            "amount": amount,
            "currency": "NGN",
            "redirect_url": callback_url,
            "customer": {"email": email, "name": f"User {user_id}"},
            "customizations": {
                "title": "Credit Purchase",
                "description": f"Purchase {credits} credits",
                "logo": "https://your-domain.com/logo.png",
            },
            "meta": {"user_id": user_id, "credits": credits},
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/payments",
                    json=payload,
                    headers=self.headers,
                    timeout=30.0,
                )

                response.raise_for_status()
                data = response.json()

                if data.get("status") == "success":
                    return {"payment_link": data["data"]["link"], "tx_ref": tx_ref}
                else:
                    raise Exception(f"Payment initialization failed: {data.get('message', 'Unknown error')}")

        except httpx.HTTPError as e:
            logger.error("HTTP error during payment initialization: %s", str(e))
            raise RuntimeError("Payment service unavailable") from e
        except Exception as e:
            logger.error("Payment initialization error: %s", str(e))
            raise RuntimeError("Payment initialization failed") from e

    async def verify_payment(self, tx_ref: str) -> Dict:
        """Verify payment status with Flutterwave"""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/transactions/verify_by_reference?tx_ref={tx_ref}",
                    headers=self.headers,
                    timeout=30.0,
                )

                response.raise_for_status()
                data = response.json()

                if data.get("status") == "success":
                    return data["data"]
                else:
                    raise Exception(f"Payment verification failed: {data.get('message', 'Unknown error')}")

        except httpx.HTTPError as e:
            logger.error("HTTP error during payment verification: %s", str(e))
            raise RuntimeError("Payment verification service unavailable") from e
        except Exception as e:
            logger.error("Payment verification error: %s", str(e))
            raise RuntimeError("Payment verification failed") from e

    async def refund_payment(self, flw_ref: str, amount: float) -> Dict:
        """Refund a payment via Flutterwave"""

        payload = {"amount": amount}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/transactions/{flw_ref}/refund",
                    json=payload,
                    headers=self.headers,
                    timeout=30.0,
                )

                response.raise_for_status()
                data = response.json()

                if data.get("status") == "success":
                    return data["data"]
                else:
                    raise Exception(f"Refund failed: {data.get('message', 'Unknown error')}")

        except httpx.HTTPError as e:
            logger.error("HTTP error during refund: %s", str(e))
            raise RuntimeError("Refund service unavailable") from e
        except Exception as e:
            logger.error("Refund error: %s", str(e))
            raise RuntimeError("Refund failed") from e
