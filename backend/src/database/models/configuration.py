"""
Vehicle configuration model for customization options.

This module defines the VehicleConfiguration model for managing vehicle customizations
with selected options stored in JSONB, price calculations, and proper relationships
to vehicles and users. Implements efficient indexing and validation for configuration
management.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any

from sqlalchemy import (
    String,
    Numeric,
    ForeignKey,
    Index,
    CheckConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import AuditedModel


class VehicleConfiguration(AuditedModel):
    """
    Vehicle configuration model for customization options.

    Manages vehicle customizations with flexible option storage in JSONB format,
    price tracking, and relationships to vehicles and users. Supports efficient
    querying and validation of configuration data.

    Attributes:
        id: Unique configuration identifier (UUID)
        vehicle_id: Foreign key to associated vehicle
        user_id: Foreign key to user who created configuration
        selected_options: JSONB field for flexible option storage
        total_price: Total price including base price and options
        created_at: Record creation timestamp (from AuditedModel)
        updated_at: Last modification timestamp (from AuditedModel)
        created_by: User who created this record (from AuditedModel)
        updated_by: User who last modified this record (from AuditedModel)
        deleted_at: Soft deletion timestamp (from AuditedModel)
    """

    __tablename__ = "vehicle_configurations"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique configuration identifier",
    )

    # Foreign keys
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated vehicle identifier",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who created this configuration",
    )

    # Configuration data stored as JSONB for flexibility
    selected_options: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Selected customization options in JSONB format",
    )

    # Pricing
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        comment="Total price including base price and options",
    )

    # Relationships
    vehicle: Mapped["Vehicle"] = relationship(
        "Vehicle",
        back_populates="configurations",
        foreign_keys=[vehicle_id],
        lazy="selectin",
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="configurations",
        foreign_keys=[user_id],
        lazy="selectin",
    )

    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="configuration",
        foreign_keys="Order.configuration_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    # Table constraints and indexes
    __table_args__ = (
        # Composite index for user's configurations
        Index(
            "ix_vehicle_configurations_user_vehicle",
            "user_id",
            "vehicle_id",
        ),
        # Index for vehicle configurations lookup
        Index(
            "ix_vehicle_configurations_vehicle_created",
            "vehicle_id",
            "created_at",
        ),
        # Index for user's recent configurations
        Index(
            "ix_vehicle_configurations_user_created",
            "user_id",
            "created_at",
        ),
        # GIN index for JSONB options search
        Index(
            "ix_vehicle_configurations_options_gin",
            "selected_options",
            postgresql_using="gin",
        ),
        # Index for price range queries
        Index(
            "ix_vehicle_configurations_total_price",
            "total_price",
        ),
        # Composite index for active configurations
        Index(
            "ix_vehicle_configurations_active",
            "user_id",
            "vehicle_id",
            "deleted_at",
        ),
        # Check constraints for data validation
        CheckConstraint(
            "total_price >= 0",
            name="ck_vehicle_configurations_total_price_non_negative",
        ),
        CheckConstraint(
            "total_price <= 10000000.00",
            name="ck_vehicle_configurations_total_price_max",
        ),
        {
            "comment": "Vehicle configurations with customization options",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of VehicleConfiguration.

        Returns:
            String representation showing key configuration attributes
        """
        return (
            f"<VehicleConfiguration(id={self.id}, "
            f"vehicle_id={self.vehicle_id}, user_id={self.user_id}, "
            f"total_price={self.total_price})>"
        )

    @property
    def is_active(self) -> bool:
        """
        Check if configuration is active (not soft deleted).

        Returns:
            True if configuration is active
        """
        return self.deleted_at is None

    @property
    def formatted_price(self) -> str:
        """
        Get formatted price string.

        Returns:
            Price formatted as currency string
        """
        return f"${self.total_price:,.2f}"

    @property
    def option_count(self) -> int:
        """
        Get count of selected options.

        Returns:
            Number of options in configuration
        """
        return len(self.selected_options) if self.selected_options else 0

    def get_option(self, key: str, default: Any = None) -> Any:
        """
        Get option value by key.

        Args:
            key: Option key to retrieve
            default: Default value if key not found

        Returns:
            Option value or default
        """
        return self.selected_options.get(key, default) if self.selected_options else default

    def set_option(self, key: str, value: Any) -> None:
        """
        Set option value.

        Args:
            key: Option key to set
            value: Value to set for the key
        """
        if self.selected_options is None:
            self.selected_options = {}
        self.selected_options[key] = value

    def update_options(self, options: dict[str, Any]) -> None:
        """
        Update multiple options at once.

        Args:
            options: Dictionary of options to update
        """
        if self.selected_options is None:
            self.selected_options = {}
        self.selected_options.update(options)

    def remove_option(self, key: str) -> bool:
        """
        Remove option by key.

        Args:
            key: Option key to remove

        Returns:
            True if option was removed, False if not found
        """
        if self.selected_options and key in self.selected_options:
            del self.selected_options[key]
            return True
        return False

    def has_option(self, key: str) -> bool:
        """
        Check if option key exists.

        Args:
            key: Option key to check

        Returns:
            True if option key exists
        """
        return key in (self.selected_options or {})

    def clear_options(self) -> None:
        """Clear all selected options."""
        self.selected_options = {}

    def update_price(self, new_price: Decimal) -> None:
        """
        Update total price with validation.

        Args:
            new_price: New total price to set

        Raises:
            ValueError: If price is negative or exceeds maximum
        """
        if new_price < 0:
            raise ValueError("Price cannot be negative")
        if new_price > Decimal("10000000.00"):
            raise ValueError("Price exceeds maximum allowed value")
        self.total_price = new_price

    def calculate_options_price(self) -> Decimal:
        """
        Calculate total price of selected options.

        Returns:
            Sum of all option prices, or 0 if no options
        """
        if not self.selected_options:
            return Decimal("0.00")

        total = Decimal("0.00")
        for option_data in self.selected_options.values():
            if isinstance(option_data, dict) and "price" in option_data:
                try:
                    total += Decimal(str(option_data["price"]))
                except (ValueError, TypeError):
                    continue

        return total

    def validate_options(self) -> tuple[bool, list[str]]:
        """
        Validate configuration options.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        if not self.selected_options:
            errors.append("No options selected")

        if self.total_price < 0:
            errors.append("Total price cannot be negative")

        if self.total_price > Decimal("10000000.00"):
            errors.append("Total price exceeds maximum allowed value")

        return len(errors) == 0, errors

    def to_dict(self, include_options: bool = True) -> dict[str, Any]:
        """
        Convert configuration to dictionary representation.

        Args:
            include_options: Whether to include selected options in output

        Returns:
            Dictionary representation of configuration
        """
        data = {
            "id": str(self.id),
            "vehicle_id": str(self.vehicle_id),
            "user_id": str(self.user_id),
            "total_price": float(self.total_price),
            "formatted_price": self.formatted_price,
            "option_count": self.option_count,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_options:
            data["selected_options"] = self.selected_options or {}

        return data

    def clone(self) -> "VehicleConfiguration":
        """
        Create a copy of this configuration with new ID.

        Returns:
            New VehicleConfiguration instance with same options
        """
        return VehicleConfiguration(
            vehicle_id=self.vehicle_id,
            user_id=self.user_id,
            selected_options=self.selected_options.copy() if self.selected_options else {},
            total_price=self.total_price,
        )

    def archive(self) -> None:
        """Archive configuration by setting deleted_at timestamp."""
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore archived configuration by clearing deleted_at timestamp."""
        self.deleted_at = None