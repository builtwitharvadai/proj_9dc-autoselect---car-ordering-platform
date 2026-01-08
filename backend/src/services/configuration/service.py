"""
Configuration service orchestrating business logic.

This module implements the ConfigurationService class that orchestrates business
rules validation, pricing calculations, and data persistence for vehicle
configurations. Integrates with caching, error handling, and provides comprehensive
logging for all operations.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.cache.redis_client import RedisClient, get_redis_client
from src.database.models.vehicle import Vehicle
from src.database.models.vehicle_option import VehicleOption
from src.database.models.package import Package
from src.database.models.vehicle_configuration import VehicleConfiguration
from src.services.configuration.repository import ConfigurationRepository
from src.services.configuration.business_rules import ConfigurationRulesEngine
from src.services.configuration.pricing_engine import (
    PricingEngine,
    PricingError,
    PricingCalculationError,
)

logger = get_logger(__name__)


class ConfigurationServiceError(Exception):
    """Base exception for configuration service errors."""

    def __init__(self, message: str, **context: Any):
        super().__init__(message)
        self.context = context


class ConfigurationValidationError(ConfigurationServiceError):
    """Exception raised when configuration validation fails."""

    def __init__(self, message: str, errors: list[str], **context: Any):
        super().__init__(message, **context)
        self.errors = errors


class ConfigurationNotFoundError(ConfigurationServiceError):
    """Exception raised when configuration is not found."""

    pass


class ConfigurationService:
    """
    Configuration service orchestrating business logic.

    Provides high-level methods for vehicle configuration management including
    retrieving options, validating configurations, calculating pricing, and
    persisting configurations. Integrates with caching for performance and
    implements comprehensive error handling.

    Attributes:
        session: Database session for queries
        repository: Configuration repository for data access
        rules_engine: Business rules engine for validation
        pricing_engine: Pricing engine for calculations
        redis_client: Redis client for caching (optional)
    """

    # Cache configuration
    CACHE_TTL_SECONDS = 3600  # 1 hour
    CACHE_KEY_PREFIX = "config_service"

    # Configuration expiration
    DEFAULT_EXPIRATION_DAYS = 30

    def __init__(
        self,
        session: AsyncSession,
        redis_client: Optional[RedisClient] = None,
        enable_caching: bool = True,
    ):
        """
        Initialize configuration service.

        Args:
            session: Database session for queries
            redis_client: Redis client for caching (optional)
            enable_caching: Enable caching for performance
        """
        self.session = session
        self.repository = ConfigurationRepository(session)
        self.rules_engine = ConfigurationRulesEngine(session)
        self.pricing_engine = PricingEngine(
            redis_client=redis_client,
            enable_caching=enable_caching,
        )
        self._redis_client = redis_client
        self._enable_caching = enable_caching

        logger.info(
            "Configuration service initialized",
            enable_caching=enable_caching,
        )

    async def _get_redis_client(self) -> Optional[RedisClient]:
        """
        Get Redis client instance.

        Returns:
            Redis client or None if caching disabled
        """
        if not self._enable_caching:
            return None

        if self._redis_client is None:
            try:
                self._redis_client = await get_redis_client()
            except Exception as e:
                logger.warning(
                    "Failed to get Redis client, caching disabled",
                    error=str(e),
                )
                return None

        return self._redis_client

    def _make_cache_key(self, *parts: Any) -> str:
        """
        Generate cache key.

        Args:
            *parts: Key components

        Returns:
            Formatted cache key
        """
        key_parts = [str(part) for part in parts if part is not None]
        return f"{self.CACHE_KEY_PREFIX}:{':'.join(key_parts)}"

    async def _get_cached_data(self, cache_key: str) -> Optional[dict[str, Any]]:
        """
        Get cached data.

        Args:
            cache_key: Cache key

        Returns:
            Cached data or None
        """
        redis = await self._get_redis_client()
        if redis is None:
            return None

        try:
            cached_data = await redis.get_json(cache_key)
            if cached_data:
                logger.debug("Cache hit", cache_key=cache_key)
                return cached_data
        except Exception as e:
            logger.warning(
                "Failed to get cached data",
                cache_key=cache_key,
                error=str(e),
            )

        return None

    async def _set_cached_data(
        self, cache_key: str, data: dict[str, Any]
    ) -> None:
        """
        Cache data.

        Args:
            cache_key: Cache key
            data: Data to cache
        """
        redis = await self._get_redis_client()
        if redis is None:
            return

        try:
            await redis.set_json(
                cache_key, data, ex=self.CACHE_TTL_SECONDS
            )
            logger.debug("Cached data", cache_key=cache_key)
        except Exception as e:
            logger.warning(
                "Failed to cache data",
                cache_key=cache_key,
                error=str(e),
            )

    async def _invalidate_cache(self, pattern: str) -> int:
        """
        Invalidate cache entries matching pattern.

        Args:
            pattern: Cache key pattern

        Returns:
            Number of cache entries invalidated
        """
        redis = await self._get_redis_client()
        if redis is None:
            return 0

        try:
            count = await redis.delete_pattern(pattern)
            logger.info(
                "Invalidated cache entries",
                pattern=pattern,
                count=count,
            )
            return count
        except Exception as e:
            logger.error(
                "Failed to invalidate cache",
                pattern=pattern,
                error=str(e),
            )
            return 0

    async def get_vehicle_options(
        self,
        vehicle_id: uuid.UUID,
        category: Optional[str] = None,
        include_required_only: bool = False,
    ) -> dict[str, Any]:
        """
        Get vehicle options with compatibility rules.

        Args:
            vehicle_id: Vehicle identifier
            category: Optional category filter
            include_required_only: If True, return only required options

        Returns:
            Dictionary with options and metadata

        Raises:
            ConfigurationServiceError: If retrieval fails
        """
        try:
            cache_key = self._make_cache_key(
                "options",
                str(vehicle_id),
                category,
                include_required_only,
            )

            cached_data = await self._get_cached_data(cache_key)
            if cached_data:
                return cached_data

            options = await self.repository.get_vehicle_options(
                vehicle_id=vehicle_id,
                category=category,
                include_required_only=include_required_only,
            )

            packages = await self.repository.get_vehicle_packages(
                vehicle_id=vehicle_id
            )

            result = {
                "vehicle_id": str(vehicle_id),
                "options": [
                    {
                        "id": str(opt.id),
                        "name": opt.name,
                        "description": opt.description,
                        "category": opt.category,
                        "price": float(opt.price),
                        "is_required": opt.is_required,
                        "mutually_exclusive_with": [
                            str(oid) for oid in (opt.mutually_exclusive_with or [])
                        ],
                        "required_options": [
                            str(oid) for oid in (opt.required_options or [])
                        ],
                    }
                    for opt in options
                ],
                "packages": [
                    {
                        "id": str(pkg.id),
                        "name": pkg.name,
                        "description": pkg.description,
                        "price": float(pkg.price),
                        "discount_percentage": float(pkg.discount_percentage),
                        "included_options": [
                            str(oid) for oid in pkg.included_options
                        ],
                        "trim_compatibility": pkg.trim_compatibility,
                        "model_year_compatibility": pkg.model_year_compatibility,
                    }
                    for pkg in packages
                ],
                "metadata": {
                    "total_options": len(options),
                    "total_packages": len(packages),
                    "category": category,
                    "required_only": include_required_only,
                },
            }

            await self._set_cached_data(cache_key, result)

            logger.info(
                "Retrieved vehicle options",
                vehicle_id=str(vehicle_id),
                option_count=len(options),
                package_count=len(packages),
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to get vehicle options",
                vehicle_id=str(vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ConfigurationServiceError(
                "Failed to retrieve vehicle options",
                vehicle_id=str(vehicle_id),
            ) from e

    async def validate_configuration(
        self,
        vehicle_id: uuid.UUID,
        selected_option_ids: list[uuid.UUID],
        selected_package_ids: list[uuid.UUID],
        trim: Optional[str] = None,
        year: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Validate vehicle configuration against business rules.

        Args:
            vehicle_id: Vehicle identifier
            selected_option_ids: List of selected option IDs
            selected_package_ids: List of selected package IDs
            trim: Vehicle trim level
            year: Vehicle model year

        Returns:
            Dictionary with validation results

        Raises:
            ConfigurationServiceError: If validation fails
        """
        try:
            is_valid, errors = await self.rules_engine.validate_configuration(
                vehicle_id=vehicle_id,
                selected_option_ids=selected_option_ids,
                selected_package_ids=selected_package_ids,
                trim=trim,
                year=year,
            )

            result = {
                "vehicle_id": str(vehicle_id),
                "is_valid": is_valid,
                "errors": errors,
                "selected_options": [str(oid) for oid in selected_option_ids],
                "selected_packages": [str(pid) for pid in selected_package_ids],
                "trim": trim,
                "year": year,
                "validated_at": datetime.utcnow().isoformat(),
            }

            logger.info(
                "Validated configuration",
                vehicle_id=str(vehicle_id),
                is_valid=is_valid,
                error_count=len(errors),
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to validate configuration",
                vehicle_id=str(vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ConfigurationServiceError(
                "Failed to validate configuration",
                vehicle_id=str(vehicle_id),
            ) from e

    async def calculate_pricing(
        self,
        vehicle_id: uuid.UUID,
        selected_option_ids: list[uuid.UUID],
        selected_package_ids: list[uuid.UUID],
        region: Optional[str] = None,
        include_tax: bool = True,
        include_destination: bool = True,
    ) -> dict[str, Any]:
        """
        Calculate total pricing for configuration.

        Args:
            vehicle_id: Vehicle identifier
            selected_option_ids: List of selected option IDs
            selected_package_ids: List of selected package IDs
            region: Region code for tax calculation
            include_tax: Include tax in total
            include_destination: Include destination charge in total

        Returns:
            Dictionary with pricing breakdown

        Raises:
            ConfigurationServiceError: If calculation fails
        """
        try:
            from sqlalchemy import select

            stmt = select(Vehicle).where(Vehicle.id == vehicle_id)
            result = await self.session.execute(stmt)
            vehicle = result.scalar_one_or_none()

            if not vehicle:
                raise ConfigurationServiceError(
                    "Vehicle not found",
                    vehicle_id=str(vehicle_id),
                )

            options = await self.repository.get_options_by_ids(
                selected_option_ids
            )

            packages_data = []
            if selected_package_ids:
                packages = await self.repository.get_packages_by_ids(
                    selected_package_ids
                )

                for package in packages:
                    included_options = await self.repository.get_options_by_ids(
                        package.included_options
                    )
                    packages_data.append((package, included_options))

            pricing_result = await self.pricing_engine.calculate_total_price(
                vehicle=vehicle,
                options=options,
                packages=packages_data,
                region=region,
                include_tax=include_tax,
                include_destination=include_destination,
            )

            logger.info(
                "Calculated pricing",
                vehicle_id=str(vehicle_id),
                total=pricing_result["total"],
                option_count=len(options),
                package_count=len(packages_data),
            )

            return pricing_result

        except PricingError:
            raise
        except Exception as e:
            logger.error(
                "Failed to calculate pricing",
                vehicle_id=str(vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ConfigurationServiceError(
                "Failed to calculate pricing",
                vehicle_id=str(vehicle_id),
            ) from e

    async def save_configuration(
        self,
        vehicle_id: uuid.UUID,
        user_id: uuid.UUID,
        selected_option_ids: list[uuid.UUID],
        selected_package_ids: list[uuid.UUID],
        trim: Optional[str] = None,
        year: Optional[int] = None,
        region: Optional[str] = None,
        notes: Optional[str] = None,
        validate_before_save: bool = True,
    ) -> dict[str, Any]:
        """
        Save vehicle configuration.

        Args:
            vehicle_id: Vehicle identifier
            user_id: User identifier
            selected_option_ids: List of selected option IDs
            selected_package_ids: List of selected package IDs
            trim: Vehicle trim level
            year: Vehicle model year
            region: Region code for pricing
            notes: Additional notes
            validate_before_save: Validate before saving

        Returns:
            Dictionary with saved configuration

        Raises:
            ConfigurationValidationError: If validation fails
            ConfigurationServiceError: If save fails
        """
        try:
            if validate_before_save:
                validation_result = await self.validate_configuration(
                    vehicle_id=vehicle_id,
                    selected_option_ids=selected_option_ids,
                    selected_package_ids=selected_package_ids,
                    trim=trim,
                    year=year,
                )

                if not validation_result["is_valid"]:
                    raise ConfigurationValidationError(
                        "Configuration validation failed",
                        errors=validation_result["errors"],
                        vehicle_id=str(vehicle_id),
                    )

            pricing_result = await self.calculate_pricing(
                vehicle_id=vehicle_id,
                selected_option_ids=selected_option_ids,
                selected_package_ids=selected_package_ids,
                region=region,
            )

            configuration = VehicleConfiguration(
                vehicle_id=vehicle_id,
                user_id=user_id,
                selected_options=[str(oid) for oid in selected_option_ids],
                selected_packages=[str(pid) for pid in selected_package_ids],
                total_price=Decimal(str(pricing_result["total"])),
                pricing_breakdown=pricing_result["breakdown"],
                configuration_status="draft",
                is_valid=True,
                trim=trim,
                model_year=year,
                region=region,
                notes=notes,
                expires_at=datetime.utcnow()
                + timedelta(days=self.DEFAULT_EXPIRATION_DAYS),
            )

            saved_config = await self.repository.save_configuration(
                configuration
            )

            await self.session.commit()

            await self._invalidate_cache(
                self._make_cache_key("user_configs", str(user_id), "*")
            )

            result = {
                "id": str(saved_config.id),
                "vehicle_id": str(saved_config.vehicle_id),
                "user_id": str(saved_config.user_id),
                "selected_options": saved_config.selected_options,
                "selected_packages": saved_config.selected_packages,
                "total_price": float(saved_config.total_price),
                "pricing_breakdown": saved_config.pricing_breakdown,
                "status": saved_config.configuration_status,
                "is_valid": saved_config.is_valid,
                "trim": saved_config.trim,
                "model_year": saved_config.model_year,
                "region": saved_config.region,
                "notes": saved_config.notes,
                "created_at": saved_config.created_at.isoformat(),
                "expires_at": (
                    saved_config.expires_at.isoformat()
                    if saved_config.expires_at
                    else None
                ),
            }

            logger.info(
                "Saved configuration",
                configuration_id=str(saved_config.id),
                vehicle_id=str(vehicle_id),
                user_id=str(user_id),
                total_price=float(saved_config.total_price),
            )

            return result

        except ConfigurationValidationError:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Failed to save configuration",
                vehicle_id=str(vehicle_id),
                user_id=str(user_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ConfigurationServiceError(
                "Failed to save configuration",
                vehicle_id=str(vehicle_id),
                user_id=str(user_id),
            ) from e

    async def get_configuration(
        self, configuration_id: uuid.UUID
    ) -> dict[str, Any]:
        """
        Get configuration by ID.

        Args:
            configuration_id: Configuration identifier

        Returns:
            Dictionary with configuration details

        Raises:
            ConfigurationNotFoundError: If configuration not found
            ConfigurationServiceError: If retrieval fails
        """
        try:
            configuration = await self.repository.get_configuration_by_id(
                configuration_id, include_relationships=True
            )

            if not configuration:
                raise ConfigurationNotFoundError(
                    "Configuration not found",
                    configuration_id=str(configuration_id),
                )

            result = {
                "id": str(configuration.id),
                "vehicle_id": str(configuration.vehicle_id),
                "user_id": str(configuration.user_id),
                "selected_options": configuration.selected_options,
                "selected_packages": configuration.selected_packages,
                "total_price": float(configuration.total_price),
                "pricing_breakdown": configuration.pricing_breakdown,
                "status": configuration.configuration_status,
                "is_valid": configuration.is_valid,
                "trim": configuration.trim,
                "model_year": configuration.model_year,
                "region": configuration.region,
                "notes": configuration.notes,
                "created_at": configuration.created_at.isoformat(),
                "updated_at": configuration.updated_at.isoformat(),
                "expires_at": (
                    configuration.expires_at.isoformat()
                    if configuration.expires_at
                    else None
                ),
            }

            logger.info(
                "Retrieved configuration",
                configuration_id=str(configuration_id),
            )

            return result

        except ConfigurationNotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Failed to get configuration",
                configuration_id=str(configuration_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ConfigurationServiceError(
                "Failed to retrieve configuration",
                configuration_id=str(configuration_id),
            ) from e

    async def get_user_configurations(
        self,
        user_id: uuid.UUID,
        vehicle_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Get user configurations with filtering.

        Args:
            user_id: User identifier
            vehicle_id: Optional vehicle filter
            status: Optional status filter
            limit: Maximum results to return
            offset: Number of results to skip

        Returns:
            Dictionary with configurations and metadata

        Raises:
            ConfigurationServiceError: If retrieval fails
        """
        try:
            configurations, total_count = (
                await self.repository.get_user_configurations(
                    user_id=user_id,
                    vehicle_id=vehicle_id,
                    status=status,
                    limit=limit,
                    offset=offset,
                )
            )

            result = {
                "user_id": str(user_id),
                "configurations": [
                    {
                        "id": str(config.id),
                        "vehicle_id": str(config.vehicle_id),
                        "total_price": float(config.total_price),
                        "status": config.configuration_status,
                        "is_valid": config.is_valid,
                        "created_at": config.created_at.isoformat(),
                        "expires_at": (
                            config.expires_at.isoformat()
                            if config.expires_at
                            else None
                        ),
                    }
                    for config in configurations
                ],
                "metadata": {
                    "total_count": total_count,
                    "limit": limit,
                    "offset": offset,
                    "vehicle_id": str(vehicle_id) if vehicle_id else None,
                    "status": status,
                },
            }

            logger.info(
                "Retrieved user configurations",
                user_id=str(user_id),
                count=len(configurations),
                total_count=total_count,
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to get user configurations",
                user_id=str(user_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ConfigurationServiceError(
                "Failed to retrieve user configurations",
                user_id=str(user_id),
            ) from e