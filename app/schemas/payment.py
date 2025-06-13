from typing import Optional
from pydantic import BaseModel

class CreditPackage(BaseModel):
    credits: int
    price_naira: float
    price_usd: float
    savings_percent: Optional[float] = None

class PaymentInitRequest(BaseModel):
    package: str  # "small", "medium", "large", "xl"
    callback_url: str

class PaymentInitResponse(BaseModel):
    payment_link: str
    tx_ref: str
    amount: float
    credits: int

class WebhookPayload(BaseModel):
    event: str
    data: dict
