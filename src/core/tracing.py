"""
Distributed Tracing with OpenTelemetry
Epic 3.3: Monitoring & Observability

Provides:
- Request tracing across services
- Performance profiling
- Error tracking
- Context propagation
"""
from typing import Optional, Dict, Any
from contextlib import contextmanager
import time

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import Status, StatusCode

from src.core.logger import get_logger
from src.core.config import settings

logger = get_logger(__name__)


# ============================================================================
# Tracer Setup
# ============================================================================

def setup_tracing() -> TracerProvider:
    """Setup OpenTelemetry tracing"""

    # Create resource with service information
    resource = Resource.create({
        "service.name": settings.app_name,
        "service.version": settings.app_version,
        "deployment.environment": settings.environment,
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Add console exporter for development
    if settings.environment == "development":
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))

    # Add OTLP exporter for production (Jaeger)
    if settings.enable_tracing and settings.jaeger_endpoint:
        try:
            otlp_exporter = OTLPSpanExporter(
                endpoint=settings.jaeger_endpoint,
                insecure=True  # Use secure=True in production with proper certs
            )
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(f"OTLP exporter configured: {settings.jaeger_endpoint}")
        except Exception as e:
            logger.error(f"Failed to configure OTLP exporter: {e}")

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    logger.info("OpenTelemetry tracing configured")
    return provider


# Initialize tracer
tracer_provider = setup_tracing()
tracer = trace.get_tracer(__name__)


# ============================================================================
# Tracing Utilities
# ============================================================================

@contextmanager
def trace_operation(
    operation_name: str,
    attributes: Optional[Dict[str, Any]] = None,
    record_exception: bool = True
):
    """
    Context manager for tracing operations

    Usage:
        with trace_operation("rag_query", {"subject": "Mathematics"}):
            result = perform_rag_query()
    """
    with tracer.start_as_current_span(operation_name) as span:
        # Add attributes
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))

        try:
            yield span
            span.set_status(Status(StatusCode.OK))

        except Exception as e:
            if record_exception:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
            raise


class TracingContext:
    """Helper class for manual span management"""

    def __init__(self, tracer_instance: Optional[trace.Tracer] = None):
        self.tracer = tracer_instance or tracer

    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> trace.Span:
        """Start a new span"""
        span = self.tracer.start_span(name)

        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))

        return span

    def end_span(
        self,
        span: trace.Span,
        status: StatusCode = StatusCode.OK,
        error: Optional[Exception] = None
    ) -> None:
        """End a span with status"""
        if error:
            span.record_exception(error)
            span.set_status(Status(StatusCode.ERROR, str(error)))
        else:
            span.set_status(Status(status))

        span.end()


# ============================================================================
# Decorators for Automatic Tracing
# ============================================================================

def trace_function(operation_name: Optional[str] = None):
    """
    Decorator to automatically trace function execution

    Usage:
        @trace_function()
        def my_function():
            pass
    """
    def decorator(func):
        from functools import wraps

        @wraps(func)
        def wrapper(*args, **kwargs):
            span_name = operation_name or f"{func.__module__}.{func.__name__}"

            with tracer.start_as_current_span(span_name) as span:
                # Add function metadata
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        return wrapper
    return decorator


def trace_async_function(operation_name: Optional[str] = None):
    """
    Decorator to automatically trace async function execution

    Usage:
        @trace_async_function()
        async def my_async_function():
            pass
    """
    def decorator(func):
        from functools import wraps

        @wraps(func)
        async def wrapper(*args, **kwargs):
            span_name = operation_name or f"{func.__module__}.{func.__name__}"

            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                span.set_attribute("function.async", "true")

                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        return wrapper
    return decorator


# ============================================================================
# RAG-Specific Tracing
# ============================================================================

class RAGTracer:
    """Specialized tracer for RAG operations"""

    def __init__(self):
        self.tracer = tracer

    @contextmanager
    def trace_rag_query(
        self,
        question: str,
        subject: Optional[str] = None,
        top_k: int = 5
    ):
        """Trace complete RAG query with sub-spans"""
        with self.tracer.start_as_current_span("rag.query") as parent_span:
            parent_span.set_attribute("rag.question", question[:100])
            if subject:
                parent_span.set_attribute("rag.subject", subject)
            parent_span.set_attribute("rag.top_k", top_k)

            try:
                yield parent_span
                parent_span.set_status(Status(StatusCode.OK))

            except Exception as e:
                parent_span.record_exception(e)
                parent_span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    @contextmanager
    def trace_retrieval(self, query: str, top_k: int):
        """Trace document retrieval phase"""
        with self.tracer.start_as_current_span("rag.retrieval") as span:
            span.set_attribute("retrieval.query", query[:100])
            span.set_attribute("retrieval.top_k", top_k)

            start_time = time.time()

            try:
                yield span
                duration = time.time() - start_time
                span.set_attribute("retrieval.duration_ms", duration * 1000)
                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    @contextmanager
    def trace_generation(self, context_size: int):
        """Trace answer generation phase"""
        with self.tracer.start_as_current_span("rag.generation") as span:
            span.set_attribute("generation.context_size", context_size)

            start_time = time.time()

            try:
                yield span
                duration = time.time() - start_time
                span.set_attribute("generation.duration_ms", duration * 1000)
                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise


# Global RAG tracer instance
rag_tracer = RAGTracer()


# ============================================================================
# Model Inference Tracing
# ============================================================================

@contextmanager
def trace_model_inference(
    model_name: str,
    quantization_type: str,
    input_length: int
):
    """Trace model inference with detailed metrics"""
    with tracer.start_as_current_span("model.inference") as span:
        span.set_attribute("model.name", model_name)
        span.set_attribute("model.quantization", quantization_type)
        span.set_attribute("model.input_length", input_length)

        start_time = time.time()

        try:
            yield span
            duration = time.time() - start_time
            span.set_attribute("model.inference_time_ms", duration * 1000)
            span.set_status(Status(StatusCode.OK))

        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise


# ============================================================================
# Trace Context Utilities
# ============================================================================

def get_current_trace_id() -> Optional[str]:
    """Get current trace ID for correlation"""
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().trace_id, '032x')
    return None


def get_current_span_id() -> Optional[str]:
    """Get current span ID"""
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().span_id, '016x')
    return None


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """Add event to current span"""
    span = trace.get_current_span()
    if span and span.is_recording():
        span.add_event(name, attributes=attributes or {})
