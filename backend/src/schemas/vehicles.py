"""
Vehicle catalog Pydantic schemas for API request/response validation.

This module defines comprehensive Pydantic models for vehicle catalog operations
including creation, updates, responses, and search functionality with nested
schemas for specifications, dimensions, and features.
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


class VehicleSpecifications(BaseModel):
    """Vehicle technical specifications schema."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )

    engine_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Engine type (e.g., V6, Inline-4, Electric)",
    )
    horsepower: int = Field(
        ...,
        ge=0,
        le=2000,
        description="Engine horsepower",
    )
    torque: int = Field(
        ...,
        ge=0,
        le=2000,
        description="Engine torque in lb-ft",
    )
    transmission: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Transmission type",
    )
    drivetrain: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Drivetrain configuration (FWD, RWD, AWD, 4WD)",
    )
    fuel_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Fuel type (Gasoline, Diesel, Electric, Hybrid)",
    )
    mpg_city: Optional[int] = Field(
        None,
        ge=0,
        le=200,
        description="City fuel economy in MPG",
    )
    mpg_highway: Optional[int] = Field(
        None,
        ge=0,
        le=200,
        description="Highway fuel economy in MPG",
    )
    electric_range: Optional[int] = Field(
        None,
        ge=0,
        le=1000,
        description="Electric range in miles for EVs/PHEVs",
    )

    @field_validator("engine_type", "transmission", "drivetrain", "fuel_type")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Validate that string fields are not empty after stripping."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def validate_fuel_economy(self) -> "VehicleSpecifications":
        """Validate fuel economy fields based on fuel type."""
        if self.fuel_type.lower() == "electric":
            if self.electric_range is None:
                raise ValueError(
                    "Electric vehicles must have electric_range specified"
                )
            if self.mpg_city is not None or self.mpg_highway is not None:
                raise ValueError(
                    "Electric vehicles should not have MPG values"
                )
        elif self.fuel_type.lower() in ["gasoline", "diesel"]:
            if self.mpg_city is None or self.mpg_highway is None:
                raise ValueError(
                    f"{self.fuel_type} vehicles must have MPG values"
                )
        return self


