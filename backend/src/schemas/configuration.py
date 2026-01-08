"""
Configuration schemas for vehicle configuration API.

This module defines Pydantic schemas for configuration requests, responses,
option selections, package selections, pricing breakdowns, and validation results.
Includes comprehensive validation rules for option compatibility and pricing calculations.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class OptionSelection(BaseModel):
    """Schema for individual option selection."""

    option_id: str = Field(
        ...,
        description="Unique identifier for the vehicle option",
        min_length=1,
        max_length=100,
    )
    quantity: int = Field(
        default=1,
        description="Quantity of the option selected",
        ge=1,
        le=100,
    )
    price: Decimal = Field(
        ...,
        description="Price of the option",
        ge=0,
        decimal_places=2,
    )
    name: str = Field(
        ...,
        description="Display name of the option",
        min_length=1,
        max_length=200,
    )
    category: Optional[str] = Field(
        None,
        description="Category of the option (e.g., 'exterior', 'interior')",
        max_length=100,
    )

    @field_validator("option_id")
    @classmethod
    def validate_option_id(cls, v: str) -> str:
        """Validate option ID format."""
        if not v or not v.strip():
            raise ValueError("Option ID cannot be empty or whitespace")
        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate option name."""
        if not v or not v.strip():
            raise ValueError("Option name cannot be empty or whitespace")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "option_id": "opt_leather_seats",
                "quantity": 1,
                "price": "1500.00",
                "name": "Premium Leather Seats",
                "category": "interior",
            }
        }
    }


class PackageSelection(BaseModel):
    """Schema for package selection."""

    package_id: str = Field(
        ...,
        description="Unique identifier for the package",
        min_length=1,
        max_length=100,
    )
    price: Decimal = Field(
        ...,
        description="Price of the package",
        ge=0,
        decimal_places=2,
    )
    name: str = Field(
        ...,
        description="Display name of the package",
        min_length=1,
        max_length=200,
    )
    included_options: list[str] = Field(
        default_factory=list,
        description="List of option IDs included in the package",
    )
    discount_amount: Optional[Decimal] = Field(
        None,
        description="Discount amount when purchasing as package",
        ge=0,
        decimal_places=2,
    )

    @field_validator("package_id")
    @classmethod
    def validate_package_id(cls, v: str) -> str:
        """Validate package ID format."""
        if not v or not v.strip():
            raise ValueError("Package ID cannot be empty or whitespace")
        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate package name."""
        if not v or not v.strip():
            raise ValueError("Package name cannot be empty or whitespace")
        return v.strip()

    @field_validator("included_options")
    @classmethod
    def validate_included_options(cls, v: list[str]) -> list[str]:
        """Validate included options list."""
        if not v:
            return v
        cleaned = [opt.strip() for opt in v if opt and opt.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Duplicate option IDs in package")
        return cleaned

    model_config = {
        "json_schema_extra": {
            "example": {
                "package_id": "pkg_premium",
                "price": "5000.00",
                "name": "Premium Package",
                "included_options": ["opt_leather_seats", "opt_sunroof"],
                "discount_amount": "500.00",
            }
        }
    }


class PricingBreakdown(BaseModel):
    """Schema for detailed pricing breakdown."""

    base_price: Decimal = Field(
        ...,
        description="Base vehicle price",
        ge=0,
        decimal_places=2,
    )
    options_total: Decimal = Field(
        ...,
        description="Total cost of selected options",
        ge=0,
        decimal_places=2,
    )
    packages_total: Decimal = Field(
        ...,
        description="Total cost of selected packages",
        ge=0,
        decimal_places=2,
    )
    subtotal: Decimal = Field(
        ...,
        description="Subtotal before taxes and fees",
        ge=0,
        decimal_places=2,
    )
    tax_amount: Decimal = Field(
        ...,
        description="Total tax amount",
        ge=0,
        decimal_places=2,
    )
    tax_rate: Decimal = Field(
        ...,
        description="Tax rate applied (as decimal, e.g., 0.08 for 8%)",
        ge=0,
        le=1,
        decimal_places=4,
    )
    destination_charge: Decimal = Field(
        ...,
        description="Destination and delivery charge",
        ge=0,
        decimal_places=2,
    )
    other_fees: Decimal = Field(
        default=Decimal("0.00"),
        description="Other miscellaneous fees",
        ge=0,
        decimal_places=2,
    )
    total_price: Decimal = Field(
        ...,
        description="Final total price including all charges",
        ge=0,
        decimal_places=2,
    )
    discount_amount: Optional[Decimal] = Field(
        None,
        description="Total discount amount applied",
        ge=0,
        decimal_places=2,
    )
    incentives: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of applicable incentives",
    )

    @model_validator(mode="after")
    def validate_pricing_calculation(self) -> "PricingBreakdown":
        """Validate pricing calculations are correct."""
        expected_subtotal = (
            self.base_price + self.options_total + self.packages_total
        )
        if self.discount_amount:
            expected_subtotal -= self.discount_amount

        if abs(self.subtotal - expected_subtotal) > Decimal("0.01"):
            raise ValueError(
                f"Subtotal mismatch: expected {expected_subtotal}, got {self.subtotal}"
            )

        expected_total = (
            self.subtotal
            + self.tax_amount
            + self.destination_charge
            + self.other_fees
        )

        if abs(self.total_price - expected_total) > Decimal("0.01"):
            raise ValueError(
                f"Total price mismatch: expected {expected_total}, got {self.total_price}"
            )

        expected_tax = self.subtotal * self.tax_rate
        if abs(self.tax_amount - expected_tax) > Decimal("0.01"):
            raise ValueError(
                f"Tax amount mismatch: expected {expected_tax}, got {self.tax_amount}"
            )

        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "base_price": "35000.00",
                "options_total": "3000.00",
                "packages_total": "5000.00",
                "subtotal": "43000.00",
                "tax_amount": "3440.00",
                "tax_rate": "0.0800",
                "destination_charge": "1200.00",
                "other_fees": "150.00",
                "total_price": "47790.00",
                "discount_amount": "500.00",
                "incentives": [],
            }
        }
    }


class ValidationResult(BaseModel):
    """Schema for configuration validation result."""

    is_valid: bool = Field(
        ...,
        description="Whether the configuration is valid",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="List of validation error messages",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="List of validation warnings",
    )
    incompatible_options: list[tuple[str, str]] = Field(
        default_factory=list,
        description="List of incompatible option pairs",
    )
    missing_required_options: list[str] = Field(
        default_factory=list,
        description="List of required options that are missing",
    )

    @model_validator(mode="after")
    def validate_consistency(self) -> "ValidationResult":
        """Validate consistency between is_valid and error lists."""
        has_errors = bool(
            self.errors or self.incompatible_options or self.missing_required_options
        )

        if self.is_valid and has_errors:
            raise ValueError(
                "Configuration cannot be valid when errors are present"
            )

        if not self.is_valid and not has_errors:
            raise ValueError(
                "Configuration must have errors when marked as invalid"
            )

        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "is_valid": False,
                "errors": ["Option 'sunroof' conflicts with 'roof_rack'"],
                "warnings": ["Selected color may increase delivery time"],
                "incompatible_options": [("sunroof", "roof_rack")],
                "missing_required_options": [],
            }
        }
    }


class ConfigurationRequest(BaseModel):
    """Schema for vehicle configuration request."""

    vehicle_id: UUID = Field(
        ...,
        description="ID of the vehicle being configured",
    )
    options: list[OptionSelection] = Field(
        default_factory=list,
        description="List of selected options",
        max_length=100,
    )
    packages: list[PackageSelection] = Field(
        default_factory=list,
        description="List of selected packages",
        max_length=20,
    )
    customer_id: Optional[UUID] = Field(
        None,
        description="ID of the customer creating the configuration",
    )
    dealer_id: Optional[UUID] = Field(
        None,
        description="ID of the dealer associated with the configuration",
    )
    notes: Optional[str] = Field(
        None,
        description="Additional notes or comments",
        max_length=2000,
    )

    @field_validator("options")
    @classmethod
    def validate_unique_options(cls, v: list[OptionSelection]) -> list[OptionSelection]:
        """Validate that option IDs are unique."""
        if not v:
            return v

        option_ids = [opt.option_id for opt in v]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("Duplicate option IDs in configuration")

        return v

    @field_validator("packages")
    @classmethod
    def validate_unique_packages(
        cls, v: list[PackageSelection]
    ) -> list[PackageSelection]:
        """Validate that package IDs are unique."""
        if not v:
            return v

        package_ids = [pkg.package_id for pkg in v]
        if len(package_ids) != len(set(package_ids)):
            raise ValueError("Duplicate package IDs in configuration")

        return v

    @model_validator(mode="after")
    def validate_option_package_overlap(self) -> "ConfigurationRequest":
        """Validate that options in packages are not also selected individually."""
        if not self.options or not self.packages:
            return self

        individual_option_ids = {opt.option_id for opt in self.options}
        package_option_ids = {
            opt_id
            for pkg in self.packages
            for opt_id in pkg.included_options
        }

        overlap = individual_option_ids & package_option_ids
        if overlap:
            raise ValueError(
                f"Options {overlap} are included in packages and cannot be selected individually"
            )

        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "vehicle_id": "123e4567-e89b-12d3-a456-426614174000",
                "options": [
                    {
                        "option_id": "opt_leather_seats",
                        "quantity": 1,
                        "price": "1500.00",
                        "name": "Premium Leather Seats",
                        "category": "interior",
                    }
                ],
                "packages": [],
                "customer_id": "123e4567-e89b-12d3-a456-426614174001",
                "dealer_id": "123e4567-e89b-12d3-a456-426614174002",
                "notes": "Customer prefers black leather",
            }
        }
    }


class ConfigurationResponse(BaseModel):
    """Schema for vehicle configuration response."""

    id: UUID = Field(
        ...,
        description="Unique identifier for the configuration",
    )
    vehicle_id: UUID = Field(
        ...,
        description="ID of the configured vehicle",
    )
    options: list[OptionSelection] = Field(
        ...,
        description="List of selected options",
    )
    packages: list[PackageSelection] = Field(
        ...,
        description="List of selected packages",
    )
    pricing: PricingBreakdown = Field(
        ...,
        description="Detailed pricing breakdown",
    )
    validation: ValidationResult = Field(
        ...,
        description="Configuration validation result",
    )
    customer_id: Optional[UUID] = Field(
        None,
        description="ID of the customer who created the configuration",
    )
    dealer_id: Optional[UUID] = Field(
        None,
        description="ID of the associated dealer",
    )
    notes: Optional[str] = Field(
        None,
        description="Additional notes or comments",
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when configuration was created",
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp when configuration was last updated",
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Timestamp when configuration expires",
    )
    status: str = Field(
        default="draft",
        description="Configuration status",
        pattern="^(draft|submitted|approved|rejected|expired)$",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174003",
                "vehicle_id": "123e4567-e89b-12d3-a456-426614174000",
                "options": [
                    {
                        "option_id": "opt_leather_seats",
                        "quantity": 1,
                        "price": "1500.00",
                        "name": "Premium Leather Seats",
                        "category": "interior",
                    }
                ],
                "packages": [],
                "pricing": {
                    "base_price": "35000.00",
                    "options_total": "1500.00",
                    "packages_total": "0.00",
                    "subtotal": "36500.00",
                    "tax_amount": "2920.00",
                    "tax_rate": "0.0800",
                    "destination_charge": "1200.00",
                    "other_fees": "150.00",
                    "total_price": "40770.00",
                    "discount_amount": None,
                    "incentives": [],
                },
                "validation": {
                    "is_valid": True,
                    "errors": [],
                    "warnings": [],
                    "incompatible_options": [],
                    "missing_required_options": [],
                },
                "customer_id": "123e4567-e89b-12d3-a456-426614174001",
                "dealer_id": "123e4567-e89b-12d3-a456-426614174002",
                "notes": "Customer prefers black leather",
                "created_at": "2026-01-07T22:30:00Z",
                "updated_at": "2026-01-07T22:30:00Z",
                "expires_at": "2026-02-07T22:30:00Z",
                "status": "draft",
            }
        }
    }