"""
Configuration management for the OMI-to-Notion Semantic Intelligence Layer.

Uses Pydantic Settings for type-safe configuration with environment variable support.
"""

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class ProcessingMode(str, Enum):
    """Processing mode for transcripts."""

    REALTIME = "realtime"
    BATCH = "batch"


class LogLevel(str, Enum):
    """Logging level."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class OMISettings(BaseSettings):
    """OMI API configuration."""

    model_config = SettingsConfigDict(env_prefix="OMI_")

    api_key: str = Field(default="", description="OMI API key")
    api_url: str = Field(
        default="https://api.omi.me/v1", description="OMI API base URL"
    )
    webhook_secret: str = Field(default="", description="Webhook verification secret")


class NotionSettings(BaseSettings):
    """Notion API configuration."""

    model_config = SettingsConfigDict(env_prefix="NOTION_")

    api_key: str = Field(default="", description="Notion integration token")
    database_id: str = Field(default="", description="Target database ID")
    version: str = Field(default="2022-06-28", description="Notion API version")


class ProcessingSettings(BaseSettings):
    """Processing pipeline configuration."""

    min_relevance_score: float = Field(
        default=5.0,
        ge=0.0,
        le=10.0,
        description="Minimum relevance score for syncing",
    )
    min_confidence_threshold: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for classifications",
    )
    batch_size: int = Field(
        default=10, ge=1, le=100, description="Batch processing size"
    )
    processing_mode: ProcessingMode = Field(
        default=ProcessingMode.REALTIME, description="Processing mode"
    )
    max_transcript_length: int = Field(
        default=50000, ge=100, description="Maximum transcript length in characters"
    )


class AISettings(BaseSettings):
    """AI/ML service configuration."""

    openai_api_key: str = Field(default="", description="OpenAI API key")
    huggingface_token: str = Field(default="", description="HuggingFace token")
    use_local_models: bool = Field(
        default=True, description="Use local models instead of API"
    )
    spacy_model: str = Field(default="en_core_web_lg", description="SpaCy model name")


class ServerSettings(BaseSettings):
    """Server configuration for webhook handling."""

    model_config = SettingsConfigDict(env_prefix="SERVER_")

    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(env_prefix="LOG_")

    level: LogLevel = Field(default=LogLevel.INFO, description="Log level")
    dir: Path = Field(default=Path("./logs"), description="Log directory")
    json_format: bool = Field(default=False, description="Use JSON log format")

    @field_validator("dir", mode="before")
    @classmethod
    def ensure_path(cls, v: str | Path) -> Path:
        """Ensure log directory is a Path object."""
        return Path(v) if isinstance(v, str) else v


class Settings(BaseSettings):
    """
    Main application settings.

    Aggregates all configuration sections and provides a unified interface.
    Configuration is loaded from environment variables and .env files.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Environment = Field(
        default=Environment.DEVELOPMENT, description="Application environment"
    )

    # Component settings
    omi: OMISettings = Field(default_factory=OMISettings)
    notion: NotionSettings = Field(default_factory=NotionSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    ai: AISettings = Field(default_factory=AISettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    # Direct access fields (loaded from env)
    omi_api_key: str = Field(default="")
    omi_api_url: str = Field(default="https://api.omi.me/v1")
    omi_webhook_secret: str = Field(default="")
    notion_api_key: str = Field(default="")
    notion_database_id: str = Field(default="")
    notion_version: str = Field(default="2022-06-28")
    min_relevance_score: float = Field(default=5.0)
    min_confidence_threshold: float = Field(default=0.65)
    batch_size: int = Field(default=10)
    processing_mode: str = Field(default="realtime")
    max_transcript_length: int = Field(default=50000)
    openai_api_key: str = Field(default="")
    huggingface_token: str = Field(default="")
    use_local_models: bool = Field(default=True)
    spacy_model: str = Field(default="en_core_web_lg")
    server_host: str = Field(default="0.0.0.0")
    server_port: int = Field(default=8000)
    log_level: str = Field(default="INFO")
    log_dir: str = Field(default="./logs")
    log_json_format: bool = Field(default=False)

    def model_post_init(self, __context) -> None:
        """Sync nested settings with flat environment variables."""
        from datetime import timezone  # Import here or at top of file
        # OMI settings
        self.omi = OMISettings(
            api_key=self.omi_api_key or self.omi.api_key,
            api_url=self.omi_api_url or self.omi.api_url,
            webhook_secret=self.omi_webhook_secret or self.omi.webhook_secret,
        )

        # Notion settings
        self.notion = NotionSettings(
            api_key=self.notion_api_key or self.notion.api_key,
            database_id=self.notion_database_id or self.notion.database_id,
            version=self.notion_version or self.notion.version,
        )

        # Processing settings
        self.processing = ProcessingSettings(
            min_relevance_score=self.min_relevance_score,
            min_confidence_threshold=self.min_confidence_threshold,
            batch_size=self.batch_size,
            processing_mode=ProcessingMode(self.processing_mode),
            max_transcript_length=self.max_transcript_length,
        )

        # AI settings
        self.ai = AISettings(
            openai_api_key=self.openai_api_key,
            huggingface_token=self.huggingface_token,
            use_local_models=self.use_local_models,
            spacy_model=self.spacy_model,
        )

        # Server settings
        self.server = ServerSettings(
            host=self.server_host,
            port=self.server_port,
        )

        # Logging settings
        self.logging = LoggingSettings(
            level=LogLevel(self.log_level.upper()),
            dir=Path(self.log_dir),
            json_format=self.log_json_format,
        )

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION

    def validate_required(self) -> list[str]:
        """
        Validate that required configuration is present.

        Returns:
            List of missing required configuration keys.
        """
        missing = []

        if not self.omi.api_key:
            missing.append("OMI_API_KEY")
        if not self.notion.api_key:
            missing.append("NOTION_API_KEY")
        if not self.notion.database_id:
            missing.append("NOTION_DATABASE_ID")

        return missing


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Singleton Settings instance loaded from environment.
    """
    return Settings()


def reload_settings() -> Settings:
    """
    Reload settings, clearing the cache.

    Returns:
        Fresh Settings instance.
    """
    get_settings.cache_clear()
    return get_settings()
