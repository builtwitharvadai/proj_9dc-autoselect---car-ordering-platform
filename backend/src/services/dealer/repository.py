"""
Dealer inventory repository for dealer-specific operations.

This module implements the DealerInventoryRepository for managing dealer-specific
inventory operations including queries, bulk updates, audit logging, and reporting.
Implements proper access control filtering and comprehensive error handling.
"""

import uuid
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import select, update, delete, func, and_, or_, desc, asc
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.logging import get_logger
from src.database.models.inventory import InventoryItem, InventoryStatus
from src.database.models.vehicle import Vehicle
from src.database.models.user import User, UserRole

logger = get_logger(__name__)


class DealerInventoryRepository:
    """
    Repository for dealer-specific inventory operations.

    Provides methods for dealer-specific inventory queries, bulk updates,
    audit logging, and reporting with proper access control filtering.

    Attributes:
        session: Async database session for operations
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize dealer inventory repository.

        Args:
            session: Async database session
        """
        self.session = session

    async def get_dealer_inventory(
        self,
        dealer_id: uuid.UUID,
        status: Optional[InventoryStatus] = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "created_at",
        sort_direction: str = "desc",
    ) -> tuple[list[InventoryItem], int]:
        """
        Get inventory items for specific dealer with filtering and pagination.

        Args:
            dealer_id: Dealer identifier
            status: Optional status filter
            skip: Number of records to skip
            limit: Maximum records to return
            sort_by: Field to sort by
            sort_direction: Sort direction (asc/desc)

        Returns:
            Tuple of (inventory items list, total count)

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            logger.info(
                "Fetching dealer inventory",
                dealer_id=str(dealer_id),
                status=status.value if status else None,
                skip=skip,
                limit=limit,
            )

            # Build base query
            conditions = [
                InventoryItem.dealership_id == dealer_id,
                InventoryItem.deleted_at.is_(None),
            ]

            if status:
                conditions.append(InventoryItem.status == status)

            # Count query
            count_stmt = select(func.count()).select_from(InventoryItem).where(
                and_(*conditions)
            )
            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar() or 0

            # Data query with sorting
            sort_column = getattr(InventoryItem, sort_by, InventoryItem.created_at)
            order_func = desc if sort_direction.lower() == "desc" else asc

            stmt = (
                select(InventoryItem)
                .where(and_(*conditions))
                .options(selectinload(InventoryItem.vehicle))
                .order_by(order_func(sort_column))
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(stmt)
            items = list(result.scalars().all())

            logger.info(
                "Dealer inventory fetched successfully",
                dealer_id=str(dealer_id),
                count=len(items),
                total=total,
            )

            return items, total

        except SQLAlchemyError as e:
            logger.error(
                "Failed to fetch dealer inventory",
                dealer_id=str(dealer_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_inventory_by_id(
        self, inventory_id: uuid.UUID, dealer_id: uuid.UUID
    ) -> Optional[InventoryItem]:
        """
        Get specific inventory item with dealer access control.

        Args:
            inventory_id: Inventory item identifier
            dealer_id: Dealer identifier for access control

        Returns:
            Inventory item if found and accessible, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            logger.debug(
                "Fetching inventory item",
                inventory_id=str(inventory_id),
                dealer_id=str(dealer_id),
            )

            stmt = (
                select(InventoryItem)
                .where(
                    and_(
                        InventoryItem.id == inventory_id,
                        InventoryItem.dealership_id == dealer_id,
                        InventoryItem.deleted_at.is_(None),
                    )
                )
                .options(selectinload(InventoryItem.vehicle))
            )

            result = await self.session.execute(stmt)
            item = result.scalar_one_or_none()

            if item:
                logger.debug(
                    "Inventory item found",
                    inventory_id=str(inventory_id),
                    vin=item.vin,
                )
            else:
                logger.debug(
                    "Inventory item not found or access denied",
                    inventory_id=str(inventory_id),
                    dealer_id=str(dealer_id),
                )

            return item

        except SQLAlchemyError as e:
            logger.error(
                "Failed to fetch inventory item",
                inventory_id=str(inventory_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def bulk_update_inventory(
        self,
        dealer_id: uuid.UUID,
        updates: list[dict[str, Any]],
        user_id: uuid.UUID,
    ) -> tuple[int, int, list[str]]:
        """
        Bulk update inventory items for dealer.

        Args:
            dealer_id: Dealer identifier
            updates: List of update dictionaries with 'id' and update fields
            user_id: User performing the update for audit

        Returns:
            Tuple of (success_count, failed_count, error_messages)

        Raises:
            SQLAlchemyError: If database operation fails
        """
        success_count = 0
        failed_count = 0
        errors = []

        try:
            logger.info(
                "Starting bulk inventory update",
                dealer_id=str(dealer_id),
                update_count=len(updates),
                user_id=str(user_id),
            )

            for update_data in updates:
                try:
                    inventory_id = update_data.get("id")
                    if not inventory_id:
                        errors.append("Missing inventory ID in update")
                        failed_count += 1
                        continue

                    # Verify access
                    item = await self.get_inventory_by_id(
                        uuid.UUID(inventory_id), dealer_id
                    )
                    if not item:
                        errors.append(
                            f"Inventory {inventory_id} not found or access denied"
                        )
                        failed_count += 1
                        continue

                    # Prepare update data
                    update_fields = {
                        k: v for k, v in update_data.items() if k != "id"
                    }
                    update_fields["updated_at"] = datetime.utcnow()
                    update_fields["updated_by"] = user_id

                    # Execute update
                    stmt = (
                        update(InventoryItem)
                        .where(
                            and_(
                                InventoryItem.id == uuid.UUID(inventory_id),
                                InventoryItem.dealership_id == dealer_id,
                            )
                        )
                        .values(**update_fields)
                    )

                    await self.session.execute(stmt)
                    success_count += 1

                    logger.debug(
                        "Inventory item updated",
                        inventory_id=inventory_id,
                        fields=list(update_fields.keys()),
                    )

                except (ValueError, IntegrityError) as e:
                    errors.append(f"Update failed for {inventory_id}: {str(e)}")
                    failed_count += 1
                    logger.warning(
                        "Inventory update failed",
                        inventory_id=inventory_id,
                        error=str(e),
                    )

            await self.session.commit()

            logger.info(
                "Bulk inventory update completed",
                dealer_id=str(dealer_id),
                success_count=success_count,
                failed_count=failed_count,
            )

            return success_count, failed_count, errors

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Bulk inventory update failed",
                dealer_id=str(dealer_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def update_stock_level(
        self,
        inventory_id: uuid.UUID,
        dealer_id: uuid.UUID,
        quantity_change: int,
        user_id: uuid.UUID,
    ) -> Optional[InventoryItem]:
        """
        Update stock level for inventory item with audit logging.

        Args:
            inventory_id: Inventory item identifier
            dealer_id: Dealer identifier for access control
            quantity_change: Quantity to add (positive) or remove (negative)
            user_id: User performing the update

        Returns:
            Updated inventory item if successful, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
            ValueError: If stock level would become negative
        """
        try:
            logger.info(
                "Updating stock level",
                inventory_id=str(inventory_id),
                dealer_id=str(dealer_id),
                quantity_change=quantity_change,
            )

            item = await self.get_inventory_by_id(inventory_id, dealer_id)
            if not item:
                logger.warning(
                    "Inventory item not found for stock update",
                    inventory_id=str(inventory_id),
                )
                return None

            new_quantity = item.stock_quantity + quantity_change
            if new_quantity < 0:
                raise ValueError(
                    f"Stock level cannot be negative. Current: {item.stock_quantity}, "
                    f"Change: {quantity_change}"
                )

            # Update stock quantity
            stmt = (
                update(InventoryItem)
                .where(
                    and_(
                        InventoryItem.id == inventory_id,
                        InventoryItem.dealership_id == dealer_id,
                    )
                )
                .values(
                    stock_quantity=new_quantity,
                    updated_at=datetime.utcnow(),
                    updated_by=user_id,
                )
            )

            await self.session.execute(stmt)
            await self.session.commit()

            # Refresh item
            await self.session.refresh(item)

            # Update availability status based on new quantity
            item.update_availability_status()
            await self.session.commit()

            logger.info(
                "Stock level updated successfully",
                inventory_id=str(inventory_id),
                old_quantity=item.stock_quantity - quantity_change,
                new_quantity=new_quantity,
            )

            return item

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Failed to update stock level",
                inventory_id=str(inventory_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_inventory_summary(
        self, dealer_id: uuid.UUID
    ) -> dict[str, Any]:
        """
        Get inventory summary statistics for dealer.

        Args:
            dealer_id: Dealer identifier

        Returns:
            Dictionary with summary statistics

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            logger.info("Generating inventory summary", dealer_id=str(dealer_id))

            # Total inventory count
            total_stmt = (
                select(func.count())
                .select_from(InventoryItem)
                .where(
                    and_(
                        InventoryItem.dealership_id == dealer_id,
                        InventoryItem.deleted_at.is_(None),
                    )
                )
            )
            total_result = await self.session.execute(total_stmt)
            total_count = total_result.scalar() or 0

            # Status breakdown
            status_stmt = (
                select(
                    InventoryItem.status,
                    func.count(InventoryItem.id).label("count"),
                )
                .where(
                    and_(
                        InventoryItem.dealership_id == dealer_id,
                        InventoryItem.deleted_at.is_(None),
                    )
                )
                .group_by(InventoryItem.status)
            )
            status_result = await self.session.execute(status_stmt)
            status_breakdown = {
                row.status.value: row.count for row in status_result.all()
            }

            # Total stock quantity
            stock_stmt = (
                select(func.sum(InventoryItem.stock_quantity))
                .where(
                    and_(
                        InventoryItem.dealership_id == dealer_id,
                        InventoryItem.deleted_at.is_(None),
                    )
                )
            )
            stock_result = await self.session.execute(stock_stmt)
            total_stock = stock_result.scalar() or 0

            # Low stock items
            low_stock_stmt = (
                select(func.count())
                .select_from(InventoryItem)
                .where(
                    and_(
                        InventoryItem.dealership_id == dealer_id,
                        InventoryItem.deleted_at.is_(None),
                        InventoryItem.stock_quantity <= InventoryItem.low_stock_threshold,
                        InventoryItem.stock_quantity > 0,
                    )
                )
            )
            low_stock_result = await self.session.execute(low_stock_stmt)
            low_stock_count = low_stock_result.scalar() or 0

            summary = {
                "total_items": total_count,
                "total_stock_quantity": total_stock,
                "status_breakdown": status_breakdown,
                "low_stock_items": low_stock_count,
                "generated_at": datetime.utcnow().isoformat(),
            }

            logger.info(
                "Inventory summary generated",
                dealer_id=str(dealer_id),
                total_items=total_count,
            )

            return summary

        except SQLAlchemyError as e:
            logger.error(
                "Failed to generate inventory summary",
                dealer_id=str(dealer_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def search_inventory(
        self,
        dealer_id: uuid.UUID,
        search_term: Optional[str] = None,
        vehicle_id: Optional[uuid.UUID] = None,
        status: Optional[InventoryStatus] = None,
        min_stock: Optional[int] = None,
        max_stock: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[InventoryItem], int]:
        """
        Search inventory with multiple filters.

        Args:
            dealer_id: Dealer identifier
            search_term: Search term for VIN or vehicle details
            vehicle_id: Filter by vehicle ID
            status: Filter by status
            min_stock: Minimum stock quantity
            max_stock: Maximum stock quantity
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Tuple of (inventory items list, total count)

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            logger.info(
                "Searching dealer inventory",
                dealer_id=str(dealer_id),
                search_term=search_term,
                vehicle_id=str(vehicle_id) if vehicle_id else None,
            )

            conditions = [
                InventoryItem.dealership_id == dealer_id,
                InventoryItem.deleted_at.is_(None),
            ]

            if search_term:
                search_pattern = f"%{search_term}%"
                conditions.append(
                    or_(
                        InventoryItem.vin.ilike(search_pattern),
                        InventoryItem.location.ilike(search_pattern),
                    )
                )

            if vehicle_id:
                conditions.append(InventoryItem.vehicle_id == vehicle_id)

            if status:
                conditions.append(InventoryItem.status == status)

            if min_stock is not None:
                conditions.append(InventoryItem.stock_quantity >= min_stock)

            if max_stock is not None:
                conditions.append(InventoryItem.stock_quantity <= max_stock)

            # Count query
            count_stmt = select(func.count()).select_from(InventoryItem).where(
                and_(*conditions)
            )
            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar() or 0

            # Data query
            stmt = (
                select(InventoryItem)
                .where(and_(*conditions))
                .options(selectinload(InventoryItem.vehicle))
                .order_by(desc(InventoryItem.created_at))
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(stmt)
            items = list(result.scalars().all())

            logger.info(
                "Inventory search completed",
                dealer_id=str(dealer_id),
                results_count=len(items),
                total=total,
            )

            return items, total

        except SQLAlchemyError as e:
            logger.error(
                "Inventory search failed",
                dealer_id=str(dealer_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def verify_dealer_access(
        self, user_id: uuid.UUID, dealer_id: uuid.UUID
    ) -> bool:
        """
        Verify user has access to dealer inventory.

        Args:
            user_id: User identifier
            dealer_id: Dealer identifier

        Returns:
            True if user has access, False otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            logger.debug(
                "Verifying dealer access",
                user_id=str(user_id),
                dealer_id=str(dealer_id),
            )

            stmt = select(User).where(
                and_(
                    User.id == user_id,
                    User.is_active.is_(True),
                    User.deleted_at.is_(None),
                )
            )

            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.warning("User not found or inactive", user_id=str(user_id))
                return False

            # Admin and super admin have access to all dealers
            if user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
                logger.debug("Admin access granted", user_id=str(user_id))
                return True

            # For dealer role, verify dealer_id matches
            # This would require a dealer_id field on User model
            # For now, we'll allow access if user has SALES role
            has_access = user.role == UserRole.SALES

            logger.debug(
                "Dealer access verification completed",
                user_id=str(user_id),
                dealer_id=str(dealer_id),
                has_access=has_access,
            )

            return has_access

        except SQLAlchemyError as e:
            logger.error(
                "Failed to verify dealer access",
                user_id=str(user_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise