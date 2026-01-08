"""
Package model for option bundles with discount pricing and compatibility rules.

This module defines the Package model for managing vehicle option packages with
bundled options, discount pricing, and comprehensive compatibility validation.
Implements efficient indexing for package queries and ARRAY storage for option lists.
"""

import uuid
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    String,
    Numeric,
    Index,
    CheckConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import BaseModel
from src.core.logging import get_logger

logger = get_logger(__name__)


class Package(BaseModel):
    """
    Package model for bundled vehicle options with discount pricing.

    Implements comprehensive package data management with included options stored
    in ARRAY for efficient queries, proper indexing for search performance, and
    price validation. Supports relationships with configurations and complex
    business rule validation for package compatibility.

    Attributes:
        id: Unique package identifier (UUID)
        vehicle_id: Reference to base vehicle (UUID)
        name: Package name
        description: Detailed package description
        base_price: Package base price before discount
        discount_percentage: Discount percentage applied to bundled options
        included_options: Array of option IDs included in package
        trim_compatibility: Array of compatible trim levels
        model_year_compatibility: Array of compatible model years
        created_at: Record creation timestamp (from BaseModel)
        updated_at: Last modification timestamp (from BaseModel)
    """

    __tablename__ = "packages"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique package identifier",
    )

    # Foreign key to vehicle
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Reference to base vehicle",
    )

    # Package details
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Package name",
    )

    description: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="Detailed package description",
    )

    # Pricing
    base_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        comment="Package base price before discount",
    )

    discount_percentage: Mapped[Decimal] = mapped_column(
        Numeric(precision=5, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0.00"),
        comment="Discount percentage applied to bundled options",
    )

    # Included options
    included_options: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=False,
        default=list,
        server_default=text("'{}'::uuid[]"),
        comment="Array of option IDs included in package",
    )

    # Compatibility rules
    trim_compatibility: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
        comment="Array of compatible trim levels",
    )

    model_year_compatibility: Mapped[list[int]] = mapped_column(
        ARRAY(text("INTEGER")),
        nullable=False,
        default=list,
        server_default=text("'{}'::integer[]"),
        comment="Array of compatible model years",
    )

    # Table constraints and indexes
    __table_args__ = (
        # Composite index for vehicle package queries
        Index(
            "ix_packages_vehicle_id",
            "vehicle_id",
        ),
        # Index for name searches
        Index(
            "ix_packages_name",
            "name",
        ),
        # Index for price range queries
        Index(
            "ix_packages_base_price",
            "base_price",
        ),
        # GIN index for array searches
        Index(
            "ix_packages_included_options_gin",
            "included_options",
            postgresql_using="gin",
        ),
        Index(
            "ix_packages_trim_compatibility_gin",
            "trim_compatibility",
            postgresql_using="gin",
        ),
        Index(
            "ix_packages_model_year_compatibility_gin",
            "model_year_compatibility",
            postgresql_using="gin",
        ),
        # Check constraints for data validation
        CheckConstraint(
            "length(name) >= 1",
            name="ck_packages_name_min_length",
        ),
        CheckConstraint(
            "length(description) >= 1",
            name="ck_packages_description_min_length",
        ),
        CheckConstraint(
            "base_price >= 0",
            name="ck_packages_base_price_non_negative",
        ),
        CheckConstraint(
            "base_price <= 100000.00",
            name="ck_packages_base_price_max",
        ),
        CheckConstraint(
            "discount_percentage >= 0",
            name="ck_packages_discount_percentage_non_negative",
        ),
        CheckConstraint(
            "discount_percentage <= 100.00",
            name="ck_packages_discount_percentage_max",
        ),
        CheckConstraint(
            "array_length(included_options, 1) >= 1",
            name="ck_packages_included_options_min_length",
        ),
        {
            "comment": "Option packages with bundled options and discount pricing",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of Package.

        Returns:
            String representation showing key package attributes
        """
        return (
            f"<Package(id={self.id}, vehicle_id={self.vehicle_id}, "
            f"name='{self.name}', base_price={self.base_price}, "
            f"discount_percentage={self.discount_percentage})>"
        )

    @property
    def formatted_price(self) -> str:
        """
        Get formatted price string.

        Returns:
            Price formatted as currency string
        """
        return f"${self.base_price:,.2f}"

    @property
    def formatted_discount(self) -> str:
        """
        Get formatted discount percentage string.

        Returns:
            Discount formatted as percentage string
        """
        return f"{self.discount_percentage}%"

    @property
    def discounted_price(self) -> Decimal:
        """
        Calculate discounted price.

        Returns:
            Price after applying discount percentage
        """
        discount_multiplier = Decimal("1.00") - (self.discount_percentage / Decimal("100.00"))
        return self.base_price * discount_multiplier

    @property
    def formatted_discounted_price(self) -> str:
        """
        Get formatted discounted price string.

        Returns:
            Discounted price formatted as currency string
        """
        return f"${self.discounted_price:,.2f}"

    @property
    def savings_amount(self) -> Decimal:
        """
        Calculate savings amount from discount.

        Returns:
            Amount saved from discount
        """
        return self.base_price - self.discounted_price

    @property
    def formatted_savings(self) -> str:
        """
        Get formatted savings amount string.

        Returns:
            Savings formatted as currency string
        """
        return f"${self.savings_amount:,.2f}"

    @property
    def option_count(self) -> int:
        """
        Get count of included options.

        Returns:
            Number of options in package
        """
        return len(self.included_options)

    @property
    def has_compatibility_rules(self) -> bool:
        """
        Check if package has compatibility rules.

        Returns:
            True if package has trim or model year compatibility rules
        """
        return bool(self.trim_compatibility or self.model_year_compatibility)

    def includes_option(self, option_id: uuid.UUID) -> bool:
        """
        Check if package includes specific option.

        Args:
            option_id: ID of option to check

        Returns:
            True if option is included in package
        """
        return option_id in self.included_options

    def is_compatible_with_trim(self, trim: str) -> bool:
        """
        Check if package is compatible with trim level.

        Args:
            trim: Trim level to check compatibility with

        Returns:
            True if package is compatible with trim (or no trim restrictions)
        """
        if not self.trim_compatibility:
            return True
        return trim in self.trim_compatibility

    def is_compatible_with_year(self, year: int) -> bool:
        """
        Check if package is compatible with model year.

        Args:
            year: Model year to check compatibility with

        Returns:
            True if package is compatible with year (or no year restrictions)
        """
        if not self.model_year_compatibility:
            return True
        return year in self.model_year_compatibility

    def validate_compatibility(
        self, trim: Optional[str] = None, year: Optional[int] = None
    ) -> tuple[bool, list[str]]:
        """
        Validate compatibility with trim and year.

        Args:
            trim: Trim level to validate
            year: Model year to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        if trim is not None and not self.is_compatible_with_trim(trim):
            errors.append(
                f"Package '{self.name}' is not compatible with trim '{trim}'"
            )
            logger.warning(
                "Package trim compatibility check failed",
                package_id=str(self.id),
                package_name=self.name,
                trim=trim,
                compatible_trims=self.trim_compatibility,
            )

        if year is not None and not self.is_compatible_with_year(year):
            errors.append(
                f"Package '{self.name}' is not compatible with year {year}"
            )
            logger.warning(
                "Package year compatibility check failed",
                package_id=str(self.id),
                package_name=self.name,
                year=year,
                compatible_years=self.model_year_compatibility,
            )

        is_valid = len(errors) == 0

        if is_valid:
            logger.debug(
                "Package compatibility validated",
                package_id=str(self.id),
                package_name=self.name,
                trim=trim,
                year=year,
            )

        return is_valid, errors

    def add_option(self, option_id: uuid.UUID) -> None:
        """
        Add option to package.

        Args:
            option_id: ID of option to add
        """
        if option_id not in self.included_options:
            if self.included_options is None:
                self.included_options = []
            self.included_options.append(option_id)
            logger.info(
                "Option added to package",
                package_id=str(self.id),
                option_id=str(option_id),
            )

    def remove_option(self, option_id: uuid.UUID) -> None:
        """
        Remove option from package.

        Args:
            option_id: ID of option to remove

        Raises:
            ValueError: If removing option would leave package empty
        """
        if self.included_options and option_id in self.included_options:
            if len(self.included_options) <= 1:
                raise ValueError("Cannot remove last option from package")
            self.included_options.remove(option_id)
            logger.info(
                "Option removed from package",
                package_id=str(self.id),
                option_id=str(option_id),
            )

    def add_trim_compatibility(self, trim: str) -> None:
        """
        Add compatible trim level.

        Args:
            trim: Trim level to add
        """
        if trim not in self.trim_compatibility:
            if self.trim_compatibility is None:
                self.trim_compatibility = []
            self.trim_compatibility.append(trim)
            logger.info(
                "Trim compatibility added",
                package_id=str(self.id),
                trim=trim,
            )

    def remove_trim_compatibility(self, trim: str) -> None:
        """
        Remove compatible trim level.

        Args:
            trim: Trim level to remove
        """
        if self.trim_compatibility and trim in self.trim_compatibility:
            self.trim_compatibility.remove(trim)
            logger.info(
                "Trim compatibility removed",
                package_id=str(self.id),
                trim=trim,
            )

    def add_year_compatibility(self, year: int) -> None:
        """
        Add compatible model year.

        Args:
            year: Model year to add
        """
        if year not in self.model_year_compatibility:
            if self.model_year_compatibility is None:
                self.model_year_compatibility = []
            self.model_year_compatibility.append(year)
            logger.info(
                "Year compatibility added",
                package_id=str(self.id),
                year=year,
            )

    def remove_year_compatibility(self, year: int) -> None:
        """
        Remove compatible model year.

        Args:
            year: Model year to remove
        """
        if self.model_year_compatibility and year in self.model_year_compatibility:
            self.model_year_compatibility.remove(year)
            logger.info(
                "Year compatibility removed",
                package_id=str(self.id),
                year=year,
            )

    def update_price(self, new_price: Decimal) -> None:
        """
        Update package price with validation.

        Args:
            new_price: New price to set

        Raises:
            ValueError: If price is negative or exceeds maximum
        """
        if new_price < 0:
            raise ValueError("Price cannot be negative")
        if new_price > Decimal("100000.00"):
            raise ValueError("Price exceeds maximum allowed value")

        old_price = self.base_price
        self.base_price = new_price

        logger.info(
            "Package price updated",
            package_id=str(self.id),
            package_name=self.name,
            old_price=float(old_price),
            new_price=float(new_price),
        )

    def update_discount(self, new_discount: Decimal) -> None:
        """
        Update discount percentage with validation.

        Args:
            new_discount: New discount percentage to set

        Raises:
            ValueError: If discount is negative or exceeds 100%
        """
        if new_discount < 0:
            raise ValueError("Discount percentage cannot be negative")
        if new_discount > Decimal("100.00"):
            raise ValueError("Discount percentage cannot exceed 100%")

        old_discount = self.discount_percentage
        self.discount_percentage = new_discount

        logger.info(
            "Package discount updated",
            package_id=str(self.id),
            package_name=self.name,
            old_discount=float(old_discount),
            new_discount=float(new_discount),
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert package to dictionary representation.

        Returns:
            Dictionary representation of package
        """
        return {
            "id": str(self.id),
            "vehicle_id": str(self.vehicle_id),
            "name": self.name,
            "description": self.description,
            "base_price": float(self.base_price),
            "formatted_price": self.formatted_price,
            "discount_percentage": float(self.discount_percentage),
            "formatted_discount": self.formatted_discount,
            "discounted_price": float(self.discounted_price),
            "formatted_discounted_price": self.formatted_discounted_price,
            "savings_amount": float(self.savings_amount),
            "formatted_savings": self.formatted_savings,
            "included_options": [str(oid) for oid in self.included_options],
            "option_count": self.option_count,
            "trim_compatibility": self.trim_compatibility,
            "model_year_compatibility": self.model_year_compatibility,
            "has_compatibility_rules": self.has_compatibility_rules,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }