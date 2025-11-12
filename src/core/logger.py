"""
Logging configuration for ExamsTutor AI API
Structured JSON logging with correlation IDs
"""
import sys
import logging
from typing import Any, Dict
from loguru import logger
from pythonjsonlogger import jsonlogger
from src.core.config import settings


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records"""

    def __init__(self, correlation_id: str = ""):
        super().__init__()
        self.correlation_id = correlation_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = self.correlation_id
        return True


def setup_logging() -> None:
    """Configure structured JSON logging"""

    # Remove default loguru handler
    logger.remove()

    # Add custom handler based on environment
    if settings.environment == "production":
        # JSON logging for production
        logger.add(
            sys.stdout,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
            level=settings.log_level,
            serialize=True,  # JSON output
            backtrace=True,
            diagnose=False,  # Don't expose variables in production
        )
    else:
        # Human-readable logging for development
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
            level=settings.log_level,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

    # Add file logging
    logger.add(
        f"logs/{settings.app_name.replace(' ', '_').lower()}.log",
        rotation="500 MB",
        retention="10 days",
        compression="zip",
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
        serialize=True if settings.environment == "production" else False,
    )

    logger.info(f"Logging configured for {settings.environment} environment")


def get_logger(name: str) -> Any:
    """Get a logger instance with the given name"""
    return logger.bind(name=name)


# Initialize logging
setup_logging()
