"""
Dealer configuration models for managing dealer-specific option and package settings.

This module defines database models for dealer configuration management with
regional availability, custom pricing, and effective date ranges. Implements
comprehensive indexing for efficient dealer queries and proper constraints for
data integrity.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    String,
    Numeric,
    Boolean,
    DateTime,
    Index,
    CheckConstraint,
    ForeignKey,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import BaseModel
from src.core.logging import get_logger

logger = get_logger(__name__)


class DealerOptionConfig(BaseModel):
    """
    Dealer-specific option configuration model.

    Manages dealer customization of vehicle options including availability,
    custom pricing, effective date ranges, and regional restrictions.
    Supports dealer-level control over option offerings with proper
    temporal and geographic constraints.

    Attributes:
        id: Unique configuration identifier (UUID)
        dealer_id: Reference to dealer (UUID)
        option_id: Reference to vehicle option (UUID, FK)
        is_available: Whether option is available for this dealer
        custom_price: Dealer-specific price override (optional)
        effective_from: Start date for configuration validity
        effective_to: End date for configuration validity (optional)
        region: Geographic region for availability (optional)
        created_at: Record creation timestamp (from BaseModel)
        updated_at: Last modification timestamp (from BaseModel)
    """

    __tablename__ = "dealer_option_configs"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique configuration identifier",
    )

    # Foreign keys
    dealer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Reference to dealer",
    )

    option_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_options.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to vehicle option",
    )

    # Configuration settings
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="Whether option is available for this dealer",
    )

    custom_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=True,
        comment="Dealer-specific price override",
    )

    # Temporal validity
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="Start date for configuration validity",
    )

    effective_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="End date for configuration validity",
    )

    # Geographic restriction
    region: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Geographic region for availability",
    )

    # Table constraints and indexes
    __table_args__ = (
        # Unique constraint for dealer-option combination
        UniqueConstraint(
            "dealer_id",
            "option_id",
            "effective_from",
            name="uq_dealer_option_configs_dealer_option_effective",
        ),
        # Composite index for dealer queries
        Index(
            "ix_dealer_option_configs_dealer_id",
            "dealer_id",
        ),
        # Index for option lookup
        Index(
            "ix_dealer_option_configs_option_id",
            "option_id",
        ),
        # Index for availability queries
        Index(
            "ix_dealer_option_configs_dealer_available",
            "dealer_id",
            "is_available",
        ),
        # Index for temporal queries
        Index(
            "ix_dealer_option_configs_effective_dates",
            "effective_from",
            "effective_to",
        ),
        # Index for regional queries
        Index(
            "ix_dealer_option_configs_region",
            "region",
        ),
        # Composite index for active configurations
        Index(
            "ix_dealer_option_configs_active",
            "dealer_id",
            "is_available",
            "effective_from",
            "effective_to",
        ),
        # Check constraints for data validation
        CheckConstraint(
            "custom_price IS NULL OR custom_price >= 0",
            name="ck_dealer_option_configs_custom_price_non_negative",
        ),
        CheckConstraint(
            "custom_price IS NULL OR custom_price <= 100000.00",
            name="ck_dealer_option_configs_custom_price_max",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="ck_dealer_option_configs_effective_dates_valid",
        ),
        CheckConstraint(
            "region IS NULL OR length(region) >= 1",
            name="ck_dealer_option_configs_region_min_length",
        ),
        {
            "comment": "Dealer-specific option configurations with pricing and availability",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of DealerOptionConfig.

        Returns:
            String representation showing key configuration attributes
        """
        return (
            f"<DealerOptionConfig(id={self.id}, dealer_id={self.dealer_id}, "
            f"option_id={self.option_id}, is_available={self.is_available}, "
            f"custom_price={self.custom_price}, region='{self.region}')>"
        )

    @property
    def is_active(self) -> bool:
        """
        Check if configuration is currently active.

        Returns:
            True if configuration is within effective date range
        """
        now = datetime.utcnow()
        return (
            self.effective_from <= now
            and (self.effective_to is None or self.effective_to > now)
        )

    @property
    def has_custom_pricing(self) -> bool:
        """
        Check if configuration has custom pricing.

        Returns:
            True if custom price is set
        """
        return self.custom_price is not None

    @property
    def has_regional_restriction(self) -> bool:
        """
        Check if configuration has regional restriction.

        Returns:
            True if region is specified
        """
        return self.region is not None

    def is_valid_for_date(self, check_date: datetime) -> bool:
        """
        Check if configuration is valid for specific date.

        Args:
            check_date: Date to check validity for

        Returns:
            True if configuration is valid for the date
        """
        return (
            self.effective_from <= check_date
            and (self.effective_to is None or self.effective_to > check_date)
        )

    def is_valid_for_region(self, check_region: Optional[str]) -> bool:
        """
        Check if configuration is valid for specific region.

        Args:
            check_region: Region to check validity for

        Returns:
            True if configuration is valid for the region
        """
        if self.region is None:
            return True
        if check_region is None:
            return False
        return self.region.lower() == check_region.lower()

    def update_availability(self, is_available: bool) -> None:
        """
        Update option availability.

        Args:
            is_available: New availability status
        """
        old_status = self.is_available
        self.is_available = is_available

        logger.info(
            "Dealer option availability updated",
            config_id=str(self.id),
            dealer_id=str(self.dealer_id),
            option_id=str(self.option_id),
            old_status=old_status,
            new_status=is_available,
        )

    def update_custom_price(self, price: Optional[Decimal]) -> None:
        """
        Update custom price with validation.

        Args:
            price: New custom price (None to remove override)

        Raises:
            ValueError: If price is negative or exceeds maximum
        """
        if price is not None:
            if price < 0:
                raise ValueError("Custom price cannot be negative")
            if price > Decimal("100000.00"):
                raise ValueError("Custom price exceeds maximum allowed value")

        old_price = self.custom_price
        self.custom_price = price

        logger.info(
            "Dealer option custom price updated",
            config_id=str(self.id),
            dealer_id=str(self.dealer_id),
            option_id=str(self.option_id),
            old_price=float(old_price) if old_price else None,
            new_price=float(price) if price else None,
        )

    def extend_validity(self, new_effective_to: Optional[datetime]) -> None:
        """
        Extend configuration validity period.

        Args:
            new_effective_to: New end date (None for indefinite)

        Raises:
            ValueError: If new end date is before start date
        """
        if new_effective_to is not None and new_effective_to <= self.effective_from:
            raise ValueError("End date must be after start date")

        old_effective_to = self.effective_to
        self.effective_to = new_effective_to

        logger.info(
            "Dealer option validity extended",
            config_id=str(self.id),
            dealer_id=str(self.dealer_id),
            option_id=str(self.option_id),
            old_effective_to=old_effective_to.isoformat() if old_effective_to else None,
            new_effective_to=new_effective_to.isoformat() if new_effective_to else None,
        )


