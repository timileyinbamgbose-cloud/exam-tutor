"""
Rate Limiting Middleware
Prevents API abuse and ensures fair usage
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from typing import Callable
import os


# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour"],  # Default limit for all endpoints
    storage_uri=os.getenv("REDIS_URL", "memory://"),  # Use Redis if available, fallback to memory
)


# Custom rate limit exceeded handler
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded) -> dict:
    """
    Custom handler for rate limit exceeded errors
    """
    return {
        "error": "rate_limit_exceeded",
        "message": "Too many requests. Please try again later.",
        "detail": str(exc.detail),
        "retry_after": exc.detail.split("in ")[-1] if "in " in exc.detail else "unknown"
    }


# Rate limit tiers for different endpoints
RATE_LIMITS = {
    # Authentication endpoints (prevent brute force)
    "auth_register": "5/minute",
    "auth_login": "10/minute",
    "auth_refresh": "20/minute",

    # AI tutor endpoints (prevent abuse, manage costs)
    "tutor_ask": "30/minute",  # 30 questions per minute
    "tutor_practice": "10/minute",  # 10 practice generations per minute
    "tutor_diagnostic": "5/minute",  # 5 diagnostic tests per minute

    # General API endpoints
    "general": "100/minute",

    # Admin endpoints (higher limits)
    "admin": "200/minute",
}


def get_rate_limit(endpoint_type: str = "general") -> str:
    """
    Get rate limit for specific endpoint type
    """
    return RATE_LIMITS.get(endpoint_type, RATE_LIMITS["general"])


# Rate limiting decorators for different tiers
def rate_limit_auth(func: Callable) -> Callable:
    """Rate limit for authentication endpoints"""
    return limiter.limit(RATE_LIMITS["auth_login"])(func)


def rate_limit_tutor(func: Callable) -> Callable:
    """Rate limit for AI tutor endpoints"""
    return limiter.limit(RATE_LIMITS["tutor_ask"])(func)


def rate_limit_practice(func: Callable) -> Callable:
    """Rate limit for practice generation"""
    return limiter.limit(RATE_LIMITS["tutor_practice"])(func)


def rate_limit_general(func: Callable) -> Callable:
    """Rate limit for general endpoints"""
    return limiter.limit(RATE_LIMITS["general"])(func)
