"""
Vehicle search Pydantic schemas for Elasticsearch integration.

This module defines comprehensive Pydantic models for vehicle search requests,
responses, filters, facets, and aggregations with proper validation and
documentation for the Elasticsearch-powered search functionality.
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


class SearchFilters(BaseModel):
    """Vehicle search filters schema."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )

    make: Optional[list[str]] = Field(
        None,
        description="Filter by vehicle makes",
        max_length=50,
    )
    model: Optional[list[str]] = Field(
        None,
        description="Filter by vehicle models",
        max_length=50,
    )
    year_min: Optional[int] = Field(
        None,
        ge=1900,
        le=2100,
        description="Minimum model year",
    )
    year_max: Optional[int] = Field(
        None,
        ge=1900,
        le=2100,
        description="Maximum model year",
    )
    body_style: Optional[list[str]] = Field(
        None,
        description="Filter by body styles",
        max_length=20,
    )
    fuel_type: Optional[list[str]] = Field(
        None,
        description="Filter by fuel types",
        max_length=20,
    )
    price_min: Optional[Decimal] = Field(
        None,
        ge=Decimal("0"),
        decimal_places=2,
        description="Minimum price in USD",
    )
    price_max: Optional[Decimal] = Field(
        None,
        ge=Decimal("0"),
        decimal_places=2,
        description="Maximum price in USD",
    )
    drivetrain: Optional[list[str]] = Field(
        None,
        description="Filter by drivetrain types",
        max_length=20,
    )
    transmission: Optional[list[str]] = Field(
        None,
        description="Filter by transmission types",
        max_length=20,
    )
    seating_capacity_min: Optional[int] = Field(
        None,
        ge=1,
        le=20,
        description="Minimum seating capacity",
    )
    seating_capacity_max: Optional[int] = Field(
        None,
        ge=1,
        le=20,
        description="Maximum seating capacity",
    )
    horsepower_min: Optional[int] = Field(
        None,
        ge=0,
        le=2000,
        description="Minimum horsepower",
    )
    horsepower_max: Optional[int] = Field(
        None,
        ge=0,
        le=2000,
        description="Maximum horsepower",
    )
    mpg_city_min: Optional[int] = Field(
        None,
        ge=0,
        le=200,
        description="Minimum city MPG",
    )
    mpg_highway_min: Optional[int] = Field(
        None,
        ge=0,
        le=200,
        description="Minimum highway MPG",
    )
    exterior_color: Optional[list[str]] = Field(
        None,
        description="Filter by exterior colors",
        max_length=30,
    )
    interior_color: Optional[list[str]] = Field(
        None,
        description="Filter by interior colors",
        max_length=30,
    )
    features: Optional[list[str]] = Field(
        None,
        description="Filter by required features",
        max_length=50,
    )
    is_active: Optional[bool] = Field(
        True,
        description="Filter by active status",
    )

    @field_validator(
        "make",
        "model",
        "body_style",
        "fuel_type",
        "drivetrain",
        "transmission",
        "exterior_color",
        "interior_color",
        "features",
    )
    @classmethod
    def validate_string_lists(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate and clean string list filters."""
        if v is None:
            return None
        cleaned = [item.strip() for item in v if item and item.strip()]
        if not cleaned:
            return None
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Duplicate values not allowed in filter lists")
        return cleaned

    @model_validator(mode="after")
    def validate_filter_ranges(self) -> "SearchFilters":
        """Validate filter range parameters."""
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

        if self.horsepower_min is not None and self.horsepower_max is not None:
            if self.horsepower_min > self.horsepower_max:
                raise ValueError(
                    "horsepower_min cannot be greater than horsepower_max"
                )

        return self


class VehicleSearchRequest(BaseModel):
    """Vehicle search request schema with comprehensive search parameters."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    query: Optional[str] = Field(
        None,
        max_length=500,
        description="Full-text search query across vehicle fields",
    )
    filters: SearchFilters = Field(
        default_factory=SearchFilters,
        description="Search filters for vehicle attributes",
    )
    fuzzy: bool = Field(
        True,
        description="Enable fuzzy matching for typo tolerance",
    )
    fuzziness: str = Field(
        "AUTO",
        pattern="^(AUTO|0|1|2)$",
        description="Fuzziness level for fuzzy matching (AUTO, 0, 1, 2)",
    )
    page: int = Field(
        1,
        ge=1,
        le=1000,
        description="Page number for pagination",
    )
    limit: int = Field(
        20,
        ge=1,
        le=100,
        description="Number of results per page",
    )
    sort_by: Optional[str] = Field(
        None,
        max_length=50,
        description="Field to sort by (relevance, price, year, make, model)",
    )
    sort_order: str = Field(
        "desc",
        pattern="^(asc|desc)$",
        description="Sort order (asc or desc)",
    )
    include_facets: bool = Field(
        True,
        description="Include faceted search aggregations in response",
    )
    highlight: bool = Field(
        True,
        description="Include search term highlighting in results",
    )
    min_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Minimum relevance score threshold",
    )

    @field_validator("query")
    @classmethod
    def validate_search_query(cls, v: Optional[str]) -> Optional[str]:
        """Validate and sanitize search query."""
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) < 2:
            raise ValueError("Search query must be at least 2 characters")
        return v

    @field_validator("sort_by")
    @classmethod
    def validate_sort_field(cls, v: Optional[str]) -> Optional[str]:
        """Validate sort field."""
        if v is None:
            return None
        v = v.strip().lower()
        allowed_fields = {
            "relevance",
            "price",
            "year",
            "make",
            "model",
            "created_at",
            "updated_at",
        }
        if v not in allowed_fields:
            raise ValueError(
                f"Invalid sort field. Allowed: {', '.join(allowed_fields)}"
            )
        return v

    @model_validator(mode="after")
    def validate_search_request(self) -> "VehicleSearchRequest":
        """Validate overall search request consistency."""
        if self.page > 100 and self.limit > 50:
            raise ValueError(
                "Deep pagination with large page size not allowed for performance"
            )

        if not self.query and not any(
            getattr(self.filters, field) is not None
            for field in self.filters.model_fields.keys()
            if field != "is_active"
        ):
            raise ValueError(
                "Either query or at least one filter must be provided"
            )

        return self


