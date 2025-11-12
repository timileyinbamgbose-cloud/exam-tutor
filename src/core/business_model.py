"""
Business Model Implementation - Freemium & Subscription Management
ExamsTutor AI - Phase 5: Scale & Growth

This module implements the freemium model with feature gating,
subscription management, and usage tracking.
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from decimal import Decimal


class SubscriptionTier(str, Enum):
    """Subscription tier types"""
    FREE = "free"  # Public schools, freemium
    PREMIUM = "premium"  # Private schools (₦500/student/month)
    ENTERPRISE = "enterprise"  # Government contracts, custom pricing
    SPONSORED = "sponsored"  # NGO-sponsored students


class BillingCycle(str, Enum):
    """Billing cycle options"""
    MONTHLY = "monthly"
    ANNUAL = "annual"  # 20% discount
    CUSTOM = "custom"  # For enterprise contracts


class PaymentStatus(str, Enum):
    """Payment status tracking"""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    OVERDUE = "overdue"


@dataclass
class SubscriptionPlan:
    """Subscription plan configuration"""
    tier: SubscriptionTier
    name: str
    price_per_student_monthly: Decimal
    features: Dict[str, Any]
    limits: Dict[str, int]
    support_sla: str
    description: str

    def get_annual_price(self, num_students: int) -> Decimal:
        """Calculate annual price with 20% discount"""
        monthly_total = self.price_per_student_monthly * num_students
        annual_total = monthly_total * 12
        return annual_total * Decimal('0.8')  # 20% discount

    def get_monthly_price(self, num_students: int) -> Decimal:
        """Calculate monthly price"""
        return self.price_per_student_monthly * num_students


# Define subscription plans
SUBSCRIPTION_PLANS = {
    SubscriptionTier.FREE: SubscriptionPlan(
        tier=SubscriptionTier.FREE,
        name="Free Tier (Public Schools)",
        price_per_student_monthly=Decimal('0'),
        features={
            "ai_tutor": True,
            "diagnostics": "basic",
            "practice_questions": "standard",
            "learning_plans": True,
            "teacher_dashboard": "basic",
            "parent_dashboard": False,
            "offline_mode": True,
            "waec_jamb_full_library": False,
            "priority_support": False,
            "custom_training": False,
            "advanced_analytics": False,
        },
        limits={
            "questions_per_month": 50,  # Per student
            "practice_sessions_per_week": 10,
            "diagnostic_tests_per_term": 3,
            "learning_plans_active": 1,
        },
        support_sla="Community support (48-hour response)",
        description="Basic access for public schools. Limited usage quotas."
    ),

    SubscriptionTier.PREMIUM: SubscriptionPlan(
        tier=SubscriptionTier.PREMIUM,
        name="Premium (Private Schools)",
        price_per_student_monthly=Decimal('500'),  # ₦500
        features={
            "ai_tutor": True,
            "diagnostics": "advanced",
            "practice_questions": "full_library",
            "learning_plans": True,
            "teacher_dashboard": "advanced",
            "parent_dashboard": True,
            "offline_mode": True,
            "waec_jamb_full_library": True,
            "priority_support": True,
            "custom_training": False,
            "advanced_analytics": True,
            "progress_reports": "detailed",
            "video_explanations": True,
        },
        limits={
            "questions_per_month": -1,  # Unlimited
            "practice_sessions_per_week": -1,  # Unlimited
            "diagnostic_tests_per_term": -1,  # Unlimited
            "learning_plans_active": 5,
        },
        support_sla="Priority support (4-hour response during school hours)",
        description="Full access for private schools. Unlimited usage."
    ),

    SubscriptionTier.ENTERPRISE: SubscriptionPlan(
        tier=SubscriptionTier.ENTERPRISE,
        name="Enterprise (Government/Corporate)",
        price_per_student_monthly=Decimal('200'),  # Bulk discount
        features={
            "ai_tutor": True,
            "diagnostics": "advanced",
            "practice_questions": "full_library",
            "learning_plans": True,
            "teacher_dashboard": "advanced",
            "parent_dashboard": True,
            "offline_mode": True,
            "waec_jamb_full_library": True,
            "priority_support": True,
            "custom_training": True,
            "advanced_analytics": True,
            "progress_reports": "detailed",
            "video_explanations": True,
            "white_label": "optional",
            "dedicated_account_manager": True,
            "quarterly_business_reviews": True,
            "sla_99_9_uptime": True,
        },
        limits={
            "questions_per_month": -1,  # Unlimited
            "practice_sessions_per_week": -1,  # Unlimited
            "diagnostic_tests_per_term": -1,  # Unlimited
            "learning_plans_active": -1,  # Unlimited
        },
        support_sla="Enterprise support (<2 hour critical issue response)",
        description="Custom solutions for government and corporate partners."
    ),

    SubscriptionTier.SPONSORED: SubscriptionPlan(
        tier=SubscriptionTier.SPONSORED,
        name="Sponsored (NGO)",
        price_per_student_monthly=Decimal('300'),  # Paid by sponsor
        features={
            "ai_tutor": True,
            "diagnostics": "advanced",
            "practice_questions": "full_library",
            "learning_plans": True,
            "teacher_dashboard": "advanced",
            "parent_dashboard": False,
            "offline_mode": True,
            "waec_jamb_full_library": True,
            "priority_support": False,
            "custom_training": False,
            "advanced_analytics": True,
            "impact_reporting": True,  # For sponsors
        },
        limits={
            "questions_per_month": -1,  # Unlimited
            "practice_sessions_per_week": -1,  # Unlimited
            "diagnostic_tests_per_term": -1,  # Unlimited
            "learning_plans_active": 3,
        },
        support_sla="Standard support (24-hour response)",
        description="Full access for underprivileged students sponsored by NGOs/corporates."
    ),
}


@dataclass
class Subscription:
    """Student or school subscription record"""
    subscription_id: str
    school_id: str
    tier: SubscriptionTier
    billing_cycle: BillingCycle
    num_students: int
    price_per_cycle: Decimal

    start_date: datetime
    end_date: datetime
    renewal_date: datetime

    status: str  # active, suspended, cancelled, trial
    payment_status: PaymentStatus

    sponsor_id: Optional[str] = None  # For sponsored subscriptions
    discount_percent: Decimal = Decimal('0')
    custom_terms: Optional[Dict[str, Any]] = None

    created_at: datetime = None
    updated_at: datetime = None

    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        now = datetime.now()
        return (
            self.status == "active" and
            self.start_date <= now <= self.end_date and
            self.payment_status == PaymentStatus.PAID
        )

    def is_trial(self) -> bool:
        """Check if subscription is in trial period"""
        return self.status == "trial"

    def days_until_expiry(self) -> int:
        """Days until subscription expires"""
        delta = self.end_date - datetime.now()
        return max(0, delta.days)

    def is_overdue(self) -> bool:
        """Check if payment is overdue"""
        return (
            self.payment_status == PaymentStatus.OVERDUE or
            (datetime.now() > self.renewal_date and
             self.payment_status != PaymentStatus.PAID)
        )


@dataclass
class UsageRecord:
    """Track feature usage for billing and limits enforcement"""
    record_id: str
    user_id: str
    school_id: str
    feature: str  # questions, practice_sessions, diagnostics, etc.
    count: int
    period_start: datetime
    period_end: datetime
    created_at: datetime


class FeatureGate:
    """Feature gating system for freemium model"""

    def __init__(self, subscription: Subscription):
        self.subscription = subscription
        self.plan = SUBSCRIPTION_PLANS[subscription.tier]

    def has_feature(self, feature_name: str) -> bool:
        """Check if subscription has access to a feature"""
        if not self.subscription.is_active():
            return False

        return self.plan.features.get(feature_name, False)

    def check_limit(self, feature: str, current_usage: int) -> Dict[str, Any]:
        """
        Check if user has exceeded usage limit

        Returns:
            {
                "allowed": bool,
                "limit": int,
                "current": int,
                "remaining": int,
                "reset_date": datetime
            }
        """
        if not self.subscription.is_active():
            return {
                "allowed": False,
                "reason": "Subscription not active",
                "limit": 0,
                "current": current_usage,
                "remaining": 0,
            }

        limit = self.plan.limits.get(feature, 0)

        # -1 means unlimited
        if limit == -1:
            return {
                "allowed": True,
                "limit": -1,  # Unlimited
                "current": current_usage,
                "remaining": -1,
            }

        # Check against limit
        remaining = max(0, limit - current_usage)
        allowed = current_usage < limit

        return {
            "allowed": allowed,
            "limit": limit,
            "current": current_usage,
            "remaining": remaining,
            "reset_date": self._get_reset_date(),
        }

    def _get_reset_date(self) -> datetime:
        """Get the date when usage limits reset"""
        if self.subscription.billing_cycle == BillingCycle.MONTHLY:
            return self.subscription.renewal_date
        elif self.subscription.billing_cycle == BillingCycle.ANNUAL:
            # Monthly reset even for annual plans
            now = datetime.now()
            next_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
            return next_month
        return self.subscription.renewal_date

    def get_upgrade_prompt(self, feature: str) -> Dict[str, Any]:
        """
        Generate upgrade prompt when user hits limit

        Returns upgrade message and CTA
        """
        if self.subscription.tier == SubscriptionTier.FREE:
            premium_plan = SUBSCRIPTION_PLANS[SubscriptionTier.PREMIUM]
            return {
                "title": "Upgrade to Premium",
                "message": f"You've reached your limit of {self.plan.limits.get(feature, 0)} {feature} this month. Upgrade to Premium for unlimited access!",
                "cta": "Upgrade Now",
                "benefits": [
                    "Unlimited questions",
                    "Full WAEC/JAMB question library",
                    "Advanced analytics",
                    "Parent dashboard",
                    "Priority support",
                ],
                "price": f"₦{premium_plan.price_per_student_monthly}/student/month",
                "upgrade_url": "/upgrade?tier=premium",
            }

        return {
            "title": "Limit Reached",
            "message": f"You've used all your {feature} for this period. Resets on {self._get_reset_date().strftime('%B %d, %Y')}.",
            "cta": None,
        }


class SubscriptionManager:
    """Manage subscriptions, billing, and upgrades"""

    def __init__(self, db_connection):
        self.db = db_connection

    async def create_subscription(
        self,
        school_id: str,
        tier: SubscriptionTier,
        billing_cycle: BillingCycle,
        num_students: int,
        trial_days: int = 30,
        sponsor_id: Optional[str] = None,
    ) -> Subscription:
        """Create a new subscription"""

        plan = SUBSCRIPTION_PLANS[tier]
        now = datetime.now()

        # Calculate pricing
        if billing_cycle == BillingCycle.MONTHLY:
            price = plan.get_monthly_price(num_students)
            end_date = now + timedelta(days=30 if trial_days == 0 else trial_days)
        elif billing_cycle == BillingCycle.ANNUAL:
            price = plan.get_annual_price(num_students)
            end_date = now + timedelta(days=365 if trial_days == 0 else trial_days)
        else:
            # Custom pricing for enterprise
            price = Decimal('0')  # Set during contract negotiation
            end_date = now + timedelta(days=365)

        subscription = Subscription(
            subscription_id=self._generate_subscription_id(),
            school_id=school_id,
            tier=tier,
            billing_cycle=billing_cycle,
            num_students=num_students,
            price_per_cycle=price,
            start_date=now,
            end_date=end_date,
            renewal_date=end_date,
            status="trial" if trial_days > 0 else "active",
            payment_status=PaymentStatus.PENDING if trial_days == 0 else PaymentStatus.PAID,
            sponsor_id=sponsor_id,
            created_at=now,
            updated_at=now,
        )

        # Save to database
        await self._save_subscription(subscription)

        return subscription

    async def upgrade_subscription(
        self,
        subscription_id: str,
        new_tier: SubscriptionTier,
        prorate: bool = True,
    ) -> Subscription:
        """Upgrade subscription to higher tier"""

        subscription = await self._get_subscription(subscription_id)

        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        # Calculate proration if upgrading mid-cycle
        if prorate:
            days_remaining = subscription.days_until_expiry()
            # Calculate refund/credit for old plan and charge for new plan
            # Implementation depends on payment processor
            pass

        # Update subscription
        subscription.tier = new_tier
        subscription.updated_at = datetime.now()

        # Recalculate pricing
        new_plan = SUBSCRIPTION_PLANS[new_tier]
        if subscription.billing_cycle == BillingCycle.MONTHLY:
            subscription.price_per_cycle = new_plan.get_monthly_price(subscription.num_students)
        elif subscription.billing_cycle == BillingCycle.ANNUAL:
            subscription.price_per_cycle = new_plan.get_annual_price(subscription.num_students)

        await self._save_subscription(subscription)

        return subscription

    async def cancel_subscription(
        self,
        subscription_id: str,
        immediate: bool = False,
    ) -> bool:
        """Cancel subscription"""

        subscription = await self._get_subscription(subscription_id)

        if not subscription:
            return False

        if immediate:
            subscription.status = "cancelled"
            subscription.end_date = datetime.now()
        else:
            # Cancel at end of billing period
            subscription.status = "cancelling"
            # Will be cancelled on renewal_date

        subscription.updated_at = datetime.now()
        await self._save_subscription(subscription)

        return True

    async def process_renewal(self, subscription_id: str) -> Dict[str, Any]:
        """Process subscription renewal (called by scheduled job)"""

        subscription = await self._get_subscription(subscription_id)

        if not subscription:
            return {"success": False, "error": "Subscription not found"}

        # Attempt payment
        payment_result = await self._process_payment(
            school_id=subscription.school_id,
            amount=subscription.price_per_cycle,
            description=f"ExamsTutor {subscription.tier.value} subscription renewal",
        )

        if payment_result["success"]:
            # Extend subscription
            if subscription.billing_cycle == BillingCycle.MONTHLY:
                subscription.end_date = subscription.end_date + timedelta(days=30)
                subscription.renewal_date = subscription.end_date
            elif subscription.billing_cycle == BillingCycle.ANNUAL:
                subscription.end_date = subscription.end_date + timedelta(days=365)
                subscription.renewal_date = subscription.end_date

            subscription.payment_status = PaymentStatus.PAID
            subscription.status = "active"
            subscription.updated_at = datetime.now()

            await self._save_subscription(subscription)

            # Send confirmation email
            await self._send_renewal_confirmation(subscription)

            return {"success": True, "subscription": subscription}

        else:
            # Payment failed - retry logic
            subscription.payment_status = PaymentStatus.FAILED
            subscription.updated_at = datetime.now()
            await self._save_subscription(subscription)

            # Send payment failed email
            await self._send_payment_failed_email(subscription)

            return {"success": False, "error": "Payment failed", "details": payment_result}

    async def handle_dunning(self, subscription_id: str) -> None:
        """
        Handle failed payment recovery (dunning management)

        Dunning sequence:
        - Day 0: Payment fails → Send reminder
        - Day 3: Send 2nd reminder
        - Day 7: Send final notice, suspend access
        - Day 14: Cancel subscription
        """
        subscription = await self._get_subscription(subscription_id)

        if not subscription or subscription.payment_status != PaymentStatus.FAILED:
            return

        days_overdue = (datetime.now() - subscription.renewal_date).days

        if days_overdue == 0:
            await self._send_payment_failed_email(subscription, reminder=1)
        elif days_overdue == 3:
            await self._send_payment_failed_email(subscription, reminder=2)
            # Retry payment
            await self.process_renewal(subscription_id)
        elif days_overdue == 7:
            await self._send_payment_failed_email(subscription, reminder=3)
            # Suspend access
            subscription.status = "suspended"
            subscription.payment_status = PaymentStatus.OVERDUE
            await self._save_subscription(subscription)
        elif days_overdue >= 14:
            # Cancel subscription
            await self.cancel_subscription(subscription_id, immediate=True)
            await self._send_cancellation_email(subscription, reason="payment_failure")

    # Helper methods (would be implemented with actual DB/payment processor)

    def _generate_subscription_id(self) -> str:
        """Generate unique subscription ID"""
        import uuid
        return f"sub_{uuid.uuid4().hex[:16]}"

    async def _get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Retrieve subscription from database"""
        # Implementation depends on database
        pass

    async def _save_subscription(self, subscription: Subscription) -> bool:
        """Save subscription to database"""
        # Implementation depends on database
        pass

    async def _process_payment(
        self,
        school_id: str,
        amount: Decimal,
        description: str,
    ) -> Dict[str, Any]:
        """
        Process payment via Paystack/Flutterwave

        Returns:
            {
                "success": bool,
                "transaction_id": str,
                "amount": Decimal,
                "error": Optional[str]
            }
        """
        # Integration with Paystack/Flutterwave API
        # This would make actual API call to payment processor
        pass

    async def _send_renewal_confirmation(self, subscription: Subscription) -> None:
        """Send subscription renewal confirmation email"""
        pass

    async def _send_payment_failed_email(
        self,
        subscription: Subscription,
        reminder: int = 1,
    ) -> None:
        """Send payment failed notification"""
        pass

    async def _send_cancellation_email(
        self,
        subscription: Subscription,
        reason: str,
    ) -> None:
        """Send subscription cancellation email"""
        pass


