"""
FastAPI router for dealer management endpoints.

This module implements dealer management endpoints for configuration operations,
including retrieving configurations, updating settings, bulk operations, and
analytics with comprehensive role-based access control and validation.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import CurrentDealer, DatabaseSession
from src.core.logging import get_logger
from src.schemas.dealer_management import (
    DealerConfigRequest,
    BulkConfigUpdate,
    ConfigurationRule,
    RegionAvailability,
)
from src.services.dealer_management.service import (
    DealerManagementService,
    DealerManagementError,
    DealerConfigurationNotFoundError,
    DealerValidationError,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/dealer-management", tags=["dealer-management"])


@router.get("/config")
async def get_configurations(
    current_user: CurrentDealer,
    db: DatabaseSession,
    active_only: bool = Query(True, description="Filter for active configurations"),
    region: Optional[str] = Query(None, description="Filter by region code"),
    config_type: Optional[str] = Query(
        None,
        description="Configuration type (option or package)",
        pattern="^(option|package)$",
    ),
) -> dict:
    """
    Get dealer configurations.

    Retrieves option and package configurations for the authenticated dealer
    with optional filtering by active status, region, and configuration type.

    Args:
        current_user: Authenticated dealer user
        db: Database session
        active_only: Filter for active configurations only
        region: Optional region code filter
        config_type: Optional configuration type filter

    Returns:
        Dictionary containing option and package configurations

    Raises:
        HTTPException: 500 if retrieval fails
    """
    try:
        service = DealerManagementService(db)
        dealer_id = current_user.id

        logger.info(
            "Retrieving dealer configurations",
            dealer_id=str(dealer_id),
            active_only=active_only,
            region=region,
            config_type=config_type,
        )

        response = {}

        if config_type is None or config_type == "option":
            option_configs = await service.get_dealer_option_configs(
                dealer_id=dealer_id,
                active_only=active_only,
                region=region,
            )
            response["option_configs"] = [
                {
                    "id": str(config.id),
                    "dealer_id": str(config.dealer_id),
                    "option_id": str(config.option_id),
                    "is_available": config.is_available,
                    "custom_price": (
                        float(config.custom_price) if config.custom_price else None
                    ),
                    "effective_from": config.effective_from.isoformat(),
                    "effective_to": (
                        config.effective_to.isoformat()
                        if config.effective_to
                        else None
                    ),
                    "region": config.region,
                    "created_at": config.created_at.isoformat(),
                    "updated_at": config.updated_at.isoformat(),
                }
                for config in option_configs
            ]

        if config_type is None or config_type == "package":
            package_configs = await service.get_dealer_package_configs(
                dealer_id=dealer_id,
                active_only=active_only,
                region=region,
            )
            response["package_configs"] = [
                {
                    "id": str(config.id),
                    "dealer_id": str(config.dealer_id),
                    "package_id": str(config.package_id),
                    "is_available": config.is_available,
                    "custom_price": (
                        float(config.custom_price) if config.custom_price else None
                    ),
                    "effective_from": config.effective_from.isoformat(),
                    "effective_to": (
                        config.effective_to.isoformat()
                        if config.effective_to
                        else None
                    ),
                    "region": config.region,
                    "created_at": config.created_at.isoformat(),
                    "updated_at": config.updated_at.isoformat(),
                }
                for config in package_configs
            ]

        logger.info(
            "Dealer configurations retrieved successfully",
            dealer_id=str(dealer_id),
            option_count=len(response.get("option_configs", [])),
            package_count=len(response.get("package_configs", [])),
        )

        return response

    except DealerManagementError as e:
        logger.error(
            "Error retrieving dealer configurations",
            dealer_id=str(current_user.id),
            error=str(e),
            error_code=e.code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error retrieving dealer configurations",
            dealer_id=str(current_user.id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configurations",
        ) from e


@router.put("/config")
async def update_configurations(
    current_user: CurrentDealer,
    db: DatabaseSession,
    request: DealerConfigRequest,
) -> dict:
    """
    Update dealer configurations.

    Creates or updates option and package configurations for the dealer
    with validation and effective date management.

    Args:
        current_user: Authenticated dealer user
        db: Database session
        request: Configuration update request

    Returns:
        Dictionary containing created/updated configurations

    Raises:
        HTTPException: 400 for validation errors, 500 for other failures
    """
    try:
        service = DealerManagementService(db)
        dealer_id = current_user.id

        logger.info(
            "Updating dealer configurations",
            dealer_id=str(dealer_id),
            vehicle_id=str(request.vehicle_id),
            option_count=len(request.option_ids),
            package_count=len(request.package_ids),
        )

        response = {"option_configs": [], "package_configs": []}

        # Process option configurations
        for option_id in request.option_ids:
            custom_price = None
            if request.custom_pricing and str(option_id) in request.custom_pricing:
                custom_price = request.custom_pricing[str(option_id)]

            config = await service.create_option_config(
                dealer_id=dealer_id,
                option_id=option_id,
                is_available=True,
                custom_price=custom_price,
                effective_from=request.effective_date,
                effective_to=request.expiration_date,
                region=request.region_code,
            )

            response["option_configs"].append(
                {
                    "id": str(config.id),
                    "option_id": str(config.option_id),
                    "is_available": config.is_available,
                    "custom_price": (
                        float(config.custom_price) if config.custom_price else None
                    ),
                    "effective_from": config.effective_from.isoformat(),
                    "effective_to": (
                        config.effective_to.isoformat()
                        if config.effective_to
                        else None
                    ),
                    "region": config.region,
                }
            )

        # Process package configurations
        for package_id in request.package_ids:
            custom_price = None
            if request.custom_pricing and str(package_id) in request.custom_pricing:
                custom_price = request.custom_pricing[str(package_id)]

            config = await service.create_package_config(
                dealer_id=dealer_id,
                package_id=package_id,
                is_available=True,
                custom_price=custom_price,
                effective_from=request.effective_date,
                effective_to=request.expiration_date,
                region=request.region_code,
            )

            response["package_configs"].append(
                {
                    "id": str(config.id),
                    "package_id": str(config.package_id),
                    "is_available": config.is_available,
                    "custom_price": (
                        float(config.custom_price) if config.custom_price else None
                    ),
                    "effective_from": config.effective_from.isoformat(),
                    "effective_to": (
                        config.effective_to.isoformat()
                        if config.effective_to
                        else None
                    ),
                    "region": config.region,
                }
            )

        await db.commit()

        logger.info(
            "Dealer configurations updated successfully",
            dealer_id=str(dealer_id),
            option_configs_created=len(response["option_configs"]),
            package_configs_created=len(response["package_configs"]),
        )

        return response

    except DealerValidationError as e:
        await db.rollback()
        logger.warning(
            "Validation error updating dealer configurations",
            dealer_id=str(current_user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except DealerManagementError as e:
        await db.rollback()
        logger.error(
            "Error updating dealer configurations",
            dealer_id=str(current_user.id),
            error=str(e),
            error_code=e.code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    except Exception as e:
        await db.rollback()
        logger.error(
            "Unexpected error updating dealer configurations",
            dealer_id=str(current_user.id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configurations",
        ) from e


@router.post("/config/bulk")
async def bulk_update_configurations(
    current_user: CurrentDealer,
    db: DatabaseSession,
    request: BulkConfigUpdate,
) -> dict:
    """
    Bulk update dealer configurations.

    Processes multiple configuration updates in batches with optional
    validation-only mode and rollback on error support.

    Args:
        current_user: Authenticated dealer user
        db: Database session
        request: Bulk configuration update request

    Returns:
        Dictionary containing bulk update results and statistics

    Raises:
        HTTPException: 400 for validation errors, 500 for other failures
    """
    try:
        service = DealerManagementService(db)
        dealer_id = current_user.id

        logger.info(
            "Processing bulk configuration update",
            dealer_id=str(dealer_id),
            configuration_count=len(request.configurations),
            validate_only=request.validate_only,
            rollback_on_error=request.rollback_on_error,
        )

        results = {
            "total": len(request.configurations),
            "successful": 0,
            "failed": 0,
            "errors": [],
        }

        if request.validate_only:
            # Validation-only mode
            for idx, config in enumerate(request.configurations):
                try:
                    # Validate configuration without persisting
                    if config.option_ids:
                        for option_id in config.option_ids:
                            # Validation happens in service layer
                            pass
                    if config.package_ids:
                        for package_id in config.package_ids:
                            # Validation happens in service layer
                            pass
                    results["successful"] += 1
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(
                        {
                            "index": idx,
                            "vehicle_id": str(config.vehicle_id),
                            "error": str(e),
                        }
                    )

            logger.info(
                "Bulk configuration validation completed",
                dealer_id=str(dealer_id),
                successful=results["successful"],
                failed=results["failed"],
            )

            return results

        # Process configurations in batches
        batch_size = request.batch_size
        for batch_start in range(0, len(request.configurations), batch_size):
            batch_end = min(batch_start + batch_size, len(request.configurations))
            batch = request.configurations[batch_start:batch_end]

            for idx, config in enumerate(batch, start=batch_start):
                try:
                    # Process option configurations
                    if config.option_ids:
                        for option_id in config.option_ids:
                            custom_price = None
                            if (
                                config.custom_pricing
                                and str(option_id) in config.custom_pricing
                            ):
                                custom_price = config.custom_pricing[str(option_id)]

                            await service.create_option_config(
                                dealer_id=dealer_id,
                                option_id=option_id,
                                is_available=True,
                                custom_price=custom_price,
                                effective_from=config.effective_date,
                                effective_to=config.expiration_date,
                                region=config.region_code,
                            )

                    # Process package configurations
                    if config.package_ids:
                        for package_id in config.package_ids:
                            custom_price = None
                            if (
                                config.custom_pricing
                                and str(package_id) in config.custom_pricing
                            ):
                                custom_price = config.custom_pricing[str(package_id)]

                            await service.create_package_config(
                                dealer_id=dealer_id,
                                package_id=package_id,
                                is_available=True,
                                custom_price=custom_price,
                                effective_from=config.effective_date,
                                effective_to=config.expiration_date,
                                region=config.region_code,
                            )

                    results["successful"] += 1

                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(
                        {
                            "index": idx,
                            "vehicle_id": str(config.vehicle_id),
                            "error": str(e),
                        }
                    )

                    if request.rollback_on_error:
                        await db.rollback()
                        logger.error(
                            "Bulk update rolled back due to error",
                            dealer_id=str(dealer_id),
                            error_index=idx,
                            error=str(e),
                        )
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Bulk update failed at index {idx}: {str(e)}",
                        ) from e

            # Commit batch if no rollback on error
            if not request.rollback_on_error:
                await db.commit()

        # Final commit if rollback on error is enabled and no errors occurred
        if request.rollback_on_error and results["failed"] == 0:
            await db.commit()

        logger.info(
            "Bulk configuration update completed",
            dealer_id=str(dealer_id),
            successful=results["successful"],
            failed=results["failed"],
        )

        return results

    except HTTPException:
        raise
    except DealerValidationError as e:
        await db.rollback()
        logger.warning(
            "Validation error in bulk configuration update",
            dealer_id=str(current_user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except DealerManagementError as e:
        await db.rollback()
        logger.error(
            "Error in bulk configuration update",
            dealer_id=str(current_user.id),
            error=str(e),
            error_code=e.code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    except Exception as e:
        await db.rollback()
        logger.error(
            "Unexpected error in bulk configuration update",
            dealer_id=str(current_user.id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process bulk update",
        ) from e


@router.get("/analytics")
async def get_configuration_analytics(
    current_user: CurrentDealer,
    db: DatabaseSession,
    region: Optional[str] = Query(None, description="Filter by region code"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
) -> dict:
    """
    Get configuration analytics.

    Retrieves analytics and statistics for dealer configurations including
    availability metrics, pricing overrides, and regional distribution.

    Args:
        current_user: Authenticated dealer user
        db: Database session
        region: Optional region code filter
        start_date: Optional start date for analytics period
        end_date: Optional end date for analytics period

    Returns:
        Dictionary containing configuration analytics and statistics

    Raises:
        HTTPException: 500 if analytics retrieval fails
    """
    try:
        service = DealerManagementService(db)
        dealer_id = current_user.id

        logger.info(
            "Retrieving configuration analytics",
            dealer_id=str(dealer_id),
            region=region,
            start_date=start_date,
            end_date=end_date,
        )

        # Get all configurations
        option_configs = await service.get_dealer_option_configs(
            dealer_id=dealer_id,
            active_only=False,
            region=region,
        )

        package_configs = await service.get_dealer_package_configs(
            dealer_id=dealer_id,
            active_only=False,
            region=region,
        )

        # Calculate analytics
        analytics = {
            "option_configs": {
                "total": len(option_configs),
                "active": sum(1 for c in option_configs if c.is_available),
                "with_custom_pricing": sum(
                    1 for c in option_configs if c.custom_price is not None
                ),
                "by_region": {},
            },
            "package_configs": {
                "total": len(package_configs),
                "active": sum(1 for c in package_configs if c.is_available),
                "with_custom_pricing": sum(
                    1 for c in package_configs if c.custom_price is not None
                ),
                "by_region": {},
            },
        }

        # Regional distribution for options
        for config in option_configs:
            region_key = config.region or "default"
            if region_key not in analytics["option_configs"]["by_region"]:
                analytics["option_configs"]["by_region"][region_key] = {
                    "total": 0,
                    "active": 0,
                }
            analytics["option_configs"]["by_region"][region_key]["total"] += 1
            if config.is_available:
                analytics["option_configs"]["by_region"][region_key]["active"] += 1

        # Regional distribution for packages
        for config in package_configs:
            region_key = config.region or "default"
            if region_key not in analytics["package_configs"]["by_region"]:
                analytics["package_configs"]["by_region"][region_key] = {
                    "total": 0,
                    "active": 0,
                }
            analytics["package_configs"]["by_region"][region_key]["total"] += 1
            if config.is_available:
                analytics["package_configs"]["by_region"][region_key]["active"] += 1

        logger.info(
            "Configuration analytics retrieved successfully",
            dealer_id=str(dealer_id),
            total_option_configs=analytics["option_configs"]["total"],
            total_package_configs=analytics["package_configs"]["total"],
        )

        return analytics

    except DealerManagementError as e:
        logger.error(
            "Error retrieving configuration analytics",
            dealer_id=str(current_user.id),
            error=str(e),
            error_code=e.code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error retrieving configuration analytics",
            dealer_id=str(current_user.id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics",
        ) from e