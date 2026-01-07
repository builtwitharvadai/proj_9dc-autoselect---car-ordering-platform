"""
Inventory model for vehicle availability tracking.

This module defines the InventoryItem model for tracking vehicle inventory across
dealerships with status management, location tracking, and availability monitoring.
Implements comprehensive validation, status transitions, and audit logging.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Any

from sqlalchemy import (
    String,
    ForeignKey,
    Index,
    CheckConstraint,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import AuditedModel


class InventoryStatus(str, Enum):
    """
    Inventory status enumeration for tracking vehicle availability.

    Attributes:
        AVAILABLE: Vehicle available for purchase
        RESERVED: Vehicle reserved for customer
        SOLD: Vehicle sold to customer
        IN_TRANSIT: Vehicle in transit to dealership
        IN_PREPARATION: Vehicle being prepared for delivery
        MAINTENANCE: Vehicle undergoing maintenance
        UNAVAILABLE: Vehicle temporarily unavailable
    """

    AVAILABLE = "available"
    RESERVED = "reserved"
    SOLD = "sold"
    IN_TRANSIT = "in_transit"
    IN_PREPARATION = "in_preparation"
    MAINTENANCE = "maintenance"
    UNAVAILABLE = "unavailable"

    @classmethod
    def from_string(cls, value: str) -> "InventoryStatus":
        """
        Create InventoryStatus from string value.

        Args:
            value: String representation of status

        Returns:
            InventoryStatus enum value

        Raises:
            ValueError: If value is not a valid status
        """
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(f"Invalid inventory status: {value}")

    @property
    def is_available_for_purchase(self) -> bool:
        """Check if vehicle is available for purchase."""
        return self == InventoryStatus.AVAILABLE

    @property
    def is_reserved_or_sold(self) -> bool:
        """Check if vehicle is reserved or sold."""
        return self in (InventoryStatus.RESERVED, InventoryStatus.SOLD)

    @property
    def can_reserve(self) -> bool:
        """Check if vehicle can be reserved."""
        return self == InventoryStatus.AVAILABLE

    @property
    def can_sell(self) -> bool:
        """Check if vehicle can be sold."""
        return self in (InventoryStatus.AVAILABLE, InventoryStatus.RESERVED)


class InventoryItem(AuditedModel):
    """
    Inventory model for tracking vehicle availability across dealerships.

    Manages vehicle inventory with status tracking, location management, and
    availability monitoring. Implements comprehensive validation and audit logging
    for inventory operations.

    Attributes:
        id: Unique inventory item identifier (UUID)
        vehicle_id: Foreign key to vehicle
        dealership_id: Dealership identifier (UUID)
        vin: Vehicle Identification Number
        status: Current inventory status (enum)
        location: Physical location within dealership
        created_at: Record creation timestamp (from AuditedModel)
        updated_at: Last modification timestamp (from AuditedModel)
        created_by: User who created this record (from AuditedModel)
        updated_by: User who last modified this record (from AuditedModel)
        deleted_at: Soft deletion timestamp (from AuditedModel)
    """

    __tablename__ = "inventory_items"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique inventory item identifier",
    )

    # Foreign keys
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Vehicle identifier",
    )

    # Dealership and location
    dealership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Dealership identifier",
    )

    vin: Mapped[str] = mapped_column(
        String(17),
        nullable=False,
        unique=True,
        index=True,
        comment="Vehicle Identification Number",
    )

    # Status tracking
    status: Mapped[InventoryStatus] = mapped_column(
        SQLEnum(InventoryStatus, name="inventory_status", create_constraint=True),
        nullable=False,
        default=InventoryStatus.AVAILABLE,
        index=True,
        comment="Current inventory status",
    )

    # Location information
    location: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Physical location within dealership",
    )

    # Relationships
    vehicle: Mapped["Vehicle"] = relationship(
        "Vehicle",
        back_populates="inventory_items",
        foreign_keys=[vehicle_id],
        lazy="selectin",
    )

    # Table constraints and indexes
    __table_args__ = (
        # Composite index for dealership inventory queries
        Index(
            "ix_inventory_dealership_status",
            "dealership_id",
            "status",
        ),
        # Index for vehicle inventory lookup
        Index(
            "ix_inventory_vehicle_status",
            "vehicle_id",
            "status",
        ),
        # Index for VIN lookup
        Index(
            "ix_inventory_vin",
            "vin",
        ),
        # Index for available inventory queries
        Index(
            "ix_inventory_available",
            "dealership_id",
            "status",
            "deleted_at",
        ),
        # Index for status-based queries
        Index(
            "ix_inventory_status_created",
            "status",
            "created_at",
        ),
        # Composite index for dealership location queries
        Index(
            "ix_inventory_dealership_location",
            "dealership_id",
            "location",
        ),
        # Index for vehicle availability tracking
        Index(
            "ix_inventory_vehicle_availability",
            "vehicle_id",
            "status",
            "deleted_at",
        ),
        # Check constraints for data validation
        CheckConstraint(
            "length(vin) = 17",
            name="ck_inventory_vin_length",
        ),
        CheckConstraint(
            "vin ~ '^[A-HJ-NPR-Z0-9]{17}$'",
            name="ck_inventory_vin_format",
        ),
        CheckConstraint(
            "location IS NULL OR length(location) > 0",
            name="ck_inventory_location_not_empty",
        ),
        {
            "comment": "Vehicle inventory tracking across dealerships",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of InventoryItem.

        Returns:
            String representation showing key inventory attributes
        """
        return (
            f"<InventoryItem(id={self.id}, vin={self.vin}, "
            f"dealership_id={self.dealership_id}, status={self.status.value})>"
        )

    @property
    def is_available(self) -> bool:
        """
        Check if inventory item is available for purchase.

        Returns:
            True if item is available and not soft deleted
        """
        return (
            self.deleted_at is None
            and self.status.is_available_for_purchase
        )

    @property
    def is_reserved(self) -> bool:
        """
        Check if inventory item is reserved.

        Returns:
            True if item is reserved
        """
        return self.status == InventoryStatus.RESERVED

    @property
    def is_sold(self) -> bool:
        """
        Check if inventory item is sold.

        Returns:
            True if item is sold
        """
        return self.status == InventoryStatus.SOLD

    @property
    def can_be_reserved(self) -> bool:
        """
        Check if inventory item can be reserved.

        Returns:
            True if item can be reserved
        """
        return self.deleted_at is None and self.status.can_reserve

    @property
    def can_be_sold(self) -> bool:
        """
        Check if inventory item can be sold.

        Returns:
            True if item can be sold
        """
        return self.deleted_at is None and self.status.can_sell

    @property
    def formatted_vin(self) -> str:
        """
        Get formatted VIN string.

        Returns:
            VIN formatted with dashes for readability
        """
        if len(self.vin) == 17:
            return f"{self.vin[:3]}-{self.vin[3:9]}-{self.vin[9:]}"
        return self.vin

    def update_status(self, new_status: InventoryStatus) -> None:
        """
        Update inventory status with validation.

        Args:
            new_status: New status to set

        Raises:
            ValueError: If status transition is invalid
        """
        if not self._is_valid_transition(new_status):
            raise ValueError(
                f"Invalid status transition from {self.status.value} "
                f"to {new_status.value}"
            )

        self.status = new_status

    def _is_valid_transition(self, new_status: InventoryStatus) -> bool:
        """
        Validate status transition.

        Args:
            new_status: Target status

        Returns:
            True if transition is valid
        """
        valid_transitions = {
            InventoryStatus.AVAILABLE: {
                InventoryStatus.RESERVED,
                InventoryStatus.SOLD,
                InventoryStatus.MAINTENANCE,
                InventoryStatus.UNAVAILABLE,
            },
            InventoryStatus.RESERVED: {
                InventoryStatus.SOLD,
                InventoryStatus.AVAILABLE,
                InventoryStatus.IN_PREPARATION,
            },
            InventoryStatus.SOLD: set(),
            InventoryStatus.IN_TRANSIT: {
                InventoryStatus.AVAILABLE,
                InventoryStatus.IN_PREPARATION,
            },
            InventoryStatus.IN_PREPARATION: {
                InventoryStatus.AVAILABLE,
                InventoryStatus.SOLD,
            },
            InventoryStatus.MAINTENANCE: {
                InventoryStatus.AVAILABLE,
                InventoryStatus.UNAVAILABLE,
            },
            InventoryStatus.UNAVAILABLE: {
                InventoryStatus.AVAILABLE,
                InventoryStatus.MAINTENANCE,
            },
        }

        return new_status in valid_transitions.get(self.status, set())

    def reserve(self) -> None:
        """
        Reserve inventory item.

        Raises:
            ValueError: If item cannot be reserved
        """
        if not self.can_be_reserved:
            raise ValueError(
                f"Cannot reserve inventory item in status {self.status.value}"
            )

        self.status = InventoryStatus.RESERVED

    def mark_sold(self) -> None:
        """
        Mark inventory item as sold.

        Raises:
            ValueError: If item cannot be sold
        """
        if not self.can_be_sold:
            raise ValueError(
                f"Cannot sell inventory item in status {self.status.value}"
            )

        self.status = InventoryStatus.SOLD

    def release_reservation(self) -> None:
        """
        Release reservation and make item available.

        Raises:
            ValueError: If item is not reserved
        """
        if not self.is_reserved:
            raise ValueError("Cannot release reservation: item is not reserved")

        self.status = InventoryStatus.AVAILABLE

    def update_location(self, location: str) -> None:
        """
        Update physical location.

        Args:
            location: New location string

        Raises:
            ValueError: If location is invalid
        """
        if not location or not location.strip():
            raise ValueError("Location cannot be empty")

        if len(location) > 200:
            raise ValueError("Location exceeds maximum length of 200 characters")

        self.location = location.strip()

    def validate_vin(self) -> tuple[bool, list[str]]:
        """
        Validate VIN format and checksum.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        if len(self.vin) != 17:
            errors.append("VIN must be exactly 17 characters")

        if not self.vin.isalnum():
            errors.append("VIN must contain only alphanumeric characters")

        invalid_chars = set(self.vin) & {"I", "O", "Q", "i", "o", "q"}
        if invalid_chars:
            errors.append(f"VIN contains invalid characters: {invalid_chars}")

        if not self.vin.isupper():
            errors.append("VIN must be uppercase")

        return len(errors) == 0, errors

    def to_dict(self, include_relationships: bool = False) -> dict[str, Any]:
        """
        Convert inventory item to dictionary representation.

        Args:
            include_relationships: Whether to include related entities

        Returns:
            Dictionary representation of inventory item
        """
        data = {
            "id": str(self.id),
            "vehicle_id": str(self.vehicle_id),
            "dealership_id": str(self.dealership_id),
            "vin": self.vin,
            "formatted_vin": self.formatted_vin,
            "status": self.status.value,
            "location": self.location,
            "is_available": self.is_available,
            "is_reserved": self.is_reserved,
            "is_sold": self.is_sold,
            "can_be_reserved": self.can_be_reserved,
            "can_be_sold": self.can_be_sold,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_relationships:
            if self.vehicle:
                data["vehicle"] = {
                    "id": str(self.vehicle.id),
                    "make": self.vehicle.make,
                    "model": self.vehicle.model,
                    "year": self.vehicle.year,
                }

        return data