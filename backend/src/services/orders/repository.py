"""
Order data access repository with transaction support.

This module implements the OrderRepository class providing async methods for
creating orders with items, updating order status, retrieving orders with
filters, and managing order history. Includes atomic transaction support for
order creation and comprehensive error handling with structured logging.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any, Sequence

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from src.core.logging import get_logger
from src.database.models.order import (
    Order,
    OrderItem,
    OrderStatusHistory,
    OrderStatus,
    PaymentStatus,
    FulfillmentStatus,
)

logger = get_logger(__name__)


class OrderRepositoryError(Exception):
    """Base exception for order repository errors."""

    def __init__(self, message: str, **context: Any):
        super().__init__(message)
        self.context = context


class OrderNotFoundError(OrderRepositoryError):
    """Raised when order is not found."""

    pass


class OrderCreationError(OrderRepositoryError):
    """Raised when order creation fails."""

    pass


class OrderUpdateError(OrderRepositoryError):
    """Raised when order update fails."""

    pass


class OrderRepository:
    """
    Repository for order data access operations.

    Provides async methods for CRUD operations on orders with support for
    atomic transactions, filtering, pagination, and relationship loading.
    Implements comprehensive error handling and structured logging.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize order repository.

        Args:
            session: Async database session
        """
        self.session = session

    async def create_order_with_items(
        self,
        user_id: uuid.UUID,
        vehicle_id: uuid.UUID,
        configuration_id: uuid.UUID,
        order_number: str,
        total_amount: Decimal,
        subtotal: Decimal,
        tax_amount: Decimal,
        items: Sequence[dict[str, Any]],
        customer_info: dict[str, Any],
        delivery_address: dict[str, Any],
        dealer_id: Optional[uuid.UUID] = None,
        manufacturer_id: Optional[uuid.UUID] = None,
        shipping_amount: Decimal = Decimal("0.00"),
        discount_amount: Decimal = Decimal("0.00"),
        total_fees: Decimal = Decimal("0.00"),
        notes: Optional[str] = None,
        special_instructions: Optional[str] = None,
        trade_in_info: Optional[dict[str, Any]] = None,
        estimated_delivery_date: Optional[datetime] = None,
    ) -> Order:
        """
        Create order with items atomically.

        Args:
            user_id: User placing the order
            vehicle_id: Vehicle being ordered
            configuration_id: Vehicle configuration
            order_number: Human-readable order number
            total_amount: Total order amount
            subtotal: Subtotal before taxes and fees
            tax_amount: Tax amount
            items: List of order items with configuration_id, quantity, unit_price
            customer_info: Customer information
            delivery_address: Delivery address
            dealer_id: Optional dealer handling order
            manufacturer_id: Optional manufacturer
            shipping_amount: Shipping charges
            discount_amount: Discount amount
            total_fees: Total fees
            notes: Optional order notes
            special_instructions: Optional special instructions
            trade_in_info: Optional trade-in information
            estimated_delivery_date: Optional estimated delivery date

        Returns:
            Created order with items

        Raises:
            OrderCreationError: If order creation fails
        """
        try:
            logger.info(
                "Creating order with items",
                user_id=str(user_id),
                vehicle_id=str(vehicle_id),
                order_number=order_number,
                item_count=len(items),
            )

            # Create order
            order = Order(
                user_id=user_id,
                vehicle_id=vehicle_id,
                configuration_id=configuration_id,
                dealer_id=dealer_id,
                manufacturer_id=manufacturer_id,
                order_number=order_number,
                status=OrderStatus.PENDING,
                payment_status=PaymentStatus.PENDING,
                fulfillment_status=FulfillmentStatus.PENDING,
                total_amount=total_amount,
                subtotal=subtotal,
                tax_amount=tax_amount,
                total_tax=tax_amount,
                shipping_amount=shipping_amount,
                discount_amount=discount_amount,
                total_fees=total_fees,
                customer_info=customer_info,
                delivery_address=delivery_address,
                trade_in_info=trade_in_info,
                notes=notes,
                special_instructions=special_instructions,
                estimated_delivery_date=estimated_delivery_date,
            )

            self.session.add(order)
            await self.session.flush()

            # Create order items
            order_items = []
            for item_data in items:
                order_item = OrderItem(
                    order_id=order.id,
                    vehicle_configuration_id=item_data["configuration_id"],
                    quantity=item_data["quantity"],
                    unit_price=item_data["unit_price"],
                    total_price=item_data["quantity"] * item_data["unit_price"],
                )
                order_items.append(order_item)
                self.session.add(order_item)

            # Create initial status history
            status_history = OrderStatusHistory(
                order_id=order.id,
                from_status=OrderStatus.PENDING,
                to_status=OrderStatus.PENDING,
                change_reason="Order created",
                metadata={"created_by": str(user_id)},
            )
            self.session.add(status_history)

            await self.session.flush()

            # Refresh to load relationships
            await self.session.refresh(
                order,
                ["order_items", "status_history", "user", "vehicle", "configuration"],
            )

            logger.info(
                "Order created successfully",
                order_id=str(order.id),
                order_number=order_number,
                item_count=len(order_items),
            )

            return order

        except IntegrityError as e:
            await self.session.rollback()
            logger.error(
                "Order creation failed - integrity error",
                error=str(e),
                order_number=order_number,
            )
            raise OrderCreationError(
                "Order creation failed due to data integrity violation",
                order_number=order_number,
                error=str(e),
            ) from e
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Order creation failed - database error",
                error=str(e),
                order_number=order_number,
            )
            raise OrderCreationError(
                "Order creation failed due to database error",
                order_number=order_number,
                error=str(e),
            ) from e
        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Order creation failed - unexpected error",
                error=str(e),
                error_type=type(e).__name__,
                order_number=order_number,
            )
            raise OrderCreationError(
                "Order creation failed due to unexpected error",
                order_number=order_number,
                error=str(e),
            ) from e

    async def get_order_by_id(
        self,
        order_id: uuid.UUID,
        include_items: bool = True,
        include_history: bool = False,
    ) -> Optional[Order]:
        """
        Get order by ID with optional relationships.

        Args:
            order_id: Order identifier
            include_items: Whether to load order items
            include_history: Whether to load status history

        Returns:
            Order if found, None otherwise

        Raises:
            OrderRepositoryError: If query fails
        """
        try:
            logger.debug("Fetching order by ID", order_id=str(order_id))

            stmt = select(Order).where(Order.id == order_id)

            # Load relationships
            options = []
            if include_items:
                options.append(selectinload(Order.order_items))
            if include_history:
                options.append(selectinload(Order.status_history))

            # Always load basic relationships
            options.extend(
                [
                    selectinload(Order.user),
                    selectinload(Order.vehicle),
                    selectinload(Order.configuration),
                ]
            )

            stmt = stmt.options(*options)

            result = await self.session.execute(stmt)
            order = result.scalar_one_or_none()

            if order:
                logger.debug("Order found", order_id=str(order_id))
            else:
                logger.debug("Order not found", order_id=str(order_id))

            return order

        except SQLAlchemyError as e:
            logger.error(
                "Failed to fetch order",
                order_id=str(order_id),
                error=str(e),
            )
            raise OrderRepositoryError(
                "Failed to fetch order",
                order_id=str(order_id),
                error=str(e),
            ) from e

    async def get_order_by_number(self, order_number: str) -> Optional[Order]:
        """
        Get order by order number.

        Args:
            order_number: Human-readable order number

        Returns:
            Order if found, None otherwise

        Raises:
            OrderRepositoryError: If query fails
        """
        try:
            logger.debug("Fetching order by number", order_number=order_number)

            stmt = (
                select(Order)
                .where(Order.order_number == order_number)
                .options(
                    selectinload(Order.order_items),
                    selectinload(Order.user),
                    selectinload(Order.vehicle),
                    selectinload(Order.configuration),
                )
            )

            result = await self.session.execute(stmt)
            order = result.scalar_one_or_none()

            if order:
                logger.debug("Order found", order_number=order_number)
            else:
                logger.debug("Order not found", order_number=order_number)

            return order

        except SQLAlchemyError as e:
            logger.error(
                "Failed to fetch order by number",
                order_number=order_number,
                error=str(e),
            )
            raise OrderRepositoryError(
                "Failed to fetch order by number",
                order_number=order_number,
                error=str(e),
            ) from e

    async def get_user_orders(
        self,
        user_id: uuid.UUID,
        status: Optional[OrderStatus] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Order], int]:
        """
        Get orders for user with pagination.

        Args:
            user_id: User identifier
            status: Optional status filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (orders, total_count)

        Raises:
            OrderRepositoryError: If query fails
        """
        try:
            logger.debug(
                "Fetching user orders",
                user_id=str(user_id),
                status=status.value if status else None,
                skip=skip,
                limit=limit,
            )

            # Build base query
            conditions = [Order.user_id == user_id, Order.deleted_at.is_(None)]
            if status:
                conditions.append(Order.status == status)

            stmt = (
                select(Order)
                .where(and_(*conditions))
                .options(
                    selectinload(Order.order_items),
                    selectinload(Order.vehicle),
                    selectinload(Order.configuration),
                )
                .order_by(Order.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            # Get total count
            count_stmt = select(func.count()).select_from(Order).where(and_(*conditions))

            result = await self.session.execute(stmt)
            count_result = await self.session.execute(count_stmt)

            orders = result.scalars().all()
            total_count = count_result.scalar_one()

            logger.debug(
                "User orders fetched",
                user_id=str(user_id),
                count=len(orders),
                total=total_count,
            )

            return orders, total_count

        except SQLAlchemyError as e:
            logger.error(
                "Failed to fetch user orders",
                user_id=str(user_id),
                error=str(e),
            )
            raise OrderRepositoryError(
                "Failed to fetch user orders",
                user_id=str(user_id),
                error=str(e),
            ) from e

    async def update_order_status(
        self,
        order_id: uuid.UUID,
        new_status: OrderStatus,
        changed_by: Optional[uuid.UUID] = None,
        change_reason: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Order:
        """
        Update order status with history tracking.

        Args:
            order_id: Order identifier
            new_status: New order status
            changed_by: User making the change
            change_reason: Reason for status change
            metadata: Additional metadata

        Returns:
            Updated order

        Raises:
            OrderNotFoundError: If order not found
            OrderUpdateError: If update fails
        """
        try:
            logger.info(
                "Updating order status",
                order_id=str(order_id),
                new_status=new_status.value,
            )

            # Get current order
            order = await self.get_order_by_id(order_id)
            if not order:
                raise OrderNotFoundError(
                    "Order not found",
                    order_id=str(order_id),
                )

            old_status = order.status

            # Update status
            order.status = new_status

            # Update delivery date if delivered
            if new_status == OrderStatus.DELIVERED and not order.actual_delivery_date:
                order.actual_delivery_date = datetime.utcnow()

            # Create status history
            status_history = OrderStatusHistory(
                order_id=order_id,
                from_status=old_status,
                to_status=new_status,
                changed_by=changed_by,
                change_reason=change_reason,
                metadata=metadata or {},
            )
            self.session.add(status_history)

            await self.session.flush()
            await self.session.refresh(order, ["status_history"])

            logger.info(
                "Order status updated",
                order_id=str(order_id),
                old_status=old_status.value,
                new_status=new_status.value,
            )

            return order

        except OrderNotFoundError:
            raise
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Failed to update order status",
                order_id=str(order_id),
                error=str(e),
            )
            raise OrderUpdateError(
                "Failed to update order status",
                order_id=str(order_id),
                error=str(e),
            ) from e

    async def update_payment_status(
        self,
        order_id: uuid.UUID,
        payment_status: PaymentStatus,
    ) -> Order:
        """
        Update order payment status.

        Args:
            order_id: Order identifier
            payment_status: New payment status

        Returns:
            Updated order

        Raises:
            OrderNotFoundError: If order not found
            OrderUpdateError: If update fails
        """
        try:
            logger.info(
                "Updating payment status",
                order_id=str(order_id),
                payment_status=payment_status.value,
            )

            stmt = (
                update(Order)
                .where(Order.id == order_id)
                .values(payment_status=payment_status)
                .returning(Order)
            )

            result = await self.session.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                raise OrderNotFoundError(
                    "Order not found",
                    order_id=str(order_id),
                )

            await self.session.flush()

            logger.info(
                "Payment status updated",
                order_id=str(order_id),
                payment_status=payment_status.value,
            )

            return order

        except OrderNotFoundError:
            raise
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Failed to update payment status",
                order_id=str(order_id),
                error=str(e),
            )
            raise OrderUpdateError(
                "Failed to update payment status",
                order_id=str(order_id),
                error=str(e),
            ) from e

    async def update_fulfillment_status(
        self,
        order_id: uuid.UUID,
        fulfillment_status: FulfillmentStatus,
    ) -> Order:
        """
        Update order fulfillment status.

        Args:
            order_id: Order identifier
            fulfillment_status: New fulfillment status

        Returns:
            Updated order

        Raises:
            OrderNotFoundError: If order not found
            OrderUpdateError: If update fails
        """
        try:
            logger.info(
                "Updating fulfillment status",
                order_id=str(order_id),
                fulfillment_status=fulfillment_status.value,
            )

            stmt = (
                update(Order)
                .where(Order.id == order_id)
                .values(fulfillment_status=fulfillment_status)
                .returning(Order)
            )

            result = await self.session.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                raise OrderNotFoundError(
                    "Order not found",
                    order_id=str(order_id),
                )

            await self.session.flush()

            logger.info(
                "Fulfillment status updated",
                order_id=str(order_id),
                fulfillment_status=fulfillment_status.value,
            )

            return order

        except OrderNotFoundError:
            raise
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Failed to update fulfillment status",
                order_id=str(order_id),
                error=str(e),
            )
            raise OrderUpdateError(
                "Failed to update fulfillment status",
                order_id=str(order_id),
                error=str(e),
            ) from e

    async def get_order_statistics(
        self,
        user_id: Optional[uuid.UUID] = None,
        dealer_id: Optional[uuid.UUID] = None,
    ) -> dict[str, Any]:
        """
        Get order statistics.

        Args:
            user_id: Optional user filter
            dealer_id: Optional dealer filter

        Returns:
            Dictionary with order statistics

        Raises:
            OrderRepositoryError: If query fails
        """
        try:
            logger.debug(
                "Fetching order statistics",
                user_id=str(user_id) if user_id else None,
                dealer_id=str(dealer_id) if dealer_id else None,
            )

            conditions = [Order.deleted_at.is_(None)]
            if user_id:
                conditions.append(Order.user_id == user_id)
            if dealer_id:
                conditions.append(Order.dealer_id == dealer_id)

            # Total orders
            total_stmt = (
                select(func.count()).select_from(Order).where(and_(*conditions))
            )

            # Status breakdown
            status_stmt = (
                select(Order.status, func.count())
                .where(and_(*conditions))
                .group_by(Order.status)
            )

            # Total amount
            amount_stmt = (
                select(func.sum(Order.total_amount))
                .where(and_(*conditions))
            )

            total_result = await self.session.execute(total_stmt)
            status_result = await self.session.execute(status_stmt)
            amount_result = await self.session.execute(amount_stmt)

            total_count = total_result.scalar_one()
            status_breakdown = {
                status.value: count for status, count in status_result.all()
            }
            total_amount = amount_result.scalar_one() or Decimal("0.00")

            statistics = {
                "total_orders": total_count,
                "status_breakdown": status_breakdown,
                "total_amount": float(total_amount),
            }

            logger.debug("Order statistics fetched", statistics=statistics)

            return statistics

        except SQLAlchemyError as e:
            logger.error(
                "Failed to fetch order statistics",
                error=str(e),
            )
            raise OrderRepositoryError(
                "Failed to fetch order statistics",
                error=str(e),
            ) from e