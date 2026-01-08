"""
Pydantic schemas for dealer management operations.

This module defines request/response schemas for dealer dashboard operations,
bulk configuration management, and regional availability settings.
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


class DealerConfigRequest(BaseModel):
    """Request schema for dealer configuration operations."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
        populate_by_name=True,
    )

    vehicle_id: UUID = Field(
        ...,
        description="Vehicle ID for configuration",
    )
    option_ids: list[UUID] = Field(
        default_factory=list,
        description="List of option IDs to configure",
        max_length=100,
    )
    package_ids: list[UUID] = Field(
        default_factory=list,
        description="List of package IDs to configure",
        max_length=50,
    )
    region_code: str = Field(
        ...,
        description="Region code for availability",
        min_length=2,
        max_length=10,
        pattern=r"^[A-Z]{2}(-[A-Z0-9]+)?$",
    )
    effective_date: datetime = Field(
        default_factory=datetime.now,
        description="Effective date for configuration",
    )
    expiration_date: Optional[datetime] = Field(
        None,
        description="Expiration date for configuration",
    )
    custom_pricing: Optional[dict[str, Decimal]] = Field(
        None,
        description="Custom pricing overrides by option/package ID",
    )
    notes: Optional[str] = Field(
        None,
        description="Configuration notes",
        max_length=1000,
    )

    @field_validator("option_ids", "package_ids")
    @classmethod
    def validate_unique_ids(cls, v: list[UUID]) -> list[UUID]:
        """Ensure IDs are unique."""
        if len(v) != len(set(v)):
            raise ValueError("Duplicate IDs are not allowed")
        return v

    @field_validator("custom_pricing")
    @classmethod
    def validate_custom_pricing(
        cls, v: Optional[dict[str, Decimal]]
    ) -> Optional[dict[str, Decimal]]:
        """Validate custom pricing values."""
        if v is None:
            return v

        for key, price in v.items():
            if price < 0:
                raise ValueError(f"Price for {key} cannot be negative")
            if price > Decimal("999999.99"):
                raise ValueError(f"Price for {key} exceeds maximum allowed")

        return v

    @model_validator(mode="after")
    def validate_dates(self) -> "DealerConfigRequest":
        """Validate date relationships."""
        if (
            self.expiration_date is not None
            and self.expiration_date <= self.effective_date
        ):
            raise ValueError("Expiration date must be after effective date")
        return self


