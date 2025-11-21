"""
Security Hardening Middleware
Implements security best practices for production
"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import re
import os


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Allow CDN resources for Swagger UI and ReDoc
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https://fastapi.tiangolo.com"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Validate and sanitize request inputs
    """

    # Common injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\bOR\b.*?=.*?|\bAND\b.*?=.*?)",
        r"(UNION.*SELECT|INSERT.*INTO|DELETE.*FROM|DROP.*TABLE|UPDATE.*SET)",
        r"(--|#|;|\*|xp_|sp_)",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
    ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip validation for certain paths
        skip_paths = ["/docs", "/redoc", "/openapi.json", "/health"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)

        # Validate query parameters
        for key, value in request.query_params.items():
            if self._contains_malicious_pattern(str(value)):
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "invalid_input",
                        "message": "Potentially malicious input detected",
                        "parameter": key
                    }
                )

        # Validate path parameters (basic check)
        if self._contains_malicious_pattern(request.url.path):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_input",
                    "message": "Invalid path parameter"
                }
            )

        return await call_next(request)

    def _contains_malicious_pattern(self, value: str) -> bool:
        """
        Check if value contains malicious patterns
        """
        # Check SQL injection patterns
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True

        # Check XSS patterns
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True

        return False


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """
    Enhanced CORS security
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Only allow configured origins in production
        allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")

        origin = request.headers.get("origin")
        if origin:
            if "*" in allowed_origins or origin in allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
            else:
                # Block unauthorized origin
                if request.method == "OPTIONS":
                    return JSONResponse(
                        status_code=403,
                        content={"error": "forbidden", "message": "Origin not allowed"}
                    )

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Limit request body size to prevent DoS
    """

    def __init__(self, app, max_request_size: int = 1048576):  # 1MB default
        super().__init__(app)
        self.max_request_size = max_request_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "payload_too_large",
                    "message": f"Request body exceeds maximum size of {self.max_request_size} bytes",
                    "max_size": self.max_request_size
                }
            )

        return await call_next(request)


class IPBlacklistMiddleware(BaseHTTPMiddleware):
    """
    Block requests from blacklisted IPs
    """

    def __init__(self, app):
        super().__init__(app)
        # Load blacklisted IPs from environment or file
        blacklist_str = os.getenv("IP_BLACKLIST", "")
        self.blacklisted_ips = set(blacklist_str.split(",")) if blacklist_str else set()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get client IP
        client_ip = request.client.host if request.client else None

        if client_ip in self.blacklisted_ips:
            return JSONResponse(
                status_code=403,
                content={
                    "error": "forbidden",
                    "message": "Access denied"
                }
            )

        return await call_next(request)


# Password validation
class PasswordValidator:
    """
    Validate password strength
    """

    @staticmethod
    def validate(password: str) -> tuple[bool, str]:
        """
        Validate password meets security requirements

        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"

        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"

        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"

        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit"

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain at least one special character"

        # Check for common passwords
        common_passwords = ["password", "12345678", "password123", "admin123"]
        if password.lower() in common_passwords:
            return False, "Password is too common"

        return True, ""


# Email validation
class EmailValidator:
    """
    Validate email addresses
    """

    EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )

    @staticmethod
    def validate(email: str) -> bool:
        """
        Validate email format
        """
        return bool(EmailValidator.EMAIL_PATTERN.match(email))


# Input sanitization
class InputSanitizer:
    """
    Sanitize user inputs
    """

    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """
        Sanitize string input
        """
        # Trim whitespace
        value = value.strip()

        # Limit length
        value = value[:max_length]

        # Remove null bytes
        value = value.replace("\x00", "")

        # Remove control characters (except newlines and tabs)
        value = "".join(char for char in value if ord(char) >= 32 or char in ["\n", "\t"])

        return value

    @staticmethod
    def sanitize_html(value: str) -> str:
        """
        Strip HTML tags from input
        """
        # Remove HTML tags
        value = re.sub(r"<[^>]+>", "", value)
        return value