class VehicleDimensions(BaseModel):
    """Vehicle physical dimensions schema."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    length: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("1000"),
        decimal_places=2,
        description="Vehicle length in inches",
    )
    width: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("1000"),
        decimal_places=2,
        description="Vehicle width in inches",
    )
    height: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("1000"),
        decimal_places=2,
        description="Vehicle height in inches",
    )
    wheelbase: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("1000"),
        decimal_places=2,
        description="Wheelbase in inches",
    )
    curb_weight: int = Field(
        ...,
        ge=0,
        le=20000,
        description="Curb weight in pounds",
    )
    cargo_capacity: Optional[Decimal] = Field(
        None,
        ge=Decimal("0"),
        le=Decimal("1000"),
        decimal_places=2,
        description="Cargo capacity in cubic feet",
    )
    seating_capacity: int = Field(
        ...,
        ge=1,
        le=20,
        description="Number of seats",
    )

    @model_validator(mode="after")
    def validate_dimensions(self) -> "VehicleDimensions":
        """Validate dimension relationships."""
        if self.wheelbase > self.length:
            raise ValueError("Wheelbase cannot exceed vehicle length")
        return self


class VehicleFeatures(BaseModel):
    """Vehicle features and options schema."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    standard_features: list[str] = Field(
        default_factory=list,
        description="List of standard features",
    )
    optional_features: list[str] = Field(
        default_factory=list,
        description="List of optional features",
    )
    safety_features: list[str] = Field(
        default_factory=list,
        description="List of safety features",
    )
    technology_features: list[str] = Field(
        default_factory=list,
        description="List of technology features",
    )
    interior_features: list[str] = Field(
        default_factory=list,
        description="List of interior features",
    )
    exterior_features: list[str] = Field(
        default_factory=list,
        description="List of exterior features",
    )

    @field_validator(
        "standard_features",
        "optional_features",
        "safety_features",
        "technology_features",
        "interior_features",
        "exterior_features",
    )
    @classmethod
    def validate_feature_list(cls, v: list[str]) -> list[str]:
        """Validate and clean feature lists."""
        cleaned = [f.strip() for f in v if f and f.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Duplicate features not allowed")
        return cleaned


class VehicleBase(BaseModel):
    """Base vehicle schema with common fields."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )

    make: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Vehicle manufacturer",
    )
    model: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Vehicle model name",
    )
    year: int = Field(
        ...,
        ge=1900,
        le=2100,
        description="Model year",
    )
    trim: Optional[str] = Field(
        None,
        max_length=100,
        description="Trim level",
    )
    body_style: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Body style (Sedan, SUV, Truck, etc.)",
    )
    exterior_color: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Exterior color",
    )
    interior_color: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Interior color",
    )
    base_price: Decimal = Field(
        ...,
        ge=Decimal("0"),
        decimal_places=2,
        description="Base price in USD",
    )

    @field_validator("make", "model", "body_style", "exterior_color", "interior_color")
    @classmethod
    def validate_non_empty_string(cls, v: str) -> str:
        """Validate that string fields are not empty."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator("trim")
    @classmethod
    def validate_optional_string(cls, v: Optional[str]) -> Optional[str]:
        """Validate optional string fields."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class VehicleCreate(VehicleBase):
    """Schema for creating a new vehicle."""

    specifications: VehicleSpecifications = Field(
        ...,
        description="Vehicle technical specifications",
    )
    dimensions: VehicleDimensions = Field(
        ...,
        description="Vehicle physical dimensions",
    )
    features: VehicleFeatures = Field(
        default_factory=VehicleFeatures,
        description="Vehicle features and options",
    )
    custom_attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom attributes for flexible data storage",
    )

    @field_validator("custom_attributes")
    @classmethod
    def validate_custom_attributes(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate custom attributes."""
        if not isinstance(v, dict):
            raise ValueError("custom_attributes must be a dictionary")
        for key in v.keys():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("All custom attribute keys must be non-empty strings")
        return v


class VehicleUpdate(BaseModel):
    """Schema for updating an existing vehicle."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )

    make: Optional[str] = Field(None, min_length=1, max_length=100)
    model: Optional[str] = Field(None, min_length=1, max_length=100)
    year: Optional[int] = Field(None, ge=1900, le=2100)
    trim: Optional[str] = Field(None, max_length=100)
    body_style: Optional[str] = Field(None, min_length=1, max_length=50)
    exterior_color: Optional[str] = Field(None, min_length=1, max_length=50)
    interior_color: Optional[str] = Field(None, min_length=1, max_length=50)
    base_price: Optional[Decimal] = Field(None, ge=Decimal("0"), decimal_places=2)
    specifications: Optional[VehicleSpecifications] = None
    dimensions: Optional[VehicleDimensions] = None
    features: Optional[VehicleFeatures] = None
    custom_attributes: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "VehicleUpdate":
        """Ensure at least one field is provided for update."""
        if not any(
            getattr(self, field) is not None
            for field in self.model_fields.keys()
        ):
            raise ValueError("At least one field must be provided for update")
        return self


class VehicleResponse(VehicleBase):
    """Schema for vehicle response."""

    id: UUID = Field(..., description="Vehicle unique identifier")
    specifications: VehicleSpecifications
    dimensions: VehicleDimensions
    features: VehicleFeatures
    custom_attributes: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = Field(..., description="Whether vehicle is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
    )


class VehicleListResponse(BaseModel):
    """Schema for paginated vehicle list response."""

    items: list[VehicleResponse] = Field(
        ...,
        description="List of vehicles",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of vehicles matching criteria",
    )
    page: int = Field(
        ...,
        ge=1,
        description="Current page number",
    )
    page_size: int = Field(
        ...,
        ge=1,
        le=100,
        description="Number of items per page",
    )
    total_pages: int = Field(
        ...,
        ge=0,
        description="Total number of pages",
    )

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def validate_pagination(self) -> "VehicleListResponse":
        """Validate pagination consistency."""
        expected_total_pages = (
            (self.total + self.page_size - 1) // self.page_size
            if self.total > 0
            else 0
        )
        if self.total_pages != expected_total_pages:
            raise ValueError("Inconsistent pagination data")
        if self.page > self.total_pages and self.total > 0:
            raise ValueError("Page number exceeds total pages")
        return self


class VehicleSearchRequest(BaseModel):
    """Schema for vehicle search request with comprehensive filters."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    make: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    year_min: Optional[int] = Field(None, ge=1900, le=2100)
    year_max: Optional[int] = Field(None, ge=1900, le=2100)
    body_style: Optional[str] = Field(None, max_length=50)
    fuel_type: Optional[str] = Field(None, max_length=50)
    price_min: Optional[Decimal] = Field(None, ge=Decimal("0"), decimal_places=2)
    price_max: Optional[Decimal] = Field(None, ge=Decimal("0"), decimal_places=2)
    drivetrain: Optional[str] = Field(None, max_length=50)
    transmission: Optional[str] = Field(None, max_length=100)
    seating_capacity_min: Optional[int] = Field(None, ge=1, le=20)
    seating_capacity_max: Optional[int] = Field(None, ge=1, le=20)
    custom_attributes: Optional[dict[str, Any]] = Field(
        None,
        description="Filter by custom attributes",
    )
    search_query: Optional[str] = Field(
        None,
        max_length=500,
        description="General search query across multiple fields",
    )
    is_active: Optional[bool] = Field(
        True,
        description="Filter by active status",
    )
    page: int = Field(
        1,
        ge=1,
        description="Page number",
    )
    page_size: int = Field(
        20,
        ge=1,
        le=100,
        description="Items per page",
    )
    sort_by: Optional[str] = Field(
        None,
        max_length=50,
        description="Field to sort by",
    )
    sort_order: str = Field(
        "asc",
        pattern="^(asc|desc)$",
        description="Sort order (asc or desc)",
    )

    @model_validator(mode="after")
    def validate_search_ranges(self) -> "VehicleSearchRequest":
        """Validate search range parameters."""
        if self.year_min is not None and self.year_max is not None:
            if self.year_min > self.year_max:
                raise ValueError("year_min cannot be greater than year_max")

        if self.price_min is not None and self.price_max is not None:
            if self.price_min > self.price_max:
                raise ValueError("price_min cannot be greater than price_max")

        if (
            self.seating_capacity_min is not None
            and self.seating_capacity_max is not None
        ):
            if self.seating_capacity_min > self.seating_capacity_max:
                raise ValueError(
                    "seating_capacity_min cannot be greater than seating_capacity_max"
                )

        return self

    @field_validator("search_query")
    @classmethod
    def validate_search_query(cls, v: Optional[str]) -> Optional[str]:
        """Validate and sanitize search query."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if len(v) < 2:
                raise ValueError("Search query must be at least 2 characters")
        return v