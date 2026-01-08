"""
Vehicle option model with categories, compatibility rules, and pricing.

This module defines the VehicleOption model for managing vehicle configuration options
with comprehensive compatibility validation, pricing calculations, and category management.
Implements efficient indexing for option queries and JSONB storage for flexible rule data.
"""

import uuid
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    String,
    Numeric,
    Boolean,
    Index,
    CheckConstraint,
    text,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import BaseModel
from src.core.logging import get_logger

logger = get_logger(__name__)


class VehicleOption(BaseModel):
    """
    Vehicle option model for configuration management.

    Implements comprehensive option data management with compatibility rules stored in JSONB
    for flexibility, proper indexing for search performance, and price validation.
    Supports relationships with configurations and complex business rule validation.

    Attributes:
        id: Unique option identifier (UUID)
        vehicle_id: Reference to base vehicle (UUID)
        category: Option category (enum)
        name: Option name
        description: Detailed option description
        price: Option price
        is_required: Whether option is required for vehicle
        mutually_exclusive_with: Array of option IDs that cannot be selected together
        required_options: Array of option IDs that must be selected with this option
        created_at: Record creation timestamp (from BaseModel)
        updated_at: Last modification timestamp (from BaseModel)
    """

    __tablename__ = "vehicle_options"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique option identifier",
    )

    # Foreign key to vehicle
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Reference to base vehicle",
    )

    # Option category
    category: Mapped[str] = mapped_column(
        SQLEnum(
            "exterior",
            "interior",
            "technology",
            "safety",
            "performance",
            "comfort",
            "package",
            name="option_category_enum",
            create_type=True,
        ),
        nullable=False,
        index=True,
        comment="Option category",
    )

    # Option details
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Option name",
    )

    description: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="Detailed option description",
    )

    # Pricing
    price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        comment="Option price",
    )

    # Configuration rules
    is_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="Whether option is required for vehicle",
    )

    mutually_exclusive_with: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=False,
        default=list,
        server_default=text("'{}'::uuid[]"),
        comment="Array of option IDs that cannot be selected together",
    )

    required_options: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=False,
        default=list,
        server_default=text("'{}'::uuid[]"),
        comment="Array of option IDs that must be selected with this option",
    )

    # Table constraints and indexes
    __table_args__ = (
        # Composite index for vehicle option queries
        Index(
            "ix_vehicle_options_vehicle_category",
            "vehicle_id",
            "category",
        ),
        # Index for vehicle lookup
        Index(
            "ix_vehicle_options_vehicle_id",
            "vehicle_id",
        ),
        # Index for category filtering
        Index(
            "ix_vehicle_options_category",
            "category",
        ),
        # Index for required options
        Index(
            "ix_vehicle_options_required",
            "vehicle_id",
            "is_required",
        ),
        # Index for price range queries
        Index(
            "ix_vehicle_options_price",
            "price",
        ),
        # GIN index for array searches
        Index(
            "ix_vehicle_options_mutually_exclusive_gin",
            "mutually_exclusive_with",
            postgresql_using="gin",
        ),
        Index(
            "ix_vehicle_options_required_options_gin",
            "required_options",
            postgresql_using="gin",
        ),
        # Check constraints for data validation
        CheckConstraint(
            "length(name) >= 1",
            name="ck_vehicle_options_name_min_length",
        ),
        CheckConstraint(
            "length(description) >= 1",
            name="ck_vehicle_options_description_min_length",
        ),
        CheckConstraint(
            "price >= 0",
            name="ck_vehicle_options_price_non_negative",
        ),
        CheckConstraint(
            "price <= 100000.00",
            name="ck_vehicle_options_price_max",
        ),
        {
            "comment": "Vehicle options with categories, compatibility rules, and pricing",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of VehicleOption.

        Returns:
            String representation showing key option attributes
        """
        return (
            f"<VehicleOption(id={self.id}, vehicle_id={self.vehicle_id}, "
            f"category='{self.category}', name='{self.name}', "
            f"price={self.price}, is_required={self.is_required})>"
        )

    @property
    def formatted_price(self) -> str:
        """
        Get formatted price string.

        Returns:
            Price formatted as currency string
        """
        return f"${self.price:,.2f}"

    @property
    def has_compatibility_rules(self) -> bool:
        """
        Check if option has compatibility rules.

        Returns:
            True if option has mutually exclusive or required options
        """
        return bool(self.mutually_exclusive_with or self.required_options)

    @property
    def has_mutually_exclusive_options(self) -> bool:
        """
        Check if option has mutually exclusive options.

        Returns:
            True if option has mutually exclusive options
        """
        return bool(self.mutually_exclusive_with)

    @property
    def has_required_options(self) -> bool:
        """
        Check if option has required options.

        Returns:
            True if option has required options
        """
        return bool(self.required_options)

    def is_compatible_with(self, option_id: uuid.UUID) -> bool:
        """
        Check if option is compatible with another option.

        Args:
            option_id: ID of option to check compatibility with

        Returns:
            True if options are compatible (not mutually exclusive)
        """
        return option_id not in self.mutually_exclusive_with

    def requires_option(self, option_id: uuid.UUID) -> bool:
        """
        Check if option requires another option.

        Args:
            option_id: ID of option to check requirement for

        Returns:
            True if this option requires the specified option
        """
        return option_id in self.required_options

    def validate_compatibility(
        self, selected_option_ids: list[uuid.UUID]
    ) -> tuple[bool, list[str]]:
        """
        Validate compatibility with selected options.

        Args:
            selected_option_ids: List of currently selected option IDs

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check mutually exclusive options
        for option_id in selected_option_ids:
            if option_id in self.mutually_exclusive_with:
                errors.append(
                    f"Option '{self.name}' is mutually exclusive with option ID {option_id}"
                )
                logger.warning(
                    "Mutually exclusive option conflict",
                    option_id=str(self.id),
                    option_name=self.name,
                    conflicting_option_id=str(option_id),
                )

        # Check required options
        for required_id in self.required_options:
            if required_id not in selected_option_ids:
                errors.append(
                    f"Option '{self.name}' requires option ID {required_id}"
                )
                logger.warning(
                    "Required option missing",
                    option_id=str(self.id),
                    option_name=self.name,
                    required_option_id=str(required_id),
                )

        is_valid = len(errors) == 0

        if is_valid:
            logger.debug(
                "Option compatibility validated",
                option_id=str(self.id),
                option_name=self.name,
                selected_count=len(selected_option_ids),
            )

        return is_valid, errors

    def add_mutually_exclusive_option(self, option_id: uuid.UUID) -> None:
        """
        Add mutually exclusive option.

        Args:
            option_id: ID of option to add as mutually exclusive
        """
        if option_id not in self.mutually_exclusive_with:
            if self.mutually_exclusive_with is None:
                self.mutually_exclusive_with = []
            self.mutually_exclusive_with.append(option_id)
            logger.info(
                "Added mutually exclusive option",
                option_id=str(self.id),
                exclusive_option_id=str(option_id),
            )

    def remove_mutually_exclusive_option(self, option_id: uuid.UUID) -> None:
        """
        Remove mutually exclusive option.

        Args:
            option_id: ID of option to remove from mutually exclusive list
        """
        if self.mutually_exclusive_with and option_id in self.mutually_exclusive_with:
            self.mutually_exclusive_with.remove(option_id)
            logger.info(
                "Removed mutually exclusive option",
                option_id=str(self.id),
                exclusive_option_id=str(option_id),
            )

    def add_required_option(self, option_id: uuid.UUID) -> None:
        """
        Add required option.

        Args:
            option_id: ID of option to add as required
        """
        if option_id not in self.required_options:
            if self.required_options is None:
                self.required_options = []
            self.required_options.append(option_id)
            logger.info(
                "Added required option",
                option_id=str(self.id),
                required_option_id=str(option_id),
            )

    def remove_required_option(self, option_id: uuid.UUID) -> None:
        """
        Remove required option.

        Args:
            option_id: ID of option to remove from required list
        """
        if self.required_options and option_id in self.required_options:
            self.required_options.remove(option_id)
            logger.info(
                "Removed required option",
                option_id=str(self.id),
                required_option_id=str(option_id),
            )

    def update_price(self, new_price: Decimal) -> None:
        """
        Update option price with validation.

        Args:
            new_price: New price to set

        Raises:
            ValueError: If price is negative or exceeds maximum
        """
        if new_price < 0:
            raise ValueError("Price cannot be negative")
        if new_price > Decimal("100000.00"):
            raise ValueError("Price exceeds maximum allowed value")
        
        old_price = self.price
        self.price = new_price
        
        logger.info(
            "Option price updated",
            option_id=str(self.id),
            option_name=self.name,
            old_price=float(old_price),
            new_price=float(new_price),
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert option to dictionary representation.

        Returns:
            Dictionary representation of option
        """
        return {
            "id": str(self.id),
            "vehicle_id": str(self.vehicle_id),
            "category": self.category,
            "name": self.name,
            "description": self.description,
            "price": float(self.price),
            "formatted_price": self.formatted_price,
            "is_required": self.is_required,
            "mutually_exclusive_with": [str(oid) for oid in self.mutually_exclusive_with],
            "required_options": [str(oid) for oid in self.required_options],
            "has_compatibility_rules": self.has_compatibility_rules,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }