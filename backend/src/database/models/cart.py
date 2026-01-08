"""
Shopping cart database models.

This module defines the Cart and CartItem models for managing shopping cart
functionality with session-based storage for anonymous users and database
storage for authenticated users. Implements proper relationships, indexes,
and expiration handling for cart management.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    String,
    Numeric,
    ForeignKey,
    Index,
    CheckConstraint,
    DateTime,
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import BaseModel


class Cart(BaseModel):
    """
    Shopping cart model for managing user cart sessions.

    Supports both authenticated users (user_id) and anonymous users (session_id).
    Implements automatic expiration handling with configurable TTL based on user type.
    Tracks cart lifecycle with created_at, updated_at, and expires_at timestamps.

    Attributes:
        id: Unique cart identifier (UUID)
        user_id: Foreign key to authenticated user (nullable for anonymous)
        session_id: Session identifier for anonymous users (nullable for authenticated)
        created_at: Cart creation timestamp (from BaseModel)
        updated_at: Last modification timestamp (from BaseModel)
        expires_at: Cart expiration timestamp (7 days for anonymous, 30 days for authenticated)
    """

    __tablename__ = "carts"

    # Primary key inherited from BaseModel (id: UUID)

    # User relationship (nullable for anonymous users)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Foreign key to authenticated user (null for anonymous)",
    )

    # Session identifier for anonymous users
    session_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Session identifier for anonymous users (null for authenticated)",
    )

    # Expiration timestamp
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Cart expiration timestamp (7 days anonymous, 30 days authenticated)",
    )

    # Relationships
    items: Mapped[list["CartItem"]] = relationship(
        "CartItem",
        back_populates="cart",
        foreign_keys="CartItem.cart_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="carts",
        foreign_keys=[user_id],
        lazy="selectin",
    )

    # Table constraints and indexes
    __table_args__ = (
        # Index for user cart lookup
        Index(
            "ix_carts_user_id",
            "user_id",
        ),
        # Index for session cart lookup
        Index(
            "ix_carts_session_id",
            "session_id",
        ),
        # Index for expiration cleanup queries
        Index(
            "ix_carts_expires_at",
            "expires_at",
        ),
        # Composite index for active cart queries
        Index(
            "ix_carts_user_expires",
            "user_id",
            "expires_at",
        ),
        # Composite index for session cart queries
        Index(
            "ix_carts_session_expires",
            "session_id",
            "expires_at",
        ),
        # Check constraint: must have either user_id or session_id
        CheckConstraint(
            "(user_id IS NOT NULL AND session_id IS NULL) OR "
            "(user_id IS NULL AND session_id IS NOT NULL)",
            name="ck_carts_user_or_session",
        ),
        # Check constraint: expires_at must be after created_at
        CheckConstraint(
            "expires_at > created_at",
            name="ck_carts_expires_after_created",
        ),
        # Check constraint: session_id length validation
        CheckConstraint(
            "session_id IS NULL OR length(session_id) >= 1",
            name="ck_carts_session_id_min_length",
        ),
        {
            "comment": "Shopping carts with session management and expiration",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of Cart.

        Returns:
            String representation showing key cart attributes
        """
        identifier = f"user_id={self.user_id}" if self.user_id else f"session_id='{self.session_id}'"
        return (
            f"<Cart(id={self.id}, {identifier}, "
            f"expires_at={self.expires_at.isoformat()})>"
        )

    @property
    def is_expired(self) -> bool:
        """
        Check if cart has expired.

        Returns:
            True if cart expiration time has passed
        """
        return datetime.utcnow() > self.expires_at

    @property
    def is_anonymous(self) -> bool:
        """
        Check if cart belongs to anonymous user.

        Returns:
            True if cart has session_id (anonymous), False if has user_id
        """
        return self.session_id is not None

    @property
    def is_authenticated(self) -> bool:
        """
        Check if cart belongs to authenticated user.

        Returns:
            True if cart has user_id (authenticated), False if has session_id
        """
        return self.user_id is not None

    @property
    def item_count(self) -> int:
        """
        Get total number of items in cart.

        Returns:
            Sum of quantities for all cart items
        """
        return sum(item.quantity for item in self.items)

    @property
    def total_price(self) -> Decimal:
        """
        Calculate total price of all items in cart.

        Returns:
            Sum of (quantity * price) for all cart items
        """
        return sum(
            (item.quantity * item.price if item.price else Decimal("0.00"))
            for item in self.items
        )

    def extend_expiration(self, days: int) -> None:
        """
        Extend cart expiration by specified number of days.

        Args:
            days: Number of days to extend expiration
        """
        from datetime import timedelta
        self.expires_at = datetime.utcnow() + timedelta(days=days)

    def is_empty(self) -> bool:
        """
        Check if cart has no items.

        Returns:
            True if cart has no items
        """
        return len(self.items) == 0