class DealerPackageConfig(BaseModel):
    """
    Dealer-specific package configuration model.

    Manages dealer customization of vehicle packages including availability,
    custom pricing, effective date ranges, and regional restrictions.
    Supports dealer-level control over package offerings with proper
    temporal and geographic constraints.

    Attributes:
        id: Unique configuration identifier (UUID)
        dealer_id: Reference to dealer (UUID)
        package_id: Reference to vehicle package (UUID, FK)
        is_available: Whether package is available for this dealer
        custom_price: Dealer-specific price override (optional)
        effective_from: Start date for configuration validity
        effective_to: End date for configuration validity (optional)
        region: Geographic region for availability (optional)
        created_at: Record creation timestamp (from BaseModel)
        updated_at: Last modification timestamp (from BaseModel)
    """

    __tablename__ = "dealer_package_configs"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique configuration identifier",
    )

    # Foreign keys
    dealer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Reference to dealer",
    )

    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to vehicle package",
    )

    # Configuration settings
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="Whether package is available for this dealer",
    )

    custom_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=True,
        comment="Dealer-specific price override",
    )

    # Temporal validity
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="Start date for configuration validity",
    )

    effective_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="End date for configuration validity",
    )

    # Geographic restriction
    region: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Geographic region for availability",
    )

    # Table constraints and indexes
    __table_args__ = (
        # Unique constraint for dealer-package combination
        UniqueConstraint(
            "dealer_id",
            "package_id",
            "effective_from",
            name="uq_dealer_package_configs_dealer_package_effective",
        ),
        # Composite index for dealer queries
        Index(
            "ix_dealer_package_configs_dealer_id",
            "dealer_id",
        ),
        # Index for package lookup
        Index(
            "ix_dealer_package_configs_package_id",
            "package_id",
        ),
        # Index for availability queries
        Index(
            "ix_dealer_package_configs_dealer_available",
            "dealer_id",
            "is_available",
        ),
        # Index for temporal queries
        Index(
            "ix_dealer_package_configs_effective_dates",
            "effective_from",
            "effective_to",
        ),
        # Index for regional queries
        Index(
            "ix_dealer_package_configs_region",
            "region",
        ),
        # Composite index for active configurations
        Index(
            "ix_dealer_package_configs_active",
            "dealer_id",
            "is_available",
            "effective_from",
            "effective_to",
        ),
        # Check constraints for data validation
        CheckConstraint(
            "custom_price IS NULL OR custom_price >= 0",
            name="ck_dealer_package_configs_custom_price_non_negative",
        ),
        CheckConstraint(
            "custom_price IS NULL OR custom_price <= 100000.00",
            name="ck_dealer_package_configs_custom_price_max",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="ck_dealer_package_configs_effective_dates_valid",
        ),
        CheckConstraint(
            "region IS NULL OR length(region) >= 1",
            name="ck_dealer_package_configs_region_min_length",
        ),
        {
            "comment": "Dealer-specific package configurations with pricing and availability",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of DealerPackageConfig.

        Returns:
            String representation showing key configuration attributes
        """
        return (
            f"<DealerPackageConfig(id={self.id}, dealer_id={self.dealer_id}, "
            f"package_id={self.package_id}, is_available={self.is_available}, "
            f"custom_price={self.custom_price}, region='{self.region}')>"
        )

    @property
    def is_active(self) -> bool:
        """
        Check if configuration is currently active.

        Returns:
            True if configuration is within effective date range
        """
        now = datetime.utcnow()
        return (
            self.effective_from <= now
            and (self.effective_to is None or self.effective_to > now)
        )

    @property
    def has_custom_pricing(self) -> bool:
        """
        Check if configuration has custom pricing.

        Returns:
            True if custom price is set
        """
        return self.custom_price is not None

    @property
    def has_regional_restriction(self) -> bool:
        """
        Check if configuration has regional restriction.

        Returns:
            True if region is specified
        """
        return self.region is not None

    def is_valid_for_date(self, check_date: datetime) -> bool:
        """
        Check if configuration is valid for specific date.

        Args:
            check_date: Date to check validity for

        Returns:
            True if configuration is valid for the date
        """
        return (
            self.effective_from <= check_date
            and (self.effective_to is None or self.effective_to > check_date)
        )

    def is_valid_for_region(self, check_region: Optional[str]) -> bool:
        """
        Check if configuration is valid for specific region.

        Args:
            check_region: Region to check validity for

        Returns:
            True if configuration is valid for the region
        """
        if self.region is None:
            return True
        if check_region is None:
            return False
        return self.region.lower() == check_region.lower()

    def update_availability(self, is_available: bool) -> None:
        """
        Update package availability.

        Args:
            is_available: New availability status
        """
        old_status = self.is_available
        self.is_available = is_available

        logger.info(
            "Dealer package availability updated",
            config_id=str(self.id),
            dealer_id=str(self.dealer_id),
            package_id=str(self.package_id),
            old_status=old_status,
            new_status=is_available,
        )

    def update_custom_price(self, price: Optional[Decimal]) -> None:
        """
        Update custom price with validation.

        Args:
            price: New custom price (None to remove override)

        Raises:
            ValueError: If price is negative or exceeds maximum
        """
        if price is not None:
            if price < 0:
                raise ValueError("Custom price cannot be negative")
            if price > Decimal("100000.00"):
                raise ValueError("Custom price exceeds maximum allowed value")

        old_price = self.custom_price
        self.custom_price = price

        logger.info(
            "Dealer package custom price updated",
            config_id=str(self.id),
            dealer_id=str(self.dealer_id),
            package_id=str(self.package_id),
            old_price=float(old_price) if old_price else None,
            new_price=float(price) if price else None,
        )

    def extend_validity(self, new_effective_to: Optional[datetime]) -> None:
        """
        Extend configuration validity period.

        Args:
            new_effective_to: New end date (None for indefinite)

        Raises:
            ValueError: If new end date is before start date
        """
        if new_effective_to is not None and new_effective_to <= self.effective_from:
            raise ValueError("End date must be after start date")

        old_effective_to = self.effective_to
        self.effective_to = new_effective_to

        logger.info(
            "Dealer package validity extended",
            config_id=str(self.id),
            dealer_id=str(self.dealer_id),
            package_id=str(self.package_id),
            old_effective_to=old_effective_to.isoformat() if old_effective_to else None,
            new_effective_to=new_effective_to.isoformat() if new_effective_to else None,
        )