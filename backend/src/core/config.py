"""
Application configuration management with environment variables.

This module provides centralized configuration management using Pydantic
BaseSettings for type-safe environment variable handling with validation
and default values.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    All settings can be overridden via environment variables with the
    APP_ prefix (e.g., APP_DATABASE_URL, APP_SECRET_KEY).
    """

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database Configuration
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/autoselect",
        description="PostgreSQL database connection URL",
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching and sessions",
    )

    # Security Configuration
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for JWT token signing and encryption",
        min_length=32,
    )

    # Logging Configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Application logging level",
    )

    # Environment Configuration
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment",
    )

    # API Configuration
    api_v1_prefix: str = Field(
        default="/api/v1",
        description="API version 1 route prefix",
    )

    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )

    # Application Configuration
    app_name: str = Field(
        default="AutoSelect API",
        description="Application name",
    )

    app_version: str = Field(
        default="1.0.0",
        description="Application version",
    )

    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    # Database Pool Configuration
    db_pool_size: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Database connection pool size",
    )

    db_max_overflow: int = Field(
        default=10,
        ge=0,
        le=50,
        description="Maximum overflow connections for database pool",
    )

    # Redis Configuration
    redis_max_connections: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum Redis connection pool size",
    )

    # JWT Configuration
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm",
    )

    jwt_access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        description="JWT access token expiration time in minutes",
    )

    jwt_refresh_token_expire_days: int = Field(
        default=7,
        ge=1,
        description="JWT refresh token expiration time in days",
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """
        Validate secret key requirements.

        Args:
            v: Secret key value
            info: Validation info context

        Returns:
            Validated secret key

        Raises:
            ValueError: If secret key is insecure in production
        """
        environment = info.data.get("environment", "development")
        if environment == "production" and v == "dev-secret-key-change-in-production":
            raise ValueError(
                "Default secret key cannot be used in production environment. "
                "Set APP_SECRET_KEY environment variable."
            )
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """
        Validate database URL format.

        Args:
            v: Database URL value

        Returns:
            Validated database URL

        Raises:
            ValueError: If database URL format is invalid
        """
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError(
                "Database URL must start with 'postgresql://' or "
                "'postgresql+asyncpg://'"
            )
        return v

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """
        Validate Redis URL format.

        Args:
            v: Redis URL value

        Returns:
            Validated Redis URL

        Raises:
            ValueError: If Redis URL format is invalid
        """
        if not v.startswith(("redis://", "rediss://")):
            raise ValueError("Redis URL must start with 'redis://' or 'rediss://'")
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v) -> list[str]:
        """
        Parse CORS origins from string or list.

        Args:
            v: CORS origins value (string or list)

        Returns:
            List of CORS origin URLs
        """
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.environment == "staging"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings instance.

    This function uses lru_cache to ensure settings are loaded only once
    and reused across the application lifecycle.

    Returns:
        Settings: Application settings instance
    """
    return Settings()
```
```