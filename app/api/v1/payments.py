from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_current_user_required
from app.services.payment import PaymentService
from app.services.credit_management import CreditService
from app.schemas.payment import *
from app.models.user import User
from app.models.transaction import CreditTransaction, TransactionStatus, TransactionType
from app.core.config import settings
import hmac
import hashlib
import json
import logging

logger = logging.getLogger(__name__)
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

@router.post("/webhook")
async def payment_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Flutterwave payment webhooks"""
    
    # Verify webhook signature
    signature = request.headers.get("verif-hash")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing webhook signature")
    
    # Get raw body
    body = await request.body()
    
    # Verify signature
    expected_signature = hmac.new(
        settings.FLUTTERWAVE_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    try:
        payload = json.loads(body)
        event = payload.get("event")
        data = payload.get("data", {})
        
        if event == "charge.completed":
            await handle_successful_payment(data, db)
        elif event == "charge.failed":
            await handle_failed_payment(data, db)
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

async def handle_successful_payment(data: dict, db: Session):
    """Handle successful payment webhook"""
    
    tx_ref = data.get("tx_ref")
    if not tx_ref:
        logger.error("Missing tx_ref in webhook data")
        return
    
    # Find transaction
    transaction = db.query(CreditTransaction).filter(
        CreditTransaction.flutterwave_tx_ref == tx_ref
    ).first()
    
    if not transaction:
        logger.error(f"Transaction not found for tx_ref: {tx_ref}")
        return
    
    if transaction.status == TransactionStatus.COMPLETED:
        logger.info(f"Transaction {tx_ref} already processed")
        return
    
    # Update transaction status
    transaction.status = TransactionStatus.COMPLETED
    transaction.payment_reference = data.get("flw_ref")
    
    # Add credits to user
    credit_service = CreditService(db)
    credit_service.add_credits(
        str(transaction.user_id),
        transaction.credits_amount,
        f"Credit purchase: {tx_ref}"
    )
    
    db.commit()
    logger.info(f"Successfully processed payment for tx_ref: {tx_ref}")

async def handle_failed_payment(data: dict, db: Session):
    """Handle failed payment webhook"""
    
    tx_ref = data.get("tx_ref")
    if not tx_ref:
        return
    
    # Find and update transaction
    transaction = db.query(CreditTransaction).filter(
        CreditTransaction.flutterwave_tx_ref == tx_ref
    ).first()
    
    if transaction and transaction.status == TransactionStatus.PENDING:
        transaction.status = TransactionStatus.FAILED
        db.commit()
        logger.info(f"Marked transaction as failed for tx_ref: {tx_ref}")

@router.get("/transactions")
async def get_user_transactions(
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get user's transaction history"""
    
    transactions = db.query(CreditTransaction).filter(
        CreditTransaction.user_id == user.id
    ).order_by(CreditTransaction.created_at.desc()).offset(skip).limit(limit).all()
    
    return {"transactions": transactions}

@router.get("/balance")
async def get_credit_balance(
    user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get user's current credit balance"""
    
    credit_service = CreditService(db)
    balance = credit_service.get_user_credits(str(user.id))
    
    return {
        "credits_balance": balance,
        "total_purchased": user.total_credits_purchased,
        "total_used": user.total_credits_used
    }
