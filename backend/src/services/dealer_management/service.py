"""
Dealer management service for configuration operations.

This module implements the DealerManagementService for managing dealer-specific
option and package configurations, including availability settings, custom pricing,
regional restrictions, and bulk operations with comprehensive validation and audit logging.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.models.dealer_configuration import (
    DealerOptionConfig,
    DealerPackageConfig,
)
from src.database.models.vehicle_option import VehicleOption
from src.database.models.package import Package

logger = get_logger(__name__)


class DealerManagementError(Exception):
    """Base exception for dealer management operations."""

    def __init__(self, message: str, code: str = "DEALER_ERROR", **context: Any):
        super().__init__(message)
        self.code = code
        self.context = context


class DealerConfigurationNotFoundError(DealerManagementError):
    """Raised when dealer configuration is not found."""

    def __init__(self, config_id: uuid.UUID, **context: Any):
        super().__init__(
            f"Dealer configuration not found: {config_id}",
            code="CONFIG_NOT_FOUND",
            config_id=str(config_id),
            **context,
        )


class DealerValidationError(DealerManagementError):
    """Raised when dealer configuration validation fails."""

    def __init__(self, message: str, **context: Any):
        super().__init__(message, code="VALIDATION_ERROR", **context)


class DealerManagementService:
    """
    Service for dealer configuration management operations.

    Provides methods for managing dealer-specific option and package configurations,
    including availability settings, custom pricing, regional restrictions, and
    bulk operations with validation and audit logging.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize dealer management service.

        Args:
            db: Async database session
        """
        self.db = db
        logger.info("DealerManagementService initialized")

    async def create_option_config(
        self,
        dealer_id: uuid.UUID,
        option_id: uuid.UUID,
        is_available: bool = True,
        custom_price: Optional[Decimal] = None,
        effective_from: Optional[datetime] = None,
        effective_to: Optional[datetime] = None,
        region: Optional[str] = None,
    ) -> DealerOptionConfig:
        """
        Create dealer option configuration.

        Args:
            dealer_id: Dealer identifier
            option_id: Vehicle option identifier
            is_available: Availability status
            custom_price: Custom price override
            effective_from: Start date for validity
            effective_to: End date for validity
            region: Geographic region restriction

        Returns:
            Created dealer option configuration

        Raises:
            DealerValidationError: If validation fails
            DealerManagementError: If creation fails
        """
        try:
            # Validate option exists
            option_stmt = select(VehicleOption).where(VehicleOption.id == option_id)
            option_result = await self.db.execute(option_stmt)
            option = option_result.scalar_one_or_none()

            if option is None:
                raise DealerValidationError(
                    f"Vehicle option not found: {option_id}",
                    option_id=str(option_id),
                )

            # Validate dates
            if effective_to is not None and effective_from is not None:
                if effective_to <= effective_from:
                    raise DealerValidationError(
                        "End date must be after start date",
                        effective_from=effective_from.isoformat(),
                        effective_to=effective_to.isoformat(),
                    )

            # Validate custom price
            if custom_price is not None:
                if custom_price < 0:
                    raise DealerValidationError(
                        "Custom price cannot be negative",
                        custom_price=float(custom_price),
                    )
                if custom_price > Decimal("100000.00"):
                    raise DealerValidationError(
                        "Custom price exceeds maximum allowed value",
                        custom_price=float(custom_price),
                    )

            # Create configuration
            config = DealerOptionConfig(
                dealer_id=dealer_id,
                option_id=option_id,
                is_available=is_available,
                custom_price=custom_price,
                effective_from=effective_from or datetime.utcnow(),
                effective_to=effective_to,
                region=region,
            )

            self.db.add(config)
            await self.db.flush()

            logger.info(
                "Dealer option configuration created",
                config_id=str(config.id),
                dealer_id=str(dealer_id),
                option_id=str(option_id),
                is_available=is_available,
                has_custom_price=custom_price is not None,
                region=region,
            )

            return config

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(
                "Integrity error creating dealer option configuration",
                dealer_id=str(dealer_id),
                option_id=str(option_id),
                error=str(e),
            )
            raise DealerManagementError(
                "Configuration already exists or constraint violation",
                code="INTEGRITY_ERROR",
                dealer_id=str(dealer_id),
                option_id=str(option_id),
            ) from e
        except DealerValidationError:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Error creating dealer option configuration",
                dealer_id=str(dealer_id),
                option_id=str(option_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerManagementError(
                "Failed to create option configuration",
                code="CREATE_ERROR",
                dealer_id=str(dealer_id),
                option_id=str(option_id),
            ) from e

    async def create_package_config(
        self,
        dealer_id: uuid.UUID,
        package_id: uuid.UUID,
        is_available: bool = True,
        custom_price: Optional[Decimal] = None,
        effective_from: Optional[datetime] = None,
        effective_to: Optional[datetime] = None,
        region: Optional[str] = None,
    ) -> DealerPackageConfig:
        """
        Create dealer package configuration.

        Args:
            dealer_id: Dealer identifier
            package_id: Vehicle package identifier
            is_available: Availability status
            custom_price: Custom price override
            effective_from: Start date for validity
            effective_to: End date for validity
            region: Geographic region restriction

        Returns:
            Created dealer package configuration

        Raises:
            DealerValidationError: If validation fails
            DealerManagementError: If creation fails
        """
        try:
            # Validate package exists
            package_stmt = select(Package).where(Package.id == package_id)
            package_result = await self.db.execute(package_stmt)
            package = package_result.scalar_one_or_none()

            if package is None:
                raise DealerValidationError(
                    f"Vehicle package not found: {package_id}",
                    package_id=str(package_id),
                )

            # Validate dates
            if effective_to is not None and effective_from is not None:
                if effective_to <= effective_from:
                    raise DealerValidationError(
                        "End date must be after start date",
                        effective_from=effective_from.isoformat(),
                        effective_to=effective_to.isoformat(),
                    )

            # Validate custom price
            if custom_price is not None:
                if custom_price < 0:
                    raise DealerValidationError(
                        "Custom price cannot be negative",
                        custom_price=float(custom_price),
                    )
                if custom_price > Decimal("100000.00"):
                    raise DealerValidationError(
                        "Custom price exceeds maximum allowed value",
                        custom_price=float(custom_price),
                    )

            # Create configuration
            config = DealerPackageConfig(
                dealer_id=dealer_id,
                package_id=package_id,
                is_available=is_available,
                custom_price=custom_price,
                effective_from=effective_from or datetime.utcnow(),
                effective_to=effective_to,
                region=region,
            )

            self.db.add(config)
            await self.db.flush()

            logger.info(
                "Dealer package configuration created",
                config_id=str(config.id),
                dealer_id=str(dealer_id),
                package_id=str(package_id),
                is_available=is_available,
                has_custom_price=custom_price is not None,
                region=region,
            )

            return config

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(
                "Integrity error creating dealer package configuration",
                dealer_id=str(dealer_id),
                package_id=str(package_id),
                error=str(e),
            )
            raise DealerManagementError(
                "Configuration already exists or constraint violation",
                code="INTEGRITY_ERROR",
                dealer_id=str(dealer_id),
                package_id=str(package_id),
            ) from e
        except DealerValidationError:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Error creating dealer package configuration",
                dealer_id=str(dealer_id),
                package_id=str(package_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerManagementError(
                "Failed to create package configuration",
                code="CREATE_ERROR",
                dealer_id=str(dealer_id),
                package_id=str(package_id),
            ) from e

    async def update_option_availability(
        self,
        config_id: uuid.UUID,
        is_available: bool,
    ) -> DealerOptionConfig:
        """
        Update option availability status.

        Args:
            config_id: Configuration identifier
            is_available: New availability status

        Returns:
            Updated configuration

        Raises:
            DealerConfigurationNotFoundError: If configuration not found
            DealerManagementError: If update fails
        """
        try:
            stmt = select(DealerOptionConfig).where(DealerOptionConfig.id == config_id)
            result = await self.db.execute(stmt)
            config = result.scalar_one_or_none()

            if config is None:
                raise DealerConfigurationNotFoundError(config_id)

            config.update_availability(is_available)
            await self.db.flush()

            logger.info(
                "Option availability updated",
                config_id=str(config_id),
                is_available=is_available,
            )

            return config

        except DealerConfigurationNotFoundError:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Error updating option availability",
                config_id=str(config_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerManagementError(
                "Failed to update option availability",
                code="UPDATE_ERROR",
                config_id=str(config_id),
            ) from e

    async def update_package_availability(
        self,
        config_id: uuid.UUID,
        is_available: bool,
    ) -> DealerPackageConfig:
        """
        Update package availability status.

        Args:
            config_id: Configuration identifier
            is_available: New availability status

        Returns:
            Updated configuration

        Raises:
            DealerConfigurationNotFoundError: If configuration not found
            DealerManagementError: If update fails
        """
        try:
            stmt = select(DealerPackageConfig).where(
                DealerPackageConfig.id == config_id
            )
            result = await self.db.execute(stmt)
            config = result.scalar_one_or_none()

            if config is None:
                raise DealerConfigurationNotFoundError(config_id)

            config.update_availability(is_available)
            await self.db.flush()

            logger.info(
                "Package availability updated",
                config_id=str(config_id),
                is_available=is_available,
            )

            return config

        except DealerConfigurationNotFoundError:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Error updating package availability",
                config_id=str(config_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerManagementError(
                "Failed to update package availability",
                code="UPDATE_ERROR",
                config_id=str(config_id),
            ) from e

    async def update_option_pricing(
        self,
        config_id: uuid.UUID,
        custom_price: Optional[Decimal],
    ) -> DealerOptionConfig:
        """
        Update option custom pricing.

        Args:
            config_id: Configuration identifier
            custom_price: New custom price (None to remove override)

        Returns:
            Updated configuration

        Raises:
            DealerConfigurationNotFoundError: If configuration not found
            DealerValidationError: If price validation fails
            DealerManagementError: If update fails
        """
        try:
            stmt = select(DealerOptionConfig).where(DealerOptionConfig.id == config_id)
            result = await self.db.execute(stmt)
            config = result.scalar_one_or_none()

            if config is None:
                raise DealerConfigurationNotFoundError(config_id)

            config.update_custom_price(custom_price)
            await self.db.flush()

            logger.info(
                "Option pricing updated",
                config_id=str(config_id),
                custom_price=float(custom_price) if custom_price else None,
            )

            return config

        except DealerConfigurationNotFoundError:
            await self.db.rollback()
            raise
        except ValueError as e:
            await self.db.rollback()
            raise DealerValidationError(str(e), config_id=str(config_id)) from e
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Error updating option pricing",
                config_id=str(config_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerManagementError(
                "Failed to update option pricing",
                code="UPDATE_ERROR",
                config_id=str(config_id),
            ) from e

    async def update_package_pricing(
        self,
        config_id: uuid.UUID,
        custom_price: Optional[Decimal],
    ) -> DealerPackageConfig:
        """
        Update package custom pricing.

        Args:
            config_id: Configuration identifier
            custom_price: New custom price (None to remove override)

        Returns:
            Updated configuration

        Raises:
            DealerConfigurationNotFoundError: If configuration not found
            DealerValidationError: If price validation fails
            DealerManagementError: If update fails
        """
        try:
            stmt = select(DealerPackageConfig).where(
                DealerPackageConfig.id == config_id
            )
            result = await self.db.execute(stmt)
            config = result.scalar_one_or_none()

            if config is None:
                raise DealerConfigurationNotFoundError(config_id)

            config.update_custom_price(custom_price)
            await self.db.flush()

            logger.info(
                "Package pricing updated",
                config_id=str(config_id),
                custom_price=float(custom_price) if custom_price else None,
            )

            return config

        except DealerConfigurationNotFoundError:
            await self.db.rollback()
            raise
        except ValueError as e:
            await self.db.rollback()
            raise DealerValidationError(str(e), config_id=str(config_id)) from e
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Error updating package pricing",
                config_id=str(config_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerManagementError(
                "Failed to update package pricing",
                code="UPDATE_ERROR",
                config_id=str(config_id),
            ) from e

    async def get_dealer_option_configs(
        self,
        dealer_id: uuid.UUID,
        active_only: bool = True,
        region: Optional[str] = None,
    ) -> list[DealerOptionConfig]:
        """
        Get dealer option configurations.

        Args:
            dealer_id: Dealer identifier
            active_only: Filter for active configurations only
            region: Filter by region

        Returns:
            List of dealer option configurations

        Raises:
            DealerManagementError: If retrieval fails
        """
        try:
            stmt = select(DealerOptionConfig).where(
                DealerOptionConfig.dealer_id == dealer_id
            )

            if active_only:
                now = datetime.utcnow()
                stmt = stmt.where(
                    and_(
                        DealerOptionConfig.is_available.is_(True),
                        DealerOptionConfig.effective_from <= now,
                        or_(
                            DealerOptionConfig.effective_to.is_(None),
                            DealerOptionConfig.effective_to > now,
                        ),
                    )
                )

            if region is not None:
                stmt = stmt.where(
                    or_(
                        DealerOptionConfig.region.is_(None),
                        DealerOptionConfig.region == region,
                    )
                )

            result = await self.db.execute(stmt)
            configs = list(result.scalars().all())

            logger.info(
                "Retrieved dealer option configurations",
                dealer_id=str(dealer_id),
                count=len(configs),
                active_only=active_only,
                region=region,
            )

            return configs

        except Exception as e:
            logger.error(
                "Error retrieving dealer option configurations",
                dealer_id=str(dealer_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerManagementError(
                "Failed to retrieve option configurations",
                code="RETRIEVAL_ERROR",
                dealer_id=str(dealer_id),
            ) from e

    async def get_dealer_package_configs(
        self,
        dealer_id: uuid.UUID,
        active_only: bool = True,
        region: Optional[str] = None,
    ) -> list[DealerPackageConfig]:
        """
        Get dealer package configurations.

        Args:
            dealer_id: Dealer identifier
            active_only: Filter for active configurations only
            region: Filter by region

        Returns:
            List of dealer package configurations

        Raises:
            DealerManagementError: If retrieval fails
        """
        try:
            stmt = select(DealerPackageConfig).where(
                DealerPackageConfig.dealer_id == dealer_id
            )

            if active_only:
                now = datetime.utcnow()
                stmt = stmt.where(
                    and_(
                        DealerPackageConfig.is_available.is_(True),
                        DealerPackageConfig.effective_from <= now,
                        or_(
                            DealerPackageConfig.effective_to.is_(None),
                            DealerPackageConfig.effective_to > now,
                        ),
                    )
                )

            if region is not None:
                stmt = stmt.where(
                    or_(
                        DealerPackageConfig.region.is_(None),
                        DealerPackageConfig.region == region,
                    )
                )

            result = await self.db.execute(stmt)
            configs = list(result.scalars().all())

            logger.info(
                "Retrieved dealer package configurations",
                dealer_id=str(dealer_id),
                count=len(configs),
                active_only=active_only,
                region=region,
            )

            return configs

        except Exception as e:
            logger.error(
                "Error retrieving dealer package configurations",
                dealer_id=str(dealer_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerManagementError(
                "Failed to retrieve package configurations",
                code="RETRIEVAL_ERROR",
                dealer_id=str(dealer_id),
            ) from e

    async def bulk_update_option_availability(
        self,
        dealer_id: uuid.UUID,
        option_ids: list[uuid.UUID],
        is_available: bool,
    ) -> int:
        """
        Bulk update option availability.

        Args:
            dealer_id: Dealer identifier
            option_ids: List of option identifiers
            is_available: New availability status

        Returns:
            Number of configurations updated

        Raises:
            DealerManagementError: If bulk update fails
        """
        try:
            stmt = (
                update(DealerOptionConfig)
                .where(
                    and_(
                        DealerOptionConfig.dealer_id == dealer_id,
                        DealerOptionConfig.option_id.in_(option_ids),
                    )
                )
                .values(is_available=is_available, updated_at=datetime.utcnow())
            )

            result = await self.db.execute(stmt)
            updated_count = result.rowcount
            await self.db.flush()

            logger.info(
                "Bulk updated option availability",
                dealer_id=str(dealer_id),
                option_count=len(option_ids),
                updated_count=updated_count,
                is_available=is_available,
            )

            return updated_count

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Error in bulk option availability update",
                dealer_id=str(dealer_id),
                option_count=len(option_ids),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerManagementError(
                "Failed to bulk update option availability",
                code="BULK_UPDATE_ERROR",
                dealer_id=str(dealer_id),
            ) from e

    async def bulk_update_package_availability(
        self,
        dealer_id: uuid.UUID,
        package_ids: list[uuid.UUID],
        is_available: bool,
    ) -> int:
        """
        Bulk update package availability.

        Args:
            dealer_id: Dealer identifier
            package_ids: List of package identifiers
            is_available: New availability status

        Returns:
            Number of configurations updated

        Raises:
            DealerManagementError: If bulk update fails
        """
        try:
            stmt = (
                update(DealerPackageConfig)
                .where(
                    and_(
                        DealerPackageConfig.dealer_id == dealer_id,
                        DealerPackageConfig.package_id.in_(package_ids),
                    )
                )
                .values(is_available=is_available, updated_at=datetime.utcnow())
            )

            result = await self.db.execute(stmt)
            updated_count = result.rowcount
            await self.db.flush()

            logger.info(
                "Bulk updated package availability",
                dealer_id=str(dealer_id),
                package_count=len(package_ids),
                updated_count=updated_count,
                is_available=is_available,
            )

            return updated_count

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Error in bulk package availability update",
                dealer_id=str(dealer_id),
                package_count=len(package_ids),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerManagementError(
                "Failed to bulk update package availability",
                code="BULK_UPDATE_ERROR",
                dealer_id=str(dealer_id),
            ) from e

    async def delete_option_config(self, config_id: uuid.UUID) -> None:
        """
        Delete dealer option configuration.

        Args:
            config_id: Configuration identifier

        Raises:
            DealerConfigurationNotFoundError: If configuration not found
            DealerManagementError: If deletion fails
        """
        try:
            stmt = delete(DealerOptionConfig).where(DealerOptionConfig.id == config_id)
            result = await self.db.execute(stmt)

            if result.rowcount == 0:
                raise DealerConfigurationNotFoundError(config_id)

            await self.db.flush()

            logger.info("Dealer option configuration deleted", config_id=str(config_id))

        except DealerConfigurationNotFoundError:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Error deleting dealer option configuration",
                config_id=str(config_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerManagementError(
                "Failed to delete option configuration",
                code="DELETE_ERROR",
                config_id=str(config_id),
            ) from e

    async def delete_package_config(self, config_id: uuid.UUID) -> None:
        """
        Delete dealer package configuration.

        Args:
            config_id: Configuration identifier

        Raises:
            DealerConfigurationNotFoundError: If configuration not found
            DealerManagementError: If deletion fails
        """
        try:
            stmt = delete(DealerPackageConfig).where(
                DealerPackageConfig.id == config_id
            )
            result = await self.db.execute(stmt)

            if result.rowcount == 0:
                raise DealerConfigurationNotFoundError(config_id)

            await self.db.flush()

            logger.info(
                "Dealer package configuration deleted", config_id=str(config_id)
            )

        except DealerConfigurationNotFoundError:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Error deleting dealer package configuration",
                config_id=str(config_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerManagementError(
                "Failed to delete package configuration",
                code="DELETE_ERROR",
                config_id=str(config_id),
            ) from e