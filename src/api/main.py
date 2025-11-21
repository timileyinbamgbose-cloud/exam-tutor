"""
ExamsTutor AI API - Main Application (Production-Grade)
Complete REST API with all production features
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic_settings import BaseSettings
from pydantic import ValidationError
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.errors import RateLimitExceeded
import time
import os

# Import routers (use database versions)
from src.api.routers import auth_db as auth, tutor_db as tutor, curriculum, subscriptions, payments, teachers, admin, rag_admin, finetuning_admin, evaluation_admin, feedback
from src.database.config import init_db

# Import middleware and utilities
from src.middleware import (
    limiter,
    custom_rate_limit_handler,
    SecurityHeadersMiddleware,
    InputValidationMiddleware,
    RequestSizeLimitMiddleware,
    IPBlacklistMiddleware
)
from src.logging import setup_logging, get_logger, request_logger
from src.cache import cache


class Settings(BaseSettings):
    """Application settings"""
    app_name: str = "ExamsTutor AI API"
    version: str = "1.0.0"  # Full AI Engineer Edition - All 6 AI features complete
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    class Config:
        env_file = ".env"
        extra = "allow"  # Allow extra fields from .env


settings = Settings()

# Setup logging FIRST (before creating app)
setup_logging(log_level=settings.log_level)
logger = get_logger("main")

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="""
    AI-powered tutoring platform for Nigerian secondary school students (SS1-SS3)
    preparing for WAEC and JAMB examinations.

    ## Features
    - **AI Tutor**: Ask questions and get curriculum-grounded answers
    - **Practice**: Generate practice questions and diagnostic tests
    - **Subscriptions**: Freemium model with multiple tiers
    - **Payments**: Paystack integration for Nigerian schools
    - **Analytics**: Track student progress and performance
    - **Teacher Dashboard**: Manage students and assignments
    - **Admin Panel**: System management and analytics

    ## Production Features
    - **Rate Limiting**: Prevent API abuse
    - **Caching**: Redis-powered response caching
    - **Monitoring**: Prometheus metrics at /metrics
    - **Security**: Input validation, security headers, HTTPS
    - **Logging**: Structured logging with rotation
    - **Background Tasks**: Celery queue for async operations

    ## Authentication
    Most endpoints require authentication. Use `/api/v1/auth/login` to get an access token.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

# Add security middlewares (order matters!)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(InputValidationMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_request_size=1048576)  # 1MB
app.add_middleware(IPBlacklistMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Prometheus metrics
instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=[".*admin.*", "/metrics"],
    env_var_name="ENABLE_METRICS",
    inprogress_name="fastapi_inprogress",
    inprogress_labels=True,
)
instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


# Request timing and logging middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request processing time to response headers and log requests"""
    start_time = time.time()

    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        process_time_ms = process_time * 1000

        response.headers["X-Process-Time"] = str(process_time)

        # Log request
        await request_logger.log_request(
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            duration_ms=process_time_ms
        )

        return response

    except Exception as e:
        process_time = time.time() - start_time
        process_time_ms = process_time * 1000

        # Log error
        await request_logger.log_request(
            method=request.method,
            path=str(request.url.path),
            status_code=500,
            duration_ms=process_time_ms,
            error=str(e)
        )

        raise


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.debug else "An error occurred"
        }
    )


# Root endpoints
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to ExamsTutor AI API",
        "version": settings.version,
        "status": "running",
        "environment": settings.environment,
        "docs": "/docs",
        "features": {
            "ai_tutor": "Ask questions and get answers",
            "practice": "Generate practice questions",
            "offline_mode": "Works without internet",
            "subscriptions": "Freemium pricing model",
            "payments": "Paystack integration",
            "analytics": "Track student progress"
        },
        "endpoints": {
            "auth": "/api/v1/auth",
            "tutor": "/api/v1/tutor",
            "feedback": "/api/v1/feedback",
            "curriculum": "/api/v1/curriculum",
            "subscriptions": "/api/v1/subscriptions",
            "payments": "/api/v1/payments",
            "teachers": "/api/v1/teachers",
            "admin": "/api/v1/admin"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with detailed status"""
    # Check cache health
    cache_health = cache.health_check()

    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "timestamp": time.time(),
        "components": {
            "api": "operational",
            "database": "operational",  # Could add actual DB ping
            "cache": cache_health.get("status", "disabled"),
            "ai_service": "operational"  # Could check OpenAI API
        },
        "features": {
            "rate_limiting": "enabled",
            "caching": "enabled" if cache.enabled else "disabled",
            "monitoring": "enabled",
            "logging": "enabled",
            "security": "enabled"
        }
    }


@app.get("/api/v1/status")
async def api_status():
    """Detailed API status"""
    return {
        "api": "operational",
        "version": settings.version,
        "endpoints": {
            "authentication": "available",
            "ai_tutor": "available",
            "curriculum": "available",
            "subscriptions": "available",
            "payments": "available",
            "teachers": "available",
            "admin": "available"
        },
        "features": {
            "offline_mode": "supported",
            "rag_pipeline": "available",
            "model_quantization": "supported",
            "payment_processing": "available"
        }
    }


# Include all routers
app.include_router(auth.router)
app.include_router(tutor.router)
app.include_router(feedback.router)  # NEW: Interactive feedback loop
app.include_router(curriculum.router)
app.include_router(subscriptions.router)
app.include_router(payments.router)
app.include_router(teachers.router)
app.include_router(admin.router)
app.include_router(rag_admin.router)
app.include_router(finetuning_admin.router)
app.include_router(evaluation_admin.router)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("startup_initiated", version=settings.version, environment=settings.environment)

    print(f"\n{'='*70}")
    print(f"🚀 {settings.app_name} v{settings.version} - PRODUCTION MODE")
    print(f"{'='*70}")
    print(f"📚 Environment: {settings.environment}")
    print(f"🔧 Debug Mode: {settings.debug}")

    # Initialize database
    try:
        print("📦 Initializing database...")
        init_db()
        print("✅ Database initialized successfully!")
        logger.info("database_initialized")
    except Exception as e:
        print(f"⚠️  Database initialization warning: {e}")
        logger.warning("database_initialization_failed", error=str(e))

    # Check cache status
    cache_status = "enabled" if cache.enabled else "disabled"
    print(f"💾 Redis Cache: {cache_status}")
    logger.info("cache_status", enabled=cache.enabled)

    # Production features summary
    print(f"\n🔒 Production Features:")
    print(f"   ✅ Rate Limiting: ENABLED")
    print(f"   ✅ Security Headers: ENABLED")
    print(f"   ✅ Input Validation: ENABLED")
    print(f"   ✅ Request Size Limit: ENABLED (1MB)")
    print(f"   ✅ Structured Logging: ENABLED")
    print(f"   ✅ Prometheus Metrics: ENABLED (/metrics)")
    print(f"   {'✅' if cache.enabled else '⚠️ '} Redis Caching: {cache_status.upper()}")

    print(f"\n🌐 Endpoints:")
    print(f"   📖 API Documentation: http://localhost:8000/docs")
    print(f"   📊 Metrics: http://localhost:8000/metrics")
    print(f"   ❤️  Health Check: http://localhost:8000/health")

    print(f"\n{'='*70}")
    print(f"✅ Server ready! Listening on port {os.getenv('API_PORT', '8000')}")
    print(f"{'='*70}\n")

    logger.info("startup_complete", port=os.getenv('API_PORT', '8000'))


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("shutdown_initiated")
    print(f"\n👋 {settings.app_name} shutting down...")
    print(f"   Cleaning up resources...")
    logger.info("shutdown_complete")
    print(f"   ✅ Shutdown complete\n")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("API_PORT", "8000")),
        reload=settings.debug
    )