# Usage tracking for billing and limits
class UsageTracker:
    """Track feature usage for billing and limit enforcement"""

    def __init__(self, db_connection):
        self.db = db_connection

    async def record_usage(
        self,
        user_id: str,
        school_id: str,
        feature: str,
        count: int = 1,
    ) -> None:
        """Record feature usage"""

        now = datetime.now()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)

        usage = UsageRecord(
            record_id=self._generate_record_id(),
            user_id=user_id,
            school_id=school_id,
            feature=feature,
            count=count,
            period_start=period_start,
            period_end=period_end,
            created_at=now,
        )

        await self._save_usage_record(usage)

    async def get_usage(
        self,
        user_id: str,
        feature: str,
        period_start: datetime,
        period_end: datetime,
    ) -> int:
        """Get total usage for a feature in a period"""
        # Query database and sum usage
        pass

    async def get_school_usage(
        self,
        school_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> Dict[str, int]:
        """Get school-wide usage breakdown"""
        # Query database and aggregate by feature
        pass

    def _generate_record_id(self) -> str:
        """Generate unique usage record ID"""
        import uuid
        return f"usage_{uuid.uuid4().hex[:16]}"

    async def _save_usage_record(self, record: UsageRecord) -> bool:
        """Save usage record to database"""
        pass


# Example usage
if __name__ == "__main__":
    # Example: Create a premium subscription for a private school
    from decimal import Decimal

    # School with 200 students wants Premium tier
    num_students = 200
    plan = SUBSCRIPTION_PLANS[SubscriptionTier.PREMIUM]

    monthly_cost = plan.get_monthly_price(num_students)
    annual_cost = plan.get_annual_price(num_students)

    print(f"Premium Plan for {num_students} students:")
    print(f"  Monthly: ₦{monthly_cost:,.2f}")
    print(f"  Annual: ₦{annual_cost:,.2f} (save ₦{monthly_cost * 12 - annual_cost:,.2f})")
    print(f"\nFeatures:")
    for feature, value in plan.features.items():
        print(f"  - {feature}: {value}")
    print(f"\nSupport SLA: {plan.support_sla}")

    # Example: Check feature gate
    sample_subscription = Subscription(
        subscription_id="sub_example123",
        school_id="school_001",
        tier=SubscriptionTier.FREE,
        billing_cycle=BillingCycle.MONTHLY,
        num_students=100,
        price_per_cycle=Decimal('0'),
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=30),
        renewal_date=datetime.now() + timedelta(days=30),
        status="active",
        payment_status=PaymentStatus.PAID,
    )

    gate = FeatureGate(sample_subscription)

    # Check if user has access to parent dashboard
    has_parent_dashboard = gate.has_feature("parent_dashboard")
    print(f"\nFree tier has parent dashboard: {has_parent_dashboard}")

    # Check question limit
    current_questions = 45
    limit_check = gate.check_limit("questions_per_month", current_questions)
    print(f"\nQuestions limit check:")
    print(f"  Allowed: {limit_check['allowed']}")
    print(f"  Current: {limit_check['current']}/{limit_check['limit']}")
    print(f"  Remaining: {limit_check['remaining']}")

    # If limit reached, get upgrade prompt
    if current_questions >= 50:
        upgrade_prompt = gate.get_upgrade_prompt("questions_per_month")
        print(f"\nUpgrade prompt:")
        print(f"  {upgrade_prompt['message']}")
        print(f"  Price: {upgrade_prompt['price']}")
