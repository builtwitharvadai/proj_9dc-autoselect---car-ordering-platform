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
        vin: Vehicle Identification Number (17 characters)
        body_style: Body style (e.g., Sedan, SUV, Truck)
        exterior_color: Exterior color name
        interior_color: Interior color name
        fuel_type: Fuel type (e.g., Gasoline, Diesel, Electric, Hybrid)
        transmission: Transmission type (e.g., Automatic, Manual)
        drivetrain: Drivetrain type (e.g., FWD, RWD, AWD, 4WD)
        engine: Engine specifications (e.g., 2.5L 4-Cylinder)
        horsepower: Engine horsepower
        torque: Engine torque in lb-ft
        mpg_city: City fuel economy in MPG
        mpg_highway: Highway fuel economy in MPG
        seating_capacity: Number of seats
        cargo_capacity: Cargo capacity in cubic feet
        towing_capacity: Towing capacity in pounds
        specifications: JSONB field for flexible specification storage
        base_price: Base price before options and configurations
        msrp: Manufacturer's Suggested Retail Price
        invoice_price: Dealer invoice price
        destination_charge: Destination and delivery charge
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

    vin: Mapped[Optional[str]] = mapped_column(
        String(17),
        nullable=True,
        unique=True,
        index=True,
        comment="Vehicle Identification Number",
    )

    # Physical characteristics
    body_style: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Body style (Sedan, SUV, Truck, etc.)",
    )

    exterior_color: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Exterior color name",
    )

    interior_color: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Interior color name",
    )

    # Powertrain specifications
    fuel_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Fuel type (Gasoline, Diesel, Electric, Hybrid)",
    )

    transmission: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Transmission type",
    )

    drivetrain: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Drivetrain type (FWD, RWD, AWD, 4WD)",
    )

    engine: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Engine specifications",
    )

    horsepower: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Engine horsepower",
    )

    torque: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Engine torque in lb-ft",
    )

    # Fuel economy
    mpg_city: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="City fuel economy in MPG",
    )

    mpg_highway: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Highway fuel economy in MPG",
    )

    # Capacity specifications
    seating_capacity: Mapped[int] = mapped_column(
        nullable=False,
        comment="Number of seats",
    )

    cargo_capacity: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=6, scale=1),
        nullable=True,
        comment="Cargo capacity in cubic feet",
    )

    towing_capacity: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Towing capacity in pounds",
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

    msrp: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        comment="Manufacturer's Suggested Retail Price",
    )

    invoice_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=True,
        comment="Dealer invoice price",
    )

    destination_charge: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0.00"),
        comment="Destination and delivery charge",
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
        # Index for body style filtering
        Index(
            "ix_vehicles_body_style",
            "body_style",
        ),
        # Index for fuel type filtering
        Index(
            "ix_vehicles_fuel_type",
            "fuel_type",
        ),
        # Composite index for catalog browsing
        Index(
            "ix_vehicles_catalog_browse",
            "body_style",
            "fuel_type",
            "year",
            "base_price",
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
        CheckConstraint(
            "msrp >= 0",
            name="ck_vehicles_msrp_non_negative",
        ),
        CheckConstraint(
            "msrp <= 10000000.00",
            name="ck_vehicles_msrp_max",
        ),
        CheckConstraint(
            "invoice_price IS NULL OR invoice_price >= 0",
            name="ck_vehicles_invoice_price_non_negative",
        ),
        CheckConstraint(
            "destination_charge >= 0",
            name="ck_vehicles_destination_charge_non_negative",
        ),
        CheckConstraint(
            "vin IS NULL OR length(vin) = 17",
            name="ck_vehicles_vin_length",
        ),
        CheckConstraint(
            "horsepower IS NULL OR horsepower > 0",
            name="ck_vehicles_horsepower_positive",
        ),
        CheckConstraint(
            "torque IS NULL OR torque > 0",
            name="ck_vehicles_torque_positive",
        ),
        CheckConstraint(
            "mpg_city IS NULL OR mpg_city > 0",
            name="ck_vehicles_mpg_city_positive",
        ),
        CheckConstraint(
            "mpg_highway IS NULL OR mpg_highway > 0",
            name="ck_vehicles_mpg_highway_positive",
        ),
        CheckConstraint(
            "seating_capacity > 0 AND seating_capacity <= 20",
            name="ck_vehicles_seating_capacity_range",
        ),
        CheckConstraint(
            "cargo_capacity IS NULL OR cargo_capacity >= 0",
            name="ck_vehicles_cargo_capacity_non_negative",
        ),
        CheckConstraint(
            "towing_capacity IS NULL OR towing_capacity >= 0",
            name="ck_vehicles_towing_capacity_non_negative",
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

    @property
    def formatted_msrp(self) -> str:
        """
        Get formatted MSRP string.

        Returns:
            MSRP formatted as currency string
        """
        return f"${self.msrp:,.2f}"

    @property
    def total_price(self) -> Decimal:
        """
        Get total price including destination charge.

        Returns:
            Total price (base_price + destination_charge)
        """
        return self.base_price + self.destination_charge

    @property
    def formatted_total_price(self) -> str:
        """
        Get formatted total price string.

        Returns:
            Total price formatted as currency string
        """
        return f"${self.total_price:,.2f}"

    @property
    def mpg_combined(self) -> Optional[int]:
        """
        Calculate combined fuel economy.

        Returns:
            Combined MPG (55% highway, 45% city) or None if data unavailable
        """
        if self.mpg_city is not None and self.mpg_highway is not None:
            return int((self.mpg_highway * 0.55) + (self.mpg_city * 0.45))
        return None

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
        body_style: Optional[str] = None,
        fuel_type: Optional[str] = None,
    ) -> bool:
        """
        Check if vehicle matches search criteria.

        Args:
            make: Make to match (case-insensitive)
            model: Model to match (case-insensitive)
            year: Year to match
            min_price: Minimum price filter
            max_price: Maximum price filter
            body_style: Body style to match (case-insensitive)
            fuel_type: Fuel type to match (case-insensitive)

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
        if body_style and self.body_style.lower() != body_style.lower():
            return False
        if fuel_type and self.fuel_type.lower() != fuel_type.lower():
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
            "vin": self.vin,
            "body_style": self.body_style,
            "exterior_color": self.exterior_color,
            "interior_color": self.interior_color,
            "fuel_type": self.fuel_type,
            "transmission": self.transmission,
            "drivetrain": self.drivetrain,
            "engine": self.engine,
            "horsepower": self.horsepower,
            "torque": self.torque,
            "mpg_city": self.mpg_city,
            "mpg_highway": self.mpg_highway,
            "mpg_combined": self.mpg_combined,
            "seating_capacity": self.seating_capacity,
            "cargo_capacity": float(self.cargo_capacity) if self.cargo_capacity else None,
            "towing_capacity": self.towing_capacity,
            "base_price": float(self.base_price),
            "msrp": float(self.msrp),
            "invoice_price": float(self.invoice_price) if self.invoice_price else None,
            "destination_charge": float(self.destination_charge),
            "total_price": float(self.total_price),
            "full_name": self.full_name,
            "display_name": self.display_name,
            "formatted_price": self.formatted_price,
            "formatted_msrp": self.formatted_msrp,
            "formatted_total_price": self.formatted_total_price,
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


class VehicleConfiguration(AuditedModel):
    """
    Vehicle configuration model for managing custom vehicle configurations.

    Stores customer-specific vehicle configurations including selected options,
    packages, and customizations. Links vehicles to orders through configurations.

    Attributes:
        id: Unique configuration identifier (UUID)
        vehicle_id: Reference to base vehicle
        configuration_data: JSONB field for configuration details
        total_price: Total price including all options
        created_at: Record creation timestamp (from AuditedModel)
        updated_at: Last modification timestamp (from AuditedModel)
        created_by: User who created this record (from AuditedModel)
        updated_by: User who last modified this record (from AuditedModel)
        deleted_at: Soft deletion timestamp (from AuditedModel)
    """

    __tablename__ = "vehicle_configurations"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique configuration identifier",
    )

    # Foreign key to vehicle
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
        index=True,
        comment="Reference to base vehicle",
    )

    # Configuration data stored as JSONB
    configuration_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Configuration details in JSONB format",
    )

    # Total price including options
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        comment="Total price including all options",
    )

    # Relationships
    vehicle: Mapped["Vehicle"] = relationship(
        "Vehicle",
        back_populates="configurations",
        foreign_keys=[vehicle_id],
        lazy="selectin",
    )

    # Table constraints and indexes
    __table_args__ = (
        # Index for vehicle lookup
        Index(
            "ix_vehicle_configurations_vehicle_id",
            "vehicle_id",
        ),
        # GIN index for configuration data search
        Index(
            "ix_vehicle_configurations_data_gin",
            "configuration_data",
            postgresql_using="gin",
        ),
        # Check constraints
        CheckConstraint(
            "total_price >= 0",
            name="ck_vehicle_configurations_total_price_non_negative",
        ),
        {
            "comment": "Vehicle configurations with custom options",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of VehicleConfiguration.

        Returns:
            String representation showing key attributes
        """
        return (
            f"<VehicleConfiguration(id={self.id}, "
            f"vehicle_id={self.vehicle_id}, "
            f"total_price={self.total_price})>"
        )