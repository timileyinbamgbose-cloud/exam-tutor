"""
Paystack Payment Integration
ExamsTutor AI - Phase 5: Scale & Growth

Integration with Paystack for subscription payments, invoicing, and billing.
"""

import os
import hmac
import hashlib
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum


class PaystackEnvironment(str, Enum):
    """Paystack environment"""
    TEST = "test"
    LIVE = "live"


@dataclass
class PaystackConfig:
    """Paystack configuration"""
    secret_key: str
    public_key: str
    environment: PaystackEnvironment = PaystackEnvironment.TEST

    @property
    def base_url(self) -> str:
        return "https://api.paystack.co"

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }


class PaystackClient:
    """Paystack API client for payment processing"""

    def __init__(self, config: PaystackConfig):
        self.config = config
        self.base_url = config.base_url
        self.headers = config.headers

    # Transaction endpoints

    def initialize_transaction(
        self,
        email: str,
        amount: int,  # Amount in kobo (₦100 = 10000 kobo)
        reference: Optional[str] = None,
        callback_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        channels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Initialize a transaction

        Args:
            email: Customer email
            amount: Amount in kobo (₦1 = 100 kobo)
            reference: Unique transaction reference
            callback_url: URL to redirect after payment
            metadata: Additional data (school_id, subscription_id, etc.)
            channels: Payment channels (card, bank, ussd, qr, mobile_money)

        Returns:
            {
                "status": True,
                "message": "Authorization URL created",
                "data": {
                    "authorization_url": "https://checkout.paystack.com/...",
                    "access_code": "...",
                    "reference": "..."
                }
            }
        """
        payload = {
            "email": email,
            "amount": amount,
        }

        if reference:
            payload["reference"] = reference
        else:
            payload["reference"] = self._generate_reference()

        if callback_url:
            payload["callback_url"] = callback_url

        if metadata:
            payload["metadata"] = metadata

        if channels:
            payload["channels"] = channels

        response = requests.post(
            f"{self.base_url}/transaction/initialize",
            json=payload,
            headers=self.headers,
        )

        return response.json()

    def verify_transaction(self, reference: str) -> Dict[str, Any]:
        """
        Verify a transaction

        Returns:
            {
                "status": True,
                "message": "Verification successful",
                "data": {
                    "status": "success",
                    "reference": "...",
                    "amount": 10000,
                    "customer": {...},
                    "metadata": {...}
                }
            }
        """
        response = requests.get(
            f"{self.base_url}/transaction/verify/{reference}",
            headers=self.headers,
        )

        return response.json()

    def charge_authorization(
        self,
        email: str,
        amount: int,
        authorization_code: str,
        reference: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Charge a customer using saved authorization code (for recurring payments)

        Args:
            email: Customer email
            amount: Amount in kobo
            authorization_code: Saved authorization code from previous transaction
            reference: Unique reference
            metadata: Additional data

        Returns:
            Transaction result
        """
        payload = {
            "email": email,
            "amount": amount,
            "authorization_code": authorization_code,
        }

        if reference:
            payload["reference"] = reference
        else:
            payload["reference"] = self._generate_reference()

        if metadata:
            payload["metadata"] = metadata

        response = requests.post(
            f"{self.base_url}/transaction/charge_authorization",
            json=payload,
            headers=self.headers,
        )

        return response.json()

    def list_transactions(
        self,
        per_page: int = 50,
        page: int = 1,
        customer: Optional[str] = None,
        status: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """List transactions with filters"""
        params = {
            "perPage": per_page,
            "page": page,
        }

        if customer:
            params["customer"] = customer

        if status:
            params["status"] = status

        if from_date:
            params["from"] = from_date.isoformat()

        if to_date:
            params["to"] = to_date.isoformat()

        response = requests.get(
            f"{self.base_url}/transaction",
            headers=self.headers,
            params=params,
        )

        return response.json()

    # Customer endpoints

    def create_customer(
        self,
        email: str,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a customer"""
        payload = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
        }

        if phone:
            payload["phone"] = phone

        if metadata:
            payload["metadata"] = metadata

        response = requests.post(
            f"{self.base_url}/customer",
            json=payload,
            headers=self.headers,
        )

        return response.json()

    def get_customer(self, email_or_code: str) -> Dict[str, Any]:
        """Get customer details"""
        response = requests.get(
            f"{self.base_url}/customer/{email_or_code}",
            headers=self.headers,
        )

        return response.json()

    # Subscription endpoints

    def create_subscription(
        self,
        customer: str,  # Customer code or email
        plan: str,  # Plan code
        authorization: str,  # Authorization code
        start_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Create a subscription

        Args:
            customer: Customer email or code
            plan: Plan code
            authorization: Authorization code from previous transaction
            start_date: When subscription should start
        """
        payload = {
            "customer": customer,
            "plan": plan,
            "authorization": authorization,
        }

        if start_date:
            payload["start_date"] = start_date.isoformat()

        response = requests.post(
            f"{self.base_url}/subscription",
            json=payload,
            headers=self.headers,
        )

        return response.json()

    def enable_subscription(self, code: str, token: str) -> Dict[str, Any]:
        """Enable a subscription"""
        payload = {
            "code": code,
            "token": token,
        }

        response = requests.post(
            f"{self.base_url}/subscription/enable",
            json=payload,
            headers=self.headers,
        )

        return response.json()

    def disable_subscription(self, code: str, token: str) -> Dict[str, Any]:
        """Disable a subscription"""
        payload = {
            "code": code,
            "token": token,
        }

        response = requests.post(
            f"{self.base_url}/subscription/disable",
            json=payload,
            headers=self.headers,
        )

        return response.json()

    # Plan endpoints

    def create_plan(
        self,
        name: str,
        amount: int,  # Amount in kobo
        interval: str,  # "daily", "weekly", "monthly", "annually"
        description: Optional[str] = None,
        currency: str = "NGN",
    ) -> Dict[str, Any]:
        """
        Create a subscription plan

        Args:
            name: Plan name (e.g., "Premium Monthly")
            amount: Amount in kobo (₦500 = 50000 kobo)
            interval: Billing interval
            description: Plan description
            currency: Currency code (default NGN)
        """
        payload = {
            "name": name,
            "amount": amount,
            "interval": interval,
            "currency": currency,
        }

        if description:
            payload["description"] = description

        response = requests.post(
            f"{self.base_url}/plan",
            json=payload,
            headers=self.headers,
        )

        return response.json()

    def list_plans(
        self,
        per_page: int = 50,
        page: int = 1,
    ) -> Dict[str, Any]:
        """List all subscription plans"""
        params = {
            "perPage": per_page,
            "page": page,
        }

        response = requests.get(
            f"{self.base_url}/plan",
            headers=self.headers,
            params=params,
        )

        return response.json()

    # Refund endpoints

    def refund_transaction(
        self,
        transaction: str,  # Transaction reference or ID
        amount: Optional[int] = None,  # Partial refund amount in kobo
        currency: str = "NGN",
        customer_note: Optional[str] = None,
        merchant_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Refund a transaction

        Args:
            transaction: Transaction reference or ID
            amount: Amount to refund (kobo). If None, full refund.
            currency: Currency code
            customer_note: Note visible to customer
            merchant_note: Internal note
        """
        payload = {
            "transaction": transaction,
            "currency": currency,
        }

        if amount:
            payload["amount"] = amount

        if customer_note:
            payload["customer_note"] = customer_note

        if merchant_note:
            payload["merchant_note"] = merchant_note

        response = requests.post(
            f"{self.base_url}/refund",
            json=payload,
            headers=self.headers,
        )

        return response.json()

    # Transfer recipients & transfers (for payouts)

    def create_transfer_recipient(
        self,
        type: str,  # "nuban" or "mobile_money" or "basa"
        name: str,
        account_number: str,
        bank_code: str,
        currency: str = "NGN",
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a transfer recipient for payouts"""
        payload = {
            "type": type,
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": currency,
        }

        if description:
            payload["description"] = description

        response = requests.post(
            f"{self.base_url}/transferrecipient",
            json=payload,
            headers=self.headers,
        )

        return response.json()

    def initiate_transfer(
        self,
        source: str,  # "balance"
        amount: int,  # Amount in kobo
        recipient: str,  # Recipient code
        reason: Optional[str] = None,
        reference: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Initiate a transfer (payout)"""
        payload = {
            "source": source,
            "amount": amount,
            "recipient": recipient,
        }

        if reason:
            payload["reason"] = reason

        if reference:
            payload["reference"] = reference
        else:
            payload["reference"] = self._generate_reference()

        response = requests.post(
            f"{self.base_url}/transfer",
            json=payload,
            headers=self.headers,
        )

        return response.json()

    # Webhook verification

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """
        Verify Paystack webhook signature

        Args:
            payload: Raw request body (bytes)
            signature: X-Paystack-Signature header value

        Returns:
            True if signature is valid
        """
        hash = hmac.new(
            self.config.secret_key.encode('utf-8'),
            payload,
            hashlib.sha512,
        ).hexdigest()

        return hash == signature

    # Helper methods

    def _generate_reference(self) -> str:
        """Generate unique transaction reference"""
        import uuid
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_id = uuid.uuid4().hex[:8]
        return f"EXAMS_{timestamp}_{unique_id}"

    def naira_to_kobo(self, naira: Decimal) -> int:
        """Convert Naira to Kobo (₦1 = 100 kobo)"""
        return int(naira * 100)

    def kobo_to_naira(self, kobo: int) -> Decimal:
        """Convert Kobo to Naira"""
        return Decimal(kobo) / 100


# ExamsTutor-specific payment service
class ExamsTutorPaymentService:
    """High-level payment service for ExamsTutor"""

    def __init__(self, paystack_client: PaystackClient, db_connection=None):
        self.paystack = paystack_client
        self.db = db_connection

    async def initialize_subscription_payment(
        self,
        school_id: str,
        subscription_id: str,
        email: str,
        amount_naira: Decimal,
        callback_url: str,
    ) -> Dict[str, Any]:
        """
        Initialize payment for a subscription

        Returns:
            {
                "payment_url": "https://checkout.paystack.com/...",
                "reference": "EXAMS_...",
                "amount_naira": 100000.00,
                "amount_kobo": 10000000
            }
        """
        # Convert to kobo
        amount_kobo = self.paystack.naira_to_kobo(amount_naira)

        # Initialize transaction
        result = self.paystack.initialize_transaction(
            email=email,
            amount=amount_kobo,
            callback_url=callback_url,
            metadata={
                "school_id": school_id,
                "subscription_id": subscription_id,
                "amount_naira": str(amount_naira),
                "purpose": "subscription_payment",
            },
            channels=["card", "bank", "ussd", "mobile_money"],
        )

        if result.get("status"):
            data = result["data"]

            # Save payment record to database
            await self._save_payment_record(
                reference=data["reference"],
                school_id=school_id,
                subscription_id=subscription_id,
                amount_naira=amount_naira,
                amount_kobo=amount_kobo,
                status="pending",
            )

            return {
                "payment_url": data["authorization_url"],
                "reference": data["reference"],
                "amount_naira": amount_naira,
                "amount_kobo": amount_kobo,
            }
        else:
            raise Exception(f"Payment initialization failed: {result.get('message')}")

    async def verify_payment(self, reference: str) -> Dict[str, Any]:
        """
        Verify payment and update subscription

        Returns:
            {
                "success": True,
                "status": "success",
                "amount_naira": 100000.00,
                "school_id": "...",
                "subscription_id": "..."
            }
        """
        # Verify with Paystack
        result = self.paystack.verify_transaction(reference)

        if not result.get("status"):
            return {
                "success": False,
                "error": result.get("message"),
            }

        data = result["data"]
        status = data["status"]  # "success", "failed", "abandoned"
        amount_kobo = data["amount"]
        metadata = data.get("metadata", {})

        school_id = metadata.get("school_id")
        subscription_id = metadata.get("subscription_id")

        # Update payment record
        await self._update_payment_record(
            reference=reference,
            status=status,
            paystack_data=data,
        )

        if status == "success":
            # Update subscription status
            await self._activate_subscription(subscription_id)

            # Save authorization code for recurring payments
            authorization = data.get("authorization", {})
            if authorization.get("reusable"):
                await self._save_authorization(
                    school_id=school_id,
                    authorization_code=authorization["authorization_code"],
                    card_type=authorization.get("card_type"),
                    last4=authorization.get("last4"),
                    exp_month=authorization.get("exp_month"),
                    exp_year=authorization.get("exp_year"),
                    bank=authorization.get("bank"),
                )

            return {
                "success": True,
                "status": status,
                "amount_naira": self.paystack.kobo_to_naira(amount_kobo),
                "school_id": school_id,
                "subscription_id": subscription_id,
            }
        else:
            return {
                "success": False,
                "status": status,
                "school_id": school_id,
                "subscription_id": subscription_id,
            }

    async def process_recurring_payment(
        self,
        school_id: str,
        subscription_id: str,
        email: str,
        amount_naira: Decimal,
    ) -> Dict[str, Any]:
        """
        Process recurring payment using saved authorization

        Returns:
            {
                "success": True,
                "reference": "...",
                "amount_naira": 100000.00
            }
        """
        # Get saved authorization
        authorization = await self._get_authorization(school_id)

        if not authorization:
            return {
                "success": False,
                "error": "No saved payment method found",
            }

        # Charge authorization
        amount_kobo = self.paystack.naira_to_kobo(amount_naira)

        result = self.paystack.charge_authorization(
            email=email,
            amount=amount_kobo,
            authorization_code=authorization["authorization_code"],
            metadata={
                "school_id": school_id,
                "subscription_id": subscription_id,
                "amount_naira": str(amount_naira),
                "purpose": "recurring_payment",
            },
        )

        if result.get("status") and result["data"]["status"] == "success":
            data = result["data"]
            reference = data["reference"]

            # Save payment record
            await self._save_payment_record(
                reference=reference,
                school_id=school_id,
                subscription_id=subscription_id,
                amount_naira=amount_naira,
                amount_kobo=amount_kobo,
                status="success",
            )

            # Extend subscription
            await self._extend_subscription(subscription_id)

            return {
                "success": True,
                "reference": reference,
                "amount_naira": amount_naira,
            }
        else:
            # Payment failed
            await self._handle_failed_payment(subscription_id)

            return {
                "success": False,
                "error": result.get("message"),
                "subscription_id": subscription_id,
            }

    async def process_refund(
        self,
        reference: str,
        amount_naira: Optional[Decimal] = None,
        reason: str = "Customer request",
    ) -> Dict[str, Any]:
        """Process a refund"""
        amount_kobo = self.paystack.naira_to_kobo(amount_naira) if amount_naira else None

        result = self.paystack.refund_transaction(
            transaction=reference,
            amount=amount_kobo,
            customer_note=reason,
        )

        if result.get("status"):
            # Update payment record
            await self._update_payment_record(
                reference=reference,
                status="refunded",
                refund_data=result["data"],
            )

            return {
                "success": True,
                "message": "Refund processed successfully",
            }
        else:
            return {
                "success": False,
                "error": result.get("message"),
            }

    # Database helpers (placeholders - implement with actual DB)

    async def _save_payment_record(self, **kwargs):
        """Save payment record to database"""
        # Implementation depends on database
        pass

    async def _update_payment_record(self, reference: str, **kwargs):
        """Update payment record"""
        pass

    async def _activate_subscription(self, subscription_id: str):
        """Activate subscription after successful payment"""
        pass

    async def _extend_subscription(self, subscription_id: str):
        """Extend subscription period"""
        pass

    async def _save_authorization(self, school_id: str, **kwargs):
        """Save payment authorization for recurring payments"""
        pass

    async def _get_authorization(self, school_id: str):
        """Get saved authorization"""
        pass

    async def _handle_failed_payment(self, subscription_id: str):
        """Handle failed recurring payment"""
        pass


# Initialize payment service
def get_payment_service() -> ExamsTutorPaymentService:
    """Factory function to get configured payment service"""

    # Load configuration from environment
    secret_key = os.getenv("PAYSTACK_SECRET_KEY")
    public_key = os.getenv("PAYSTACK_PUBLIC_KEY")
    environment = os.getenv("PAYSTACK_ENVIRONMENT", "test")

    if not secret_key or not public_key:
        raise ValueError("Paystack credentials not configured")

    config = PaystackConfig(
        secret_key=secret_key,
        public_key=public_key,
        environment=PaystackEnvironment(environment),
    )

    paystack_client = PaystackClient(config)

    return ExamsTutorPaymentService(paystack_client)


# Example usage
if __name__ == "__main__":
    # Example: Initialize payment for Premium subscription
    import asyncio
    from decimal import Decimal

    # Mock service
    service = get_payment_service()

    # Initialize payment
    payment_info = asyncio.run(
        service.initialize_subscription_payment(
            school_id="SCH001",
            subscription_id="SUB001",
            email="principal@greenfield.ng",
            amount_naira=Decimal("100000"),  # ₦100,000 for 200 students × ₦500
            callback_url="https://examstutor.ng/payment/callback",
        )
    )

    print("Payment initialized:")
    print(f"  Payment URL: {payment_info['payment_url']}")
    print(f"  Reference: {payment_info['reference']}")
    print(f"  Amount: ₦{payment_info['amount_naira']:,.2f}")

    # After payment, verify
    # verification = asyncio.run(service.verify_payment(payment_info['reference']))
    # print(f"Payment verified: {verification['success']}")
