from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_current_user_required
from app.services.payment import PaymentService
from app.services.credit_management import CreditService
from app.schemas.payment import *
from app.models.user import User
from app.models.transaction import CreditTransaction, TransactionStatus, TransactionType
import hmac
import hashlib

router = APIRouter(prefix="/payments", tags=["Payments"])

# Credit packages configuration
CREDIT_PACKAGES = {
    "small": CreditPackage(credits=10, price_naira=1000, price_usd=2.5),
    "medium": CreditPackage(credits=50, price_naira=4500, price_usd=11.25, savings_percent=10),
    "large": CreditPackage(credits=100, price_naira=8500, price_usd=21.25, savings_percent=15),
    "xl": CreditPackage(credits=500, price_naira=35000, price_usd=87.5, savings_percent=30)
}

@router.get("/packages")
async def get_credit_packages():
    """Get available credit packages"""
    return {"packages": CREDIT_PACKAGES}

@router.post("/initialize", response_model=PaymentInitResponse)
async def initialize_payment(
    payment_request: PaymentInitRequest,
    user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Initialize payment for credit purchase"""
    
    if payment_request.package not in CREDIT_PACKAGES:
        raise HTTPException(status_code=400, detail="Invalid package")
    
    package = CREDIT_PACKAGES[payment_request.package]
    payment_service = PaymentService()
    
    # Initialize payment with Flutterwave
    payment_data = await payment_service.initialize_payment(
        str(user.id),
        user.email,
        package.price_naira,
        package.credits,
        payment_request.callback_url
    )
    
    # Create pending transaction record
    transaction = CreditTransaction(
        user_id=user.id,
        transaction_type=TransactionType.PURCHASE,
        status=TransactionStatus.PENDING,
        credits_amount=package.credits,
        cost_naira=package.price_naira,
        cost_usd=package.price_usd,
        flutterwave_tx_ref=payment_data["tx_ref"],
        description=f"Purchase {package.credits} credits - {payment_request.package} package"
    )
    
    db.add(transaction)
    db.commit()

    return PaymentInitResponse(
        payment_link=payment_data["payment_link"],
        tx_ref=payment_data["tx_ref"],
        amount=package.price_naira,
        credits=package.credits
    )

