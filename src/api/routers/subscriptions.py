"""
Subscription Management Router
Handles subscription plans, upgrades, and management
"""
from fastapi import APIRouter, HTTPException, status, Depends
from src.api.models import SubscriptionPlanResponse, SubscribeRequest, SubscriptionResponse
from src.api.auth import get_current_user
from src.core.business_model import SUBSCRIPTION_PLANS, SubscriptionTier
from typing import List
from datetime import datetime, timedelta
import uuid

router = APIRouter(prefix="/api/v1/subscriptions", tags=["Subscriptions"])


@router.get("/plans", response_model=List[SubscriptionPlanResponse])
async def get_subscription_plans():
    """Get all available subscription plans"""
    plans = []

    for tier, plan in SUBSCRIPTION_PLANS.items():
        plan_response = SubscriptionPlanResponse(
            tier=plan.tier.value,
            name=plan.name,
            price_monthly=float(plan.price_per_student_monthly),
            price_annual=float(plan.get_annual_price(1)),  # Price for 1 student
            features=plan.features,
            limits=plan.limits
        )
        plans.append(plan_response)

    return plans


@router.get("/plans/{tier}")
async def get_plan_details(tier: str):
    """Get details of a specific subscription plan"""
    try:
        subscription_tier = SubscriptionTier(tier)
        plan = SUBSCRIPTION_PLANS.get(subscription_tier)

        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plan '{tier}' not found"
            )

        return SubscriptionPlanResponse(
            tier=plan.tier.value,
            name=plan.name,
            price_monthly=float(plan.price_per_student_monthly),
            price_annual=float(plan.get_annual_price(1)),
            features=plan.features,
            limits=plan.limits
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid subscription tier: {tier}"
        )


@router.post("/subscribe", response_model=SubscriptionResponse)
async def create_subscription(
    request: SubscribeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new subscription"""
    try:
        subscription_tier = SubscriptionTier(request.plan_tier)
        plan = SUBSCRIPTION_PLANS.get(subscription_tier)

        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plan '{request.plan_tier}' not found"
            )

        # Calculate subscription period
        start_date = datetime.utcnow()
        if request.billing_cycle == "monthly":
            end_date = start_date + timedelta(days=30)
        elif request.billing_cycle == "annual":
            end_date = start_date + timedelta(days=365)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid billing cycle"
            )

        # Create subscription
        subscription = SubscriptionResponse(
            subscription_id=str(uuid.uuid4()),
            plan_tier=request.plan_tier,
            status="pending",  # Will be "active" after payment
            start_date=start_date,
            end_date=end_date,
            auto_renew=True
        )

        return subscription

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/my-subscription", response_model=SubscriptionResponse)
async def get_my_subscription(current_user: dict = Depends(get_current_user)):
    """Get current user's subscription"""
    # Mock subscription
    return SubscriptionResponse(
        subscription_id=str(uuid.uuid4()),
        plan_tier="free",
        status="active",
        start_date=datetime.utcnow() - timedelta(days=30),
        end_date=datetime.utcnow() + timedelta(days=335),
        auto_renew=True
    )


@router.patch("/my-subscription")
async def update_subscription(
    auto_renew: bool = None,
    current_user: dict = Depends(get_current_user)
):
    """Update subscription settings"""
    return {
        "message": "Subscription updated successfully",
        "auto_renew": auto_renew
    }


@router.post("/my-subscription/cancel")
async def cancel_subscription(current_user: dict = Depends(get_current_user)):
    """Cancel current subscription"""
    return {
        "message": "Subscription will be cancelled at the end of the current billing period",
        "cancellation_date": datetime.utcnow() + timedelta(days=30)
    }


@router.post("/my-subscription/upgrade")
async def upgrade_subscription(
    new_tier: str,
    current_user: dict = Depends(get_current_user)
):
    """Upgrade to a higher subscription tier"""
    try:
        subscription_tier = SubscriptionTier(new_tier)
        plan = SUBSCRIPTION_PLANS.get(subscription_tier)

        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plan '{new_tier}' not found"
            )

        return {
            "message": f"Subscription upgraded to {plan.name}",
            "new_tier": new_tier,
            "effective_date": datetime.utcnow()
        }
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid subscription tier: {new_tier}"
        )