class CartItem(BaseModel):
    """
    Cart item model for individual items in shopping cart.

    Represents a configured vehicle in the cart with quantity tracking,
    inventory reservation, and price caching. Implements proper relationships
    to cart, vehicle, and configuration with expiration handling for reservations.

    Attributes:
        id: Unique cart item identifier (UUID)
        cart_id: Foreign key to parent cart
        vehicle_id: Foreign key to vehicle
        configuration_id: Foreign key to vehicle configuration
        quantity: Number of items (default 1)
        price: Cached price at time of addition
        reserved_until: Inventory reservation expiration timestamp (15 minutes)
        created_at: Item creation timestamp (from BaseModel)
        updated_at: Last modification timestamp (from BaseModel)
    """

    __tablename__ = "cart_items"

    # Primary key inherited from BaseModel (id: UUID)

    # Foreign keys
    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to parent cart",
    )

    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to vehicle",
    )

    configuration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_configurations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to vehicle configuration",
    )

    # Item details
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Number of items (default 1)",
    )

    price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=True,
        comment="Cached price at time of addition",
    )

    # Inventory reservation
    reserved_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Inventory reservation expiration timestamp (15 minutes)",
    )

    # Relationships
    cart: Mapped["Cart"] = relationship(
        "Cart",
        back_populates="items",
        foreign_keys=[cart_id],
        lazy="selectin",
    )

    vehicle: Mapped["Vehicle"] = relationship(
        "Vehicle",
        back_populates="cart_items",
        foreign_keys=[vehicle_id],
        lazy="selectin",
    )

    configuration: Mapped["VehicleConfiguration"] = relationship(
        "VehicleConfiguration",
        back_populates="cart_items",
        foreign_keys=[configuration_id],
        lazy="selectin",
    )

    # Table constraints and indexes
    __table_args__ = (
        # Index for cart item lookup
        Index(
            "ix_cart_items_cart_id",
            "cart_id",
        ),
        # Index for vehicle lookup
        Index(
            "ix_cart_items_vehicle_id",
            "vehicle_id",
        ),
        # Index for configuration lookup
        Index(
            "ix_cart_items_configuration_id",
            "configuration_id",
        ),
        # Index for reservation expiration cleanup
        Index(
            "ix_cart_items_reserved_until",
            "reserved_until",
        ),
        # Composite index for cart item queries
        Index(
            "ix_cart_items_cart_vehicle",
            "cart_id",
            "vehicle_id",
        ),
        # Composite index for reservation queries
        Index(
            "ix_cart_items_vehicle_reserved",
            "vehicle_id",
            "reserved_until",
        ),
        # Check constraint: quantity must be positive
        CheckConstraint(
            "quantity > 0",
            name="ck_cart_items_quantity_positive",
        ),
        # Check constraint: quantity maximum limit
        CheckConstraint(
            "quantity <= 100",
            name="ck_cart_items_quantity_max",
        ),
        # Check constraint: price validation
        CheckConstraint(
            "price IS NULL OR price >= 0",
            name="ck_cart_items_price_non_negative",
        ),
        # Check constraint: price maximum limit
        CheckConstraint(
            "price IS NULL OR price <= 10000000.00",
            name="ck_cart_items_price_max",
        ),
        # Check constraint: reserved_until must be after created_at
        CheckConstraint(
            "reserved_until IS NULL OR reserved_until > created_at",
            name="ck_cart_items_reserved_after_created",
        ),
        {
            "comment": "Cart items with inventory reservations and price caching",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of CartItem.

        Returns:
            String representation showing key cart item attributes
        """
        return (
            f"<CartItem(id={self.id}, cart_id={self.cart_id}, "
            f"vehicle_id={self.vehicle_id}, quantity={self.quantity}, "
            f"price={self.price})>"
        )

    @property
    def is_reserved(self) -> bool:
        """
        Check if item has active inventory reservation.

        Returns:
            True if reservation exists and hasn't expired
        """
        if self.reserved_until is None:
            return False
        return datetime.utcnow() < self.reserved_until

    @property
    def reservation_expired(self) -> bool:
        """
        Check if inventory reservation has expired.

        Returns:
            True if reservation exists but has expired
        """
        if self.reserved_until is None:
            return False
        return datetime.utcnow() >= self.reserved_until

    @property
    def subtotal(self) -> Decimal:
        """
        Calculate subtotal for this cart item.

        Returns:
            Quantity multiplied by price, or 0 if price not set
        """
        if self.price is None:
            return Decimal("0.00")
        return self.quantity * self.price

    @property
    def formatted_price(self) -> str:
        """
        Get formatted price string.

        Returns:
            Price formatted as currency string, or "N/A" if not set
        """
        if self.price is None:
            return "N/A"
        return f"${self.price:,.2f}"

    @property
    def formatted_subtotal(self) -> str:
        """
        Get formatted subtotal string.

        Returns:
            Subtotal formatted as currency string
        """
        return f"${self.subtotal:,.2f}"

    def reserve_inventory(self, minutes: int = 15) -> None:
        """
        Reserve inventory for this cart item.

        Args:
            minutes: Number of minutes to reserve (default 15)
        """
        from datetime import timedelta
        self.reserved_until = datetime.utcnow() + timedelta(minutes=minutes)

    def release_reservation(self) -> None:
        """Release inventory reservation by clearing reserved_until."""
        self.reserved_until = None

    def update_quantity(self, new_quantity: int) -> None:
        """
        Update item quantity with validation.

        Args:
            new_quantity: New quantity value

        Raises:
            ValueError: If quantity is invalid
        """
        if new_quantity <= 0:
            raise ValueError("Quantity must be positive")
        if new_quantity > 100:
            raise ValueError("Quantity cannot exceed 100")
        self.quantity = new_quantity

    def update_price(self, new_price: Decimal) -> None:
        """
        Update cached price with validation.

        Args:
            new_price: New price value

        Raises:
            ValueError: If price is invalid
        """
        if new_price < 0:
            raise ValueError("Price cannot be negative")
        if new_price > Decimal("10000000.00"):
            raise ValueError("Price exceeds maximum allowed value")
        self.price = new_price