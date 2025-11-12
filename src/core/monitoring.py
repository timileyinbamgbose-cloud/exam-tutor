"""
Monitoring and Metrics Collection
Epic 3.3: Monitoring & Observability

Provides:
- Prometheus metrics
- Custom metrics for business logic
- Performance tracking
- Model monitoring
"""
from typing import Dict, Any, Optional, Callable
import time
from functools import wraps
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST
)
from src.core.logger import get_logger
from src.core.config import settings

logger = get_logger(__name__)


# Create registry
registry = CollectorRegistry()


# ============================================================================
# API Metrics
# ============================================================================

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=registry,
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0)
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently in progress',
    ['method', 'endpoint'],
    registry=registry
)


# ============================================================================
# RAG Metrics
# ============================================================================

rag_queries_total = Counter(
    'rag_queries_total',
    'Total RAG queries',
    ['subject', 'status'],
    registry=registry
)

rag_retrieval_duration_seconds = Histogram(
    'rag_retrieval_duration_seconds',
    'RAG retrieval duration in seconds',
    ['subject'],
    registry=registry,
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0)
)

rag_context_documents = Histogram(
    'rag_context_documents',
    'Number of context documents retrieved',
    ['subject'],
    registry=registry,
    buckets=(1, 2, 3, 5, 10, 20)
)

rag_generation_duration_seconds = Histogram(
    'rag_generation_duration_seconds',
    'Answer generation duration in seconds',
    ['subject'],
    registry=registry,
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0)
)


# ============================================================================
# Model Metrics
# ============================================================================

model_inference_duration_seconds = Histogram(
    'model_inference_duration_seconds',
    'Model inference duration in seconds',
    ['model_name', 'quantization_type'],
    registry=registry,
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0)
)

model_inference_total = Counter(
    'model_inference_total',
    'Total model inferences',
    ['model_name', 'quantization_type', 'status'],
    registry=registry
)

model_token_count = Histogram(
    'model_token_count',
    'Number of tokens processed',
    ['model_name', 'type'],  # type: input, output
    registry=registry,
    buckets=(10, 50, 100, 250, 500, 1000, 2000, 4000)
)

model_memory_usage_bytes = Gauge(
    'model_memory_usage_bytes',
    'Model memory usage in bytes',
    ['model_name'],
    registry=registry
)


# ============================================================================
# Sync Metrics
# ============================================================================

sync_queue_size = Gauge(
    'sync_queue_size',
    'Number of items in sync queue',
    registry=registry
)

sync_operations_total = Counter(
    'sync_operations_total',
    'Total sync operations',
    ['status'],  # status: success, failed
    registry=registry
)

sync_duration_seconds = Histogram(
    'sync_duration_seconds',
    'Sync operation duration in seconds',
    registry=registry,
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

sync_records_processed = Counter(
    'sync_records_processed',
    'Total records synced',
    ['record_type'],
    registry=registry
)


# ============================================================================
# Vector Store Metrics
# ============================================================================

vector_store_documents_total = Gauge(
    'vector_store_documents_total',
    'Total documents in vector store',
    ['collection'],
    registry=registry
)

vector_store_search_duration_seconds = Histogram(
    'vector_store_search_duration_seconds',
    'Vector store search duration in seconds',
    ['collection'],
    registry=registry,
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0)
)

vector_store_search_total = Counter(
    'vector_store_search_total',
    'Total vector store searches',
    ['collection', 'status'],
    registry=registry
)


# ============================================================================
# System Metrics
# ============================================================================

system_cpu_usage_percent = Gauge(
    'system_cpu_usage_percent',
    'CPU usage percentage',
    registry=registry
)

system_memory_usage_bytes = Gauge(
    'system_memory_usage_bytes',
    'Memory usage in bytes',
    registry=registry
)

system_disk_usage_bytes = Gauge(
    'system_disk_usage_bytes',
    'Disk usage in bytes',
    ['path'],
    registry=registry
)


# ============================================================================
# Business Metrics
# ============================================================================

student_questions_total = Counter(
    'student_questions_total',
    'Total student questions',
    ['subject', 'topic'],
    registry=registry
)

student_sessions_active = Gauge(
    'student_sessions_active',
    'Active student sessions',
    registry=registry
)

student_practice_answers_total = Counter(
    'student_practice_answers_total',
    'Total practice answers submitted',
    ['subject', 'correct'],
    registry=registry
)


# ============================================================================
# Metric Collection Functions
# ============================================================================