class FacetBucket(BaseModel):
    """Facet bucket schema for aggregation results."""

    model_config = ConfigDict(from_attributes=True)

    key: str = Field(..., description="Bucket key value")
    count: int = Field(..., ge=0, description="Number of documents in bucket")


class RangeFacetBucket(BaseModel):
    """Range facet bucket schema for numeric range aggregations."""

    model_config = ConfigDict(from_attributes=True)

    from_value: Optional[float] = Field(
        None,
        description="Range start value (inclusive)",
    )
    to_value: Optional[float] = Field(
        None,
        description="Range end value (exclusive)",
    )
    count: int = Field(..., ge=0, description="Number of documents in range")
    key: str = Field(..., description="Range label")


class SearchFacets(BaseModel):
    """Search facets schema for aggregated filter counts."""

    model_config = ConfigDict(from_attributes=True)

    makes: list[FacetBucket] = Field(
        default_factory=list,
        description="Vehicle make facets",
    )
    models: list[FacetBucket] = Field(
        default_factory=list,
        description="Vehicle model facets",
    )
    years: list[FacetBucket] = Field(
        default_factory=list,
        description="Model year facets",
    )
    body_styles: list[FacetBucket] = Field(
        default_factory=list,
        description="Body style facets",
    )
    fuel_types: list[FacetBucket] = Field(
        default_factory=list,
        description="Fuel type facets",
    )
    drivetrains: list[FacetBucket] = Field(
        default_factory=list,
        description="Drivetrain facets",
    )
    transmissions: list[FacetBucket] = Field(
        default_factory=list,
        description="Transmission facets",
    )
    price_ranges: list[RangeFacetBucket] = Field(
        default_factory=list,
        description="Price range facets",
    )
    exterior_colors: list[FacetBucket] = Field(
        default_factory=list,
        description="Exterior color facets",
    )
    interior_colors: list[FacetBucket] = Field(
        default_factory=list,
        description="Interior color facets",
    )
    seating_capacities: list[FacetBucket] = Field(
        default_factory=list,
        description="Seating capacity facets",
    )


class SearchHighlight(BaseModel):
    """Search result highlight schema."""

    model_config = ConfigDict(from_attributes=True)

    field: str = Field(..., description="Field name with highlights")
    fragments: list[str] = Field(
        ...,
        description="Highlighted text fragments with <em> tags",
    )