class BulkConfigUpdate(BaseModel):
    """Schema for bulk configuration updates."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    configurations: list[DealerConfigRequest] = Field(
        ...,
        description="List of configurations to update",
        min_length=1,
        max_length=1000,
    )
    validate_only: bool = Field(
        False,
        description="Only validate without applying changes",
    )
    rollback_on_error: bool = Field(
        True,
        description="Rollback all changes if any configuration fails",
    )
    batch_size: int = Field(
        100,
        description="Number of configurations to process per batch",
        ge=1,
        le=500,
    )

    @field_validator("configurations")
    @classmethod
    def validate_configurations(
        cls, v: list[DealerConfigRequest]
    ) -> list[DealerConfigRequest]:
        """Validate configuration list."""
        vehicle_ids = [config.vehicle_id for config in v]
        if len(vehicle_ids) != len(set(vehicle_ids)):
            raise ValueError(
                "Duplicate vehicle IDs found in bulk update"
            )
        return v


class ConfigurationRule(BaseModel):
    """Schema for pricing and availability rules."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )

    rule_id: Optional[UUID] = Field(
        None,
        description="Rule ID for updates",
    )
    name: str = Field(
        ...,
        description="Rule name",
        min_length=3,
        max_length=100,
    )
    description: Optional[str] = Field(
        None,
        description="Rule description",
        max_length=500,
    )
    rule_type: str = Field(
        ...,
        description="Type of rule (pricing, availability, discount)",
        pattern=r"^(pricing|availability|discount|bundle)$",
    )
    conditions: dict[str, Any] = Field(
        ...,
        description="Rule conditions as key-value pairs",
    )
    actions: dict[str, Any] = Field(
        ...,
        description="Actions to apply when conditions are met",
    )
    priority: int = Field(
        0,
        description="Rule priority (higher values take precedence)",
        ge=0,
        le=100,
    )
    enabled: bool = Field(
        True,
        description="Whether rule is active",
    )
    effective_date: datetime = Field(
        default_factory=datetime.now,
        description="When rule becomes effective",
    )
    expiration_date: Optional[datetime] = Field(
        None,
        description="When rule expires",
    )
    regions: list[str] = Field(
        default_factory=list,
        description="Region codes where rule applies",
        max_length=100,
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate rule name."""
        if not v.strip():
            raise ValueError("Rule name cannot be empty")
        return v.strip()

    @field_validator("conditions", "actions")
    @classmethod
    def validate_rule_data(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate rule conditions and actions."""
        if not v:
            raise ValueError("Conditions and actions cannot be empty")

        max_depth = 5
        max_keys = 50

        def check_depth(obj: Any, depth: int = 0) -> None:
            if depth > max_depth:
                raise ValueError(
                    f"Rule data exceeds maximum nesting depth of {max_depth}"
                )
            if isinstance(obj, dict):
                if len(obj) > max_keys:
                    raise ValueError(
                        f"Rule data exceeds maximum keys of {max_keys}"
                    )
                for value in obj.values():
                    check_depth(value, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    check_depth(item, depth + 1)

        check_depth(v)
        return v

    @field_validator("regions")
    @classmethod
    def validate_regions(cls, v: list[str]) -> list[str]:
        """Validate region codes."""
        import re

        pattern = re.compile(r"^[A-Z]{2}(-[A-Z0-9]+)?$")
        for region in v:
            if not pattern.match(region):
                raise ValueError(
                    f"Invalid region code format: {region}"
                )
        return v

    @model_validator(mode="after")
    def validate_dates(self) -> "ConfigurationRule":
        """Validate date relationships."""
        if (
            self.expiration_date is not None
            and self.expiration_date <= self.effective_date
        ):
            raise ValueError("Expiration date must be after effective date")
        return self


class RegionAvailability(BaseModel):
    """Schema for regional availability settings."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    region_code: str = Field(
        ...,
        description="Region code",
        min_length=2,
        max_length=10,
        pattern=r"^[A-Z]{2}(-[A-Z0-9]+)?$",
    )
    region_name: str = Field(
        ...,
        description="Human-readable region name",
        min_length=2,
        max_length=100,
    )
    available_vehicle_ids: list[UUID] = Field(
        default_factory=list,
        description="Vehicle IDs available in this region",
        max_length=10000,
    )
    available_option_ids: list[UUID] = Field(
        default_factory=list,
        description="Option IDs available in this region",
        max_length=10000,
    )
    available_package_ids: list[UUID] = Field(
        default_factory=list,
        description="Package IDs available in this region",
        max_length=5000,
    )
    pricing_adjustments: dict[str, Decimal] = Field(
        default_factory=dict,
        description="Regional pricing adjustments by item ID",
    )
    tax_rate: Decimal = Field(
        Decimal("0.00"),
        description="Regional tax rate",
        ge=Decimal("0.00"),
        le=Decimal("1.00"),
        decimal_places=4,
    )
    currency_code: str = Field(
        "USD",
        description="Currency code for region",
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
    )
    enabled: bool = Field(
        True,
        description="Whether region is active",
    )
    effective_date: datetime = Field(
        default_factory=datetime.now,
        description="When availability becomes effective",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional region metadata",
    )

    @field_validator("region_name")
    @classmethod
    def validate_region_name(cls, v: str) -> str:
        """Validate region name."""
        if not v.strip():
            raise ValueError("Region name cannot be empty")
        return v.strip()

    @field_validator("pricing_adjustments")
    @classmethod
    def validate_pricing_adjustments(
        cls, v: dict[str, Decimal]
    ) -> dict[str, Decimal]:
        """Validate pricing adjustments."""
        for key, adjustment in v.items():
            if adjustment < Decimal("-999999.99"):
                raise ValueError(
                    f"Adjustment for {key} is below minimum allowed"
                )
            if adjustment > Decimal("999999.99"):
                raise ValueError(
                    f"Adjustment for {key} exceeds maximum allowed"
                )
        return v

    @field_validator(
        "available_vehicle_ids",
        "available_option_ids",
        "available_package_ids",
    )
    @classmethod
    def validate_unique_ids(cls, v: list[UUID]) -> list[UUID]:
        """Ensure IDs are unique."""
        if len(v) != len(set(v)):
            raise ValueError("Duplicate IDs are not allowed")
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate metadata structure."""
        if len(v) > 100:
            raise ValueError("Metadata cannot exceed 100 keys")

        max_depth = 3

        def check_depth(obj: Any, depth: int = 0) -> None:
            if depth > max_depth:
                raise ValueError(
                    f"Metadata exceeds maximum nesting depth of {max_depth}"
                )
            if isinstance(obj, dict):
                for value in obj.values():
                    check_depth(value, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    check_depth(item, depth + 1)

        check_depth(v)
        return v