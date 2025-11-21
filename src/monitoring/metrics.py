"""
Monitoring and Metrics
Prometheus metrics for production monitoring
"""
from prometheus_client import Counter, Histogram, Gauge, Info
from functools import wraps
import time
from typing import Callable


# API Request Metrics
request_count = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status_code']
)

request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint']
)

request_errors = Counter(
    'api_request_errors_total',
    'Total API request errors',
    ['method', 'endpoint', 'error_type']
)

# AI Operation Metrics
ai_questions_total = Counter(
    'ai_questions_total',
    'Total AI questions asked',
    ['subject', 'class_level']
)

ai_response_time = Histogram(
    'ai_response_time_seconds',
    'AI response time in seconds',
    ['subject']
)

ai_confidence = Histogram(
    'ai_confidence_score',
    'AI confidence scores',
    ['subject'],
    buckets=[0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 1.0]
)

ai_cache_hits = Counter(
    'ai_cache_hits_total',
    'Total AI cache hits'
)

ai_cache_misses = Counter(
    'ai_cache_misses_total',
    'Total AI cache misses'
)

# Database Metrics
db_query_count = Counter(
    'db_queries_total',
    'Total database queries',
    ['operation', 'table']
)

db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table']
)

db_connection_errors = Counter(
    'db_connection_errors_total',
    'Total database connection errors'
)

# User Metrics
active_users = Gauge(
    'active_users',
    'Number of currently active users'
)

user_registrations = Counter(
    'user_registrations_total',
    'Total user registrations',
    ['role']
)

user_logins = Counter(
    'user_logins_total',
    'Total user logins',
    ['role']
)

login_failures = Counter(
    'login_failures_total',
    'Total login failures',
    ['reason']
)

# Subscription Metrics
active_subscriptions = Gauge(
    'active_subscriptions',
    'Number of active subscriptions',
    ['tier']
)

subscription_revenue = Gauge(
    'subscription_revenue_total',
    'Total subscription revenue',
    ['tier', 'currency']
)

# Practice Question Metrics
practice_questions_generated = Counter(
    'practice_questions_generated_total',
    'Total practice questions generated',
    ['subject', 'difficulty']
)

practice_questions_answered = Counter(
    'practice_questions_answered_total',
    'Total practice questions answered',
    ['subject', 'correct']
)

# Background Task Metrics
celery_task_count = Counter(
    'celery_tasks_total',
    'Total Celery tasks',
    ['task_name', 'status']
)

celery_task_duration = Histogram(
    'celery_task_duration_seconds',
    'Celery task duration in seconds',
    ['task_name']
)

# System Metrics
app_info = Info(
    'examstutor_app',
    'ExamsTutor application information'
)

# Cache Metrics
cache_operations = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'status']
)

# Rate Limit Metrics
rate_limit_exceeded = Counter(
    'rate_limit_exceeded_total',
    'Total rate limit violations',
    ['endpoint', 'ip']
)


# Decorators for automatic metrics collection
def track_request_metrics(func: Callable) -> Callable:
    """
    Decorator to track request metrics
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time

            # Track metrics (simplified - would need request context)
            request_count.labels(
                method="UNKNOWN",
                endpoint=func.__name__,
                status_code=200
            ).inc()

            request_duration.labels(
                method="UNKNOWN",
                endpoint=func.__name__
            ).observe(duration)

            return result

        except Exception as e:
            duration = time.time() - start_time

            request_errors.labels(
                method="UNKNOWN",
                endpoint=func.__name__,
                error_type=type(e).__name__
            ).inc()

            request_duration.labels(
                method="UNKNOWN",
                endpoint=func.__name__
            ).observe(duration)

            raise

    return wrapper


def track_ai_metrics(subject: str = "unknown"):
    """
    Decorator to track AI operation metrics
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                ai_questions_total.labels(
                    subject=subject,
                    class_level="unknown"
                ).inc()

                ai_response_time.labels(
                    subject=subject
                ).observe(duration)

                return result

            except Exception as e:
                raise

        return wrapper

    return decorator


def track_db_metrics(operation: str, table: str):
    """
    Decorator to track database operation metrics
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                db_query_count.labels(
                    operation=operation,
                    table=table
                ).inc()

                db_query_duration.labels(
                    operation=operation,
                    table=table
                ).observe(duration)

                return result

            except Exception as e:
                db_connection_errors.inc()
                raise

        return wrapper

    return decorator


# Helper functions for manual metrics updates
class MetricsCollector:
    """
    Helper class for collecting metrics
    """

    @staticmethod
    def track_user_registration(role: str):
        """Track user registration"""
        user_registrations.labels(role=role).inc()

    @staticmethod
    def track_user_login(role: str, success: bool, reason: str = None):
        """Track user login"""
        if success:
            user_logins.labels(role=role).inc()
        else:
            login_failures.labels(reason=reason or "unknown").inc()

    @staticmethod
    def track_ai_question(subject: str, class_level: str, response_time: float, confidence: float, cached: bool):
        """Track AI question"""
        ai_questions_total.labels(subject=subject, class_level=class_level).inc()
        ai_response_time.labels(subject=subject).observe(response_time)
        ai_confidence.labels(subject=subject).observe(confidence)

        if cached:
            ai_cache_hits.inc()
        else:
            ai_cache_misses.inc()

    @staticmethod
    def track_practice_generation(subject: str, difficulty: str, num_questions: int):
        """Track practice question generation"""
        practice_questions_generated.labels(subject=subject, difficulty=difficulty).inc(num_questions)

    @staticmethod
    def track_practice_answer(subject: str, correct: bool):
        """Track practice question answer"""
        practice_questions_answered.labels(subject=subject, correct=str(correct).lower()).inc()

    @staticmethod
    def track_cache_operation(operation: str, success: bool):
        """Track cache operation"""
        status = "success" if success else "failure"
        cache_operations.labels(operation=operation, status=status).inc()

    @staticmethod
    def track_rate_limit_exceeded(endpoint: str, ip: str):
        """Track rate limit violation"""
        rate_limit_exceeded.labels(endpoint=endpoint, ip=ip).inc()

    @staticmethod
    def update_active_users(count: int):
        """Update active users gauge"""
        active_users.set(count)

    @staticmethod
    def update_active_subscriptions(tier: str, count: int):
        """Update active subscriptions gauge"""
        active_subscriptions.labels(tier=tier).set(count)


# Initialize app info
app_info.info({
    'version': '0.6.0',
    'app_name': 'ExamsTutor AI API',
    'environment': 'production'
})


# Expose collector
metrics_collector = MetricsCollector()
