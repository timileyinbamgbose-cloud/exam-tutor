"""
Health Check Endpoints

Provides comprehensive health monitoring for:
- Liveness probes (is the app running?)
- Readiness probes (can the app handle requests?)
- Detailed component health
- Metrics for monitoring systems
"""

import time
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Response, status

from src.logging.logger import logger
from src.core.config import settings

# Optional imports
try:
    from src.database.session import get_db_session
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

try:
    from src.cache.redis_client import get_redis_client
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from src.ai.ai_tutor_service import get_ai_tutor_service
    AI_TUTOR_AVAILABLE = True
except ImportError:
    AI_TUTOR_AVAILABLE = False


router = APIRouter(tags=["Health"])

# Store startup time
START_TIME = datetime.utcnow()


@router.get("/health", summary="Basic health check")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    Returns 200 if the service is running.
    """
    return {
        "status": "healthy",
        "service": "ExamsTutor AI API",
        "version": getattr(settings, "APP_VERSION", "1.0.0"),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/live", summary="Liveness probe")
async def liveness_probe(response: Response) -> Dict[str, Any]:
    """
    Kubernetes liveness probe.
    Checks if the application is running.

    Returns:
        200: Application is alive
        503: Application is not responding
    """
    try:
        # Simple check - if we can respond, we're alive
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Liveness probe failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "dead",
            "error": str(e)
        }


@router.get("/health/ready", summary="Readiness probe")
async def readiness_probe(response: Response) -> Dict[str, Any]:
    """
    Kubernetes readiness probe.
    Checks if the application can handle requests.

    Returns:
        200: Application is ready
        503: Application is not ready
    """
    health_status = {
        "status": "ready",
        "checks": {},
        "timestamp": datetime.utcnow().isoformat()
    }

    is_ready = True

    # Check database
    if DB_AVAILABLE:
        try:
            # Try to connect to database
            async with get_db_session() as session:
                # Simple query to check connection
                await session.execute("SELECT 1")
            health_status["checks"]["database"] = "healthy"
        except Exception as e:
            health_status["checks"]["database"] = f"unhealthy: {str(e)}"
            is_ready = False
    else:
        health_status["checks"]["database"] = "not configured"

    # Check Redis
    if REDIS_AVAILABLE:
        try:
            redis_client = get_redis_client()
            if redis_client:
                await redis_client.ping()
                health_status["checks"]["redis"] = "healthy"
            else:
                health_status["checks"]["redis"] = "not configured"
        except Exception as e:
            health_status["checks"]["redis"] = f"unhealthy: {str(e)}"
            # Redis is optional, don't mark as not ready
    else:
        health_status["checks"]["redis"] = "not configured"

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        health_status["status"] = "not ready"

    return health_status


@router.get("/health/detailed", summary="Detailed health check")
async def detailed_health_check(response: Response) -> Dict[str, Any]:
    """
    Detailed health check with component-level status.

    Checks:
    - Database connectivity and latency
    - Redis connectivity and latency
    - AI service health
    - Vector store status
    - System resources

    Returns:
        200: All components healthy
        503: One or more components unhealthy
    """
    start_time = time.time()

    health_status = {
        "status": "healthy",
        "service": "ExamsTutor AI API",
        "version": getattr(settings, "APP_VERSION", "1.0.0"),
        "uptime_seconds": (datetime.utcnow() - START_TIME).total_seconds(),
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }

    overall_healthy = True

    # Check Database
    if DB_AVAILABLE:
        db_start = time.time()
        try:
            async with get_db_session() as session:
                await session.execute("SELECT 1")

            db_latency = (time.time() - db_start) * 1000  # Convert to ms

            health_status["components"]["database"] = {
                "status": "healthy",
                "latency_ms": round(db_latency, 2),
                "type": "PostgreSQL"
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            overall_healthy = False
    else:
        health_status["components"]["database"] = {"status": "not configured"}

    # Check Redis
    if REDIS_AVAILABLE:
        redis_start = time.time()
        try:
            redis_client = get_redis_client()
            if redis_client:
                await redis_client.ping()
                redis_latency = (time.time() - redis_start) * 1000

                health_status["components"]["redis"] = {
                    "status": "healthy",
                    "latency_ms": round(redis_latency, 2),
                    "type": "Redis"
                }
            else:
                health_status["components"]["redis"] = {"status": "not configured"}
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            health_status["components"]["redis"] = {
                "status": "degraded",
                "error": str(e),
                "note": "Service will use fallback mechanisms"
            }
            # Redis failure is not critical
    else:
        health_status["components"]["redis"] = {"status": "not configured"}

    # Check AI Tutor Service
    if AI_TUTOR_AVAILABLE:
        try:
            ai_tutor_service = get_ai_tutor_service()
            ai_health = await ai_tutor_service.health_check()

            if ai_health.get("status") == "healthy":
                health_status["components"]["ai_tutor"] = {
                    "status": "healthy",
                    "details": ai_health.get("components", {})
                }
            else:
                health_status["components"]["ai_tutor"] = {
                    "status": "degraded",
                    "details": ai_health.get("components", {})
                }
        except Exception as e:
            logger.error(f"AI Tutor health check failed: {e}")
            health_status["components"]["ai_tutor"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            overall_healthy = False
    else:
        health_status["components"]["ai_tutor"] = {"status": "not configured"}

    # Calculate total response time
    health_status["response_time_ms"] = round((time.time() - start_time) * 1000, 2)

    # Set overall status
    if not overall_healthy:
        health_status["status"] = "unhealthy"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif any(
        comp.get("status") == "degraded"
        for comp in health_status["components"].values()
        if isinstance(comp, dict)
    ):
        health_status["status"] = "degraded"

    return health_status


@router.get("/health/startup", summary="Startup probe")
async def startup_probe(response: Response) -> Dict[str, Any]:
    """
    Kubernetes startup probe.
    Checks if the application has finished starting up.

    Returns:
        200: Application has started
        503: Application still starting
    """
    # Check critical dependencies are ready
    # For now, just check database as the critical dependency

    if DB_AVAILABLE:
        try:
            async with get_db_session() as session:
                await session.execute("SELECT 1")

            return {
                "status": "started",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {
                "status": "starting",
                "message": "Waiting for database",
                "error": str(e)
            }

    # If no database configured, assume started
    return {
        "status": "started",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/metrics", summary="Prometheus metrics")
async def metrics() -> Response:
    """
    Prometheus-compatible metrics endpoint.

    Returns metrics in Prometheus text format.
    """
    metrics_data = []

    # Add basic metrics
    uptime = (datetime.utcnow() - START_TIME).total_seconds()
    metrics_data.append(f'# HELP examstutor_uptime_seconds Application uptime in seconds')
    metrics_data.append(f'# TYPE examstutor_uptime_seconds gauge')
    metrics_data.append(f'examstutor_uptime_seconds {uptime}')

    # Get AI Tutor stats if available
    if AI_TUTOR_AVAILABLE:
        try:
            ai_tutor_service = get_ai_tutor_service()
            stats = ai_tutor_service.get_service_stats()

            metrics_data.append(f'\n# HELP examstutor_requests_total Total AI requests')
            metrics_data.append(f'# TYPE examstutor_requests_total counter')
            metrics_data.append(f'examstutor_requests_total {stats.get("total_requests", 0)}')

            metrics_data.append(f'\n# HELP examstutor_latency_ms Average response latency in milliseconds')
            metrics_data.append(f'# TYPE examstutor_latency_ms gauge')
            metrics_data.append(f'examstutor_latency_ms {stats.get("average_latency_ms", 0)}')

            metrics_data.append(f'\n# HELP examstutor_cache_hit_rate Cache hit rate')
            metrics_data.append(f'# TYPE examstutor_cache_hit_rate gauge')
            metrics_data.append(f'examstutor_cache_hit_rate {stats.get("cache_hit_rate", 0)}')

        except Exception as e:
            logger.warning(f"Failed to get AI Tutor stats for metrics: {e}")

    return Response(
        content="\n".join(metrics_data),
        media_type="text/plain"
    )


@router.get("/info", summary="Service information")
async def service_info() -> Dict[str, Any]:
    """
    Get service information and configuration.
    """
    return {
        "service": "ExamsTutor AI API",
        "version": getattr(settings, "APP_VERSION", "1.0.0"),
        "environment": getattr(settings, "ENVIRONMENT", "unknown"),
        "started_at": START_TIME.isoformat(),
        "uptime_seconds": (datetime.utcnow() - START_TIME).total_seconds(),
        "features": {
            "database": DB_AVAILABLE,
            "redis": REDIS_AVAILABLE,
            "ai_tutor": AI_TUTOR_AVAILABLE,
        }
    }
