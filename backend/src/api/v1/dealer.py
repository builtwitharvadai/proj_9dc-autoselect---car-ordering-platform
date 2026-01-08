"""
Dealer inventory management API endpoints.

This module implements FastAPI router for dealer inventory management including
inventory listing, bulk CSV upload, individual vehicle updates, stock adjustments,
and dashboard analytics with comprehensive authentication and authorization.
"""

import uuid
from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import CurrentDealer, DatabaseSession
from src.core.logging import get_logger
from src.database.models.inventory import InventoryStatus
from src.schemas.dealer import (
    BulkInventoryResponse,
    BulkInventoryUpdate,
    DealerDashboardStats,
    DealerInventoryResponse,
    DealerInventoryUpdate,
)
from src.services.dealer.service import (
    DealerAuthorizationError,
    DealerInventoryNotFoundError,
    DealerInventoryService,
    DealerServiceError,
    get_dealer_inventory_service,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/dealer", tags=["dealer"])


@router.get(
    "/inventory",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get dealer inventory list",
    description="Retrieve paginated list of inventory items for authenticated dealer",
)
async def get_dealer_inventory(
    current_user: CurrentDealer,
    db: DatabaseSession,
    dealer_id: Annotated[
        uuid.UUID,
        Query(description="Dealer unique identifier"),
    ],
    status_filter: Annotated[
        Optional[str],
        Query(
            alias="status",
            description="Filter by inventory status",
        ),
    ] = None,
    skip: Annotated[
        int,
        Query(
            ge=0,
            description="Number of records to skip",
        ),
    ] = 0,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=1000,
            description="Maximum records to return",
        ),
    ] = 100,
    sort_by: Annotated[
        str,
        Query(
            description="Field to sort by",
        ),
    ] = "created_at",
    sort_direction: Annotated[
        str,
        Query(
            pattern="^(asc|desc)$",
            description="Sort direction",
        ),
    ] = "desc",
) -> dict:
    """
    Get dealer inventory with filtering, sorting, and pagination.

    Args:
        current_user: Authenticated dealer user
        db: Database session
        dealer_id: Dealer identifier
        status_filter: Optional status filter
        skip: Number of records to skip
        limit: Maximum records to return
        sort_by: Field to sort by
        sort_direction: Sort direction (asc/desc)

    Returns:
        Dictionary with inventory items and metadata

    Raises:
        HTTPException: 403 if unauthorized, 500 if operation fails
    """
    try:
        logger.info(
            "Fetching dealer inventory",
            dealer_id=str(dealer_id),
            user_id=str(current_user.id),
            status_filter=status_filter,
            skip=skip,
            limit=limit,
        )

        status_enum = None
        if status_filter:
            try:
                status_enum = InventoryStatus(status_filter.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status filter: {status_filter}",
                )

        service = get_dealer_inventory_service(db)

        items, total = await service.get_dealer_inventory(
            dealer_id=dealer_id,
            user_id=current_user.id,
            status=status_enum,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )

        logger.info(
            "Dealer inventory fetched successfully",
            dealer_id=str(dealer_id),
            count=len(items),
            total=total,
        )

        return {
            "items": [item.model_dump() for item in items],
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": (skip + len(items)) < total,
        }

    except DealerAuthorizationError as e:
        logger.warning(
            "Authorization failed for dealer inventory access",
            dealer_id=str(dealer_id),
            user_id=str(current_user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except DealerServiceError as e:
        logger.error(
            "Service error fetching dealer inventory",
            dealer_id=str(dealer_id),
            error=str(e),
            error_code=e.code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dealer inventory",
        )
    except Exception as e:
        logger.error(
            "Unexpected error fetching dealer inventory",
            dealer_id=str(dealer_id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post(
    "/inventory/bulk-upload",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Bulk upload inventory via CSV",
    description="Upload CSV file for bulk inventory updates",
)
async def bulk_upload_inventory(
    current_user: CurrentDealer,
    db: DatabaseSession,
    dealer_id: Annotated[
        uuid.UUID,
        Query(description="Dealer unique identifier"),
    ],
    file: Annotated[
        UploadFile,
        File(description="CSV file with inventory data"),
    ],
) -> dict:
    """
    Process CSV file upload for bulk inventory updates.

    Args:
        current_user: Authenticated dealer user
        db: Database session
        dealer_id: Dealer identifier
        file: Uploaded CSV file

    Returns:
        Dictionary with processing results

    Raises:
        HTTPException: 400 if invalid file, 403 if unauthorized, 500 if processing fails
    """
    try:
        logger.info(
            "Processing bulk inventory upload",
            dealer_id=str(dealer_id),
            user_id=str(current_user.id),
            filename=file.filename,
            content_type=file.content_type,
        )

        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided",
            )

        if not file.filename.endswith((".csv", ".xlsx")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format. Only CSV and Excel files are supported",
            )

        if file.content_type not in [
            "text/csv",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid content type",
            )

        import tempfile
        import aiofiles

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".csv" if file.filename.endswith(".csv") else ".xlsx",
        ) as tmp_file:
            temp_path = tmp_file.name

        try:
            async with aiofiles.open(temp_path, "wb") as f:
                content = await file.read()
                await f.write(content)

            service = get_dealer_inventory_service(db)

            result = await service.process_file_upload(
                file_path=temp_path,
                dealer_id=dealer_id,
                user_id=current_user.id,
            )

            logger.info(
                "Bulk inventory upload processed successfully",
                dealer_id=str(dealer_id),
                valid_items=result["valid_items"],
                invalid_items=result["invalid_items"],
            )

            return result

        finally:
            import os

            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except DealerAuthorizationError as e:
        logger.warning(
            "Authorization failed for bulk upload",
            dealer_id=str(dealer_id),
            user_id=str(current_user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except DealerServiceError as e:
        logger.error(
            "Service error processing bulk upload",
            dealer_id=str(dealer_id),
            error=str(e),
            error_code=e.code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process bulk upload",
        )
    except Exception as e:
        logger.error(
            "Unexpected error processing bulk upload",
            dealer_id=str(dealer_id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.put(
    "/inventory/{inventory_id}",
    response_model=DealerInventoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update inventory item",
    description="Update individual inventory item attributes",
)
async def update_inventory_item(
    current_user: CurrentDealer,
    db: DatabaseSession,
    inventory_id: Annotated[
        uuid.UUID,
        Query(description="Inventory item unique identifier"),
    ],
    dealer_id: Annotated[
        uuid.UUID,
        Query(description="Dealer unique identifier"),
    ],
    update_data: DealerInventoryUpdate,
) -> DealerInventoryResponse:
    """
    Update inventory item with validation and authorization.

    Args:
        current_user: Authenticated dealer user
        db: Database session
        inventory_id: Inventory item identifier
        dealer_id: Dealer identifier
        update_data: Update data

    Returns:
        Updated inventory item

    Raises:
        HTTPException: 403 if unauthorized, 404 if not found, 500 if update fails
    """
    try:
        logger.info(
            "Updating inventory item",
            inventory_id=str(inventory_id),
            dealer_id=str(dealer_id),
            user_id=str(current_user.id),
        )

        service = get_dealer_inventory_service(db)

        item = await service.update_inventory_item(
            inventory_id=inventory_id,
            dealer_id=dealer_id,
            user_id=current_user.id,
            update_data=update_data,
        )

        logger.info(
            "Inventory item updated successfully",
            inventory_id=str(inventory_id),
        )

        return item

    except DealerAuthorizationError as e:
        logger.warning(
            "Authorization failed for inventory update",
            inventory_id=str(inventory_id),
            dealer_id=str(dealer_id),
            user_id=str(current_user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except DealerInventoryNotFoundError as e:
        logger.warning(
            "Inventory item not found",
            inventory_id=str(inventory_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except DealerServiceError as e:
        logger.error(
            "Service error updating inventory item",
            inventory_id=str(inventory_id),
            error=str(e),
            error_code=e.code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update inventory item",
        )
    except Exception as e:
        logger.error(
            "Unexpected error updating inventory item",
            inventory_id=str(inventory_id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/dashboard/stats",
    response_model=DealerDashboardStats,
    status_code=status.HTTP_200_OK,
    summary="Get dashboard statistics",
    description="Retrieve comprehensive dashboard analytics for dealer",
)
async def get_dashboard_statistics(
    current_user: CurrentDealer,
    db: DatabaseSession,
    dealer_id: Annotated[
        uuid.UUID,
        Query(description="Dealer unique identifier"),
    ],
) -> DealerDashboardStats:
    """
    Get dashboard statistics and analytics.

    Args:
        current_user: Authenticated dealer user
        db: Database session
        dealer_id: Dealer identifier

    Returns:
        Dashboard statistics

    Raises:
        HTTPException: 403 if unauthorized, 500 if operation fails
    """
    try:
        logger.info(
            "Fetching dashboard statistics",
            dealer_id=str(dealer_id),
            user_id=str(current_user.id),
        )

        service = get_dealer_inventory_service(db)

        stats = await service.get_dashboard_statistics(
            dealer_id=dealer_id,
            user_id=current_user.id,
        )

        logger.info(
            "Dashboard statistics fetched successfully",
            dealer_id=str(dealer_id),
            total_vehicles=stats.total_vehicles,
        )

        return stats

    except DealerAuthorizationError as e:
        logger.warning(
            "Authorization failed for dashboard access",
            dealer_id=str(dealer_id),
            user_id=str(current_user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except DealerServiceError as e:
        logger.error(
            "Service error fetching dashboard statistics",
            dealer_id=str(dealer_id),
            error=str(e),
            error_code=e.code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard statistics",
        )
    except Exception as e:
        logger.error(
            "Unexpected error fetching dashboard statistics",
            dealer_id=str(dealer_id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )