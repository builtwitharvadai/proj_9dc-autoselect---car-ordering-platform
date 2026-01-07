"""
Vehicle model with specifications and metadata.

This module defines the Vehicle model for managing vehicle inventory with comprehensive
specifications, pricing, and search capabilities. Implements efficient indexing for
search operations and JSONB storage for flexible specification data.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any

from sqlalchemy import (
    String,
    Numeric,
    Index,
    CheckConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import AuditedModel


class Vehicle(AuditedModel):
    """
    Vehicle model for inventory management.

    Implements comprehensive vehicle data management with specifications stored in JSONB
    for flexibility, proper indexing for search performance, and price validation.
    Supports relationships with orders and configurations.

    Attributes:
        id: Unique vehicle identifier (UUID)
        make: Vehicle manufacturer (e.g., Toyota, Ford)
        model: Vehicle model name (e.g., Camry, F-150)
        year: Manufacturing year
        trim: Trim level/package (e.g., LE, XLT, Premium)
        specifications: JSONB field for flexible specification storage
        base_price: Base price before options and configurations
        created_at: Record creation timestamp (from AuditedModel)
        updated_at: Last modification timestamp (from AuditedModel)
        created_by: User who created this record (from AuditedModel)
        updated_by: User who last modified this record (from AuditedModel)
        deleted_at: Soft deletion timestamp (from AuditedModel)
    """

    __tablename__ = "vehicles"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique vehicle identifier",
    )

    # Vehicle identification fields
    make: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Vehicle manufacturer",
    )

    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Vehicle model name",
    )

    year: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
        comment="Manufacturing year",
    )

    trim: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Trim level or package",
    )

    # Specifications stored as JSONB for flexibility
    specifications: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Vehicle specifications in JSONB format",
    )

    # Pricing
    base_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        comment="Base price before options",
    )

    # Relationships
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="vehicle",
        foreign_keys="Order.vehicle_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    configurations: Mapped[list["VehicleConfiguration"]] = relationship(
        "VehicleConfiguration",
        back_populates="vehicle",
        foreign_keys="VehicleConfiguration.vehicle_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    # Table constraints and indexes
    __table_args__ = (
        # Composite index for common search patterns
        Index(
            "ix_vehicles_make_model_year",
            "make",
            "model",
            "year",
        ),
        # Index for year-based queries
        Index(
            "ix_vehicles_year_make",
            "year",
            "make",
        ),
        # GIN index for JSONB specifications search
        Index(
            "ix_vehicles_specifications_gin",
            "specifications",
            postgresql_using="gin",
        ),
        # Index for price range queries
        Index(
            "ix_vehicles_base_price",
            "base_price",
        ),
        # Composite index for active vehicles search
        Index(
            "ix_vehicles_active_search",
            "make",
            "model",
            "year",
            "deleted_at",
        ),
        # Check constraints for data validation
        CheckConstraint(
            "length(make) >= 1",
            name="ck_vehicles_make_min_length",
        ),
        CheckConstraint(
            "length(model) >= 1",
            name="ck_vehicles_model_min_length",
        ),
        CheckConstraint(
            "length(trim) >= 1",
            name="ck_vehicles_trim_min_length",
        ),
        CheckConstraint(
            "year >= 1900 AND year <= 2100",
            name="ck_vehicles_year_range",
        ),
        CheckConstraint(
            "base_price >= 0",
            name="ck_vehicles_base_price_non_negative",
        ),
        CheckConstraint(
            "base_price <= 10000000.00",
            name="ck_vehicles_base_price_max",
        ),
        {
            "comment": "Vehicle inventory with specifications and pricing",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of Vehicle.

        Returns:
            String representation showing key vehicle attributes
        """
        return (
            f"<Vehicle(id={self.id}, make='{self.make}', "
            f"model='{self.model}', year={self.year}, "
            f"trim='{self.trim}', base_price={self.base_price})>"
        )

    @property
    def full_name(self) -> str:
        """
        Get vehicle's full name.

        Returns:
            Formatted string with year, make, model, and trim
        """
        return f"{self.year} {self.make} {self.model} {self.trim}"

    @property
    def display_name(self) -> str:
        """
        Get vehicle's display name without trim.

        Returns:
            Formatted string with year, make, and model
        """
        return f"{self.year} {self.make} {self.model}"

    @property
    def is_available(self) -> bool:
        """
        Check if vehicle is available (not soft deleted).

        Returns:
            True if vehicle is available for ordering
        """
        return self.deleted_at is None

    @property
    def formatted_price(self) -> str:
        """
        Get formatted price string.

        Returns:
            Price formatted as currency string
        """
        return f"${self.base_price:,.2f}"

    def get_specification(self, key: str, default: Any = None) -> Any:
        """
        Get specification value by key.

        Args:
            key: Specification key to retrieve
            default: Default value if key not found

        Returns:
            Specification value or default
        """
        return self.specifications.get(key, default)

    def set_specification(self, key: str, value: Any) -> None:
        """
        Set specification value.

        Args:
            key: Specification key to set
            value: Value to set for the key
        """
        if self.specifications is None:
            self.specifications = {}
        self.specifications[key] = value

    def update_specifications(self, specs: dict[str, Any]) -> None:
        """
        Update multiple specifications at once.

        Args:
            specs: Dictionary of specifications to update
        """
        if self.specifications is None:
            self.specifications = {}
        self.specifications.update(specs)

    def has_specification(self, key: str) -> bool:
        """
        Check if specification key exists.

        Args:
            key: Specification key to check

        Returns:
            True if specification key exists
        """
        return key in (self.specifications or {})

    def update_price(self, new_price: Decimal) -> None:
        """
        Update base price with validation.

        Args:
            new_price: New base price to set

        Raises:
            ValueError: If price is negative or exceeds maximum
        """
        if new_price < 0:
            raise ValueError("Price cannot be negative")
        if new_price > Decimal("10000000.00"):
            raise ValueError("Price exceeds maximum allowed value")
        self.base_price = new_price

    def matches_search(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        year: Optional[int] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
    ) -> bool:
        """
        Check if vehicle matches search criteria.

        Args:
            make: Make to match (case-insensitive)
            model: Model to match (case-insensitive)
            year: Year to match
            min_price: Minimum price filter
            max_price: Maximum price filter

        Returns:
            True if vehicle matches all provided criteria
        """
        if make and self.make.lower() != make.lower():
            return False
        if model and self.model.lower() != model.lower():
            return False
        if year and self.year != year:
            return False
        if min_price and self.base_price < min_price:
            return False
        if max_price and self.base_price > max_price:
            return False
        return True

    def to_dict(self, include_specifications: bool = True) -> dict[str, Any]:
        """
        Convert vehicle to dictionary representation.

        Args:
            include_specifications: Whether to include specifications in output

        Returns:
            Dictionary representation of vehicle
        """
        data = {
            "id": str(self.id),
            "make": self.make,
            "model": self.model,
            "year": self.year,
            "trim": self.trim,
            "base_price": float(self.base_price),
            "full_name": self.full_name,
            "display_name": self.display_name,
            "formatted_price": self.formatted_price,
            "is_available": self.is_available,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_specifications:
            data["specifications"] = self.specifications or {}

        return data

    def archive(self) -> None:
        """Archive vehicle by setting deleted_at timestamp."""
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore archived vehicle by clearing deleted_at timestamp."""
        self.deleted_at = None