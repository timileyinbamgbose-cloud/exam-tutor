"""
Core configuration for ExamsTutor AI API
Epic 3.1: Offline Capability Development
"""
from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Application
    app_name: str = "ExamsTutor AI API"
    app_version: str = "0.3.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    log_level: str = "INFO"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    api_reload: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://examstutor:password@localhost:5432/examstutor_db"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 3600

    # JWT
    secret_key: str = Field(default="dev-secret-key-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Model Configuration (Epic 3.1)
    model_name: str = "meta-llama/Llama-3-8B-Instruct"
    model_path: str = "./models/"
    quantization_type: Literal["none", "int8", "int4", "gguf", "awq", "gptq"] = "int8"
    use_onnx: bool = False
    device: Literal["cuda", "cpu", "mps"] = "cpu"

    # Offline RAG (Epic 3.1)
    vector_db_type: Literal["qdrant", "chromadb", "faiss"] = "qdrant"
    vector_db_path: str = "./data/vector_db/"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    vector_db_collection: str = "examstutor_curriculum"
    rag_top_k: int = 5

    # Offline Sync (Epic 3.1)
    offline_mode: bool = False
    sync_interval_seconds: int = 300
    sync_batch_size: int = 100
    enable_background_sync: bool = True

    # Performance
    max_batch_size: int = 16
    max_sequence_length: int = 2048
    inference_timeout_seconds: int = 30

    # Monitoring (Epic 3.3)
    enable_metrics: bool = True
    prometheus_port: int = 9090
    enable_tracing: bool = True
    jaeger_endpoint: str = "http://localhost:14268/api/traces"

    # NDPR Compliance
    data_encryption_key: str = Field(default="dev-encryption-key-change-in-production")
    enable_audit_logs: bool = True
    data_retention_days: int = 365

    # Cloud (optional)
    aws_region: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    s3_bucket_name: Optional[str] = None

    # Feature Flags
    enable_offline_mode: bool = True
    enable_quantization: bool = True
    enable_onnx_runtime: bool = True
    enable_distillation: bool = False


# Global settings instance
settings = Settings()
