"""
Order model for order management and fulfillment tracking.

This module defines the Order model for managing customer orders with status tracking,
fulfillment management, and proper relationships to users, vehicles, and configurations.
Implements comprehensive validation, status transitions, and audit logging.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Any

from sqlalchemy import (
    String,
    Numeric,
    ForeignKey,
    Index,
    CheckConstraint,
    Enum as SQLEnum,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import AuditedModel


class OrderStatus(str, Enum):
    """
    Order status enumeration for tracking order lifecycle.

    Attributes:
        PENDING: Order created but not yet confirmed
        CONFIRMED: Order confirmed and payment received
        PROCESSING: Order being prepared for fulfillment
        IN_PRODUCTION: Vehicle in production
        READY_FOR_DELIVERY: Order ready for shipment
        IN_TRANSIT: Order shipped and in transit
        DELIVERED: Order delivered to customer
        CANCELLED: Order cancelled by customer or system
        REFUNDED: Order refunded after cancellation
    """

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    IN_PRODUCTION = "in_production"
    READY_FOR_DELIVERY = "ready_for_delivery"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

    @classmethod
    def from_string(cls, value: str) -> "OrderStatus":
        """
        Create OrderStatus from string value.

        Args:
            value: String representation of status

        Returns:
            OrderStatus enum value

        Raises:
            ValueError: If value is not a valid status
        """
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(f"Invalid order status: {value}")

    @property
    def is_terminal(self) -> bool:
        """Check if status is terminal (no further transitions)."""
        return self in (
            OrderStatus.DELIVERED,
            OrderStatus.CANCELLED,
            OrderStatus.REFUNDED,
        )

    @property
    def is_active(self) -> bool:
        """Check if order is in active processing state."""
        return self in (
            OrderStatus.CONFIRMED,
            OrderStatus.PROCESSING,
            OrderStatus.IN_PRODUCTION,
            OrderStatus.READY_FOR_DELIVERY,
            OrderStatus.IN_TRANSIT,
        )

    @property
    def can_cancel(self) -> bool:
        """Check if order can be cancelled from this status."""
        return self in (
            OrderStatus.PENDING,
            OrderStatus.CONFIRMED,
            OrderStatus.PROCESSING,
        )


class PaymentStatus(str, Enum):
    """
    Payment status enumeration for tracking payment lifecycle.

    Attributes:
        PENDING: Payment initiated but not completed
        AUTHORIZED: Payment authorized but not captured
        CAPTURED: Payment captured successfully
        FAILED: Payment failed
        REFUNDED: Payment refunded
        PARTIALLY_REFUNDED: Payment partially refunded
    """

    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class FulfillmentStatus(str, Enum):
    """
    Fulfillment status enumeration for tracking order fulfillment.

    Attributes:
        PENDING: Fulfillment not started
        PROCESSING: Order being prepared
        READY: Order ready for pickup/delivery
        SHIPPED: Order shipped
        DELIVERED: Order delivered
        CANCELLED: Fulfillment cancelled
    """

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order(AuditedModel):
    """
    Order model for managing customer orders and fulfillment.

    Manages complete order lifecycle from creation through delivery, including
    status tracking, payment management, and relationships to users, vehicles,
    and configurations. Implements comprehensive validation and audit logging.

    Attributes:
        id: Unique order identifier (UUID)
        user_id: Foreign key to user who placed order
        vehicle_id: Foreign key to ordered vehicle
        configuration_id: Foreign key to vehicle configuration
        dealer_id: Foreign key to dealer handling order
        manufacturer_id: Foreign key to manufacturer
        status: Current order status (enum)
        payment_status: Current payment status (enum)
        fulfillment_status: Current fulfillment status (enum)
        total_amount: Total order amount including all charges
        subtotal: Subtotal before taxes and fees
        tax_amount: Tax amount
        total_tax: Total tax amount (alias for tax_amount)
        shipping_amount: Shipping/delivery charges
        discount_amount: Applied discount amount
        total_fees: Total fees amount
        order_number: Human-readable order number
        notes: Additional order notes
        special_instructions: Special delivery or handling instructions
        customer_info: Customer information stored as JSONB
        delivery_address: Delivery address stored as JSONB
        trade_in_info: Trade-in vehicle information stored as JSONB
        estimated_delivery_date: Estimated delivery date
        actual_delivery_date: Actual delivery date
        created_at: Record creation timestamp (from AuditedModel)
        updated_at: Last modification timestamp (from AuditedModel)
        created_by: User who created this record (from AuditedModel)
        updated_by: User who last modified this record (from AuditedModel)
        deleted_at: Soft deletion timestamp (from AuditedModel)
    """

    __tablename__ = "orders"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique order identifier",
    )

    # Foreign keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who placed the order",
    )

    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Ordered vehicle identifier",
    )

    configuration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_configurations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Vehicle configuration identifier",
    )

    dealer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Dealer handling the order",
    )

    manufacturer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("manufacturers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Manufacturer identifier",
    )

    # Order status
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus, name="order_status", create_constraint=True),
        nullable=False,
        default=OrderStatus.PENDING,
        index=True,
        comment="Current order status",
    )

    payment_status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus, name="payment_status", create_constraint=True),
        nullable=False,
        default=PaymentStatus.PENDING,
        index=True,
        comment="Current payment status",
    )

    fulfillment_status: Mapped[FulfillmentStatus] = mapped_column(
        SQLEnum(FulfillmentStatus, name="fulfillment_status", create_constraint=True),
        nullable=False,
        default=FulfillmentStatus.PENDING,
        index=True,
        comment="Current fulfillment status",
    )

    # Pricing fields
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        comment="Total order amount including all charges",
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        comment="Subtotal before taxes and fees",
    )

    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Tax amount",
    )

    total_tax: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Total tax amount",
    )

    shipping_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Shipping/delivery charges",
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Applied discount amount",
    )

    total_fees: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Total fees amount",
    )

    # Order identification
    order_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Human-readable order number",
    )

    # Additional information
    notes: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="Additional order notes",
    )

    special_instructions: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="Special delivery or handling instructions",
    )

    # JSONB fields for flexible data storage
    customer_info: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Customer information stored as JSONB",
    )

    delivery_address: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Delivery address stored as JSONB",
    )

    trade_in_info: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Trade-in vehicle information stored as JSONB",
    )

    # Delivery tracking
    estimated_delivery_date: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        index=True,
        comment="Estimated delivery date",
    )

    actual_delivery_date: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="Actual delivery date",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="orders",
        foreign_keys=[user_id],
        lazy="selectin",
    )

    vehicle: Mapped["Vehicle"] = relationship(
        "Vehicle",
        back_populates="orders",
        foreign_keys=[vehicle_id],
        lazy="selectin",
    )

    configuration: Mapped["VehicleConfiguration"] = relationship(
        "VehicleConfiguration",
        back_populates="orders",
        foreign_keys=[configuration_id],
        lazy="selectin",
    )

    order_items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        foreign_keys="OrderItem.order_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    status_history: Mapped[list["OrderStatusHistory"]] = relationship(
        "OrderStatusHistory",
        back_populates="order",
        foreign_keys="OrderStatusHistory.order_id",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.created_at.desc()",
    )

    # Table constraints and indexes
    __table_args__ = (
        # Composite index for user's orders
        Index(
            "ix_orders_user_status",
            "user_id",
            "status",
        ),
        # Index for order lookup by number
        Index(
            "ix_orders_order_number",
            "order_number",
        ),
        # Index for status-based queries
        Index(
            "ix_orders_status_created",
            "status",
            "created_at",
        ),
        # Index for delivery tracking
        Index(
            "ix_orders_estimated_delivery",
            "estimated_delivery_date",
        ),
        # Index for vehicle orders
        Index(
            "ix_orders_vehicle_status",
            "vehicle_id",
            "status",
        ),
        # Index for configuration orders
        Index(
            "ix_orders_configuration",
            "configuration_id",
        ),
        # Composite index for active orders
        Index(
            "ix_orders_active",
            "user_id",
            "status",
            "deleted_at",
        ),
        # Index for dealer orders
        Index(
            "ix_orders_dealer_status",
            "dealer_id",
            "status",
        ),
        # Index for manufacturer orders
        Index(
            "ix_orders_manufacturer_status",
            "manufacturer_id",
            "status",
        ),
        # Index for payment status
        Index(
            "ix_orders_payment_status",
            "payment_status",
        ),
        # Index for fulfillment status
        Index(
            "ix_orders_fulfillment_status",
            "fulfillment_status",
        ),
        # GIN index for customer_info JSONB search
        Index(
            "ix_orders_customer_info_gin",
            "customer_info",
            postgresql_using="gin",
        ),
        # GIN index for delivery_address JSONB search
        Index(
            "ix_orders_delivery_address_gin",
            "delivery_address",
            postgresql_using="gin",
        ),
        # GIN index for trade_in_info JSONB search
        Index(
            "ix_orders_trade_in_info_gin",
            "trade_in_info",
            postgresql_using="gin",
        ),
        # Check constraints for data validation
        CheckConstraint(
            "total_amount >= 0",
            name="ck_orders_total_amount_non_negative",
        ),
        CheckConstraint(
            "subtotal >= 0",
            name="ck_orders_subtotal_non_negative",
        ),
        CheckConstraint(
            "tax_amount >= 0",
            name="ck_orders_tax_amount_non_negative",
        ),
        CheckConstraint(
            "total_tax >= 0",
            name="ck_orders_total_tax_non_negative",
        ),
        CheckConstraint(
            "shipping_amount >= 0",
            name="ck_orders_shipping_amount_non_negative",
        ),
        CheckConstraint(
            "discount_amount >= 0",
            name="ck_orders_discount_amount_non_negative",
        ),
        CheckConstraint(
            "total_fees >= 0",
            name="ck_orders_total_fees_non_negative",
        ),
        CheckConstraint(
            "total_amount <= 10000000.00",
            name="ck_orders_total_amount_max",
        ),
        CheckConstraint(
            "actual_delivery_date IS NULL OR actual_delivery_date >= created_at",
            name="ck_orders_delivery_after_creation",
        ),
        CheckConstraint(
            "estimated_delivery_date IS NULL OR estimated_delivery_date >= created_at",
            name="ck_orders_estimated_delivery_after_creation",
        ),
        {
            "comment": "Customer orders with status tracking and fulfillment",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of Order.

        Returns:
            String representation showing key order attributes
        """
        return (
            f"<Order(id={self.id}, order_number={self.order_number}, "
            f"user_id={self.user_id}, status={self.status.value}, "
            f"total_amount={self.total_amount})>"
        )

    @property
    def is_active(self) -> bool:
        """
        Check if order is active (not soft deleted and not terminal).

        Returns:
            True if order is active
        """
        return self.deleted_at is None and self.status.is_active

    @property
    def is_terminal(self) -> bool:
        """
        Check if order is in terminal state.

        Returns:
            True if order is in terminal state
        """
        return self.status.is_terminal

    @property
    def can_cancel(self) -> bool:
        """
        Check if order can be cancelled.

        Returns:
            True if order can be cancelled
        """
        return self.deleted_at is None and self.status.can_cancel

    @property
    def formatted_total(self) -> str:
        """
        Get formatted total amount string.

        Returns:
            Total amount formatted as currency string
        """
        return f"${self.total_amount:,.2f}"

    @property
    def formatted_subtotal(self) -> str:
        """
        Get formatted subtotal string.

        Returns:
            Subtotal formatted as currency string
        """
        return f"${self.subtotal:,.2f}"

    @property
    def is_delivered(self) -> bool:
        """
        Check if order has been delivered.

        Returns:
            True if order is delivered
        """
        return self.status == OrderStatus.DELIVERED

    @property
    def is_cancelled(self) -> bool:
        """
        Check if order is cancelled.

        Returns:
            True if order is cancelled
        """
        return self.status in (OrderStatus.CANCELLED, OrderStatus.REFUNDED)

    @property
    def days_until_delivery(self) -> Optional[int]:
        """
        Calculate days until estimated delivery.

        Returns:
            Number of days until delivery, or None if no estimate
        """
        if self.estimated_delivery_date is None:
            return None
        delta = self.estimated_delivery_date - datetime.utcnow()
        return max(0, delta.days)

    def update_status(self, new_status: OrderStatus) -> None:
        """
        Update order status with validation.

        Args:
            new_status: New status to set

        Raises:
            ValueError: If status transition is invalid
        """
        if self.status.is_terminal:
            raise ValueError(
                f"Cannot change status from terminal state {self.status.value}"
            )

        if not self._is_valid_transition(new_status):
            raise ValueError(
                f"Invalid status transition from {self.status.value} to {new_status.value}"
            )

        self.status = new_status

        if new_status == OrderStatus.DELIVERED and self.actual_delivery_date is None:
            self.actual_delivery_date = datetime.utcnow()

    def _is_valid_transition(self, new_status: OrderStatus) -> bool:
        """
        Validate status transition.

        Args:
            new_status: Target status

        Returns:
            True if transition is valid
        """
        valid_transitions = {
            OrderStatus.PENDING: {
                OrderStatus.CONFIRMED,
                OrderStatus.CANCELLED,
            },
            OrderStatus.CONFIRMED: {
                OrderStatus.PROCESSING,
                OrderStatus.CANCELLED,
            },
            OrderStatus.PROCESSING: {
                OrderStatus.IN_PRODUCTION,
                OrderStatus.CANCELLED,
            },
            OrderStatus.IN_PRODUCTION: {
                OrderStatus.READY_FOR_DELIVERY,
            },
            OrderStatus.READY_FOR_DELIVERY: {
                OrderStatus.IN_TRANSIT,
            },
            OrderStatus.IN_TRANSIT: {
                OrderStatus.DELIVERED,
            },
            OrderStatus.CANCELLED: {
                OrderStatus.REFUNDED,
            },
        }

        return new_status in valid_transitions.get(self.status, set())

    def calculate_total(self) -> Decimal:
        """
        Calculate total amount from components.

        Returns:
            Calculated total amount
        """
        return (
            self.subtotal
            + self.tax_amount
            + self.shipping_amount
            + self.total_fees
            - self.discount_amount
        )

    def validate_amounts(self) -> tuple[bool, list[str]]:
        """
        Validate order amounts.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        if self.subtotal < 0:
            errors.append("Subtotal cannot be negative")

        if self.tax_amount < 0:
            errors.append("Tax amount cannot be negative")

        if self.total_tax < 0:
            errors.append("Total tax cannot be negative")

        if self.shipping_amount < 0:
            errors.append("Shipping amount cannot be negative")

        if self.discount_amount < 0:
            errors.append("Discount amount cannot be negative")

        if self.total_fees < 0:
            errors.append("Total fees cannot be negative")

        if self.discount_amount > self.subtotal:
            errors.append("Discount cannot exceed subtotal")

        calculated_total = self.calculate_total()
        if abs(self.total_amount - calculated_total) > Decimal("0.01"):
            errors.append(
                f"Total amount mismatch: expected {calculated_total}, got {self.total_amount}"
            )

        if self.total_amount > Decimal("10000000.00"):
            errors.append("Total amount exceeds maximum allowed value")

        return len(errors) == 0, errors

    def apply_discount(self, discount: Decimal) -> None:
        """
        Apply discount to order.

        Args:
            discount: Discount amount to apply

        Raises:
            ValueError: If discount is invalid
        """
        if discount < 0:
            raise ValueError("Discount cannot be negative")

        if discount > self.subtotal:
            raise ValueError("Discount cannot exceed subtotal")

        self.discount_amount = discount
        self.total_amount = self.calculate_total()

    def set_estimated_delivery(self, delivery_date: datetime) -> None:
        """
        Set estimated delivery date with validation.

        Args:
            delivery_date: Estimated delivery date

        Raises:
            ValueError: If delivery date is invalid
        """
        if delivery_date < self.created_at:
            raise ValueError("Delivery date cannot be before order creation")

        self.estimated_delivery_date = delivery_date

    def mark_delivered(self, delivery_date: Optional[datetime] = None) -> None:
        """
        Mark order as delivered.

        Args:
            delivery_date: Actual delivery date (defaults to now)

        Raises:
            ValueError: If order cannot be marked as delivered
        """
        if self.status.is_terminal and self.status != OrderStatus.IN_TRANSIT:
            raise ValueError(
                f"Cannot mark order as delivered from status {self.status.value}"
            )

        self.status = OrderStatus.DELIVERED
        self.actual_delivery_date = delivery_date or datetime.utcnow()

    def cancel(self, reason: Optional[str] = None) -> None:
        """
        Cancel order.

        Args:
            reason: Cancellation reason

        Raises:
            ValueError: If order cannot be cancelled
        """
        if not self.can_cancel:
            raise ValueError(
                f"Cannot cancel order in status {self.status.value}"
            )

        self.status = OrderStatus.CANCELLED
        if reason:
            self.notes = f"{self.notes or ''}\nCancellation reason: {reason}".strip()

    def to_dict(self, include_relationships: bool = False) -> dict[str, Any]:
        """
        Convert order to dictionary representation.

        Args:
            include_relationships: Whether to include related entities

        Returns:
            Dictionary representation of order
        """
        data = {
            "id": str(self.id),
            "order_number": self.order_number,
            "user_id": str(self.user_id),
            "vehicle_id": str(self.vehicle_id),
            "configuration_id": str(self.configuration_id),
            "dealer_id": str(self.dealer_id) if self.dealer_id else None,
            "manufacturer_id": str(self.manufacturer_id) if self.manufacturer_id else None,
            "status": self.status.value,
            "payment_status": self.payment_status.value,
            "fulfillment_status": self.fulfillment_status.value,
            "total_amount": float(self.total_amount),
            "subtotal": float(self.subtotal),
            "tax_amount": float(self.tax_amount),
            "total_tax": float(self.total_tax),
            "shipping_amount": float(self.shipping_amount),
            "discount_amount": float(self.discount_amount),
            "total_fees": float(self.total_fees),
            "formatted_total": self.formatted_total,
            "notes": self.notes,
            "special_instructions": self.special_instructions,
            "customer_info": self.customer_info,
            "delivery_address": self.delivery_address,
            "trade_in_info": self.trade_in_info,
            "estimated_delivery_date": (
                self.estimated_delivery_date.isoformat()
                if self.estimated_delivery_date
                else None
            ),
            "actual_delivery_date": (
                self.actual_delivery_date.isoformat()
                if self.actual_delivery_date
                else None
            ),
            "days_until_delivery": self.days_until_delivery,
            "is_active": self.is_active,
            "is_terminal": self.is_terminal,
            "can_cancel": self.can_cancel,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_relationships:
            if self.user:
                data["user"] = {
                    "id": str(self.user.id),
                    "email": self.user.email,
                }
            if self.vehicle:
                data["vehicle"] = {
                    "id": str(self.vehicle.id),
                    "make": self.vehicle.make,
                    "model": self.vehicle.model,
                }
            if self.configuration:
                data["configuration"] = {
                    "id": str(self.configuration.id),
                    "total_price": float(self.configuration.total_price),
                }

        return data


class OrderItem(AuditedModel):
    """
    Order item model for individual items in an order.

    Attributes:
        id: Unique order item identifier (UUID)
        order_id: Foreign key to parent order
        vehicle_configuration_id: Foreign key to vehicle configuration
        quantity: Quantity of items
        unit_price: Price per unit
        total_price: Total price for this item
        created_at: Record creation timestamp (from AuditedModel)
        updated_at: Last modification timestamp (from AuditedModel)
        created_by: User who created this record (from AuditedModel)
        updated_by: User who last modified this record (from AuditedModel)
        deleted_at: Soft deletion timestamp (from AuditedModel)
    """

    __tablename__ = "order_items"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique order item identifier",
    )

    # Foreign keys
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent order identifier",
    )

    vehicle_configuration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_configurations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Vehicle configuration identifier",
    )

    # Item details
    quantity: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
        comment="Quantity of items",
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        comment="Price per unit",
    )

    total_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        comment="Total price for this item",
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="order_items",
        foreign_keys=[order_id],
        lazy="selectin",
    )

    vehicle_configuration: Mapped["VehicleConfiguration"] = relationship(
        "VehicleConfiguration",
        foreign_keys=[vehicle_configuration_id],
        lazy="selectin",
    )

    # Table constraints and indexes
    __table_args__ = (
        Index(
            "ix_order_items_order",
            "order_id",
        ),
        Index(
            "ix_order_items_configuration",
            "vehicle_configuration_id",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_order_items_quantity_positive",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="ck_order_items_unit_price_non_negative",
        ),
        CheckConstraint(
            "total_price >= 0",
            name="ck_order_items_total_price_non_negative",
        ),
        {
            "comment": "Individual items in an order",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of OrderItem.

        Returns:
            String representation showing key item attributes
        """
        return (
            f"<OrderItem(id={self.id}, order_id={self.order_id}, "
            f"quantity={self.quantity}, total_price={self.total_price})>"
        )


class OrderStatusHistory(AuditedModel):
    """
    Order status history model for audit trail.

    Attributes:
        id: Unique history record identifier (UUID)
        order_id: Foreign key to parent order
        from_status: Previous status
        to_status: New status
        changed_by: User who made the change
        change_reason: Reason for status change
        metadata: Additional metadata stored as JSONB
        created_at: Record creation timestamp (from AuditedModel)
        updated_at: Last modification timestamp (from AuditedModel)
        created_by: User who created this record (from AuditedModel)
        updated_by: User who last modified this record (from AuditedModel)
        deleted_at: Soft deletion timestamp (from AuditedModel)
    """

    __tablename__ = "order_status_history"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique history record identifier",
    )

    # Foreign keys
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent order identifier",
    )

    # Status change details
    from_status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus, name="order_status", create_constraint=True),
        nullable=False,
        comment="Previous status",
    )

    to_status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus, name="order_status", create_constraint=True),
        nullable=False,
        comment="New status",
    )

    changed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who made the change",
    )

    change_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Reason for status change",
    )

    metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Additional metadata stored as JSONB",
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="status_history",
        foreign_keys=[order_id],
        lazy="selectin",
    )

    # Table constraints and indexes
    __table_args__ = (
        Index(
            "ix_order_status_history_order",
            "order_id",
        ),
        Index(
            "ix_order_status_history_order_created",
            "order_id",
            "created_at",
        ),
        Index(
            "ix_order_status_history_to_status",
            "to_status",
        ),
        Index(
            "ix_order_status_history_metadata_gin",
            "metadata",
            postgresql_using="gin",
        ),
        {
            "comment": "Order status change history for audit trail",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of OrderStatusHistory.

        Returns:
            String representation showing key history attributes
        """
        return (
            f"<OrderStatusHistory(id={self.id}, order_id={self.order_id}, "
            f"from_status={self.from_status.value}, to_status={self.to_status.value})>"
        )