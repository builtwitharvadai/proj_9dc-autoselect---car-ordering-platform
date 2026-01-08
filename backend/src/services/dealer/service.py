"""
Dealer inventory management service for business logic operations.

This module implements the DealerInventoryService providing comprehensive
business logic for dealer inventory management including CRUD operations,
bulk updates, audit logging, dashboard analytics, and authorization checks.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.models.inventory import InventoryItem, InventoryStatus
from src.schemas.dealer import (
    BulkInventoryResponse,
    BulkInventoryUpdate,
    DealerDashboardStats,
    DealerInventoryResponse,
    DealerInventoryUpdate,
)
from src.services.dealer.file_processor import FileProcessor, get_file_processor
from src.services.dealer.repository import DealerInventoryRepository

logger = get_logger(__name__)


class DealerServiceError(Exception):
    """Base exception for dealer service errors."""

    def __init__(
        self,
        message: str,
        code: str,
        **context: Any,
    ):
        super().__init__(message)
        self.code = code
        self.context = context


class DealerAuthorizationError(DealerServiceError):
    """Exception raised for authorization failures."""

    pass


class DealerInventoryNotFoundError(DealerServiceError):
    """Exception raised when inventory item is not found."""

    pass


class DealerInventoryService:
    """
    Service for dealer inventory management business logic.

    Provides methods for inventory operations, bulk updates, audit logging,
    and dashboard analytics with proper authorization and validation.

    Attributes:
        repository: Dealer inventory repository instance
        file_processor: File processor for CSV/Excel uploads
    """

    def __init__(
        self,
        session: AsyncSession,
        file_processor: Optional[FileProcessor] = None,
    ):
        """
        Initialize dealer inventory service.

        Args:
            session: Async database session
            file_processor: Optional file processor instance
        """
        self.repository = DealerInventoryRepository(session)
        self.file_processor = file_processor or get_file_processor()
        self.session = session

    async def get_dealer_inventory(
        self,
        dealer_id: uuid.UUID,
        user_id: uuid.UUID,
        status: Optional[InventoryStatus] = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "created_at",
        sort_direction: str = "desc",
    ) -> tuple[list[DealerInventoryResponse], int]:
        """
        Get inventory items for dealer with authorization check.

        Args:
            dealer_id: Dealer identifier
            user_id: User requesting the data
            status: Optional status filter
            skip: Number of records to skip
            limit: Maximum records to return
            sort_by: Field to sort by
            sort_direction: Sort direction (asc/desc)

        Returns:
            Tuple of (inventory responses list, total count)

        Raises:
            DealerAuthorizationError: If user lacks access
            DealerServiceError: If operation fails
        """
        try:
            logger.info(
                "Fetching dealer inventory",
                dealer_id=str(dealer_id),
                user_id=str(user_id),
                status=status.value if status else None,
            )

            # Verify authorization
            has_access = await self.repository.verify_dealer_access(
                user_id, dealer_id
            )
            if not has_access:
                raise DealerAuthorizationError(
                    "User does not have access to dealer inventory",
                    code="ACCESS_DENIED",
                    dealer_id=str(dealer_id),
                    user_id=str(user_id),
                )

            # Fetch inventory
            items, total = await self.repository.get_dealer_inventory(
                dealer_id=dealer_id,
                status=status,
                skip=skip,
                limit=limit,
                sort_by=sort_by,
                sort_direction=sort_direction,
            )

            # Convert to response models
            responses = [self._to_response(item) for item in items]

            logger.info(
                "Dealer inventory fetched successfully",
                dealer_id=str(dealer_id),
                count=len(responses),
                total=total,
            )

            return responses, total

        except DealerAuthorizationError:
            raise
        except SQLAlchemyError as e:
            logger.error(
                "Database error fetching dealer inventory",
                dealer_id=str(dealer_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerServiceError(
                "Failed to fetch dealer inventory",
                code="DB_ERROR",
                dealer_id=str(dealer_id),
            ) from e
        except Exception as e:
            logger.error(
                "Unexpected error fetching dealer inventory",
                dealer_id=str(dealer_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerServiceError(
                "Failed to fetch dealer inventory",
                code="UNKNOWN_ERROR",
                dealer_id=str(dealer_id),
            ) from e

    async def get_inventory_item(
        self,
        inventory_id: uuid.UUID,
        dealer_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> DealerInventoryResponse:
        """
        Get specific inventory item with authorization check.

        Args:
            inventory_id: Inventory item identifier
            dealer_id: Dealer identifier
            user_id: User requesting the data

        Returns:
            Inventory item response

        Raises:
            DealerAuthorizationError: If user lacks access
            DealerInventoryNotFoundError: If item not found
            DealerServiceError: If operation fails
        """
        try:
            logger.info(
                "Fetching inventory item",
                inventory_id=str(inventory_id),
                dealer_id=str(dealer_id),
                user_id=str(user_id),
            )

            # Verify authorization
            has_access = await self.repository.verify_dealer_access(
                user_id, dealer_id
            )
            if not has_access:
                raise DealerAuthorizationError(
                    "User does not have access to dealer inventory",
                    code="ACCESS_DENIED",
                    dealer_id=str(dealer_id),
                    user_id=str(user_id),
                )

            # Fetch item
            item = await self.repository.get_inventory_by_id(
                inventory_id, dealer_id
            )
            if not item:
                raise DealerInventoryNotFoundError(
                    "Inventory item not found",
                    code="NOT_FOUND",
                    inventory_id=str(inventory_id),
                    dealer_id=str(dealer_id),
                )

            response = self._to_response(item)

            logger.info(
                "Inventory item fetched successfully",
                inventory_id=str(inventory_id),
            )

            return response

        except (DealerAuthorizationError, DealerInventoryNotFoundError):
            raise
        except SQLAlchemyError as e:
            logger.error(
                "Database error fetching inventory item",
                inventory_id=str(inventory_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerServiceError(
                "Failed to fetch inventory item",
                code="DB_ERROR",
                inventory_id=str(inventory_id),
            ) from e
        except Exception as e:
            logger.error(
                "Unexpected error fetching inventory item",
                inventory_id=str(inventory_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerServiceError(
                "Failed to fetch inventory item",
                code="UNKNOWN_ERROR",
                inventory_id=str(inventory_id),
            ) from e

    async def update_inventory_item(
        self,
        inventory_id: uuid.UUID,
        dealer_id: uuid.UUID,
        user_id: uuid.UUID,
        update_data: DealerInventoryUpdate,
    ) -> DealerInventoryResponse:
        """
        Update inventory item with authorization and validation.

        Args:
            inventory_id: Inventory item identifier
            dealer_id: Dealer identifier
            user_id: User performing the update
            update_data: Update data

        Returns:
            Updated inventory item response

        Raises:
            DealerAuthorizationError: If user lacks access
            DealerInventoryNotFoundError: If item not found
            DealerServiceError: If operation fails
        """
        try:
            logger.info(
                "Updating inventory item",
                inventory_id=str(inventory_id),
                dealer_id=str(dealer_id),
                user_id=str(user_id),
            )

            # Verify authorization
            has_access = await self.repository.verify_dealer_access(
                user_id, dealer_id
            )
            if not has_access:
                raise DealerAuthorizationError(
                    "User does not have access to dealer inventory",
                    code="ACCESS_DENIED",
                    dealer_id=str(dealer_id),
                    user_id=str(user_id),
                )

            # Prepare update dictionary
            update_dict = {
                "id": str(inventory_id),
                **update_data.model_dump(exclude_unset=True),
            }

            # Perform bulk update with single item
            success_count, failed_count, errors = (
                await self.repository.bulk_update_inventory(
                    dealer_id=dealer_id,
                    updates=[update_dict],
                    user_id=user_id,
                )
            )

            if failed_count > 0:
                error_msg = errors[0] if errors else "Update failed"
                raise DealerServiceError(
                    f"Failed to update inventory item: {error_msg}",
                    code="UPDATE_FAILED",
                    inventory_id=str(inventory_id),
                )

            # Fetch updated item
            item = await self.repository.get_inventory_by_id(
                inventory_id, dealer_id
            )
            if not item:
                raise DealerInventoryNotFoundError(
                    "Inventory item not found after update",
                    code="NOT_FOUND",
                    inventory_id=str(inventory_id),
                )

            response = self._to_response(item)

            logger.info(
                "Inventory item updated successfully",
                inventory_id=str(inventory_id),
            )

            return response

        except (DealerAuthorizationError, DealerInventoryNotFoundError):
            raise
        except SQLAlchemyError as e:
            logger.error(
                "Database error updating inventory item",
                inventory_id=str(inventory_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerServiceError(
                "Failed to update inventory item",
                code="DB_ERROR",
                inventory_id=str(inventory_id),
            ) from e
        except Exception as e:
            logger.error(
                "Unexpected error updating inventory item",
                inventory_id=str(inventory_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerServiceError(
                "Failed to update inventory item",
                code="UNKNOWN_ERROR",
                inventory_id=str(inventory_id),
            ) from e

    async def bulk_update_inventory(
        self,
        dealer_id: uuid.UUID,
        user_id: uuid.UUID,
        bulk_update: BulkInventoryUpdate,
    ) -> BulkInventoryResponse:
        """
        Perform bulk inventory update with validation.

        Args:
            dealer_id: Dealer identifier
            user_id: User performing the update
            bulk_update: Bulk update data

        Returns:
            Bulk update response with results

        Raises:
            DealerAuthorizationError: If user lacks access
            DealerServiceError: If operation fails
        """
        start_time = datetime.now()

        try:
            logger.info(
                "Starting bulk inventory update",
                dealer_id=str(dealer_id),
                user_id=str(user_id),
                item_count=len(bulk_update.items),
                operation=bulk_update.operation,
            )

            # Verify authorization
            has_access = await self.repository.verify_dealer_access(
                user_id, dealer_id
            )
            if not has_access:
                raise DealerAuthorizationError(
                    "User does not have access to dealer inventory",
                    code="ACCESS_DENIED",
                    dealer_id=str(dealer_id),
                    user_id=str(user_id),
                )

            # Validate only mode
            if bulk_update.validate_only:
                logger.info(
                    "Validation-only mode, skipping persistence",
                    dealer_id=str(dealer_id),
                )
                return BulkInventoryResponse(
                    total_items=len(bulk_update.items),
                    successful_items=len(bulk_update.items),
                    failed_items=0,
                    errors=[],
                    warnings=[],
                    processed_ids=[],
                    processing_time_ms=0,
                )

            # Convert items to update dictionaries
            updates = [
                {
                    "id": str(item.vehicle_id),
                    "quantity": item.quantity,
                    "status": item.status,
                    "location": item.location,
                    "vin": item.vin,
                    "notes": item.notes,
                }
                for item in bulk_update.items
            ]

            # Perform bulk update
            success_count, failed_count, errors = (
                await self.repository.bulk_update_inventory(
                    dealer_id=dealer_id,
                    updates=updates,
                    user_id=user_id,
                )
            )

            # Calculate processing time
            processing_time_ms = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )

            # Build error list
            error_list = [
                {"message": error, "code": "UPDATE_FAILED"}
                for error in errors
            ]

            response = BulkInventoryResponse(
                total_items=len(bulk_update.items),
                successful_items=success_count,
                failed_items=failed_count,
                errors=error_list,
                warnings=[],
                processed_ids=[],
                processing_time_ms=processing_time_ms,
            )

            logger.info(
                "Bulk inventory update completed",
                dealer_id=str(dealer_id),
                success_count=success_count,
                failed_count=failed_count,
                processing_time_ms=processing_time_ms,
            )

            return response

        except DealerAuthorizationError:
            raise
        except SQLAlchemyError as e:
            logger.error(
                "Database error during bulk update",
                dealer_id=str(dealer_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerServiceError(
                "Failed to perform bulk update",
                code="DB_ERROR",
                dealer_id=str(dealer_id),
            ) from e
        except Exception as e:
            logger.error(
                "Unexpected error during bulk update",
                dealer_id=str(dealer_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerServiceError(
                "Failed to perform bulk update",
                code="UNKNOWN_ERROR",
                dealer_id=str(dealer_id),
            ) from e

    async def process_file_upload(
        self,
        file_path: str,
        dealer_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Process uploaded CSV/Excel file for bulk inventory update.

        Args:
            file_path: Path to uploaded file
            dealer_id: Dealer identifier
            user_id: User who uploaded the file

        Returns:
            Processing results dictionary

        Raises:
            DealerAuthorizationError: If user lacks access
            DealerServiceError: If processing fails
        """
        try:
            logger.info(
                "Processing file upload",
                file_path=file_path,
                dealer_id=str(dealer_id),
                user_id=str(user_id),
            )

            # Verify authorization
            has_access = await self.repository.verify_dealer_access(
                user_id, dealer_id
            )
            if not has_access:
                raise DealerAuthorizationError(
                    "User does not have access to dealer inventory",
                    code="ACCESS_DENIED",
                    dealer_id=str(dealer_id),
                    user_id=str(user_id),
                )

            # Process file
            result = await self.file_processor.process_file(
                file_path=file_path,
                dealer_id=dealer_id,
                user_id=user_id,
            )

            logger.info(
                "File upload processed successfully",
                file_path=file_path,
                valid_items=result["valid_items"],
                invalid_items=result["invalid_items"],
            )

            return result

        except DealerAuthorizationError:
            raise
        except Exception as e:
            logger.error(
                "Error processing file upload",
                file_path=file_path,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerServiceError(
                "Failed to process file upload",
                code="FILE_PROCESSING_ERROR",
                file_path=file_path,
            ) from e

    async def adjust_stock_level(
        self,
        inventory_id: uuid.UUID,
        dealer_id: uuid.UUID,
        user_id: uuid.UUID,
        quantity_change: int,
    ) -> DealerInventoryResponse:
        """
        Adjust stock level for inventory item with audit logging.

        Args:
            inventory_id: Inventory item identifier
            dealer_id: Dealer identifier
            user_id: User performing the adjustment
            quantity_change: Quantity to add (positive) or remove (negative)

        Returns:
            Updated inventory item response

        Raises:
            DealerAuthorizationError: If user lacks access
            DealerInventoryNotFoundError: If item not found
            DealerServiceError: If operation fails
        """
        try:
            logger.info(
                "Adjusting stock level",
                inventory_id=str(inventory_id),
                dealer_id=str(dealer_id),
                user_id=str(user_id),
                quantity_change=quantity_change,
            )

            # Verify authorization
            has_access = await self.repository.verify_dealer_access(
                user_id, dealer_id
            )
            if not has_access:
                raise DealerAuthorizationError(
                    "User does not have access to dealer inventory",
                    code="ACCESS_DENIED",
                    dealer_id=str(dealer_id),
                    user_id=str(user_id),
                )

            # Adjust stock level
            item = await self.repository.update_stock_level(
                inventory_id=inventory_id,
                dealer_id=dealer_id,
                quantity_change=quantity_change,
                user_id=user_id,
            )

            if not item:
                raise DealerInventoryNotFoundError(
                    "Inventory item not found",
                    code="NOT_FOUND",
                    inventory_id=str(inventory_id),
                )

            response = self._to_response(item)

            logger.info(
                "Stock level adjusted successfully",
                inventory_id=str(inventory_id),
                new_quantity=item.stock_quantity,
            )

            return response

        except (DealerAuthorizationError, DealerInventoryNotFoundError):
            raise
        except ValueError as e:
            logger.warning(
                "Invalid stock adjustment",
                inventory_id=str(inventory_id),
                error=str(e),
            )
            raise DealerServiceError(
                str(e),
                code="INVALID_ADJUSTMENT",
                inventory_id=str(inventory_id),
            ) from e
        except SQLAlchemyError as e:
            logger.error(
                "Database error adjusting stock level",
                inventory_id=str(inventory_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerServiceError(
                "Failed to adjust stock level",
                code="DB_ERROR",
                inventory_id=str(inventory_id),
            ) from e
        except Exception as e:
            logger.error(
                "Unexpected error adjusting stock level",
                inventory_id=str(inventory_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerServiceError(
                "Failed to adjust stock level",
                code="UNKNOWN_ERROR",
                inventory_id=str(inventory_id),
            ) from e

    async def get_dashboard_statistics(
        self,
        dealer_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> DealerDashboardStats:
        """
        Get dashboard statistics for dealer.

        Args:
            dealer_id: Dealer identifier
            user_id: User requesting the statistics

        Returns:
            Dashboard statistics

        Raises:
            DealerAuthorizationError: If user lacks access
            DealerServiceError: If operation fails
        """
        try:
            logger.info(
                "Fetching dashboard statistics",
                dealer_id=str(dealer_id),
                user_id=str(user_id),
            )

            # Verify authorization
            has_access = await self.repository.verify_dealer_access(
                user_id, dealer_id
            )
            if not has_access:
                raise DealerAuthorizationError(
                    "User does not have access to dealer inventory",
                    code="ACCESS_DENIED",
                    dealer_id=str(dealer_id),
                    user_id=str(user_id),
                )

            # Get inventory summary
            summary = await self.repository.get_inventory_summary(dealer_id)

            # Build dashboard stats
            stats = DealerDashboardStats(
                dealer_id=dealer_id,
                total_vehicles=summary["total_items"],
                active_vehicles=summary["status_breakdown"].get("active", 0),
                inactive_vehicles=summary["status_breakdown"].get("inactive", 0),
                sold_vehicles=summary["status_breakdown"].get("sold", 0),
                reserved_vehicles=summary["status_breakdown"].get("reserved", 0),
                total_inventory_value=0,
                average_vehicle_price=0,
                low_stock_count=summary["low_stock_items"],
                out_of_stock_count=0,
                recent_updates_count=0,
                pending_orders_count=0,
                last_updated=datetime.fromisoformat(summary["generated_at"]),
                top_makes=[],
                top_models=[],
                inventory_by_status=summary["status_breakdown"],
                inventory_by_body_style={},
            )

            logger.info(
                "Dashboard statistics fetched successfully",
                dealer_id=str(dealer_id),
                total_vehicles=stats.total_vehicles,
            )

            return stats

        except DealerAuthorizationError:
            raise
        except SQLAlchemyError as e:
            logger.error(
                "Database error fetching dashboard statistics",
                dealer_id=str(dealer_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerServiceError(
                "Failed to fetch dashboard statistics",
                code="DB_ERROR",
                dealer_id=str(dealer_id),
            ) from e
        except Exception as e:
            logger.error(
                "Unexpected error fetching dashboard statistics",
                dealer_id=str(dealer_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise DealerServiceError(
                "Failed to fetch dashboard statistics",
                code="UNKNOWN_ERROR",
                dealer_id=str(dealer_id),
            ) from e

    def _to_response(self, item: InventoryItem) -> DealerInventoryResponse:
        """
        Convert inventory item to response model.

        Args:
            item: Inventory item database model

        Returns:
            Inventory item response
        """
        return DealerInventoryResponse(
            id=item.id,
            dealer_id=item.dealership_id,
            vehicle_id=item.vehicle_id,
            quantity=item.stock_quantity,
            location=item.location,
            status=item.status.value,
            vin=item.vin,
            notes=item.notes,
            custom_attributes=item.custom_attributes or {},
            created_at=item.created_at,
            updated_at=item.updated_at,
            created_by=item.created_by,
            updated_by=item.updated_by,
        )


def get_dealer_inventory_service(
    session: AsyncSession,
    file_processor: Optional[FileProcessor] = None,
) -> DealerInventoryService:
    """
    Get dealer inventory service instance.

    Args:
        session: Async database session
        file_processor: Optional file processor instance

    Returns:
        DealerInventoryService instance
    """
    return DealerInventoryService(session=session, file_processor=file_processor)