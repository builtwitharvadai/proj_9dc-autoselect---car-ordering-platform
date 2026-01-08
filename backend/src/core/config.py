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
        default="postgresql://postgres:postgres@postgres:5432/autoselect",
        description="PostgreSQL database connection URL",
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://redis:6379/0",
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

    # Docker/Container Configuration
    postgres_host: str = Field(
        default="postgres",
        description="PostgreSQL host for Docker environment",
    )

    postgres_port: int = Field(
        default=5432,
        ge=1,
        le=65535,
        description="PostgreSQL port",
    )

    postgres_db: str = Field(
        default="autoselect",
        description="PostgreSQL database name",
    )

    postgres_user: str = Field(
        default="postgres",
        description="PostgreSQL user",
    )

    postgres_password: str = Field(
        default="postgres",
        description="PostgreSQL password",
    )

    redis_host: str = Field(
        default="redis",
        description="Redis host for Docker environment",
    )

    redis_port: int = Field(
        default=6379,
        ge=1,
        le=65535,
        description="Redis port",
    )

    # Health Check Configuration
    health_check_path: str = Field(
        default="/health",
        description="Health check endpoint path",
    )

    # Elasticsearch Configuration
    elasticsearch_url: str = Field(
        default="http://elasticsearch:9200",
        description="Elasticsearch connection URL",
    )

    elasticsearch_index_name: str = Field(
        default="vehicles",
        description="Elasticsearch index name for vehicle search",
    )

    elasticsearch_enabled: bool = Field(
        default=True,
        description="Enable Elasticsearch search functionality",
    )

    # Stripe Payment Configuration
    stripe_publishable_key: str = Field(
        default="pk_test_default_key",
        description="Stripe publishable API key for client-side integration",
    )

    stripe_secret_key: str = Field(
        default="sk_test_default_key",
        description="Stripe secret API key for server-side operations",
    )

    stripe_webhook_secret: str = Field(
        default="whsec_default_secret",
        description="Stripe webhook signing secret for event verification",
    )

    stripe_enabled: bool = Field(
        default=True,
        description="Enable Stripe payment processing functionality",
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

    @field_validator("elasticsearch_url")
    @classmethod
    def validate_elasticsearch_url(cls, v: str) -> str:
        """
        Validate Elasticsearch URL format.

        Args:
            v: Elasticsearch URL value

        Returns:
            Validated Elasticsearch URL

        Raises:
            ValueError: If Elasticsearch URL format is invalid
        """
        if not v.startswith(("http://", "https://")):
            raise ValueError(
                "Elasticsearch URL must start with 'http://' or 'https://'"
            )
        return v

    @field_validator("stripe_publishable_key")
    @classmethod
    def validate_stripe_publishable_key(cls, v: str, info) -> str:
        """
        Validate Stripe publishable key format.

        Args:
            v: Stripe publishable key value
            info: Validation info context

        Returns:
            Validated Stripe publishable key

        Raises:
            ValueError: If key format is invalid or default key used in production
        """
        environment = info.data.get("environment", "development")
        if environment == "production" and v == "pk_test_default_key":
            raise ValueError(
                "Default Stripe publishable key cannot be used in production. "
                "Set APP_STRIPE_PUBLISHABLE_KEY environment variable."
            )
        if not v.startswith(("pk_test_", "pk_live_")):
            raise ValueError(
                "Stripe publishable key must start with 'pk_test_' or 'pk_live_'"
            )
        return v

    @field_validator("stripe_secret_key")
    @classmethod
    def validate_stripe_secret_key(cls, v: str, info) -> str:
        """
        Validate Stripe secret key format.

        Args:
            v: Stripe secret key value
            info: Validation info context

        Returns:
            Validated Stripe secret key

        Raises:
            ValueError: If key format is invalid or default key used in production
        """
        environment = info.data.get("environment", "development")
        if environment == "production" and v == "sk_test_default_key":
            raise ValueError(
                "Default Stripe secret key cannot be used in production. "
                "Set APP_STRIPE_SECRET_KEY environment variable."
            )
        if not v.startswith(("sk_test_", "sk_live_")):
            raise ValueError(
                "Stripe secret key must start with 'sk_test_' or 'sk_live_'"
            )
        return v

    @field_validator("stripe_webhook_secret")
    @classmethod
    def validate_stripe_webhook_secret(cls, v: str, info) -> str:
        """
        Validate Stripe webhook secret format.

        Args:
            v: Stripe webhook secret value
            info: Validation info context

        Returns:
            Validated Stripe webhook secret

        Raises:
            ValueError: If secret format is invalid or default secret used in production
        """
        environment = info.data.get("environment", "development")
        if environment == "production" and v == "whsec_default_secret":
            raise ValueError(
                "Default Stripe webhook secret cannot be used in production. "
                "Set APP_STRIPE_WEBHOOK_SECRET environment variable."
            )
        if not v.startswith("whsec_"):
            raise ValueError("Stripe webhook secret must start with 'whsec_'")
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

    @property
    def postgres_connection_string(self) -> str:
        """
        Build PostgreSQL connection string from components.

        Returns:
            PostgreSQL connection URL
        """
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_connection_string(self) -> str:
        """
        Build Redis connection string from components.

        Returns:
            Redis connection URL
        """
        return f"redis://{self.redis_host}:{self.redis_port}/0"


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