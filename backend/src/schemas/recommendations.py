"""
Recommendation schemas for package recommendation requests and responses.

This module defines Pydantic schemas for the recommendation engine, including
request validation, package recommendations, popular configurations, and
response formatting with comprehensive validation rules.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class RecommendationRequest(BaseModel):
    """Schema for package recommendation request."""

    vehicle_id: UUID = Field(
        ...,
        description="ID of the vehicle for recommendations",
    )
    selected_options: list[str] = Field(
        default_factory=list,
        description="List of currently selected option IDs",
        max_length=100,
    )
    selected_packages: list[str] = Field(
        default_factory=list,
        description="List of currently selected package IDs",
        max_length=20,
    )
    customer_id: Optional[UUID] = Field(
        None,
        description="ID of the customer requesting recommendations",
    )
    dealer_id: Optional[UUID] = Field(
        None,
        description="ID of the dealer for regional recommendations",
    )
    max_recommendations: int = Field(
        default=5,
        description="Maximum number of recommendations to return",
        ge=1,
        le=20,
    )
    include_popular: bool = Field(
        default=True,
        description="Include popular configurations in response",
    )
    price_sensitivity: Optional[Decimal] = Field(
        None,
        description="Price sensitivity factor (0.0 to 1.0)",
        ge=Decimal("0.0"),
        le=Decimal("1.0"),
        decimal_places=2,
    )

    @field_validator("selected_options")
    @classmethod
    def validate_unique_options(cls, v: list[str]) -> list[str]:
        """Validate that option IDs are unique and non-empty."""
        if not v:
            return v

        cleaned = [opt.strip() for opt in v if opt and opt.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Duplicate option IDs in selected options")

        return cleaned

    @field_validator("selected_packages")
    @classmethod
    def validate_unique_packages(cls, v: list[str]) -> list[str]:
        """Validate that package IDs are unique and non-empty."""
        if not v:
            return v

        cleaned = [pkg.strip() for pkg in v if pkg and pkg.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Duplicate package IDs in selected packages")

        return cleaned

    model_config = {
        "json_schema_extra": {
            "example": {
                "vehicle_id": "123e4567-e89b-12d3-a456-426614174000",
                "selected_options": ["opt_leather_seats", "opt_sunroof"],
                "selected_packages": [],
                "customer_id": "123e4567-e89b-12d3-a456-426614174001",
                "dealer_id": "123e4567-e89b-12d3-a456-426614174002",
                "max_recommendations": 5,
                "include_popular": True,
                "price_sensitivity": "0.75",
            }
        }
    }


class PackageRecommendation(BaseModel):
    """Schema for individual package recommendation."""

    package_id: str = Field(
        ...,
        description="Unique identifier for the recommended package",
        min_length=1,
        max_length=100,
    )
    name: str = Field(
        ...,
        description="Display name of the package",
        min_length=1,
        max_length=200,
    )
    description: Optional[str] = Field(
        None,
        description="Detailed description of the package",
        max_length=1000,
    )
    price: Decimal = Field(
        ...,
        description="Package price",
        ge=0,
        decimal_places=2,
    )
    discount_amount: Optional[Decimal] = Field(
        None,
        description="Discount amount when purchasing as package",
        ge=0,
        decimal_places=2,
    )
    savings_amount: Decimal = Field(
        ...,
        description="Total savings compared to individual options",
        ge=0,
        decimal_places=2,
    )
    savings_percentage: Decimal = Field(
        ...,
        description="Savings percentage (0.0 to 100.0)",
        ge=Decimal("0.0"),
        le=Decimal("100.0"),
        decimal_places=2,
    )
    included_options: list[str] = Field(
        default_factory=list,
        description="List of option IDs included in the package",
    )
    confidence_score: Decimal = Field(
        ...,
        description="Recommendation confidence score (0.0 to 1.0)",
        ge=Decimal("0.0"),
        le=Decimal("1.0"),
        decimal_places=4,
    )
    relevance_score: Decimal = Field(
        ...,
        description="Relevance score based on selected options (0.0 to 1.0)",
        ge=Decimal("0.0"),
        le=Decimal("1.0"),
        decimal_places=4,
    )
    popularity_rank: Optional[int] = Field(
        None,
        description="Popularity ranking among similar configurations",
        ge=1,
    )
    value_proposition: str = Field(
        ...,
        description="Key value proposition for this recommendation",
        min_length=1,
        max_length=500,
    )
    reasons: list[str] = Field(
        default_factory=list,
        description="List of reasons for this recommendation",
        max_length=10,
    )
    compatible_with_selections: bool = Field(
        default=True,
        description="Whether package is compatible with current selections",
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

    @field_validator("reasons")
    @classmethod
    def validate_reasons(cls, v: list[str]) -> list[str]:
        """Validate reasons list."""
        if not v:
            return v
        cleaned = [reason.strip() for reason in v if reason and reason.strip()]
        return cleaned

    @model_validator(mode="after")
    def validate_savings_calculation(self) -> "PackageRecommendation":
        """Validate savings calculations are consistent."""
        if self.discount_amount is not None:
            if self.savings_amount < self.discount_amount:
                raise ValueError(
                    "Savings amount cannot be less than discount amount"
                )

        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "package_id": "pkg_premium",
                "name": "Premium Package",
                "description": "Complete premium features package",
                "price": "5000.00",
                "discount_amount": "500.00",
                "savings_amount": "750.00",
                "savings_percentage": "13.04",
                "included_options": ["opt_leather_seats", "opt_sunroof", "opt_premium_audio"],
                "confidence_score": "0.8750",
                "relevance_score": "0.9200",
                "popularity_rank": 2,
                "value_proposition": "Save $750 with our most popular premium features",
                "reasons": [
                    "Complements your selected leather seats",
                    "Popular choice for this vehicle model",
                    "Best value for premium features",
                ],
                "compatible_with_selections": True,
            }
        }
    }


class PopularConfiguration(BaseModel):
    """Schema for popular vehicle configuration."""

    configuration_id: Optional[str] = Field(
        None,
        description="Unique identifier for the configuration",
        max_length=100,
    )
    name: str = Field(
        ...,
        description="Display name for the configuration",
        min_length=1,
        max_length=200,
    )
    description: Optional[str] = Field(
        None,
        description="Description of the configuration",
        max_length=1000,
    )
    selected_options: list[str] = Field(
        default_factory=list,
        description="List of option IDs in this configuration",
    )
    selected_packages: list[str] = Field(
        default_factory=list,
        description="List of package IDs in this configuration",
    )
    total_price: Decimal = Field(
        ...,
        description="Total price of the configuration",
        ge=0,
        decimal_places=2,
    )
    popularity_score: Decimal = Field(
        ...,
        description="Popularity score (0.0 to 1.0)",
        ge=Decimal("0.0"),
        le=Decimal("1.0"),
        decimal_places=4,
    )
    selection_count: int = Field(
        ...,
        description="Number of times this configuration was selected",
        ge=0,
    )
    similarity_score: Optional[Decimal] = Field(
        None,
        description="Similarity to current selections (0.0 to 1.0)",
        ge=Decimal("0.0"),
        le=Decimal("1.0"),
        decimal_places=4,
    )
    region: Optional[str] = Field(
        None,
        description="Geographic region for this configuration",
        max_length=100,
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate configuration name."""
        if not v or not v.strip():
            raise ValueError("Configuration name cannot be empty or whitespace")
        return v.strip()

    @field_validator("selected_options")
    @classmethod
    def validate_unique_options(cls, v: list[str]) -> list[str]:
        """Validate that option IDs are unique."""
        if not v:
            return v
        cleaned = [opt.strip() for opt in v if opt and opt.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Duplicate option IDs in configuration")
        return cleaned

    @field_validator("selected_packages")
    @classmethod
    def validate_unique_packages(cls, v: list[str]) -> list[str]:
        """Validate that package IDs are unique."""
        if not v:
            return v
        cleaned = [pkg.strip() for pkg in v if pkg and pkg.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Duplicate package IDs in configuration")
        return cleaned

    model_config = {
        "json_schema_extra": {
            "example": {
                "configuration_id": "config_popular_001",
                "name": "Sport Enthusiast",
                "description": "Popular configuration for sport-oriented buyers",
                "selected_options": ["opt_sport_seats", "opt_performance_tires"],
                "selected_packages": ["pkg_sport"],
                "total_price": "42500.00",
                "popularity_score": "0.8900",
                "selection_count": 1247,
                "similarity_score": "0.7500",
                "region": "West Coast",
            }
        }
    }


class RecommendationResponse(BaseModel):
    """Schema for package recommendation response."""

    vehicle_id: UUID = Field(
        ...,
        description="ID of the vehicle for recommendations",
    )
    recommendations: list[PackageRecommendation] = Field(
        default_factory=list,
        description="List of package recommendations",
    )
    popular_configurations: list[PopularConfiguration] = Field(
        default_factory=list,
        description="List of popular configurations",
    )
    total_potential_savings: Decimal = Field(
        default=Decimal("0.00"),
        description="Total potential savings from all recommendations",
        ge=0,
        decimal_places=2,
    )
    recommendation_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about recommendations",
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when recommendations were generated",
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Timestamp when recommendations expire",
    )
    algorithm_version: str = Field(
        default="1.0",
        description="Version of recommendation algorithm used",
        max_length=20,
    )
    processing_time_ms: Optional[int] = Field(
        None,
        description="Processing time in milliseconds",
        ge=0,
    )

    @model_validator(mode="after")
    def validate_recommendations_count(self) -> "RecommendationResponse":
        """Validate recommendations count is reasonable."""
        if len(self.recommendations) > 20:
            raise ValueError("Too many recommendations (max 20)")

        if len(self.popular_configurations) > 10:
            raise ValueError("Too many popular configurations (max 10)")

        return self

    @model_validator(mode="after")
    def validate_expiration(self) -> "RecommendationResponse":
        """Validate expiration is after generation time."""
        if self.expires_at is not None:
            if self.expires_at <= self.generated_at:
                raise ValueError(
                    "Expiration time must be after generation time"
                )

        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "vehicle_id": "123e4567-e89b-12d3-a456-426614174000",
                "recommendations": [
                    {
                        "package_id": "pkg_premium",
                        "name": "Premium Package",
                        "description": "Complete premium features",
                        "price": "5000.00",
                        "discount_amount": "500.00",
                        "savings_amount": "750.00",
                        "savings_percentage": "13.04",
                        "included_options": ["opt_leather_seats", "opt_sunroof"],
                        "confidence_score": "0.8750",
                        "relevance_score": "0.9200",
                        "popularity_rank": 2,
                        "value_proposition": "Save $750 with premium features",
                        "reasons": ["Complements your selections"],
                        "compatible_with_selections": True,
                    }
                ],
                "popular_configurations": [
                    {
                        "configuration_id": "config_001",
                        "name": "Sport Enthusiast",
                        "description": "Popular sport configuration",
                        "selected_options": ["opt_sport_seats"],
                        "selected_packages": ["pkg_sport"],
                        "total_price": "42500.00",
                        "popularity_score": "0.8900",
                        "selection_count": 1247,
                        "similarity_score": "0.7500",
                        "region": "West Coast",
                    }
                ],
                "total_potential_savings": "750.00",
                "recommendation_metadata": {
                    "algorithm": "collaborative_filtering",
                    "data_points": 10000,
                },
                "generated_at": "2026-01-07T22:30:00Z",
                "expires_at": "2026-01-07T23:30:00Z",
                "algorithm_version": "1.0",
                "processing_time_ms": 45,
            }
        }
    }