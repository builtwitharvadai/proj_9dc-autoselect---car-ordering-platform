"""
Dealer inventory management Pydantic schemas.

This module defines comprehensive Pydantic models for dealer inventory operations
including inventory updates, bulk operations, audit logging, and dashboard statistics
with validation for dealer-specific workflows.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class DealerInventoryUpdate(BaseModel):
    """Schema for updating dealer inventory item."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )

    vehicle_id: UUID = Field(
        ...,
        description="Vehicle unique identifier",
    )
    quantity: Optional[int] = Field(
        None,
        ge=0,
        le=10000,
        description="Available quantity",
    )
    location: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Storage location",
    )
    status: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="Inventory status",
    )
    vin: Optional[str] = Field(
        None,
        min_length=17,
        max_length=17,
        pattern=r"^[A-HJ-NPR-Z0-9]{17}$",
        description="Vehicle Identification Number",
    )
    notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Additional notes",
    )
    custom_attributes: Optional[dict[str, Any]] = Field(
        None,
        description="Custom dealer-specific attributes",
    )

    @field_validator("location", "status")
    @classmethod
    def validate_non_empty_string(cls, v: Optional[str]) -> Optional[str]:
        """Validate that string fields are not empty after stripping."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("vin")
    @classmethod
    def validate_vin_uppercase(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize VIN to uppercase."""
        if v is not None:
            v = v.strip().upper()
            if not v:
                return None
        return v

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean notes field."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("custom_attributes")
    @classmethod
    def validate_custom_attributes(
        cls, v: Optional[dict[str, Any]]
    ) -> Optional[dict[str, Any]]:
        """Validate custom attributes structure."""
        if v is not None:
            if not isinstance(v, dict):
                raise ValueError("custom_attributes must be a dictionary")
            for key in v.keys():
                if not isinstance(key, str) or not key.strip():
                    raise ValueError(
                        "All custom attribute keys must be non-empty strings"
                    )
        return v

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "DealerInventoryUpdate":
        """Ensure at least one field is provided for update."""
        update_fields = [
            "quantity",
            "location",
            "status",
            "vin",
            "notes",
            "custom_attributes",
        ]
        if not any(getattr(self, field) is not None for field in update_fields):
            raise ValueError("At least one field must be provided for update")
        return self


class BulkInventoryItem(BaseModel):
    """Schema for individual item in bulk inventory update."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    vehicle_id: UUID = Field(
        ...,
        description="Vehicle unique identifier",
    )
    quantity: int = Field(
        ...,
        ge=0,
        le=10000,
        description="Available quantity",
    )
    location: Optional[str] = Field(
        None,
        max_length=200,
        description="Storage location",
    )
    status: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Inventory status",
    )
    vin: Optional[str] = Field(
        None,
        min_length=17,
        max_length=17,
        pattern=r"^[A-HJ-NPR-Z0-9]{17}$",
        description="Vehicle Identification Number",
    )
    notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Additional notes",
    )

    @field_validator("location", "status")
    @classmethod
    def validate_non_empty_string(cls, v: Optional[str]) -> Optional[str]:
        """Validate that string fields are not empty."""
        if v is not None:
            v = v.strip()
            if not v:
                if cls.model_fields[cls.__name__].is_required():
                    raise ValueError("Field cannot be empty")
                return None
        return v

    @field_validator("vin")
    @classmethod
    def validate_vin_uppercase(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize VIN to uppercase."""
        if v is not None:
            v = v.strip().upper()
            if not v:
                return None
        return v


class BulkInventoryUpdate(BaseModel):
    """Schema for bulk inventory update operations."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    items: list[BulkInventoryItem] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="List of inventory items to update",
    )
    operation: str = Field(
        ...,
        pattern=r"^(create|update|upsert)$",
        description="Bulk operation type",
    )
    validate_only: bool = Field(
        False,
        description="Only validate without persisting changes",
    )

    @field_validator("items")
    @classmethod
    def validate_unique_vehicle_ids(
        cls, v: list[BulkInventoryItem]
    ) -> list[BulkInventoryItem]:
        """Validate that vehicle IDs are unique in the batch."""
        vehicle_ids = [item.vehicle_id for item in v]
        if len(vehicle_ids) != len(set(vehicle_ids)):
            raise ValueError("Duplicate vehicle IDs found in bulk update")
        return v

    @model_validator(mode="after")
    def validate_batch_size(self) -> "BulkInventoryUpdate":
        """Validate batch size is within acceptable limits."""
        if len(self.items) > 1000:
            raise ValueError("Bulk update cannot exceed 1000 items")
        return self


class InventoryAuditLog(BaseModel):
    """Schema for inventory audit log entry."""

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
    )

    id: UUID = Field(
        ...,
        description="Audit log entry unique identifier",
    )
    dealer_id: UUID = Field(
        ...,
        description="Dealer unique identifier",
    )
    vehicle_id: UUID = Field(
        ...,
        description="Vehicle unique identifier",
    )
    action: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Action performed",
    )
    changes: dict[str, Any] = Field(
        ...,
        description="Changes made to inventory",
    )
    previous_values: Optional[dict[str, Any]] = Field(
        None,
        description="Previous values before change",
    )
    user_id: UUID = Field(
        ...,
        description="User who performed the action",
    )
    ip_address: Optional[str] = Field(
        None,
        max_length=45,
        description="IP address of the user",
    )
    user_agent: Optional[str] = Field(
        None,
        max_length=500,
        description="User agent string",
    )
    timestamp: datetime = Field(
        ...,
        description="Timestamp of the action",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class DealerDashboardStats(BaseModel):
    """Schema for dealer dashboard statistics."""

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
    )

    dealer_id: UUID = Field(
        ...,
        description="Dealer unique identifier",
    )
    total_vehicles: int = Field(
        ...,
        ge=0,
        description="Total number of vehicles in inventory",
    )
    active_vehicles: int = Field(
        ...,
        ge=0,
        description="Number of active vehicles",
    )
    inactive_vehicles: int = Field(
        ...,
        ge=0,
        description="Number of inactive vehicles",
    )
    sold_vehicles: int = Field(
        ...,
        ge=0,
        description="Number of sold vehicles",
    )
    reserved_vehicles: int = Field(
        ...,
        ge=0,
        description="Number of reserved vehicles",
    )
    total_inventory_value: Decimal = Field(
        ...,
        ge=Decimal("0"),
        decimal_places=2,
        description="Total inventory value in USD",
    )
    average_vehicle_price: Decimal = Field(
        ...,
        ge=Decimal("0"),
        decimal_places=2,
        description="Average vehicle price in USD",
    )
    low_stock_count: int = Field(
        ...,
        ge=0,
        description="Number of vehicles with low stock",
    )
    out_of_stock_count: int = Field(
        ...,
        ge=0,
        description="Number of out of stock vehicles",
    )
    recent_updates_count: int = Field(
        ...,
        ge=0,
        description="Number of recent inventory updates",
    )
    pending_orders_count: int = Field(
        ...,
        ge=0,
        description="Number of pending orders",
    )
    last_updated: datetime = Field(
        ...,
        description="Last statistics update timestamp",
    )
    top_makes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Top vehicle makes by count",
    )
    top_models: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Top vehicle models by count",
    )
    inventory_by_status: dict[str, int] = Field(
        default_factory=dict,
        description="Inventory breakdown by status",
    )
    inventory_by_body_style: dict[str, int] = Field(
        default_factory=dict,
        description="Inventory breakdown by body style",
    )

    @model_validator(mode="after")
    def validate_vehicle_counts(self) -> "DealerDashboardStats":
        """Validate that vehicle counts are consistent."""
        calculated_total = (
            self.active_vehicles
            + self.inactive_vehicles
            + self.sold_vehicles
            + self.reserved_vehicles
        )
        if calculated_total > self.total_vehicles:
            raise ValueError(
                "Sum of status counts cannot exceed total vehicles"
            )
        return self

    @model_validator(mode="after")
    def validate_average_price(self) -> "DealerDashboardStats":
        """Validate average price calculation."""
        if self.total_vehicles > 0 and self.average_vehicle_price == Decimal("0"):
            raise ValueError(
                "Average vehicle price must be greater than zero when vehicles exist"
            )
        if self.total_vehicles == 0 and self.average_vehicle_price != Decimal("0"):
            raise ValueError(
                "Average vehicle price must be zero when no vehicles exist"
            )
        return self


class DealerInventoryResponse(BaseModel):
    """Schema for dealer inventory item response."""

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
    )

    id: UUID = Field(
        ...,
        description="Inventory item unique identifier",
    )
    dealer_id: UUID = Field(
        ...,
        description="Dealer unique identifier",
    )
    vehicle_id: UUID = Field(
        ...,
        description="Vehicle unique identifier",
    )
    quantity: int = Field(
        ...,
        ge=0,
        description="Available quantity",
    )
    location: Optional[str] = Field(
        None,
        description="Storage location",
    )
    status: str = Field(
        ...,
        description="Inventory status",
    )
    vin: Optional[str] = Field(
        None,
        description="Vehicle Identification Number",
    )
    notes: Optional[str] = Field(
        None,
        description="Additional notes",
    )
    custom_attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom dealer-specific attributes",
    )
    created_at: datetime = Field(
        ...,
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
    )
    created_by: UUID = Field(
        ...,
        description="User who created the entry",
    )
    updated_by: UUID = Field(
        ...,
        description="User who last updated the entry",
    )


class BulkInventoryResponse(BaseModel):
    """Schema for bulk inventory operation response."""

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
    )

    total_items: int = Field(
        ...,
        ge=0,
        description="Total number of items processed",
    )
    successful_items: int = Field(
        ...,
        ge=0,
        description="Number of successfully processed items",
    )
    failed_items: int = Field(
        ...,
        ge=0,
        description="Number of failed items",
    )
    errors: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of errors encountered",
    )
    warnings: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of warnings",
    )
    processed_ids: list[UUID] = Field(
        default_factory=list,
        description="List of successfully processed inventory IDs",
    )
    processing_time_ms: int = Field(
        ...,
        ge=0,
        description="Processing time in milliseconds",
    )

    @model_validator(mode="after")
    def validate_counts(self) -> "BulkInventoryResponse":
        """Validate that counts are consistent."""
        if self.successful_items + self.failed_items != self.total_items:
            raise ValueError(
                "Sum of successful and failed items must equal total items"
            )
        if self.successful_items != len(self.processed_ids):
            raise ValueError(
                "Number of successful items must match processed IDs count"
            )
        return self