"""
Business rules engine for vehicle configuration validation.

This module implements the ConfigurationRulesEngine for validating vehicle
configurations against complex business rules including option compatibility,
package requirements, and configuration completeness. Provides detailed error
reporting and comprehensive validation logic.
"""

import uuid
from typing import Any, Optional
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.models.vehicle_option import VehicleOption
from src.database.models.package import Package

logger = get_logger(__name__)


class ConfigurationValidationError(Exception):
    """Exception raised when configuration validation fails."""

    def __init__(
        self,
        message: str,
        errors: list[str],
        vehicle_id: Optional[uuid.UUID] = None,
        **context: Any
    ):
        """
        Initialize configuration validation error.

        Args:
            message: Error message
            errors: List of validation error messages
            vehicle_id: Vehicle ID if applicable
            **context: Additional error context
        """
        super().__init__(message)
        self.errors = errors
        self.vehicle_id = vehicle_id
        self.context = context


class ConfigurationRulesEngine:
    """
    Business rules engine for vehicle configuration validation.

    Implements comprehensive validation logic for vehicle configurations including
    option compatibility checks, package requirement validation, and configuration
    completeness verification. Provides detailed error reporting for all validation
    failures.

    Attributes:
        session: Database session for querying options and packages
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize configuration rules engine.

        Args:
            session: Database session for querying options and packages
        """
        self.session = session
        logger.info("Configuration rules engine initialized")

    async def validate_configuration(
        self,
        vehicle_id: uuid.UUID,
        selected_option_ids: list[uuid.UUID],
        selected_package_ids: list[uuid.UUID],
        trim: Optional[str] = None,
        year: Optional[int] = None,
    ) -> tuple[bool, list[str]]:
        """
        Validate complete vehicle configuration.

        Performs comprehensive validation including required options, mutual
        exclusivity, package compatibility, and configuration completeness.

        Args:
            vehicle_id: Vehicle ID to validate configuration for
            selected_option_ids: List of selected option IDs
            selected_package_ids: List of selected package IDs
            trim: Vehicle trim level
            year: Vehicle model year

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        logger.info(
            "Validating vehicle configuration",
            vehicle_id=str(vehicle_id),
            option_count=len(selected_option_ids),
            package_count=len(selected_package_ids),
            trim=trim,
            year=year,
        )

        # Load all options for vehicle
        options = await self._load_vehicle_options(vehicle_id)
        if not options:
            errors.append(f"No options found for vehicle {vehicle_id}")
            logger.warning(
                "No options found for vehicle",
                vehicle_id=str(vehicle_id),
            )
            return False, errors

        # Load all packages for vehicle
        packages = await self._load_vehicle_packages(vehicle_id)

        # Validate required options
        required_errors = await self.check_required_options(
            options, selected_option_ids
        )
        errors.extend(required_errors)

        # Validate mutual exclusivity
        exclusivity_errors = await self.check_mutually_exclusive(
            options, selected_option_ids
        )
        errors.extend(exclusivity_errors)

        # Validate option dependencies
        dependency_errors = await self.check_option_dependencies(
            options, selected_option_ids
        )
        errors.extend(dependency_errors)

        # Validate package requirements
        package_errors = await self.validate_package_requirements(
            packages, selected_package_ids, selected_option_ids
        )
        errors.extend(package_errors)

        # Validate package compatibility with trim and year
        if packages:
            compatibility_errors = await self.validate_package_compatibility(
                packages, selected_package_ids, trim, year
            )
            errors.extend(compatibility_errors)

        # Validate configuration completeness
        completeness_errors = await self.validate_configuration_completeness(
            options, selected_option_ids, selected_package_ids
        )
        errors.extend(completeness_errors)

        is_valid = len(errors) == 0

        if is_valid:
            logger.info(
                "Configuration validation successful",
                vehicle_id=str(vehicle_id),
                option_count=len(selected_option_ids),
                package_count=len(selected_package_ids),
            )
        else:
            logger.warning(
                "Configuration validation failed",
                vehicle_id=str(vehicle_id),
                error_count=len(errors),
                errors=errors,
            )

        return is_valid, errors

    async def check_required_options(
        self,
        options: list[VehicleOption],
        selected_option_ids: list[uuid.UUID],
    ) -> list[str]:
        """
        Check that all required options are selected.

        Args:
            options: List of all vehicle options
            selected_option_ids: List of selected option IDs

        Returns:
            List of error messages for missing required options
        """
        errors = []
        required_options = [opt for opt in options if opt.is_required]

        for option in required_options:
            if option.id not in selected_option_ids:
                errors.append(
                    f"Required option '{option.name}' (category: {option.category}) "
                    f"must be selected"
                )
                logger.warning(
                    "Required option not selected",
                    option_id=str(option.id),
                    option_name=option.name,
                    category=option.category,
                )

        if errors:
            logger.info(
                "Required options validation completed",
                missing_count=len(errors),
            )

        return errors

    async def check_mutually_exclusive(
        self,
        options: list[VehicleOption],
        selected_option_ids: list[uuid.UUID],
    ) -> list[str]:
        """
        Check for mutually exclusive option conflicts.

        Args:
            options: List of all vehicle options
            selected_option_ids: List of selected option IDs

        Returns:
            List of error messages for mutual exclusivity violations
        """
        errors = []
        selected_options = [opt for opt in options if opt.id in selected_option_ids]

        for option in selected_options:
            if not option.mutually_exclusive_with:
                continue

            for exclusive_id in option.mutually_exclusive_with:
                if exclusive_id in selected_option_ids:
                    exclusive_option = next(
                        (opt for opt in options if opt.id == exclusive_id),
                        None,
                    )
                    exclusive_name = (
                        exclusive_option.name if exclusive_option else str(exclusive_id)
                    )

                    errors.append(
                        f"Option '{option.name}' is mutually exclusive with "
                        f"'{exclusive_name}' - only one can be selected"
                    )
                    logger.warning(
                        "Mutually exclusive options conflict",
                        option_id=str(option.id),
                        option_name=option.name,
                        exclusive_option_id=str(exclusive_id),
                        exclusive_option_name=exclusive_name,
                    )

        if errors:
            logger.info(
                "Mutual exclusivity validation completed",
                conflict_count=len(errors),
            )

        return errors

    async def check_option_dependencies(
        self,
        options: list[VehicleOption],
        selected_option_ids: list[uuid.UUID],
    ) -> list[str]:
        """
        Check that all option dependencies are satisfied.

        Args:
            options: List of all vehicle options
            selected_option_ids: List of selected option IDs

        Returns:
            List of error messages for missing dependencies
        """
        errors = []
        selected_options = [opt for opt in options if opt.id in selected_option_ids]

        for option in selected_options:
            if not option.required_options:
                continue

            for required_id in option.required_options:
                if required_id not in selected_option_ids:
                    required_option = next(
                        (opt for opt in options if opt.id == required_id),
                        None,
                    )
                    required_name = (
                        required_option.name if required_option else str(required_id)
                    )

                    errors.append(
                        f"Option '{option.name}' requires '{required_name}' "
                        f"to be selected"
                    )
                    logger.warning(
                        "Option dependency not satisfied",
                        option_id=str(option.id),
                        option_name=option.name,
                        required_option_id=str(required_id),
                        required_option_name=required_name,
                    )

        if errors:
            logger.info(
                "Option dependencies validation completed",
                missing_count=len(errors),
            )

        return errors

    async def validate_package_requirements(
        self,
        packages: list[Package],
        selected_package_ids: list[uuid.UUID],
        selected_option_ids: list[uuid.UUID],
    ) -> list[str]:
        """
        Validate that package requirements are met.

        Args:
            packages: List of all vehicle packages
            selected_package_ids: List of selected package IDs
            selected_option_ids: List of selected option IDs

        Returns:
            List of error messages for package requirement violations
        """
        errors = []
        selected_packages = [pkg for pkg in packages if pkg.id in selected_package_ids]

        for package in selected_packages:
            missing_options = []
            for option_id in package.included_options:
                if option_id not in selected_option_ids:
                    missing_options.append(str(option_id))

            if missing_options:
                errors.append(
                    f"Package '{package.name}' requires all included options "
                    f"to be selected. Missing options: {', '.join(missing_options)}"
                )
                logger.warning(
                    "Package requirements not met",
                    package_id=str(package.id),
                    package_name=package.name,
                    missing_option_count=len(missing_options),
                )

        if errors:
            logger.info(
                "Package requirements validation completed",
                violation_count=len(errors),
            )

        return errors

    async def validate_package_compatibility(
        self,
        packages: list[Package],
        selected_package_ids: list[uuid.UUID],
        trim: Optional[str] = None,
        year: Optional[int] = None,
    ) -> list[str]:
        """
        Validate package compatibility with trim and year.

        Args:
            packages: List of all vehicle packages
            selected_package_ids: List of selected package IDs
            trim: Vehicle trim level
            year: Vehicle model year

        Returns:
            List of error messages for compatibility violations
        """
        errors = []
        selected_packages = [pkg for pkg in packages if pkg.id in selected_package_ids]

        for package in selected_packages:
            is_valid, package_errors = package.validate_compatibility(trim, year)
            if not is_valid:
                errors.extend(package_errors)

        if errors:
            logger.info(
                "Package compatibility validation completed",
                incompatibility_count=len(errors),
            )

        return errors

    async def validate_configuration_completeness(
        self,
        options: list[VehicleOption],
        selected_option_ids: list[uuid.UUID],
        selected_package_ids: list[uuid.UUID],
    ) -> list[str]:
        """
        Validate that configuration is complete and coherent.

        Args:
            options: List of all vehicle options
            selected_option_ids: List of selected option IDs
            selected_package_ids: List of selected package IDs

        Returns:
            List of error messages for completeness issues
        """
        errors = []

        # Check if any options are selected
        if not selected_option_ids and not selected_package_ids:
            errors.append(
                "Configuration must include at least one option or package"
            )
            logger.warning("Empty configuration detected")

        # Check for duplicate selections
        if len(selected_option_ids) != len(set(selected_option_ids)):
            errors.append("Configuration contains duplicate option selections")
            logger.warning(
                "Duplicate option selections detected",
                total_count=len(selected_option_ids),
                unique_count=len(set(selected_option_ids)),
            )

        if len(selected_package_ids) != len(set(selected_package_ids)):
            errors.append("Configuration contains duplicate package selections")
            logger.warning(
                "Duplicate package selections detected",
                total_count=len(selected_package_ids),
                unique_count=len(set(selected_package_ids)),
            )

        # Check for invalid option IDs
        valid_option_ids = {opt.id for opt in options}
        invalid_option_ids = [
            opt_id for opt_id in selected_option_ids if opt_id not in valid_option_ids
        ]
        if invalid_option_ids:
            errors.append(
                f"Configuration contains invalid option IDs: "
                f"{', '.join(str(oid) for oid in invalid_option_ids)}"
            )
            logger.warning(
                "Invalid option IDs detected",
                invalid_count=len(invalid_option_ids),
            )

        if errors:
            logger.info(
                "Configuration completeness validation completed",
                issue_count=len(errors),
            )

        return errors

    async def validate_package_eligibility(
        self,
        vehicle_id: uuid.UUID,
        package_id: uuid.UUID,
        trim: Optional[str] = None,
        year: Optional[int] = None,
    ) -> tuple[bool, list[str]]:
        """
        Validate if a package is eligible for a vehicle configuration.

        Args:
            vehicle_id: Vehicle ID
            package_id: Package ID to validate
            trim: Vehicle trim level
            year: Vehicle model year

        Returns:
            Tuple of (is_eligible, error_messages)
        """
        errors = []

        logger.info(
            "Validating package eligibility",
            vehicle_id=str(vehicle_id),
            package_id=str(package_id),
            trim=trim,
            year=year,
        )

        # Load package
        stmt = select(Package).where(
            Package.id == package_id,
            Package.vehicle_id == vehicle_id,
        )
        result = await self.session.execute(stmt)
        package = result.scalar_one_or_none()

        if not package:
            errors.append(
                f"Package {package_id} not found for vehicle {vehicle_id}"
            )
            logger.warning(
                "Package not found",
                vehicle_id=str(vehicle_id),
                package_id=str(package_id),
            )
            return False, errors

        # Validate compatibility
        is_valid, compatibility_errors = package.validate_compatibility(trim, year)
        errors.extend(compatibility_errors)

        if is_valid:
            logger.info(
                "Package eligibility validated",
                package_id=str(package_id),
                package_name=package.name,
            )
        else:
            logger.warning(
                "Package not eligible",
                package_id=str(package_id),
                package_name=package.name,
                error_count=len(errors),
            )

        return is_valid, errors

    async def _load_vehicle_options(
        self, vehicle_id: uuid.UUID
    ) -> list[VehicleOption]:
        """
        Load all options for a vehicle.

        Args:
            vehicle_id: Vehicle ID

        Returns:
            List of vehicle options
        """
        stmt = select(VehicleOption).where(VehicleOption.vehicle_id == vehicle_id)
        result = await self.session.execute(stmt)
        options = list(result.scalars().all())

        logger.debug(
            "Loaded vehicle options",
            vehicle_id=str(vehicle_id),
            option_count=len(options),
        )

        return options

    async def _load_vehicle_packages(self, vehicle_id: uuid.UUID) -> list[Package]:
        """
        Load all packages for a vehicle.

        Args:
            vehicle_id: Vehicle ID

        Returns:
            List of vehicle packages
        """
        stmt = select(Package).where(Package.vehicle_id == vehicle_id)
        result = await self.session.execute(stmt)
        packages = list(result.scalars().all())

        logger.debug(
            "Loaded vehicle packages",
            vehicle_id=str(vehicle_id),
            package_count=len(packages),
        )

        return packages