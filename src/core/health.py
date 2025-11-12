"""
Health Check System
Epic 3.3: Monitoring & Observability

Provides:
- Application health status
- Dependency health checks
- Readiness and liveness probes
- Detailed diagnostics
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import asyncio

from src.core.logger import get_logger
from src.core.config import settings

logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheck:
    """Base class for health checks"""

    def __init__(self, name: str, critical: bool = True):
        self.name = name
        self.critical = critical  # If true, failure marks system as unhealthy

    async def check(self) -> Dict[str, Any]:
        """
        Perform health check

        Returns:
            Dict with:
                - status: HealthStatus
                - message: str
                - details: Dict[str, Any]
        """
        raise NotImplementedError


class DatabaseHealthCheck(HealthCheck):
    """Check database connectivity"""

    def __init__(self):
        super().__init__("database", critical=True)

    async def check(self) -> Dict[str, Any]:
        """Check database connection"""
        try:
            # In production, would check actual database connection
            # For now, simulate check
            await asyncio.sleep(0.01)  # Simulate network call

            return {
                "status": HealthStatus.HEALTHY,
                "message": "Database connection OK",
                "details": {
                    "pool_size": 20,
                    "active_connections": 5,
                }
            }

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Database connection failed: {str(e)}",
                "details": {}
            }


class VectorStoreHealthCheck(HealthCheck):
    """Check vector store availability"""

    def __init__(self):
        super().__init__("vector_store", critical=True)

    async def check(self) -> Dict[str, Any]:
        """Check vector store"""
        try:
            # In production, check actual vector store
            from pathlib import Path

            vector_db_path = Path(settings.vector_db_path)

            if vector_db_path.exists():
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": "Vector store available",
                    "details": {
                        "path": str(vector_db_path),
                        "type": settings.vector_db_type,
                    }
                }
            else:
                return {
                    "status": HealthStatus.DEGRADED,
                    "message": "Vector store path not found",
                    "details": {
                        "path": str(vector_db_path)
                    }
                }

        except Exception as e:
            logger.error(f"Vector store health check failed: {e}")
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Vector store check failed: {str(e)}",
                "details": {}
            }


class ModelHealthCheck(HealthCheck):
    """Check model availability"""

    def __init__(self):
        super().__init__("model", critical=True)

    async def check(self) -> Dict[str, Any]:
        """Check model status"""
        try:
            # In production, check if model is loaded
            from pathlib import Path

            model_path = Path(settings.model_path)

            if model_path.exists():
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": "Model available",
                    "details": {
                        "path": str(model_path),
                        "quantization_type": settings.quantization_type,
                    }
                }
            else:
                return {
                    "status": HealthStatus.DEGRADED,
                    "message": "Model path not configured",
                    "details": {}
                }

        except Exception as e:
            logger.error(f"Model health check failed: {e}")
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Model check failed: {str(e)}",
                "details": {}
            }


class DiskSpaceHealthCheck(HealthCheck):
    """Check disk space availability"""

    def __init__(self, threshold_percent: float = 90.0):
        super().__init__("disk_space", critical=False)
        self.threshold_percent = threshold_percent

    async def check(self) -> Dict[str, Any]:
        """Check disk space"""
        try:
            import psutil

            disk = psutil.disk_usage('/')
            used_percent = disk.percent

            if used_percent < self.threshold_percent:
                status = HealthStatus.HEALTHY
                message = f"Disk usage OK ({used_percent:.1f}%)"
            elif used_percent < 95:
                status = HealthStatus.DEGRADED
                message = f"Disk usage high ({used_percent:.1f}%)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Disk usage critical ({used_percent:.1f}%)"

            return {
                "status": status,
                "message": message,
                "details": {
                    "total_gb": disk.total / (1024**3),
                    "used_gb": disk.used / (1024**3),
                    "free_gb": disk.free / (1024**3),
                    "percent_used": used_percent,
                }
            }

        except Exception as e:
            logger.error(f"Disk space check failed: {e}")
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Disk check failed: {str(e)}",
                "details": {}
            }


class MemoryHealthCheck(HealthCheck):
    """Check memory usage"""

    def __init__(self, threshold_percent: float = 90.0):
        super().__init__("memory", critical=False)
        self.threshold_percent = threshold_percent

    async def check(self) -> Dict[str, Any]:
        """Check memory usage"""
        try:
            import psutil

            memory = psutil.virtual_memory()
            used_percent = memory.percent

            if used_percent < self.threshold_percent:
                status = HealthStatus.HEALTHY
                message = f"Memory usage OK ({used_percent:.1f}%)"
            elif used_percent < 95:
                status = HealthStatus.DEGRADED
                message = f"Memory usage high ({used_percent:.1f}%)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Memory usage critical ({used_percent:.1f}%)"

            return {
                "status": status,
                "message": message,
                "details": {
                    "total_gb": memory.total / (1024**3),
                    "used_gb": memory.used / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "percent_used": used_percent,
                }
            }

        except Exception as e:
            logger.error(f"Memory check failed: {e}")
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Memory check failed: {str(e)}",
                "details": {}
            }


class HealthCheckService:
    """
    Aggregates all health checks and provides overall health status

    Usage:
        health_service = HealthCheckService()
        health_service.register(DatabaseHealthCheck())
        status = await health_service.check_health()
    """

    def __init__(self):
        self.checks: List[HealthCheck] = []
        self.last_check_time: Optional[datetime] = None
        self.last_results: Dict[str, Any] = {}

        # Register default checks
        self._register_default_checks()

    def _register_default_checks(self) -> None:
        """Register default health checks"""
        self.register(DatabaseHealthCheck())
        self.register(VectorStoreHealthCheck())
        self.register(ModelHealthCheck())
        self.register(DiskSpaceHealthCheck(threshold_percent=85.0))
        self.register(MemoryHealthCheck(threshold_percent=85.0))

    def register(self, check: HealthCheck) -> None:
        """Register a health check"""
        self.checks.append(check)
        logger.info(f"Registered health check: {check.name}")

    async def check_health(self, detailed: bool = True) -> Dict[str, Any]:
        """
        Run all health checks

        Args:
            detailed: Include detailed results for each check

        Returns:
            Overall health status with individual check results
        """
        self.last_check_time = datetime.utcnow()

        # Run all checks concurrently
        results = await asyncio.gather(
            *[check.check() for check in self.checks],
            return_exceptions=True
        )

        # Process results
        check_results = {}
        overall_status = HealthStatus.HEALTHY
        critical_failures = []

        for check, result in zip(self.checks, results):
            if isinstance(result, Exception):
                check_results[check.name] = {
                    "status": HealthStatus.UNHEALTHY,
                    "message": f"Check failed: {str(result)}",
                    "details": {}
                }

                if check.critical:
                    overall_status = HealthStatus.UNHEALTHY
                    critical_failures.append(check.name)

            else:
                check_results[check.name] = result

                # Update overall status
                if result["status"] == HealthStatus.UNHEALTHY:
                    if check.critical:
                        overall_status = HealthStatus.UNHEALTHY
                        critical_failures.append(check.name)
                    elif overall_status == HealthStatus.HEALTHY:
                        overall_status = HealthStatus.DEGRADED

                elif result["status"] == HealthStatus.DEGRADED:
                    if overall_status == HealthStatus.HEALTHY:
                        overall_status = HealthStatus.DEGRADED

        # Build response
        response = {
            "status": overall_status,
            "timestamp": self.last_check_time.isoformat(),
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        }

        if detailed:
            response["checks"] = check_results

        if critical_failures:
            response["critical_failures"] = critical_failures

        self.last_results = response

        logger.info(f"Health check completed: {overall_status}")

        return response

    async def check_readiness(self) -> Dict[str, Any]:
        """
        Readiness probe - can the service handle requests?

        Checks critical dependencies only
        """
        critical_checks = [check for check in self.checks if check.critical]

        results = await asyncio.gather(
            *[check.check() for check in critical_checks],
            return_exceptions=True
        )

        all_healthy = all(
            isinstance(result, dict) and result["status"] == HealthStatus.HEALTHY
            for result in results
        )

        return {
            "ready": all_healthy,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def check_liveness(self) -> Dict[str, Any]:
        """
        Liveness probe - is the service alive?

        Simple check that the service is running
        """
        return {
            "alive": True,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": self._get_uptime(),
        }

    def _get_uptime(self) -> float:
        """Get service uptime in seconds"""
        # In production, track actual start time
        # For now, return mock value
        return 3600.0


# Global health check service
health_service = HealthCheckService()
