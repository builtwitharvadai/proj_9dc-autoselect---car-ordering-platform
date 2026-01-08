"""
Vehicle catalog API endpoints.

This module implements FastAPI router for vehicle catalog operations including
CRUD endpoints, search functionality, filtering, and pagination. Provides
comprehensive error handling, validation, and response models with proper
logging and security.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import DatabaseSession, OptionalUser
from src.cache.redis_client import RedisClient, get_redis_client
from src.core.logging import get_logger
from src.schemas.vehicles import (
    VehicleCreate,
    VehicleListResponse,
    VehicleResponse,
    VehicleSearchRequest,
    VehicleUpdate,
)
from src.services.vehicles.service import (
    VehicleNotFoundError,
    VehicleService,
    VehicleServiceError,
    VehicleValidationError,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


async def get_vehicle_service(
    db: DatabaseSession,
    cache_client: Annotated[RedisClient, Depends(get_redis_client)],
) -> VehicleService:
    """
    Dependency for vehicle service initialization.

    Args:
        db: Database session
        cache_client: Redis cache client

    Returns:
        Initialized vehicle service
    """
    return VehicleService(session=db, cache_client=cache_client)


@router.get(
    "",
    response_model=VehicleListResponse,
    status_code=status.HTTP_200_OK,
    summary="List vehicles with pagination and filtering",
    description="Retrieve paginated list of vehicles with optional filtering",
)
async def list_vehicles(
    service: Annotated[VehicleService, Depends(get_vehicle_service)],
    current_user: OptionalUser,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=100, description="Items per page")
    ] = 20,
    make: Annotated[str | None, Query(max_length=100)] = None,
    model: Annotated[str | None, Query(max_length=100)] = None,
    year_min: Annotated[int | None, Query(ge=1900, le=2100)] = None,
    year_max: Annotated[int | None, Query(ge=1900, le=2100)] = None,
    body_style: Annotated[str | None, Query(max_length=50)] = None,
    fuel_type: Annotated[str | None, Query(max_length=50)] = None,
    price_min: Annotated[float | None, Query(ge=0)] = None,
    price_max: Annotated[float | None, Query(ge=0)] = None,
    sort_by: Annotated[str | None, Query(max_length=50)] = None,
    sort_order: Annotated[
        str, Query(pattern="^(asc|desc)$")
    ] = "asc",
) -> VehicleListResponse:
    """
    List vehicles with pagination and filtering.

    Args:
        service: Vehicle service instance
        current_user: Optional authenticated user
        page: Page number (1-indexed)
        page_size: Number of items per page
        make: Filter by manufacturer
        model: Filter by model name
        year_min: Minimum year filter
        year_max: Maximum year filter
        body_style: Filter by body style
        fuel_type: Filter by fuel type
        price_min: Minimum price filter
        price_max: Maximum price filter
        sort_by: Field to sort by
        sort_order: Sort order (asc or desc)

    Returns:
        Paginated list of vehicles

    Raises:
        HTTPException: 400 for validation errors, 500 for server errors
    """
    try:
        search_request = VehicleSearchRequest(
            make=make,
            model=model,
            year_min=year_min,
            year_max=year_max,
            body_style=body_style,
            fuel_type=fuel_type,
            price_min=price_min,
            price_max=price_max,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        result = await service.search_vehicles(search_request)

        logger.info(
            "Vehicles listed successfully",
            total=result.total,
            page=page,
            page_size=page_size,
            user_id=str(current_user.id) if current_user else None,
        )

        return result

    except VehicleValidationError as e:
        logger.warning(
            "Vehicle list validation error",
            error=str(e),
            code=e.code,
            context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except VehicleServiceError as e:
        logger.error(
            "Vehicle list service error",
            error=str(e),
            code=e.code,
            context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve vehicles",
        ) from e

    except Exception as e:
        logger.error(
            "Unexpected error listing vehicles",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get vehicle by ID",
    description="Retrieve detailed information about a specific vehicle",
)
async def get_vehicle(
    vehicle_id: UUID,
    service: Annotated[VehicleService, Depends(get_vehicle_service)],
    current_user: OptionalUser,
    include_inventory: Annotated[
        bool, Query(description="Include inventory information")
    ] = False,
) -> VehicleResponse:
    """
    Get vehicle details by ID.

    Args:
        vehicle_id: Vehicle unique identifier
        service: Vehicle service instance
        current_user: Optional authenticated user
        include_inventory: Whether to include inventory data

    Returns:
        Vehicle details

    Raises:
        HTTPException: 404 if not found, 500 for server errors
    """
    try:
        result = await service.get_vehicle(
            vehicle_id=vehicle_id,
            include_inventory=include_inventory,
        )

        logger.info(
            "Vehicle retrieved successfully",
            vehicle_id=str(vehicle_id),
            user_id=str(current_user.id) if current_user else None,
        )

        return result

    except VehicleNotFoundError as e:
        logger.warning(
            "Vehicle not found",
            vehicle_id=str(vehicle_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle not found: {vehicle_id}",
        ) from e

    except VehicleServiceError as e:
        logger.error(
            "Vehicle retrieval service error",
            vehicle_id=str(vehicle_id),
            error=str(e),
            code=e.code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve vehicle",
        ) from e

    except Exception as e:
        logger.error(
            "Unexpected error retrieving vehicle",
            vehicle_id=str(vehicle_id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.post(
    "",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new vehicle",
    description="Create a new vehicle in the catalog",
)
async def create_vehicle(
    vehicle_data: VehicleCreate,
    service: Annotated[VehicleService, Depends(get_vehicle_service)],
    current_user: OptionalUser,
) -> VehicleResponse:
    """
    Create new vehicle.

    Args:
        vehicle_data: Vehicle creation data
        service: Vehicle service instance
        current_user: Optional authenticated user

    Returns:
        Created vehicle details

    Raises:
        HTTPException: 400 for validation errors, 500 for server errors
    """
    try:
        result = await service.create_vehicle(vehicle_data)

        logger.info(
            "Vehicle created successfully",
            vehicle_id=str(result.id),
            make=result.make,
            model=result.model,
            year=result.year,
            user_id=str(current_user.id) if current_user else None,
        )

        return result

    except VehicleValidationError as e:
        logger.warning(
            "Vehicle creation validation error",
            error=str(e),
            code=e.code,
            context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except VehicleServiceError as e:
        logger.error(
            "Vehicle creation service error",
            error=str(e),
            code=e.code,
            context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create vehicle",
        ) from e

    except Exception as e:
        logger.error(
            "Unexpected error creating vehicle",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.put(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update vehicle",
    description="Update existing vehicle information",
)
async def update_vehicle(
    vehicle_id: UUID,
    vehicle_data: VehicleUpdate,
    service: Annotated[VehicleService, Depends(get_vehicle_service)],
    current_user: OptionalUser,
) -> VehicleResponse:
    """
    Update existing vehicle.

    Args:
        vehicle_id: Vehicle unique identifier
        vehicle_data: Vehicle update data
        service: Vehicle service instance
        current_user: Optional authenticated user

    Returns:
        Updated vehicle details

    Raises:
        HTTPException: 404 if not found, 400 for validation, 500 for errors
    """
    try:
        result = await service.update_vehicle(
            vehicle_id=vehicle_id,
            vehicle_data=vehicle_data,
        )

        logger.info(
            "Vehicle updated successfully",
            vehicle_id=str(vehicle_id),
            user_id=str(current_user.id) if current_user else None,
        )

        return result

    except VehicleNotFoundError as e:
        logger.warning(
            "Vehicle not found for update",
            vehicle_id=str(vehicle_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle not found: {vehicle_id}",
        ) from e

    except VehicleValidationError as e:
        logger.warning(
            "Vehicle update validation error",
            vehicle_id=str(vehicle_id),
            error=str(e),
            code=e.code,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except VehicleServiceError as e:
        logger.error(
            "Vehicle update service error",
            vehicle_id=str(vehicle_id),
            error=str(e),
            code=e.code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update vehicle",
        ) from e

    except Exception as e:
        logger.error(
            "Unexpected error updating vehicle",
            vehicle_id=str(vehicle_id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.delete(
    "/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete vehicle",
    description="Delete vehicle from catalog (soft delete by default)",
)
async def delete_vehicle(
    vehicle_id: UUID,
    service: Annotated[VehicleService, Depends(get_vehicle_service)],
    current_user: OptionalUser,
    soft: Annotated[
        bool, Query(description="Perform soft delete")
    ] = True,
) -> None:
    """
    Delete vehicle.

    Args:
        vehicle_id: Vehicle unique identifier
        service: Vehicle service instance
        current_user: Optional authenticated user
        soft: If True, perform soft delete; otherwise hard delete

    Raises:
        HTTPException: 404 if not found, 500 for server errors
    """
    try:
        await service.delete_vehicle(vehicle_id=vehicle_id, soft=soft)

        logger.info(
            "Vehicle deleted successfully",
            vehicle_id=str(vehicle_id),
            soft_delete=soft,
            user_id=str(current_user.id) if current_user else None,
        )

    except VehicleNotFoundError as e:
        logger.warning(
            "Vehicle not found for deletion",
            vehicle_id=str(vehicle_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle not found: {vehicle_id}",
        ) from e

    except VehicleServiceError as e:
        logger.error(
            "Vehicle deletion service error",
            vehicle_id=str(vehicle_id),
            error=str(e),
            code=e.code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete vehicle",
        ) from e

    except Exception as e:
        logger.error(
            "Unexpected error deleting vehicle",
            vehicle_id=str(vehicle_id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e