class VehicleSearchResult(BaseModel):
    """Individual vehicle search result schema."""

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
    )

    id: UUID = Field(..., description="Vehicle unique identifier")
    make: str = Field(..., description="Vehicle manufacturer")
    model: str = Field(..., description="Vehicle model name")
    year: int = Field(..., description="Model year")
    trim: Optional[str] = Field(None, description="Trim level")
    body_style: str = Field(..., description="Body style")
    exterior_color: str = Field(..., description="Exterior color")
    interior_color: str = Field(..., description="Interior color")
    base_price: Decimal = Field(..., description="Base price in USD")
    fuel_type: str = Field(..., description="Fuel type")
    drivetrain: str = Field(..., description="Drivetrain configuration")
    transmission: str = Field(..., description="Transmission type")
    horsepower: int = Field(..., description="Engine horsepower")
    seating_capacity: int = Field(..., description="Number of seats")
    mpg_city: Optional[int] = Field(None, description="City fuel economy")
    mpg_highway: Optional[int] = Field(None, description="Highway fuel economy")
    score: float = Field(..., ge=0.0, description="Relevance score")
    highlights: list[SearchHighlight] = Field(
        default_factory=list,
        description="Search term highlights",
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class SearchMetadata(BaseModel):
    """Search metadata schema."""

    model_config = ConfigDict(from_attributes=True)

    query: Optional[str] = Field(None, description="Original search query")
    total_results: int = Field(..., ge=0, description="Total matching results")
    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, description="Results per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    took_ms: int = Field(..., ge=0, description="Search execution time in ms")
    max_score: Optional[float] = Field(
        None,
        description="Maximum relevance score in results",
    )
    timed_out: bool = Field(
        False,
        description="Whether search timed out",
    )

    @model_validator(mode="after")
    def validate_pagination_metadata(self) -> "SearchMetadata":
        """Validate pagination metadata consistency."""
        expected_total_pages = (
            (self.total_results + self.limit - 1) // self.limit
            if self.total_results > 0
            else 0
        )
        if self.total_pages != expected_total_pages:
            raise ValueError("Inconsistent pagination metadata")
        if self.page > self.total_pages and self.total_results > 0:
            raise ValueError("Page number exceeds total pages")
        return self


class SearchResponse(BaseModel):
    """Vehicle search response schema with results and facets."""

    model_config = ConfigDict(from_attributes=True)

    results: list[VehicleSearchResult] = Field(
        ...,
        description="Search results",
    )
    facets: Optional[SearchFacets] = Field(
        None,
        description="Faceted search aggregations",
    )
    metadata: SearchMetadata = Field(
        ...,
        description="Search metadata and pagination info",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Search query suggestions for typos",
    )

    @model_validator(mode="after")
    def validate_search_response(self) -> "SearchResponse":
        """Validate search response consistency."""
        if len(self.results) > self.metadata.limit:
            raise ValueError("Results exceed page limit")

        if self.metadata.total_results == 0 and len(self.results) > 0:
            raise ValueError("Results present but total_results is zero")

        if self.metadata.total_results > 0 and len(self.results) == 0:
            if self.metadata.page == 1:
                raise ValueError("No results on first page but total_results > 0")

        return self


class SearchSuggestionRequest(BaseModel):
    """Search suggestion request schema."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    query: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Partial query for suggestions",
    )
    field: str = Field(
        "make",
        pattern="^(make|model|body_style)$",
        description="Field to get suggestions for",
    )
    limit: int = Field(
        5,
        ge=1,
        le=20,
        description="Maximum number of suggestions",
    )

    @field_validator("query")
    @classmethod
    def validate_suggestion_query(cls, v: str) -> str:
        """Validate and sanitize suggestion query."""
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        return v


class SearchSuggestion(BaseModel):
    """Search suggestion schema."""

    model_config = ConfigDict(from_attributes=True)

    text: str = Field(..., description="Suggested text")
    score: float = Field(..., ge=0.0, description="Suggestion score")
    frequency: int = Field(..., ge=0, description="Term frequency in index")


class SearchSuggestionResponse(BaseModel):
    """Search suggestion response schema."""

    model_config = ConfigDict(from_attributes=True)

    suggestions: list[SearchSuggestion] = Field(
        ...,
        description="List of suggestions",
    )
    query: str = Field(..., description="Original query")
    field: str = Field(..., description="Field suggestions are for")