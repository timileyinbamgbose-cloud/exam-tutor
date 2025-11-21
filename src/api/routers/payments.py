"""
Payment Router
Handles payment processing with Paystack
"""
from fastapi import APIRouter, HTTPException, status, Depends, Request
from src.api.models import PaymentInitRequest, PaymentInitResponse, PaymentVerifyResponse
from src.api.auth import get_current_user
from src.payments.paystack_integration import PaystackClient, PaystackConfig, PaystackEnvironment
import os
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])

# Initialize Paystack client
paystack_config = PaystackConfig(
    secret_key=os.getenv("PAYSTACK_SECRET_KEY", "sk_test_xxxxx"),
    public_key=os.getenv("PAYSTACK_PUBLIC_KEY", "pk_test_xxxxx"),
    environment=PaystackEnvironment.TEST
)
paystack_client = PaystackClient(paystack_config)


@router.post("/initialize", response_model=PaymentInitResponse)
async def initialize_payment(
    request: PaymentInitRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Initialize a payment transaction
    Returns Paystack authorization URL for payment
    """
    try:
        # Convert amount to kobo (Paystack uses kobo)
        amount_kobo = int(request.amount * 100)

        # Generate unique reference
        reference = f"examstutor_{uuid.uuid4().hex[:12]}"

        # Initialize transaction with Paystack
        result = paystack_client.initialize_transaction(
            email=request.email,
            amount=amount_kobo,
            reference=reference,
            callback_url=request.callback_url or f"{os.getenv('APP_URL', 'http://localhost:8000')}/api/v1/payments/callback",
            metadata={
                "user_id": current_user["id"],
                "subscription_id": request.subscription_id,
                "full_name": current_user["full_name"]
            }
        )

        if result.get("status"):
            data = result.get("data", {})
            return PaymentInitResponse(
                authorization_url=data.get("authorization_url"),
                access_code=data.get("access_code"),
                reference=reference
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Payment initialization failed")
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment initialization error: {str(e)}"
        )


@router.get("/verify/{reference}", response_model=PaymentVerifyResponse)
async def verify_payment(
    reference: str,
    current_user: dict = Depends(get_current_user)
):
    """Verify a payment transaction"""
    try:
        result = paystack_client.verify_transaction(reference)

        if result.get("status"):
            data = result.get("data", {})
            paid_at = data.get("paid_at")

            return PaymentVerifyResponse(
                status=data.get("status"),
                amount=data.get("amount", 0) / 100,  # Convert from kobo
                paid_at=datetime.fromisoformat(paid_at.replace("Z", "+00:00")) if paid_at else None,
                reference=reference,
                subscription_id=data.get("metadata", {}).get("subscription_id", "")
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found"
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment verification error: {str(e)}"
        )


@router.post("/webhook")
async def payment_webhook(request: Request):
    """
    Paystack webhook endpoint
    Receives payment notifications from Paystack
    """
    try:
        # Get raw body
        body = await request.body()
        signature = request.headers.get("x-paystack-signature")

        # Verify webhook signature
        is_valid = paystack_client.verify_webhook_signature(body, signature)

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )

        # Parse event
        import json
        event = json.loads(body)

        event_type = event.get("event")
        data = event.get("data", {})

        # Handle different event types
        if event_type == "charge.success":
            # Payment successful - activate subscription
            reference = data.get("reference")
            metadata = data.get("metadata", {})
            subscription_id = metadata.get("subscription_id")

            # TODO: Update subscription status in database
            print(f"Payment successful: {reference}, Subscription: {subscription_id}")

        elif event_type == "subscription.create":
            # Subscription created
            print(f"Subscription created: {data.get('subscription_code')}")

        elif event_type == "subscription.disable":
            # Subscription cancelled
            print(f"Subscription cancelled: {data.get('subscription_code')}")

        return {"status": "success", "message": "Webhook processed"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing error: {str(e)}"
        )


@router.get("/history")
async def get_payment_history(
    current_user: dict = Depends(get_current_user)
):
    """Get payment history for current user"""
    # Mock payment history
    return {
        "payments": [
            {
                "id": "pay_001",
                "amount": 5000.00,
                "status": "success",
                "reference": "examstutor_abc123",
                "paid_at": "2024-11-01T10:30:00Z",
                "subscription_id": "sub_001"
            },
            {
                "id": "pay_002",
                "amount": 5000.00,
                "status": "success",
                "reference": "examstutor_def456",
                "paid_at": "2024-10-01T10:30:00Z",
                "subscription_id": "sub_001"
            }
        ],
        "total": 2
    }


@router.get("/methods")
async def get_payment_methods():
    """Get available payment methods"""
    return {
        "methods": [
            {"id": "card", "name": "Debit/Credit Card", "enabled": True},
            {"id": "bank", "name": "Bank Transfer", "enabled": True},
            {"id": "ussd", "name": "USSD", "enabled": True},
            {"id": "mobile_money", "name": "Mobile Money", "enabled": True}
        ]
    }
