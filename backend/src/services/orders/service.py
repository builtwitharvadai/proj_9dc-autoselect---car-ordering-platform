"""
Order service orchestrating business logic and integrations.

This module implements the OrderService class for managing order operations
including creating orders, updating status, processing state transitions, and
coordinating with payment and inventory services. Includes order validation,
pricing calculations, and notification triggers with comprehensive error
handling and structured logging.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.models.order import OrderStatus, PaymentStatus, FulfillmentStatus
from src.services.orders.repository import (
    OrderRepository,
    OrderNotFoundError,
    OrderCreationError,
    OrderUpdateError,
    OrderRepositoryError,
)
from src.services.orders.state_machine import (
    OrderStateMachine,
    StateTransitionError,
)
from src.services.payments.service import (
    PaymentService,
    PaymentProcessingError,
    PaymentValidationError,
)
from src.services.notifications.service import (
    NotificationService,
    NotificationServiceError,
)
from src.database.models.notification import NotificationType

logger = get_logger(__name__)


class OrderServiceError(Exception):
    """Base exception for order service errors."""

    def __init__(self, message: str, **context: Any):
        super().__init__(message)
        self.context = context


class OrderValidationError(OrderServiceError):
    """Raised when order validation fails."""

    pass


class OrderProcessingError(OrderServiceError):
    """Raised when order processing fails."""

    pass


class OrderService:
    """
    Order service orchestrating business logic and integrations.

    Provides methods for creating orders, updating status, processing state
    transitions, and coordinating with payment and inventory services.
    Implements order validation, pricing calculations, and notification
    triggers with comprehensive error handling.

    Attributes:
        repository: Order repository for data access
        state_machine: State machine for order lifecycle management
        payment_service: Payment service for payment operations
        notification_service: Notification service for customer notifications
    """

    def __init__(
        self,
        session: AsyncSession,
        payment_service: Optional[PaymentService] = None,
        notification_service: Optional[NotificationService] = None,
    ):
        """
        Initialize order service.

        Args:
            session: Async database session
            payment_service: Optional payment service instance
            notification_service: Optional notification service instance
        """
        self.repository = OrderRepository(session)
        self.state_machine = OrderStateMachine(session)
        self.payment_service = payment_service
        self.notification_service = notification_service

        logger.info(
            "OrderService initialized",
            has_payment_service=payment_service is not None,
            has_notification_service=notification_service is not None,
        )

    async def create_order(
        self,
        user_id: uuid.UUID,
        vehicle_id: uuid.UUID,
        configuration_id: uuid.UUID,
        items: list[dict[str, Any]],
        customer_info: dict[str, Any],
        delivery_address: dict[str, Any],
        payment_method: str,
        dealer_id: Optional[uuid.UUID] = None,
        manufacturer_id: Optional[uuid.UUID] = None,
        trade_in_info: Optional[dict[str, Any]] = None,
        promotional_code: Optional[str] = None,
        notes: Optional[str] = None,
        special_instructions: Optional[str] = None,
        estimated_delivery_date: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """
        Create new order with validation and pricing.

        Args:
            user_id: User placing the order
            vehicle_id: Vehicle being ordered
            configuration_id: Vehicle configuration
            items: List of order items
            customer_info: Customer information
            delivery_address: Delivery address
            payment_method: Payment method identifier
            dealer_id: Optional dealer handling order
            manufacturer_id: Optional manufacturer
            trade_in_info: Optional trade-in information
            promotional_code: Optional promotional code
            notes: Optional order notes
            special_instructions: Optional special instructions
            estimated_delivery_date: Optional estimated delivery date

        Returns:
            Dictionary containing created order details

        Raises:
            OrderValidationError: If order validation fails
            OrderProcessingError: If order creation fails
        """
        logger.info(
            "Creating order",
            user_id=str(user_id),
            vehicle_id=str(vehicle_id),
            item_count=len(items),
        )

        try:
            # Validate order data
            self._validate_order_data(
                items=items,
                customer_info=customer_info,
                delivery_address=delivery_address,
                payment_method=payment_method,
            )

            # Calculate pricing
            pricing = self._calculate_order_pricing(
                items=items,
                trade_in_info=trade_in_info,
                promotional_code=promotional_code,
            )

            # Generate order number
            order_number = self._generate_order_number()

            # Create order with items
            order = await self.repository.create_order_with_items(
                user_id=user_id,
                vehicle_id=vehicle_id,
                configuration_id=configuration_id,
                order_number=order_number,
                total_amount=pricing["total_amount"],
                subtotal=pricing["subtotal"],
                tax_amount=pricing["tax_amount"],
                items=items,
                customer_info=customer_info,
                delivery_address=delivery_address,
                dealer_id=dealer_id,
                manufacturer_id=manufacturer_id,
                shipping_amount=pricing.get("shipping_amount", Decimal("0.00")),
                discount_amount=pricing.get("discount_amount", Decimal("0.00")),
                total_fees=pricing.get("total_fees", Decimal("0.00")),
                notes=notes,
                special_instructions=special_instructions,
                trade_in_info=trade_in_info,
                estimated_delivery_date=estimated_delivery_date,
            )

            # Create payment intent if payment service available
            payment_intent_id = None
            if self.payment_service:
                try:
                    payment_result = await self.payment_service.create_payment_intent(
                        order_id=order.id,
                        amount=pricing["total_amount"],
                        currency="USD",
                        customer_email=customer_info.get("email"),
                        metadata={
                            "order_number": order_number,
                            "vehicle_id": str(vehicle_id),
                        },
                        created_by=str(user_id),
                    )
                    payment_intent_id = payment_result["payment_intent_id"]

                    logger.info(
                        "Payment intent created for order",
                        order_id=str(order.id),
                        payment_intent_id=payment_intent_id,
                    )
                except (PaymentProcessingError, PaymentValidationError) as e:
                    logger.error(
                        "Failed to create payment intent",
                        order_id=str(order.id),
                        error=str(e),
                    )
                    # Continue without payment intent - can be created later

            # Send order creation notification
            if self.notification_service:
                await self._send_order_notification(
                    user_id=user_id,
                    order=order,
                    notification_type=NotificationType.ORDER_CREATED,
                )

            logger.info(
                "Order created successfully",
                order_id=str(order.id),
                order_number=order_number,
                total_amount=float(pricing["total_amount"]),
            )

            return {
                "order_id": str(order.id),
                "order_number": order_number,
                "status": order.status.value,
                "payment_status": order.payment_status.value,
                "fulfillment_status": order.fulfillment_status.value,
                "total_amount": float(order.total_amount),
                "subtotal": float(order.subtotal),
                "tax_amount": float(order.tax_amount),
                "payment_intent_id": payment_intent_id,
                "created_at": order.created_at.isoformat(),
            }

        except OrderValidationError:
            raise

        except OrderCreationError as e:
            logger.error(
                "Order creation failed",
                user_id=str(user_id),
                error=str(e),
            )
            raise OrderProcessingError(
                "Failed to create order",
                user_id=str(user_id),
                error=str(e),
            ) from e

        except Exception as e:
            logger.error(
                "Unexpected error creating order",
                user_id=str(user_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise OrderProcessingError(
                "Unexpected error creating order",
                user_id=str(user_id),
                error=str(e),
            ) from e

    async def update_order_status(
        self,
        order_id: uuid.UUID,
        new_status: OrderStatus,
        user_id: Optional[uuid.UUID] = None,
        reason: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Update order status with state machine validation.

        Args:
            order_id: Order identifier
            new_status: New order status
            user_id: User making the change
            reason: Reason for status change
            metadata: Additional metadata

        Returns:
            Dictionary containing updated order details

        Raises:
            OrderNotFoundError: If order not found
            OrderProcessingError: If status update fails
        """
        logger.info(
            "Updating order status",
            order_id=str(order_id),
            new_status=new_status.value,
        )

        try:
            # Get current order
            order = await self.repository.get_order_by_id(order_id)
            if not order:
                raise OrderNotFoundError(
                    "Order not found",
                    order_id=str(order_id),
                )

            # Validate and apply state transition
            self.state_machine.apply_transition(
                order=order,
                target_status=new_status,
                user_id=user_id,
                reason=reason,
                metadata=metadata,
            )

            # Refresh order to get updated data
            order = await self.repository.get_order_by_id(
                order_id,
                include_history=True,
            )

            # Send status change notification
            if self.notification_service and order.user_id:
                notification_type = self._get_notification_type_for_status(new_status)
                if notification_type:
                    await self._send_order_notification(
                        user_id=order.user_id,
                        order=order,
                        notification_type=notification_type,
                    )

            logger.info(
                "Order status updated successfully",
                order_id=str(order_id),
                new_status=new_status.value,
            )

            return {
                "order_id": str(order.id),
                "order_number": order.order_number,
                "status": order.status.value,
                "payment_status": order.payment_status.value,
                "fulfillment_status": order.fulfillment_status.value,
                "updated_at": order.updated_at.isoformat(),
            }

        except OrderNotFoundError:
            raise

        except StateTransitionError as e:
            logger.warning(
                "Invalid state transition",
                order_id=str(order_id),
                current_status=e.current_state.value,
                target_status=e.target_state.value,
            )
            raise OrderProcessingError(
                f"Invalid status transition: {e}",
                order_id=str(order_id),
                current_status=e.current_state.value,
                target_status=e.target_state.value,
            ) from e

        except Exception as e:
            logger.error(
                "Failed to update order status",
                order_id=str(order_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise OrderProcessingError(
                "Failed to update order status",
                order_id=str(order_id),
                error=str(e),
            ) from e

    async def get_order(
        self,
        order_id: uuid.UUID,
        include_items: bool = True,
        include_history: bool = False,
    ) -> dict[str, Any]:
        """
        Get order details.

        Args:
            order_id: Order identifier
            include_items: Whether to include order items
            include_history: Whether to include status history

        Returns:
            Dictionary containing order details

        Raises:
            OrderNotFoundError: If order not found
            OrderProcessingError: If retrieval fails
        """
        logger.debug("Retrieving order", order_id=str(order_id))

        try:
            order = await self.repository.get_order_by_id(
                order_id=order_id,
                include_items=include_items,
                include_history=include_history,
            )

            if not order:
                raise OrderNotFoundError(
                    "Order not found",
                    order_id=str(order_id),
                )

            return self._format_order_response(order)

        except OrderNotFoundError:
            raise

        except OrderRepositoryError as e:
            logger.error(
                "Failed to retrieve order",
                order_id=str(order_id),
                error=str(e),
            )
            raise OrderProcessingError(
                "Failed to retrieve order",
                order_id=str(order_id),
                error=str(e),
            ) from e

    async def get_user_orders(
        self,
        user_id: uuid.UUID,
        status: Optional[OrderStatus] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Get orders for user with pagination.

        Args:
            user_id: User identifier
            status: Optional status filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Dictionary containing orders and pagination info

        Raises:
            OrderProcessingError: If retrieval fails
        """
        logger.debug(
            "Retrieving user orders",
            user_id=str(user_id),
            status=status.value if status else None,
        )

        try:
            orders, total_count = await self.repository.get_user_orders(
                user_id=user_id,
                status=status,
                skip=skip,
                limit=limit,
            )

            return {
                "orders": [self._format_order_response(order) for order in orders],
                "total_count": total_count,
                "skip": skip,
                "limit": limit,
            }

        except OrderRepositoryError as e:
            logger.error(
                "Failed to retrieve user orders",
                user_id=str(user_id),
                error=str(e),
            )
            raise OrderProcessingError(
                "Failed to retrieve user orders",
                user_id=str(user_id),
                error=str(e),
            ) from e

    async def _send_order_notification(
        self,
        user_id: uuid.UUID,
        order: Any,
        notification_type: NotificationType,
    ) -> None:
        """
        Send order notification to user.

        Args:
            user_id: User ID to send notification to
            order: Order instance
            notification_type: Type of notification to send
        """
        try:
            context = {
                "order_number": order.order_number,
                "order_id": str(order.id),
                "status": order.status.value,
                "total_amount": float(order.total_amount),
                "customer_name": f"{order.customer_info.get('first_name', '')} {order.customer_info.get('last_name', '')}".strip(),
                "estimated_delivery_date": order.estimated_delivery_date.isoformat() if order.estimated_delivery_date else None,
            }

            await self.notification_service.send_notification(
                user_id=user_id,
                notification_type=notification_type,
                context=context,
            )

            logger.info(
                "Order notification sent",
                order_id=str(order.id),
                user_id=str(user_id),
                notification_type=notification_type.value,
            )

        except NotificationServiceError as e:
            logger.error(
                "Failed to send order notification",
                order_id=str(order.id),
                user_id=str(user_id),
                notification_type=notification_type.value,
                error=str(e),
            )
            # Don't raise - notification failure shouldn't block order processing

    def _get_notification_type_for_status(
        self,
        status: OrderStatus,
    ) -> Optional[NotificationType]:
        """
        Get notification type for order status.

        Args:
            status: Order status

        Returns:
            Notification type or None if no notification needed
        """
        status_notification_map = {
            OrderStatus.CONFIRMED: NotificationType.ORDER_CONFIRMED,
            OrderStatus.SHIPPED: NotificationType.ORDER_SHIPPED,
            OrderStatus.DELIVERED: NotificationType.ORDER_DELIVERED,
            OrderStatus.CANCELLED: NotificationType.ORDER_CANCELLED,
        }
        return status_notification_map.get(status)

    def _validate_order_data(
        self,
        items: list[dict[str, Any]],
        customer_info: dict[str, Any],
        delivery_address: dict[str, Any],
        payment_method: str,
    ) -> None:
        """
        Validate order data.

        Args:
            items: Order items
            customer_info: Customer information
            delivery_address: Delivery address
            payment_method: Payment method

        Raises:
            OrderValidationError: If validation fails
        """
        # Validate items
        if not items:
            raise OrderValidationError(
                "Order must contain at least one item",
                item_count=0,
            )

        for item in items:
            if "configuration_id" not in item:
                raise OrderValidationError(
                    "Item missing configuration_id",
                    item=item,
                )
            if "quantity" not in item or item["quantity"] <= 0:
                raise OrderValidationError(
                    "Item quantity must be positive",
                    item=item,
                )
            if "unit_price" not in item or item["unit_price"] <= 0:
                raise OrderValidationError(
                    "Item unit_price must be positive",
                    item=item,
                )

        # Validate customer info
        required_customer_fields = ["first_name", "last_name", "email", "phone"]
        for field in required_customer_fields:
            if field not in customer_info or not customer_info[field]:
                raise OrderValidationError(
                    f"Customer info missing required field: {field}",
                    field=field,
                )

        # Validate delivery address
        required_address_fields = ["street_address", "city", "state", "postal_code"]
        for field in required_address_fields:
            if field not in delivery_address or not delivery_address[field]:
                raise OrderValidationError(
                    f"Delivery address missing required field: {field}",
                    field=field,
                )

        # Validate payment method
        if not payment_method:
            raise OrderValidationError(
                "Payment method is required",
            )

    def _calculate_order_pricing(
        self,
        items: list[dict[str, Any]],
        trade_in_info: Optional[dict[str, Any]] = None,
        promotional_code: Optional[str] = None,
    ) -> dict[str, Decimal]:
        """
        Calculate order pricing.

        Args:
            items: Order items
            trade_in_info: Optional trade-in information
            promotional_code: Optional promotional code

        Returns:
            Dictionary containing pricing breakdown
        """
        # Calculate subtotal
        subtotal = sum(
            Decimal(str(item["quantity"])) * Decimal(str(item["unit_price"]))
            for item in items
        )

        # Calculate discount
        discount_amount = Decimal("0.00")
        if promotional_code:
            # Placeholder for promotional code logic
            discount_amount = subtotal * Decimal("0.05")  # 5% discount

        # Apply trade-in value
        trade_in_value = Decimal("0.00")
        if trade_in_info and "estimated_value" in trade_in_info:
            trade_in_value = Decimal(str(trade_in_info["estimated_value"]))

        # Calculate tax (8% rate)
        taxable_amount = subtotal - discount_amount - trade_in_value
        tax_amount = taxable_amount * Decimal("0.08")

        # Calculate total
        total_amount = taxable_amount + tax_amount

        return {
            "subtotal": subtotal,
            "discount_amount": discount_amount,
            "trade_in_value": trade_in_value,
            "tax_amount": tax_amount,
            "total_amount": total_amount,
            "shipping_amount": Decimal("0.00"),
            "total_fees": Decimal("0.00"),
        }

    def _generate_order_number(self) -> str:
        """
        Generate unique order number.

        Returns:
            Order number string
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_suffix = uuid.uuid4().hex[:6].upper()
        return f"ORD-{timestamp}-{random_suffix}"

    def _format_order_response(self, order: Any) -> dict[str, Any]:
        """
        Format order for response.

        Args:
            order: Order instance

        Returns:
            Dictionary containing formatted order data
        """
        return {
            "id": str(order.id),
            "order_number": order.order_number,
            "user_id": str(order.user_id) if order.user_id else None,
            "vehicle_id": str(order.vehicle_id),
            "configuration_id": str(order.configuration_id),
            "dealer_id": str(order.dealer_id) if order.dealer_id else None,
            "status": order.status.value,
            "payment_status": order.payment_status.value,
            "fulfillment_status": order.fulfillment_status.value,
            "total_amount": float(order.total_amount),
            "subtotal": float(order.subtotal),
            "tax_amount": float(order.tax_amount),
            "shipping_amount": float(order.shipping_amount),
            "discount_amount": float(order.discount_amount),
            "customer_info": order.customer_info,
            "delivery_address": order.delivery_address,
            "notes": order.notes,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
        }