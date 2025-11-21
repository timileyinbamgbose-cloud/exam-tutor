"""
Structured Logging Configuration
Production-grade logging with rotation and structured output
"""
import structlog
import logging
import sys
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Any


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Setup structured logging with file rotation

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        max_bytes: Maximum size of each log file before rotation
        backup_count: Number of backup files to keep
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Configure standard logging
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_path / "examstutor.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(numeric_level)

    # Error file handler (errors only)
    error_handler = RotatingFileHandler(
        log_path / "examstutor_errors.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    error_handler.setLevel(logging.ERROR)

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format="%(message)s",
        handlers=[console_handler, file_handler, error_handler]
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if os.getenv("LOG_FORMAT") == "json" else structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "examstutor") -> Any:
    """
    Get structured logger instance

    Args:
        name: Logger name

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


# Request logging middleware
class RequestLogger:
    """
    Log all API requests with structured data
    """

    def __init__(self):
        self.logger = get_logger("requests")

    async def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: str = None,
        error: str = None
    ):
        """
        Log API request with structured data
        """
        log_data = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
        }

        if user_id:
            log_data["user_id"] = user_id

        if error:
            log_data["error"] = error

        # Log at appropriate level
        if status_code >= 500:
            self.logger.error("request_error", **log_data)
        elif status_code >= 400:
            self.logger.warning("request_client_error", **log_data)
        else:
            self.logger.info("request_success", **log_data)


# AI operation logger
class AILogger:
    """
    Log AI operations with metrics
    """

    def __init__(self):
        self.logger = get_logger("ai")

    async def log_question_answer(
        self,
        user_id: str,
        subject: str,
        question_length: int,
        answer_length: int,
        response_time_ms: float,
        confidence: float,
        cached: bool = False,
        error: str = None
    ):
        """
        Log AI question answering operation
        """
        log_data = {
            "operation": "question_answer",
            "user_id": user_id,
            "subject": subject,
            "question_length": question_length,
            "answer_length": answer_length,
            "response_time_ms": round(response_time_ms, 2),
            "confidence": confidence,
            "cached": cached,
        }

        if error:
            log_data["error"] = error
            self.logger.error("ai_error", **log_data)
        else:
            self.logger.info("ai_success", **log_data)

    async def log_practice_generation(
        self,
        user_id: str,
        subject: str,
        num_questions: int,
        difficulty: str,
        generation_time_ms: float,
        error: str = None
    ):
        """
        Log practice question generation
        """
        log_data = {
            "operation": "practice_generation",
            "user_id": user_id,
            "subject": subject,
            "num_questions": num_questions,
            "difficulty": difficulty,
            "generation_time_ms": round(generation_time_ms, 2),
        }

        if error:
            log_data["error"] = error
            self.logger.error("ai_error", **log_data)
        else:
            self.logger.info("ai_success", **log_data)


# Database operation logger
class DatabaseLogger:
    """
    Log database operations
    """

    def __init__(self):
        self.logger = get_logger("database")

    async def log_query(
        self,
        operation: str,
        table: str,
        duration_ms: float,
        rows_affected: int = 0,
        error: str = None
    ):
        """
        Log database query
        """
        log_data = {
            "operation": operation,
            "table": table,
            "duration_ms": round(duration_ms, 2),
            "rows_affected": rows_affected,
        }

        if error:
            log_data["error"] = error
            self.logger.error("db_error", **log_data)
        else:
            self.logger.debug("db_query", **log_data)


# Security event logger
class SecurityLogger:
    """
    Log security events
    """

    def __init__(self):
        self.logger = get_logger("security")

    async def log_login_attempt(
        self,
        email: str,
        success: bool,
        ip_address: str,
        reason: str = None
    ):
        """
        Log login attempt
        """
        log_data = {
            "event": "login_attempt",
            "email": email,
            "success": success,
            "ip_address": ip_address,
        }

        if reason:
            log_data["reason"] = reason

        if success:
            self.logger.info("login_success", **log_data)
        else:
            self.logger.warning("login_failed", **log_data)

    async def log_rate_limit_exceeded(
        self,
        endpoint: str,
        ip_address: str,
        limit: str
    ):
        """
        Log rate limit exceeded
        """
        self.logger.warning(
            "rate_limit_exceeded",
            endpoint=endpoint,
            ip_address=ip_address,
            limit=limit
        )


# Global logger instances
request_logger = RequestLogger()
ai_logger = AILogger()
db_logger = DatabaseLogger()
security_logger = SecurityLogger()
