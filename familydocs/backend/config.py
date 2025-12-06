"""
FamilyDocs Backend Configuration
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    database_url: str = "postgresql://familydocs:familydocs_dev_password@localhost:5432/familydocs"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # vLLM
    vllm_api_url: str = "http://localhost:8002/v1"
    vllm_model_name: str = "qwen2.5-32b"

    # File Storage
    upload_dir: str = "./uploads"
    pc_sync_root: str = "C:/FamilyDocs"

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8420
    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    # AI Settings
    rag_enabled: bool = True
    lancedb_path: str = "./data/lancedb"
    embedding_model: str = "qwen2.5-32b"

    # Logging
    log_level: str = "INFO"

    # Gmail API (Optional)
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_redirect_uri: str = "http://localhost:8420/api/modules/gmail/callback"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins as list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
