"""
Recommendation analytics database models.

This module defines database models for tracking recommendation events and popular
vehicle configurations. Implements comprehensive analytics tracking with JSONB storage
for flexible event data, proper indexing for query performance, and audit trails.
"""

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    String,
    Index,
    CheckConstraint,
    Enum as SQLEnum,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import BaseModel
from src.core.logging import get_logger

logger = get_logger(__name__)


class RecommendationEventType(str, enum.Enum):
    """Recommendation event type enumeration."""

    VIEWED = "viewed"
    CLICKED = "clicked"
    ADDED_TO_CART = "added_to_cart"
    PURCHASED = "purchased"
    DISMISSED = "dismissed"
    SHARED = "shared"

    @classmethod
    def from_string(cls, value: str) -> "RecommendationEventType":
        """
        Convert string to RecommendationEventType enum.

        Args:
            value: String representation of event type

        Returns:
            RecommendationEventType enum value

        Raises:
            ValueError: If value is not a valid event type
        """
        try:
            return cls[value.upper()]
        except KeyError:
            raise ValueError(f"Invalid event type: {value}")


class RecommendationEvent(BaseModel):
    """
    Recommendation event tracking model.

    Tracks user interactions with package recommendations including views, clicks,
    cart additions, and purchases. Stores recommendation context in JSONB for
    flexible analytics and A/B testing support.

    Attributes:
        id: Unique event identifier (UUID)
        user_id: User who triggered the event (optional for anonymous)
        session_id: Session identifier for anonymous tracking
        vehicle_id: Vehicle being configured
        recommended_packages: JSONB array of recommended package IDs with scores
        selected_packages: JSONB array of packages user selected
        event_type: Type of recommendation event
        event_metadata: Additional event context (A/B test variant, etc.)
        created_at: Event timestamp (from BaseModel)
        updated_at: Last modification timestamp (from BaseModel)
    """

    __tablename__ = "recommendation_events"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique event identifier",
    )

    # User identification (nullable for anonymous users)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="User who triggered the event",
    )

    session_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Session identifier for anonymous tracking",
    )

    # Vehicle context
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Vehicle being configured",
    )

    # Recommendation data
    recommended_packages: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Recommended packages with scores and metadata",
    )

    selected_packages: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Packages user selected from recommendations",
    )

    # Event classification
    event_type: Mapped[RecommendationEventType] = mapped_column(
        SQLEnum(
            RecommendationEventType,
            name="recommendation_event_type",
            native_enum=False,
        ),
        nullable=False,
        index=True,
        comment="Type of recommendation event",
    )

    # Additional context
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Additional event context and metadata",
    )

    # Table constraints and indexes
    __table_args__ = (
        # Composite index for user analytics
        Index(
            "ix_recommendation_events_user_vehicle",
            "user_id",
            "vehicle_id",
            "event_type",
        ),
        # Index for session-based analytics
        Index(
            "ix_recommendation_events_session",
            "session_id",
            "event_type",
            "created_at",
        ),
        # Index for time-based queries
        Index(
            "ix_recommendation_events_created_at",
            "created_at",
        ),
        # GIN index for JSONB queries
        Index(
            "ix_recommendation_events_recommended_packages_gin",
            "recommended_packages",
            postgresql_using="gin",
        ),
        Index(
            "ix_recommendation_events_selected_packages_gin",
            "selected_packages",
            postgresql_using="gin",
        ),
        Index(
            "ix_recommendation_events_metadata_gin",
            "event_metadata",
            postgresql_using="gin",
        ),
        # Check constraints
        CheckConstraint(
            "user_id IS NOT NULL OR session_id IS NOT NULL",
            name="ck_recommendation_events_user_or_session",
        ),
        CheckConstraint(
            "length(session_id) >= 1",
            name="ck_recommendation_events_session_id_min_length",
        ),
        {
            "comment": "Recommendation event tracking for analytics",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of RecommendationEvent.

        Returns:
            String representation showing key event attributes
        """
        user_info = f"user_id={self.user_id}" if self.user_id else f"session_id={self.session_id}"
        return (
            f"<RecommendationEvent(id={self.id}, {user_info}, "
            f"vehicle_id={self.vehicle_id}, event_type={self.event_type.value})>"
        )

    @property
    def is_anonymous(self) -> bool:
        """
        Check if event is from anonymous user.

        Returns:
            True if event has no user_id
        """
        return self.user_id is None

    @property
    def recommended_package_ids(self) -> list[str]:
        """
        Extract recommended package IDs from JSONB.

        Returns:
            List of recommended package IDs
        """
        if not self.recommended_packages:
            return []
        return [pkg.get("id") for pkg in self.recommended_packages.get("packages", []) if pkg.get("id")]

    @property
    def selected_package_ids(self) -> list[str]:
        """
        Extract selected package IDs from JSONB.

        Returns:
            List of selected package IDs
        """
        if not self.selected_packages:
            return []
        return [pkg.get("id") for pkg in self.selected_packages.get("packages", []) if pkg.get("id")]

    @property
    def conversion_rate(self) -> float:
        """
        Calculate conversion rate (selected / recommended).

        Returns:
            Conversion rate as percentage (0-100)
        """
        recommended = len(self.recommended_package_ids)
        if recommended == 0:
            return 0.0
        selected = len(self.selected_package_ids)
        return (selected / recommended) * 100

    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """
        Get metadata value by key.

        Args:
            key: Metadata key to retrieve
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        return self.event_metadata.get(key, default)

    def set_metadata_value(self, key: str, value: Any) -> None:
        """
        Set metadata value.

        Args:
            key: Metadata key to set
            value: Value to set for the key
        """
        if self.event_metadata is None:
            self.event_metadata = {}
        self.event_metadata[key] = value

    def to_dict(self) -> dict[str, Any]:
        """
        Convert event to dictionary representation.

        Returns:
            Dictionary representation of event
        """
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "session_id": self.session_id,
            "vehicle_id": str(self.vehicle_id),
            "recommended_packages": self.recommended_packages,
            "selected_packages": self.selected_packages,
            "event_type": self.event_type.value,
            "event_metadata": self.event_metadata,
            "is_anonymous": self.is_anonymous,
            "conversion_rate": self.conversion_rate,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PopularConfiguration(BaseModel):
    """
    Popular vehicle configuration tracking model.

    Tracks frequently selected option and package combinations for similar vehicles.
    Used to generate "popular configurations" recommendations and identify trends.

    Attributes:
        id: Unique configuration identifier (UUID)
        vehicle_id: Vehicle this configuration applies to
        make: Vehicle make for broader matching
        model: Vehicle model for broader matching
        year: Vehicle year for broader matching
        body_style: Vehicle body style for broader matching
        configuration_data: JSONB with selected options and packages
        selection_count: Number of times this configuration was selected
        conversion_count: Number of times this led to purchase
        last_selected_at: Most recent selection timestamp
        created_at: First selection timestamp (from BaseModel)
        updated_at: Last modification timestamp (from BaseModel)
    """

    __tablename__ = "popular_configurations"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique configuration identifier",
    )

    # Vehicle identification
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Specific vehicle this configuration applies to",
    )

    make: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Vehicle make for broader matching",
    )

    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Vehicle model for broader matching",
    )

    year: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
        comment="Vehicle year for broader matching",
    )

    body_style: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Vehicle body style for broader matching",
    )

    # Configuration details
    configuration_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Selected options and packages configuration",
    )

    # Popularity metrics
    selection_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Number of times this configuration was selected",
    )

    conversion_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Number of times this led to purchase",
    )

    last_selected_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="Most recent selection timestamp",
    )

    # Table constraints and indexes
    __table_args__ = (
        # Composite index for vehicle matching
        Index(
            "ix_popular_configurations_vehicle_match",
            "make",
            "model",
            "year",
            "body_style",
        ),
        # Index for popularity ranking
        Index(
            "ix_popular_configurations_popularity",
            "selection_count",
            "conversion_count",
            "last_selected_at",
        ),
        # GIN index for configuration data queries
        Index(
            "ix_popular_configurations_data_gin",
            "configuration_data",
            postgresql_using="gin",
        ),
        # Check constraints
        CheckConstraint(
            "selection_count >= 0",
            name="ck_popular_configurations_selection_count_non_negative",
        ),
        CheckConstraint(
            "conversion_count >= 0",
            name="ck_popular_configurations_conversion_count_non_negative",
        ),
        CheckConstraint(
            "conversion_count <= selection_count",
            name="ck_popular_configurations_conversion_lte_selection",
        ),
        CheckConstraint(
            "year >= 1900 AND year <= 2100",
            name="ck_popular_configurations_year_range",
        ),
        CheckConstraint(
            "length(make) >= 1",
            name="ck_popular_configurations_make_min_length",
        ),
        CheckConstraint(
            "length(model) >= 1",
            name="ck_popular_configurations_model_min_length",
        ),
        {
            "comment": "Popular vehicle configurations for recommendations",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of PopularConfiguration.

        Returns:
            String representation showing key configuration attributes
        """
        return (
            f"<PopularConfiguration(id={self.id}, "
            f"vehicle={self.year} {self.make} {self.model}, "
            f"selections={self.selection_count}, "
            f"conversions={self.conversion_count})>"
        )

    @property
    def conversion_rate(self) -> float:
        """
        Calculate conversion rate.

        Returns:
            Conversion rate as percentage (0-100)
        """
        if self.selection_count == 0:
            return 0.0
        return (self.conversion_count / self.selection_count) * 100

    @property
    def popularity_score(self) -> float:
        """
        Calculate popularity score combining selections and conversions.

        Returns:
            Weighted popularity score
        """
        # Weight conversions more heavily than selections
        return (self.selection_count * 1.0) + (self.conversion_count * 2.0)

    @property
    def is_trending(self) -> bool:
        """
        Check if configuration is trending (recent selections).

        Returns:
            True if selected within last 30 days
        """
        if not self.last_selected_at:
            return False
        days_since_selection = (datetime.utcnow() - self.last_selected_at).days
        return days_since_selection <= 30

    @property
    def package_ids(self) -> list[str]:
        """
        Extract package IDs from configuration data.

        Returns:
            List of package IDs in configuration
        """
        if not self.configuration_data:
            return []
        return self.configuration_data.get("package_ids", [])

    @property
    def option_ids(self) -> list[str]:
        """
        Extract option IDs from configuration data.

        Returns:
            List of option IDs in configuration
        """
        if not self.configuration_data:
            return []
        return self.configuration_data.get("option_ids", [])

    def increment_selection(self) -> None:
        """Increment selection count and update last selected timestamp."""
        self.selection_count += 1
        self.last_selected_at = datetime.utcnow()
        logger.debug(
            "Configuration selection incremented",
            configuration_id=str(self.id),
            new_count=self.selection_count,
        )

    def increment_conversion(self) -> None:
        """Increment conversion count."""
        self.conversion_count += 1
        logger.debug(
            "Configuration conversion incremented",
            configuration_id=str(self.id),
            new_count=self.conversion_count,
        )

    def matches_vehicle(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        year: Optional[int] = None,
        body_style: Optional[str] = None,
    ) -> bool:
        """
        Check if configuration matches vehicle criteria.

        Args:
            make: Vehicle make to match (case-insensitive)
            model: Vehicle model to match (case-insensitive)
            year: Vehicle year to match
            body_style: Vehicle body style to match (case-insensitive)

        Returns:
            True if configuration matches all provided criteria
        """
        if make and self.make.lower() != make.lower():
            return False
        if model and self.model.lower() != model.lower():
            return False
        if year and self.year != year:
            return False
        if body_style and self.body_style.lower() != body_style.lower():
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        """
        Convert configuration to dictionary representation.

        Returns:
            Dictionary representation of configuration
        """
        return {
            "id": str(self.id),
            "vehicle_id": str(self.vehicle_id),
            "make": self.make,
            "model": self.model,
            "year": self.year,
            "body_style": self.body_style,
            "configuration_data": self.configuration_data,
            "selection_count": self.selection_count,
            "conversion_count": self.conversion_count,
            "conversion_rate": self.conversion_rate,
            "popularity_score": self.popularity_score,
            "is_trending": self.is_trending,
            "last_selected_at": self.last_selected_at.isoformat() if self.last_selected_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }