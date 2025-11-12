# ExamsTutor AI Tutor API - Production Dockerfile
# Epic 3.4: Kubernetes Deployment & Security
# Multi-stage build for optimized image size

# Stage 1: Builder
FROM python:3.10-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Configure Poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi --no-root --only main

# Stage 2: Runtime
FROM python:3.10-slim

# Set labels for image metadata
LABEL maintainer="support@examstutor.ng"
LABEL version="0.4.0"
LABEL description="ExamsTutor AI Tutor API - Production Image"
LABEL org.opencontainers.image.source="https://github.com/examstutor/ai-api"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_HOME=/app \
    USER_NAME=appuser \
    USER_UID=1000 \
    USER_GID=1000

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g ${USER_GID} ${USER_NAME} && \
    useradd -m -u ${USER_UID} -g ${USER_GID} -s /bin/bash ${USER_NAME}

# Set working directory
WORKDIR ${APP_HOME}

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=${USER_NAME}:${USER_NAME} src/ ${APP_HOME}/src/
COPY --chown=${USER_NAME}:${USER_NAME} config/ ${APP_HOME}/config/
COPY --chown=${USER_NAME}:${USER_NAME} pyproject.toml poetry.lock ./

# Create necessary directories with proper permissions
RUN mkdir -p ${APP_HOME}/data ${APP_HOME}/models ${APP_HOME}/logs && \
    chown -R ${USER_NAME}:${USER_NAME} ${APP_HOME}

# Switch to non-root user
USER ${USER_NAME}

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Run the application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
