from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "Enterprise Agent RAG"
    environment: str = "local"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://agent:agent@localhost:5432/agent_rag"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    log_level: str = "INFO"
    json_logs: bool = True
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 120
    security_scan_enabled: bool = True

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket_name: str = "agent-rag"
    s3_region: str = "us-east-1"
    s3_force_path_style: bool = True

    max_upload_size_mb: int = 50
    supported_kb_file_extensions: str = "docx,doc,pdf,md"

    dashscope_api_key: str = ""
    bailian_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    bailian_chat_model: str = "qwen-plus"
    bailian_vision_model: str = "qwen-vl-plus"
    bailian_embedding_model: str = "text-embedding-v4"
    bailian_embedding_dimensions: int = 1024
    rag_top_k: int = 8
    rag_max_context_tokens: int = 3500
    rag_temperature: float = 0.2
    agent_max_iterations: int = 4
    agent_memory_window: int = 12
    agent_tool_result_max_chars: int = 16000
    agent_require_citations: bool = True
    max_chat_attachment_size_mb: int = 20
    supported_chat_file_extensions: str = "docx,doc,pdf,md,txt"
    supported_chat_image_extensions: str = "png,jpg,jpeg,webp"
    chunk_target_tokens: int = 700
    chunk_overlap_tokens: int = 120
    libreoffice_binary: str = "soffice"

    jwt_secret_key: str = Field(default="change-me-in-production", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    backend_cors_origins: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def supported_extensions(self) -> set[str]:
        return {
            extension.strip().lower().lstrip(".")
            for extension in self.supported_kb_file_extensions.split(",")
            if extension.strip()
        }

    @property
    def max_chat_attachment_size_bytes(self) -> int:
        return self.max_chat_attachment_size_mb * 1024 * 1024

    @property
    def supported_chat_file_exts(self) -> set[str]:
        return {
            extension.strip().lower().lstrip(".")
            for extension in self.supported_chat_file_extensions.split(",")
            if extension.strip()
        }

    @property
    def supported_chat_image_exts(self) -> set[str]:
        return {
            extension.strip().lower().lstrip(".")
            for extension in self.supported_chat_image_extensions.split(",")
            if extension.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