class MetricsCollector:
    """Collect and track metrics"""

    def __init__(self):
        self.logger = get_logger(__name__)

    def track_http_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration: float
    ) -> None:
        """Track HTTP request metrics"""
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()

        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

    def track_rag_query(
        self,
        subject: str,
        retrieval_duration: float,
        num_documents: int,
        generation_duration: Optional[float] = None,
        status: str = "success"
    ) -> None:
        """Track RAG query metrics"""
        rag_queries_total.labels(
            subject=subject,
            status=status
        ).inc()

        rag_retrieval_duration_seconds.labels(
            subject=subject
        ).observe(retrieval_duration)

        rag_context_documents.labels(
            subject=subject
        ).observe(num_documents)

        if generation_duration:
            rag_generation_duration_seconds.labels(
                subject=subject
            ).observe(generation_duration)

    def track_model_inference(
        self,
        model_name: str,
        quantization_type: str,
        duration: float,
        input_tokens: int,
        output_tokens: int,
        status: str = "success"
    ) -> None:
        """Track model inference metrics"""
        model_inference_total.labels(
            model_name=model_name,
            quantization_type=quantization_type,
            status=status
        ).inc()

        model_inference_duration_seconds.labels(
            model_name=model_name,
            quantization_type=quantization_type
        ).observe(duration)

        model_token_count.labels(
            model_name=model_name,
            type="input"
        ).observe(input_tokens)

        model_token_count.labels(
            model_name=model_name,
            type="output"
        ).observe(output_tokens)

    def track_sync_operation(
        self,
        duration: float,
        records_count: int,
        record_type: str,
        status: str = "success"
    ) -> None:
        """Track sync operation metrics"""
        sync_operations_total.labels(status=status).inc()
        sync_duration_seconds.observe(duration)

        for _ in range(records_count):
            sync_records_processed.labels(record_type=record_type).inc()

    def update_sync_queue_size(self, size: int) -> None:
        """Update sync queue size"""
        sync_queue_size.set(size)

    def track_vector_search(
        self,
        collection: str,
        duration: float,
        status: str = "success"
    ) -> None:
        """Track vector store search"""
        vector_store_search_total.labels(
            collection=collection,
            status=status
        ).inc()

        vector_store_search_duration_seconds.labels(
            collection=collection
        ).observe(duration)

    def update_vector_store_size(self, collection: str, size: int) -> None:
        """Update vector store document count"""
        vector_store_documents_total.labels(collection=collection).set(size)

    def update_system_metrics(self) -> None:
        """Update system resource metrics"""
        try:
            import psutil

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            system_cpu_usage_percent.set(cpu_percent)

            # Memory usage
            memory = psutil.virtual_memory()
            system_memory_usage_bytes.set(memory.used)

            # Disk usage
            disk = psutil.disk_usage('/')
            system_disk_usage_bytes.labels(path='/').set(disk.used)

        except Exception as e:
            self.logger.error(f"Error updating system metrics: {e}")

    def track_student_activity(
        self,
        subject: str,
        topic: Optional[str] = None,
        correct: Optional[bool] = None
    ) -> None:
        """Track student activity metrics"""
        if topic:
            student_questions_total.labels(
                subject=subject,
                topic=topic
            ).inc()

        if correct is not None:
            student_practice_answers_total.labels(
                subject=subject,
                correct=str(correct)
            ).inc()


# Global metrics collector
metrics_collector = MetricsCollector()


# ============================================================================
# Decorators for Automatic Metrics Collection
# ============================================================================

def track_time(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """Decorator to track function execution time"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # Log performance
                logger.info(
                    f"Function {func.__name__} completed",
                    extra={
                        "duration_seconds": duration,
                        "metric": metric_name,
                        "labels": labels or {}
                    }
                )

                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Function {func.__name__} failed",
                    extra={
                        "duration_seconds": duration,
                        "error": str(e),
                        "metric": metric_name
                    }
                )
                raise
        return wrapper
    return decorator


def track_async_time(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """Decorator to track async function execution time"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                logger.info(
                    f"Async function {func.__name__} completed",
                    extra={
                        "duration_seconds": duration,
                        "metric": metric_name,
                        "labels": labels or {}
                    }
                )

                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Async function {func.__name__} failed",
                    extra={
                        "duration_seconds": duration,
                        "error": str(e),
                        "metric": metric_name
                    }
                )
                raise
        return wrapper
    return decorator


# ============================================================================
# Metrics Endpoint
# ============================================================================

def get_metrics() -> bytes:
    """Get Prometheus metrics in text format"""
    return generate_latest(registry)


def get_metrics_content_type() -> str:
    """Get content type for Prometheus metrics"""
    return CONTENT_TYPE_LATEST
