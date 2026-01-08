"""
Configuration repository for data access operations.

This module implements the ConfigurationRepository class with async methods for
retrieving vehicle options, packages, saving configurations, and querying
configuration history. Includes optimized queries with proper joins and caching
support for high-performance configuration management.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from src.core.logging import get_logger
from src.database.models.vehicle_option import VehicleOption
from src.database.models.package import Package
from src.database.models.vehicle_configuration import VehicleConfiguration

logger = get_logger(__name__)


class ConfigurationRepository:
    """
    Repository for configuration data access operations.

    Provides async methods for retrieving vehicle options, packages, saving
    configurations, and querying configuration history with optimized queries,
    proper joins, and caching support.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize configuration repository.

        Args:
            session: Async database session for queries
        """
        self.session = session
        logger.debug("ConfigurationRepository initialized")

    async def get_vehicle_options(
        self,
        vehicle_id: uuid.UUID,
        category: Optional[str] = None,
        include_required_only: bool = False,
    ) -> list[VehicleOption]:
        """
        Retrieve vehicle options with optional filtering.

        Args:
            vehicle_id: Vehicle identifier
            category: Optional category filter
            include_required_only: If True, return only required options

        Returns:
            List of vehicle options matching criteria
        """
        try:
            stmt = select(VehicleOption).where(
                VehicleOption.vehicle_id == vehicle_id
            )

            if category:
                stmt = stmt.where(VehicleOption.category == category)

            if include_required_only:
                stmt = stmt.where(VehicleOption.is_required.is_(True))

            stmt = stmt.order_by(
                VehicleOption.category,
                VehicleOption.name,
            )

            result = await self.session.execute(stmt)
            options = list(result.scalars().all())

            logger.info(
                "Retrieved vehicle options",
                vehicle_id=str(vehicle_id),
                category=category,
                required_only=include_required_only,
                count=len(options),
            )

            return options

        except Exception as e:
            logger.error(
                "Failed to retrieve vehicle options",
                vehicle_id=str(vehicle_id),
                category=category,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_option_by_id(
        self, option_id: uuid.UUID
    ) -> Optional[VehicleOption]:
        """
        Retrieve single option by ID.

        Args:
            option_id: Option identifier

        Returns:
            VehicleOption if found, None otherwise
        """
        try:
            stmt = select(VehicleOption).where(VehicleOption.id == option_id)
            result = await self.session.execute(stmt)
            option = result.scalar_one_or_none()

            if option:
                logger.debug(
                    "Retrieved option by ID",
                    option_id=str(option_id),
                    option_name=option.name,
                )
            else:
                logger.warning(
                    "Option not found",
                    option_id=str(option_id),
                )

            return option

        except Exception as e:
            logger.error(
                "Failed to retrieve option by ID",
                option_id=str(option_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_options_by_ids(
        self, option_ids: list[uuid.UUID]
    ) -> list[VehicleOption]:
        """
        Retrieve multiple options by IDs.

        Args:
            option_ids: List of option identifiers

        Returns:
            List of vehicle options found
        """
        try:
            if not option_ids:
                return []

            stmt = select(VehicleOption).where(
                VehicleOption.id.in_(option_ids)
            )
            result = await self.session.execute(stmt)
            options = list(result.scalars().all())

            logger.info(
                "Retrieved options by IDs",
                requested_count=len(option_ids),
                found_count=len(options),
            )

            return options

        except Exception as e:
            logger.error(
                "Failed to retrieve options by IDs",
                count=len(option_ids),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_vehicle_packages(
        self,
        vehicle_id: uuid.UUID,
        trim: Optional[str] = None,
        model_year: Optional[int] = None,
    ) -> list[Package]:
        """
        Retrieve vehicle packages with compatibility filtering.

        Args:
            vehicle_id: Vehicle identifier
            trim: Optional trim level filter
            model_year: Optional model year filter

        Returns:
            List of packages matching criteria
        """
        try:
            stmt = select(Package).where(Package.vehicle_id == vehicle_id)

            if trim:
                stmt = stmt.where(
                    or_(
                        Package.trim_compatibility == [],
                        Package.trim_compatibility.contains([trim]),
                    )
                )

            if model_year:
                stmt = stmt.where(
                    or_(
                        Package.model_year_compatibility == [],
                        Package.model_year_compatibility.contains([model_year]),
                    )
                )

            stmt = stmt.order_by(Package.name)

            result = await self.session.execute(stmt)
            packages = list(result.scalars().all())

            logger.info(
                "Retrieved vehicle packages",
                vehicle_id=str(vehicle_id),
                trim=trim,
                model_year=model_year,
                count=len(packages),
            )

            return packages

        except Exception as e:
            logger.error(
                "Failed to retrieve vehicle packages",
                vehicle_id=str(vehicle_id),
                trim=trim,
                model_year=model_year,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_package_by_id(self, package_id: uuid.UUID) -> Optional[Package]:
        """
        Retrieve single package by ID.

        Args:
            package_id: Package identifier

        Returns:
            Package if found, None otherwise
        """
        try:
            stmt = select(Package).where(Package.id == package_id)
            result = await self.session.execute(stmt)
            package = result.scalar_one_or_none()

            if package:
                logger.debug(
                    "Retrieved package by ID",
                    package_id=str(package_id),
                    package_name=package.name,
                )
            else:
                logger.warning(
                    "Package not found",
                    package_id=str(package_id),
                )

            return package

        except Exception as e:
            logger.error(
                "Failed to retrieve package by ID",
                package_id=str(package_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_packages_by_ids(
        self, package_ids: list[uuid.UUID]
    ) -> list[Package]:
        """
        Retrieve multiple packages by IDs.

        Args:
            package_ids: List of package identifiers

        Returns:
            List of packages found
        """
        try:
            if not package_ids:
                return []

            stmt = select(Package).where(Package.id.in_(package_ids))
            result = await self.session.execute(stmt)
            packages = list(result.scalars().all())

            logger.info(
                "Retrieved packages by IDs",
                requested_count=len(package_ids),
                found_count=len(packages),
            )

            return packages

        except Exception as e:
            logger.error(
                "Failed to retrieve packages by IDs",
                count=len(package_ids),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def save_configuration(
        self, configuration: VehicleConfiguration
    ) -> VehicleConfiguration:
        """
        Save vehicle configuration to database.

        Args:
            configuration: Configuration to save

        Returns:
            Saved configuration with updated timestamps
        """
        try:
            self.session.add(configuration)
            await self.session.flush()
            await self.session.refresh(configuration)

            logger.info(
                "Saved vehicle configuration",
                configuration_id=str(configuration.id),
                vehicle_id=str(configuration.vehicle_id),
                user_id=str(configuration.user_id),
                total_price=float(configuration.total_price),
                status=configuration.configuration_status,
            )

            return configuration

        except Exception as e:
            logger.error(
                "Failed to save configuration",
                vehicle_id=str(configuration.vehicle_id),
                user_id=str(configuration.user_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_configuration_by_id(
        self,
        configuration_id: uuid.UUID,
        include_relationships: bool = True,
    ) -> Optional[VehicleConfiguration]:
        """
        Retrieve configuration by ID with optional relationships.

        Args:
            configuration_id: Configuration identifier
            include_relationships: If True, eagerly load vehicle and user

        Returns:
            VehicleConfiguration if found, None otherwise
        """
        try:
            stmt = select(VehicleConfiguration).where(
                VehicleConfiguration.id == configuration_id
            )

            if include_relationships:
                stmt = stmt.options(
                    selectinload(VehicleConfiguration.vehicle),
                    selectinload(VehicleConfiguration.user),
                )

            result = await self.session.execute(stmt)
            configuration = result.scalar_one_or_none()

            if configuration:
                logger.debug(
                    "Retrieved configuration by ID",
                    configuration_id=str(configuration_id),
                    vehicle_id=str(configuration.vehicle_id),
                    user_id=str(configuration.user_id),
                )
            else:
                logger.warning(
                    "Configuration not found",
                    configuration_id=str(configuration_id),
                )

            return configuration

        except Exception as e:
            logger.error(
                "Failed to retrieve configuration by ID",
                configuration_id=str(configuration_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_user_configurations(
        self,
        user_id: uuid.UUID,
        vehicle_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[VehicleConfiguration], int]:
        """
        Retrieve user configurations with filtering and pagination.

        Args:
            user_id: User identifier
            vehicle_id: Optional vehicle filter
            status: Optional status filter
            limit: Maximum results to return
            offset: Number of results to skip

        Returns:
            Tuple of (configurations list, total count)
        """
        try:
            base_stmt = select(VehicleConfiguration).where(
                and_(
                    VehicleConfiguration.user_id == user_id,
                    VehicleConfiguration.deleted_at.is_(None),
                )
            )

            if vehicle_id:
                base_stmt = base_stmt.where(
                    VehicleConfiguration.vehicle_id == vehicle_id
                )

            if status:
                base_stmt = base_stmt.where(
                    VehicleConfiguration.configuration_status == status
                )

            count_stmt = select(func.count()).select_from(base_stmt.subquery())
            count_result = await self.session.execute(count_stmt)
            total_count = count_result.scalar() or 0

            stmt = (
                base_stmt.options(
                    selectinload(VehicleConfiguration.vehicle),
                )
                .order_by(desc(VehicleConfiguration.created_at))
                .limit(limit)
                .offset(offset)
            )

            result = await self.session.execute(stmt)
            configurations = list(result.scalars().all())

            logger.info(
                "Retrieved user configurations",
                user_id=str(user_id),
                vehicle_id=str(vehicle_id) if vehicle_id else None,
                status=status,
                count=len(configurations),
                total_count=total_count,
                limit=limit,
                offset=offset,
            )

            return configurations, total_count

        except Exception as e:
            logger.error(
                "Failed to retrieve user configurations",
                user_id=str(user_id),
                vehicle_id=str(vehicle_id) if vehicle_id else None,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_vehicle_configurations(
        self,
        vehicle_id: uuid.UUID,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[VehicleConfiguration], int]:
        """
        Retrieve configurations for a vehicle with filtering and pagination.

        Args:
            vehicle_id: Vehicle identifier
            status: Optional status filter
            limit: Maximum results to return
            offset: Number of results to skip

        Returns:
            Tuple of (configurations list, total count)
        """
        try:
            base_stmt = select(VehicleConfiguration).where(
                and_(
                    VehicleConfiguration.vehicle_id == vehicle_id,
                    VehicleConfiguration.deleted_at.is_(None),
                )
            )

            if status:
                base_stmt = base_stmt.where(
                    VehicleConfiguration.configuration_status == status
                )

            count_stmt = select(func.count()).select_from(base_stmt.subquery())
            count_result = await self.session.execute(count_stmt)
            total_count = count_result.scalar() or 0

            stmt = (
                base_stmt.options(
                    selectinload(VehicleConfiguration.user),
                )
                .order_by(desc(VehicleConfiguration.created_at))
                .limit(limit)
                .offset(offset)
            )

            result = await self.session.execute(stmt)
            configurations = list(result.scalars().all())

            logger.info(
                "Retrieved vehicle configurations",
                vehicle_id=str(vehicle_id),
                status=status,
                count=len(configurations),
                total_count=total_count,
                limit=limit,
                offset=offset,
            )

            return configurations, total_count

        except Exception as e:
            logger.error(
                "Failed to retrieve vehicle configurations",
                vehicle_id=str(vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def update_configuration(
        self, configuration: VehicleConfiguration
    ) -> VehicleConfiguration:
        """
        Update existing configuration.

        Args:
            configuration: Configuration with updated values

        Returns:
            Updated configuration
        """
        try:
            await self.session.flush()
            await self.session.refresh(configuration)

            logger.info(
                "Updated vehicle configuration",
                configuration_id=str(configuration.id),
                vehicle_id=str(configuration.vehicle_id),
                user_id=str(configuration.user_id),
                status=configuration.configuration_status,
                is_valid=configuration.is_valid,
            )

            return configuration

        except Exception as e:
            logger.error(
                "Failed to update configuration",
                configuration_id=str(configuration.id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def delete_configuration(
        self, configuration_id: uuid.UUID, soft_delete: bool = True
    ) -> bool:
        """
        Delete configuration (soft or hard delete).

        Args:
            configuration_id: Configuration identifier
            soft_delete: If True, perform soft delete; otherwise hard delete

        Returns:
            True if deleted successfully
        """
        try:
            configuration = await self.get_configuration_by_id(
                configuration_id, include_relationships=False
            )

            if not configuration:
                logger.warning(
                    "Configuration not found for deletion",
                    configuration_id=str(configuration_id),
                )
                return False

            if soft_delete:
                configuration.deleted_at = datetime.utcnow()
                await self.session.flush()
                logger.info(
                    "Soft deleted configuration",
                    configuration_id=str(configuration_id),
                )
            else:
                await self.session.delete(configuration)
                await self.session.flush()
                logger.info(
                    "Hard deleted configuration",
                    configuration_id=str(configuration_id),
                )

            return True

        except Exception as e:
            logger.error(
                "Failed to delete configuration",
                configuration_id=str(configuration_id),
                soft_delete=soft_delete,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_configuration_statistics(
        self, vehicle_id: Optional[uuid.UUID] = None
    ) -> dict[str, Any]:
        """
        Get configuration statistics.

        Args:
            vehicle_id: Optional vehicle filter

        Returns:
            Dictionary with configuration statistics
        """
        try:
            base_stmt = select(VehicleConfiguration).where(
                VehicleConfiguration.deleted_at.is_(None)
            )

            if vehicle_id:
                base_stmt = base_stmt.where(
                    VehicleConfiguration.vehicle_id == vehicle_id
                )

            total_stmt = select(func.count()).select_from(base_stmt.subquery())
            total_result = await self.session.execute(total_stmt)
            total_count = total_result.scalar() or 0

            valid_stmt = select(func.count()).select_from(
                base_stmt.where(VehicleConfiguration.is_valid.is_(True)).subquery()
            )
            valid_result = await self.session.execute(valid_stmt)
            valid_count = valid_result.scalar() or 0

            avg_price_stmt = select(
                func.avg(VehicleConfiguration.total_price)
            ).select_from(base_stmt.subquery())
            avg_price_result = await self.session.execute(avg_price_stmt)
            avg_price = avg_price_result.scalar() or Decimal("0.00")

            status_stmt = (
                select(
                    VehicleConfiguration.configuration_status,
                    func.count(VehicleConfiguration.id),
                )
                .select_from(base_stmt.subquery())
                .group_by(VehicleConfiguration.configuration_status)
            )
            status_result = await self.session.execute(status_stmt)
            status_breakdown = dict(status_result.all())

            statistics = {
                "total_configurations": total_count,
                "valid_configurations": valid_count,
                "invalid_configurations": total_count - valid_count,
                "average_price": float(avg_price),
                "status_breakdown": status_breakdown,
            }

            logger.info(
                "Retrieved configuration statistics",
                vehicle_id=str(vehicle_id) if vehicle_id else None,
                total_count=total_count,
                valid_count=valid_count,
            )

            return statistics

        except Exception as e:
            logger.error(
                "Failed to retrieve configuration statistics",
                vehicle_id=str(vehicle_id) if vehicle_id else None,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise