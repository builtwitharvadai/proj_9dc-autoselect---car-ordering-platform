"""
Configuration API endpoints for vehicle configuration management.

This module implements FastAPI router endpoints for vehicle configuration including
retrieving available options, validating configurations, calculating pricing, and
saving configurations. Integrates with authentication, business rules validation,
and pricing engine services.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import CurrentActiveUser, DatabaseSession
from src.core.logging import get_logger
from src.database.models.user import User
from src.schemas.configuration import (
    ConfigurationRequest,
    ConfigurationResponse,
    OptionSelection,
    PackageSelection,
    PricingBreakdown,
    ValidationResult,
)
from src.services.configuration.service import (
    ConfigurationService,
    ConfigurationServiceError,
    ConfigurationValidationError,
    ConfigurationNotFoundError,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/vehicles", tags=["configuration"])


async def get_configuration_service(
    session: DatabaseSession,
) -> ConfigurationService:
    """
    Dependency to create configuration service instance.

    Args:
        session: Database session

    Returns:
        ConfigurationService instance
    """
    return ConfigurationService(session=session, enable_caching=True)


ConfigService = Annotated[
    ConfigurationService, Depends(get_configuration_service)
]


@router.get(
    "/{vehicle_id}/options",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get vehicle options",
    description="Retrieve all available options and packages for a vehicle with compatibility rules",
)
async def get_vehicle_options(
    vehicle_id: UUID,
    service: ConfigService,
    category: Optional[str] = None,
    required_only: bool = False,
) -> dict:
    """
    Get vehicle options with compatibility rules.

    Args:
        vehicle_id: Vehicle identifier
        service: Configuration service
        category: Optional category filter
        required_only: If True, return only required options

    Returns:
        Dictionary with options, packages, and metadata

    Raises:
        HTTPException: 404 if vehicle not found, 500 for service errors
    """
    try:
        logger.info(
            "Retrieving vehicle options",
            vehicle_id=str(vehicle_id),
            category=category,
            required_only=required_only,
        )

        result = await service.get_vehicle_options(
            vehicle_id=vehicle_id,
            category=category,
            include_required_only=required_only,
        )

        logger.info(
            "Vehicle options retrieved successfully",
            vehicle_id=str(vehicle_id),
            option_count=result["metadata"]["total_options"],
            package_count=result["metadata"]["total_packages"],
        )

        return result

    except ConfigurationServiceError as e:
        logger.error(
            "Failed to retrieve vehicle options",
            vehicle_id=str(vehicle_id),
            error=str(e),
            error_context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle not found: {vehicle_id}",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error retrieving vehicle options",
            vehicle_id=str(vehicle_id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve vehicle options",
        ) from e


@router.post(
    "/{vehicle_id}/validate",
    response_model=ValidationResult,
    status_code=status.HTTP_200_OK,
    summary="Validate configuration",
    description="Validate vehicle configuration against business rules and compatibility constraints",
)
async def validate_configuration(
    vehicle_id: UUID,
    service: ConfigService,
    selected_options: list[str],
    selected_packages: list[str],
    trim: Optional[str] = None,
    year: Optional[int] = None,
) -> ValidationResult:
    """
    Validate vehicle configuration.

    Args:
        vehicle_id: Vehicle identifier
        service: Configuration service
        selected_options: List of selected option IDs
        selected_packages: List of selected package IDs
        trim: Vehicle trim level
        year: Vehicle model year

    Returns:
        Validation result with errors and warnings

    Raises:
        HTTPException: 400 for validation errors, 500 for service errors
    """
    try:
        logger.info(
            "Validating configuration",
            vehicle_id=str(vehicle_id),
            option_count=len(selected_options),
            package_count=len(selected_packages),
        )

        option_ids = [UUID(opt_id) for opt_id in selected_options]
        package_ids = [UUID(pkg_id) for pkg_id in selected_packages]

        result = await service.validate_configuration(
            vehicle_id=vehicle_id,
            selected_option_ids=option_ids,
            selected_package_ids=package_ids,
            trim=trim,
            year=year,
        )

        validation_result = ValidationResult(
            is_valid=result["is_valid"],
            errors=result["errors"],
            warnings=[],
            incompatible_options=[],
            missing_required_options=[],
        )

        logger.info(
            "Configuration validation completed",
            vehicle_id=str(vehicle_id),
            is_valid=validation_result.is_valid,
            error_count=len(validation_result.errors),
        )

        return validation_result

    except ConfigurationServiceError as e:
        logger.error(
            "Configuration validation failed",
            vehicle_id=str(vehicle_id),
            error=str(e),
            error_context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error during validation",
            vehicle_id=str(vehicle_id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate configuration",
        ) from e


@router.post(
    "/{vehicle_id}/price",
    response_model=PricingBreakdown,
    status_code=status.HTTP_200_OK,
    summary="Calculate pricing",
    description="Calculate total pricing including base price, options, packages, taxes, and fees",
)
async def calculate_pricing(
    vehicle_id: UUID,
    service: ConfigService,
    selected_options: list[str],
    selected_packages: list[str],
    region: Optional[str] = None,
    include_tax: bool = True,
    include_destination: bool = True,
) -> PricingBreakdown:
    """
    Calculate configuration pricing.

    Args:
        vehicle_id: Vehicle identifier
        service: Configuration service
        selected_options: List of selected option IDs
        selected_packages: List of selected package IDs
        region: Region code for tax calculation
        include_tax: Include tax in total
        include_destination: Include destination charge in total

    Returns:
        Detailed pricing breakdown

    Raises:
        HTTPException: 404 if vehicle not found, 500 for service errors
    """
    try:
        logger.info(
            "Calculating pricing",
            vehicle_id=str(vehicle_id),
            option_count=len(selected_options),
            package_count=len(selected_packages),
            region=region,
        )

        option_ids = [UUID(opt_id) for opt_id in selected_options]
        package_ids = [UUID(pkg_id) for pkg_id in selected_packages]

        result = await service.calculate_pricing(
            vehicle_id=vehicle_id,
            selected_option_ids=option_ids,
            selected_package_ids=package_ids,
            region=region,
            include_tax=include_tax,
            include_destination=include_destination,
        )

        pricing = PricingBreakdown(
            base_price=result["breakdown"]["base_price"],
            options_total=result["breakdown"]["options_total"],
            packages_total=result["breakdown"]["packages_total"],
            subtotal=result["breakdown"]["subtotal"],
            tax_amount=result["breakdown"]["tax_amount"],
            tax_rate=result["breakdown"]["tax_rate"],
            destination_charge=result["breakdown"]["destination_charge"],
            other_fees=result["breakdown"].get("other_fees", 0),
            total_price=result["total"],
            discount_amount=result["breakdown"].get("discount_amount"),
            incentives=result["breakdown"].get("incentives", []),
        )

        logger.info(
            "Pricing calculated successfully",
            vehicle_id=str(vehicle_id),
            total_price=float(pricing.total_price),
        )

        return pricing

    except ConfigurationServiceError as e:
        logger.error(
            "Pricing calculation failed",
            vehicle_id=str(vehicle_id),
            error=str(e),
            error_context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle not found: {vehicle_id}",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error calculating pricing",
            vehicle_id=str(vehicle_id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate pricing",
        ) from e


@router.post(
    "/configurations",
    response_model=ConfigurationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save configuration",
    description="Save customer vehicle configuration with validation and pricing",
)
async def save_configuration(
    request: ConfigurationRequest,
    service: ConfigService,
    current_user: CurrentActiveUser,
) -> ConfigurationResponse:
    """
    Save vehicle configuration.

    Args:
        request: Configuration request data
        service: Configuration service
        current_user: Authenticated user

    Returns:
        Saved configuration with ID and details

    Raises:
        HTTPException: 400 for validation errors, 500 for service errors
    """
    try:
        logger.info(
            "Saving configuration",
            vehicle_id=str(request.vehicle_id),
            user_id=str(current_user.id),
            option_count=len(request.options),
            package_count=len(request.packages),
        )

        option_ids = [UUID(opt.option_id) for opt in request.options]
        package_ids = [UUID(pkg.package_id) for pkg in request.packages]

        result = await service.save_configuration(
            vehicle_id=request.vehicle_id,
            user_id=current_user.id,
            selected_option_ids=option_ids,
            selected_package_ids=package_ids,
            notes=request.notes,
            validate_before_save=True,
        )

        response = ConfigurationResponse(
            id=UUID(result["id"]),
            vehicle_id=UUID(result["vehicle_id"]),
            options=request.options,
            packages=request.packages,
            pricing=PricingBreakdown(
                base_price=result["pricing_breakdown"]["base_price"],
                options_total=result["pricing_breakdown"]["options_total"],
                packages_total=result["pricing_breakdown"]["packages_total"],
                subtotal=result["pricing_breakdown"]["subtotal"],
                tax_amount=result["pricing_breakdown"]["tax_amount"],
                tax_rate=result["pricing_breakdown"]["tax_rate"],
                destination_charge=result["pricing_breakdown"][
                    "destination_charge"
                ],
                other_fees=result["pricing_breakdown"].get("other_fees", 0),
                total_price=result["total_price"],
                discount_amount=result["pricing_breakdown"].get(
                    "discount_amount"
                ),
                incentives=result["pricing_breakdown"].get("incentives", []),
            ),
            validation=ValidationResult(
                is_valid=result["is_valid"],
                errors=[],
                warnings=[],
                incompatible_options=[],
                missing_required_options=[],
            ),
            customer_id=request.customer_id,
            dealer_id=request.dealer_id,
            notes=result.get("notes"),
            created_at=result["created_at"],
            updated_at=result["created_at"],
            expires_at=result.get("expires_at"),
            status=result["status"],
        )

        logger.info(
            "Configuration saved successfully",
            configuration_id=str(response.id),
            vehicle_id=str(request.vehicle_id),
            user_id=str(current_user.id),
        )

        return response

    except ConfigurationValidationError as e:
        logger.warning(
            "Configuration validation failed",
            vehicle_id=str(request.vehicle_id),
            user_id=str(current_user.id),
            errors=e.errors,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": str(e),
                "errors": e.errors,
            },
        ) from e
    except ConfigurationServiceError as e:
        logger.error(
            "Failed to save configuration",
            vehicle_id=str(request.vehicle_id),
            user_id=str(current_user.id),
            error=str(e),
            error_context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save configuration",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error saving configuration",
            vehicle_id=str(request.vehicle_id),
            user_id=str(current_user.id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save configuration",
        ) from e


@router.get(
    "/configurations/{configuration_id}",
    response_model=ConfigurationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get configuration",
    description="Retrieve saved configuration by ID",
)
async def get_configuration(
    configuration_id: UUID,
    service: ConfigService,
    current_user: CurrentActiveUser,
) -> ConfigurationResponse:
    """
    Get configuration by ID.

    Args:
        configuration_id: Configuration identifier
        service: Configuration service
        current_user: Authenticated user

    Returns:
        Configuration details

    Raises:
        HTTPException: 404 if not found, 403 if unauthorized, 500 for service errors
    """
    try:
        logger.info(
            "Retrieving configuration",
            configuration_id=str(configuration_id),
            user_id=str(current_user.id),
        )

        result = await service.get_configuration(configuration_id)

        if UUID(result["user_id"]) != current_user.id:
            logger.warning(
                "Unauthorized configuration access attempt",
                configuration_id=str(configuration_id),
                user_id=str(current_user.id),
                owner_id=result["user_id"],
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this configuration",
            )

        response = ConfigurationResponse(
            id=UUID(result["id"]),
            vehicle_id=UUID(result["vehicle_id"]),
            options=[
                OptionSelection(
                    option_id=opt_id,
                    quantity=1,
                    price=0,
                    name="",
                    category=None,
                )
                for opt_id in result["selected_options"]
            ],
            packages=[
                PackageSelection(
                    package_id=pkg_id,
                    price=0,
                    name="",
                    included_options=[],
                    discount_amount=None,
                )
                for pkg_id in result["selected_packages"]
            ],
            pricing=PricingBreakdown(
                base_price=result["pricing_breakdown"]["base_price"],
                options_total=result["pricing_breakdown"]["options_total"],
                packages_total=result["pricing_breakdown"]["packages_total"],
                subtotal=result["pricing_breakdown"]["subtotal"],
                tax_amount=result["pricing_breakdown"]["tax_amount"],
                tax_rate=result["pricing_breakdown"]["tax_rate"],
                destination_charge=result["pricing_breakdown"][
                    "destination_charge"
                ],
                other_fees=result["pricing_breakdown"].get("other_fees", 0),
                total_price=result["total_price"],
                discount_amount=result["pricing_breakdown"].get(
                    "discount_amount"
                ),
                incentives=result["pricing_breakdown"].get("incentives", []),
            ),
            validation=ValidationResult(
                is_valid=result["is_valid"],
                errors=[],
                warnings=[],
                incompatible_options=[],
                missing_required_options=[],
            ),
            customer_id=None,
            dealer_id=None,
            notes=result.get("notes"),
            created_at=result["created_at"],
            updated_at=result["updated_at"],
            expires_at=result.get("expires_at"),
            status=result["status"],
        )

        logger.info(
            "Configuration retrieved successfully",
            configuration_id=str(configuration_id),
            user_id=str(current_user.id),
        )

        return response

    except ConfigurationNotFoundError as e:
        logger.warning(
            "Configuration not found",
            configuration_id=str(configuration_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration not found: {configuration_id}",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error retrieving configuration",
            configuration_id=str(configuration_id),
            user_id=str(current_user.id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configuration",
        ) from e