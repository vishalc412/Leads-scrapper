"""
Configuration settings for the Leads Scraper application.
Supports local and cloud deployments.
"""

import os
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class Environment(str, Enum):
    """Deployment environment types."""
    LOCAL = "local"
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class AIModel(str, Enum):
    """Supported AI models for lead analysis."""
    ANTHROPIC_SONNET_4 = "claude-sonnet-4-20250514"
    ANTHROPIC_SONNET_4_5 = "claude-sonnet-4-5-20250929"
    OPENAI_GPT4 = "gpt-4-turbo-preview"
    OPENAI_GPT4O = "gpt-4o"
    OPENAI_O1 = "o1-preview"


class ScraperConfig(BaseModel):
    """Configuration for web scrapers."""
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    rate_limit: float = Field(default=1.0, description="Requests per second")
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        description="User agent string"
    )
    proxy_enabled: bool = Field(default=False, description="Enable proxy usage")
    proxy_rotation: bool = Field(default=False, description="Rotate proxies")


class AIConfig(BaseModel):
    """Configuration for AI analysis."""
    model: AIModel = Field(default=AIModel.ANTHROPIC_SONNET_4_5)
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=4096)
    api_key: Optional[str] = Field(default=None)

    def get_api_key(self) -> str:
        """Get API key from config or environment."""
        if self.api_key:
            return self.api_key

        if "anthropic" in self.model.value.lower():
            return os.getenv("ANTHROPIC_API_KEY", "")
        elif "gpt" in self.model.value.lower() or "o1" in self.model.value.lower():
            return os.getenv("OPENAI_API_KEY", "")

        return ""


class StorageConfig(BaseModel):
    """Configuration for data storage."""
    backend: str = Field(default="sqlite", description="Storage backend type")
    connection_string: Optional[str] = Field(default=None)
    cache_enabled: bool = Field(default=True)
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")

    # Local storage
    data_dir: str = Field(default="./data", description="Local data directory")

    # Cloud storage
    s3_bucket: Optional[str] = Field(default=None, description="AWS S3 bucket")
    azure_container: Optional[str] = Field(default=None, description="Azure container")


class APIConfig(BaseModel):
    """Configuration for API backend."""
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    reload: bool = Field(default=False)
    workers: int = Field(default=4)
    log_level: str = Field(default="info")


class AppConfig(BaseModel):
    """Main application configuration."""
    environment: Environment = Field(default=Environment.LOCAL)
    scraper: ScraperConfig = Field(default_factory=ScraperConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    api: APIConfig = Field(default_factory=APIConfig)

    # Job search parameters
    enabled_job_boards: List[str] = Field(
        default=["indeed", "linkedin", "glassdoor", "monster"],
        description="Enabled job boards for scraping"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def load_config(config_file: Optional[str] = None) -> AppConfig:
    """Load configuration from file or environment variables."""
    if config_file and os.path.exists(config_file):
        import json
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        return AppConfig(**config_data)

    # Load from environment variables with defaults
    return AppConfig(
        environment=Environment(os.getenv("ENVIRONMENT", "local")),
        scraper=ScraperConfig(
            max_retries=int(os.getenv("SCRAPER_MAX_RETRIES", "3")),
            timeout=int(os.getenv("SCRAPER_TIMEOUT", "30")),
            rate_limit=float(os.getenv("SCRAPER_RATE_LIMIT", "1.0"))
        ),
        ai=AIConfig(
            model=AIModel(os.getenv("AI_MODEL", AIModel.ANTHROPIC_SONNET_4_5.value)),
            temperature=float(os.getenv("AI_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("AI_MAX_TOKENS", "4096"))
        ),
        storage=StorageConfig(
            backend=os.getenv("STORAGE_BACKEND", "sqlite"),
            data_dir=os.getenv("DATA_DIR", "./data"),
            cache_enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true"
        ),
        api=APIConfig(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            workers=int(os.getenv("API_WORKERS", "4"))
        )
    )


def set_config(config: AppConfig):
    """Set the global configuration instance."""
    global _config
    _config = config
