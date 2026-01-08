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
    Boolean,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
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
        selected_options: JSONB field for flexible option storage with option IDs and values
        selected_packages: Array of package IDs included in configuration
        base_price: Base vehicle price
        options_price: Total price of selected options
        packages_price: Total price of selected packages
        discount_amount: Total discount amount applied
        tax_amount: Tax amount calculated
        destination_charge: Destination and delivery charge
        total_price: Total price including all components
        configuration_status: Current status of configuration
        is_valid: Whether configuration passes validation rules
        validation_errors: JSONB field storing validation error details
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
        comment="Selected customization options with option IDs and values in JSONB format",
    )

    # Selected packages
    selected_packages: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=False,
        default=list,
        server_default=text("'{}'::uuid[]"),
        comment="Array of package IDs included in configuration",
    )

    # Pricing breakdown
    base_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        comment="Base vehicle price",
    )

    options_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0.00"),
        comment="Total price of selected options",
    )

    packages_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0.00"),
        comment="Total price of selected packages",
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0.00"),
        comment="Total discount amount applied",
    )

    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0.00"),
        comment="Tax amount calculated",
    )

    destination_charge: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0.00"),
        comment="Destination and delivery charge",
    )

    total_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        comment="Total price including base price, options, packages, taxes, and fees",
    )

    # Configuration status
    configuration_status: Mapped[str] = mapped_column(
        SQLEnum(
            "draft",
            "pending_validation",
            "validated",
            "invalid",
            "finalized",
            name="configuration_status_enum",
            create_type=True,
        ),
        nullable=False,
        default="draft",
        server_default=text("'draft'"),
        index=True,
        comment="Current status of configuration",
    )

    # Validation
    is_valid: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        index=True,
        comment="Whether configuration passes validation rules",
    )

    validation_errors: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="JSONB field storing validation error details",
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
        # GIN index for JSONB validation errors search
        Index(
            "ix_vehicle_configurations_validation_errors_gin",
            "validation_errors",
            postgresql_using="gin",
        ),
        # GIN index for packages array search
        Index(
            "ix_vehicle_configurations_packages_gin",
            "selected_packages",
            postgresql_using="gin",
        ),
        # Index for price range queries
        Index(
            "ix_vehicle_configurations_total_price",
            "total_price",
        ),
        # Index for status filtering
        Index(
            "ix_vehicle_configurations_status",
            "configuration_status",
        ),
        # Index for validation status
        Index(
            "ix_vehicle_configurations_valid",
            "is_valid",
        ),
        # Composite index for active configurations
        Index(
            "ix_vehicle_configurations_active",
            "user_id",
            "vehicle_id",
            "deleted_at",
        ),
        # Composite index for status and validation
        Index(
            "ix_vehicle_configurations_status_valid",
            "configuration_status",
            "is_valid",
        ),
        # Check constraints for data validation
        CheckConstraint(
            "base_price >= 0",
            name="ck_vehicle_configurations_base_price_non_negative",
        ),
        CheckConstraint(
            "base_price <= 10000000.00",
            name="ck_vehicle_configurations_base_price_max",
        ),
        CheckConstraint(
            "options_price >= 0",
            name="ck_vehicle_configurations_options_price_non_negative",
        ),
        CheckConstraint(
            "packages_price >= 0",
            name="ck_vehicle_configurations_packages_price_non_negative",
        ),
        CheckConstraint(
            "discount_amount >= 0",
            name="ck_vehicle_configurations_discount_amount_non_negative",
        ),
        CheckConstraint(
            "tax_amount >= 0",
            name="ck_vehicle_configurations_tax_amount_non_negative",
        ),
        CheckConstraint(
            "destination_charge >= 0",
            name="ck_vehicle_configurations_destination_charge_non_negative",
        ),
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
            f"total_price={self.total_price}, status='{self.configuration_status}', "
            f"is_valid={self.is_valid})>"
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
    def formatted_base_price(self) -> str:
        """
        Get formatted base price string.

        Returns:
            Base price formatted as currency string
        """
        return f"${self.base_price:,.2f}"

    @property
    def formatted_options_price(self) -> str:
        """
        Get formatted options price string.

        Returns:
            Options price formatted as currency string
        """
        return f"${self.options_price:,.2f}"

    @property
    def formatted_packages_price(self) -> str:
        """
        Get formatted packages price string.

        Returns:
            Packages price formatted as currency string
        """
        return f"${self.packages_price:,.2f}"

    @property
    def formatted_discount(self) -> str:
        """
        Get formatted discount amount string.

        Returns:
            Discount formatted as currency string
        """
        return f"${self.discount_amount:,.2f}"

    @property
    def formatted_tax(self) -> str:
        """
        Get formatted tax amount string.

        Returns:
            Tax formatted as currency string
        """
        return f"${self.tax_amount:,.2f}"

    @property
    def formatted_destination_charge(self) -> str:
        """
        Get formatted destination charge string.

        Returns:
            Destination charge formatted as currency string
        """
        return f"${self.destination_charge:,.2f}"

    @property
    def option_count(self) -> int:
        """
        Get count of selected options.

        Returns:
            Number of options in configuration
        """
        return len(self.selected_options) if self.selected_options else 0

    @property
    def package_count(self) -> int:
        """
        Get count of selected packages.

        Returns:
            Number of packages in configuration
        """
        return len(self.selected_packages) if self.selected_packages else 0

    @property
    def has_validation_errors(self) -> bool:
        """
        Check if configuration has validation errors.

        Returns:
            True if validation errors exist
        """
        return bool(self.validation_errors)

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

    def add_package(self, package_id: uuid.UUID) -> None:
        """
        Add package to configuration.

        Args:
            package_id: ID of package to add
        """
        if package_id not in self.selected_packages:
            if self.selected_packages is None:
                self.selected_packages = []
            self.selected_packages.append(package_id)

    def remove_package(self, package_id: uuid.UUID) -> bool:
        """
        Remove package from configuration.

        Args:
            package_id: ID of package to remove

        Returns:
            True if package was removed, False if not found
        """
        if self.selected_packages and package_id in self.selected_packages:
            self.selected_packages.remove(package_id)
            return True
        return False

    def has_package(self, package_id: uuid.UUID) -> bool:
        """
        Check if package is included.

        Args:
            package_id: ID of package to check

        Returns:
            True if package is included
        """
        return package_id in (self.selected_packages or [])

    def clear_packages(self) -> None:
        """Clear all selected packages."""
        self.selected_packages = []

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

    def add_validation_error(self, error_code: str, message: str, **context: Any) -> None:
        """
        Add validation error to configuration.

        Args:
            error_code: Error code identifier
            message: Error message
            **context: Additional context data
        """
        if self.validation_errors is None:
            self.validation_errors = {}
        
        if "errors" not in self.validation_errors:
            self.validation_errors["errors"] = []
        
        self.validation_errors["errors"].append({
            "code": error_code,
            "message": message,
            "context": context,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.is_valid = False

    def clear_validation_errors(self) -> None:
        """Clear all validation errors."""
        self.validation_errors = {}
        self.is_valid = True

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

        if self.base_price < 0:
            errors.append("Base price cannot be negative")

        if self.options_price < 0:
            errors.append("Options price cannot be negative")

        if self.packages_price < 0:
            errors.append("Packages price cannot be negative")

        if self.discount_amount < 0:
            errors.append("Discount amount cannot be negative")

        if self.tax_amount < 0:
            errors.append("Tax amount cannot be negative")

        if self.destination_charge < 0:
            errors.append("Destination charge cannot be negative")

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
            "base_price": float(self.base_price),
            "formatted_base_price": self.formatted_base_price,
            "options_price": float(self.options_price),
            "formatted_options_price": self.formatted_options_price,
            "packages_price": float(self.packages_price),
            "formatted_packages_price": self.formatted_packages_price,
            "discount_amount": float(self.discount_amount),
            "formatted_discount": self.formatted_discount,
            "tax_amount": float(self.tax_amount),
            "formatted_tax": self.formatted_tax,
            "destination_charge": float(self.destination_charge),
            "formatted_destination_charge": self.formatted_destination_charge,
            "total_price": float(self.total_price),
            "formatted_price": self.formatted_price,
            "configuration_status": self.configuration_status,
            "is_valid": self.is_valid,
            "option_count": self.option_count,
            "package_count": self.package_count,
            "has_validation_errors": self.has_validation_errors,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_options:
            data["selected_options"] = self.selected_options or {}
            data["selected_packages"] = [str(pid) for pid in self.selected_packages]
            data["validation_errors"] = self.validation_errors or {}

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
            selected_packages=self.selected_packages.copy() if self.selected_packages else [],
            base_price=self.base_price,
            options_price=self.options_price,
            packages_price=self.packages_price,
            discount_amount=self.discount_amount,
            tax_amount=self.tax_amount,
            destination_charge=self.destination_charge,
            total_price=self.total_price,
            configuration_status="draft",
            is_valid=False,
            validation_errors={},
        )

    def archive(self) -> None:
        """Archive configuration by setting deleted_at timestamp."""
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore archived configuration by clearing deleted_at timestamp."""
        self.deleted_at = None