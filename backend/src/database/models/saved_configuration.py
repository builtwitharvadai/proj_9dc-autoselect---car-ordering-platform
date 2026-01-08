"""
Saved configuration model for vehicle configurations.

This module defines the SavedConfiguration model for managing saved vehicle
configurations with sharing capabilities. Implements secure token generation,
proper relationships, and efficient indexing for configuration management.
"""

import secrets
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Boolean,
    ForeignKey,
    Index,
    CheckConstraint,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import AuditedModel
from src.core.logging import get_logger

logger = get_logger(__name__)


class SavedConfiguration(AuditedModel):
    """
    Saved configuration model for vehicle configurations.

    Manages saved vehicle configurations with custom names, sharing tokens,
    and public/private visibility. Supports efficient querying and secure
    sharing via unique tokens.

    Attributes:
        id: Unique configuration identifier (UUID)
        user_id: Foreign key to user who saved configuration
        name: Custom name for the configuration
        configuration_id: Foreign key to vehicle configuration
        share_token: Unique token for sharing (32 characters)
        is_public: Whether configuration is publicly accessible
        created_at: Record creation timestamp (from AuditedModel)
        updated_at: Last modification timestamp (from AuditedModel)
        created_by: User who created this record (from AuditedModel)
        updated_by: User who last modified this record (from AuditedModel)
        deleted_at: Soft deletion timestamp (from AuditedModel)
    """

    __tablename__ = "saved_configurations"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique saved configuration identifier",
    )

    # Foreign keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who saved this configuration",
    )

    configuration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_configurations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated vehicle configuration",
    )

    # Configuration metadata
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Custom name for the saved configuration",
    )

    share_token: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: secrets.token_urlsafe(24)[:32],
        comment="Unique token for sharing configuration",
    )

    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        index=True,
        comment="Whether configuration is publicly accessible",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="saved_configurations",
        foreign_keys=[user_id],
        lazy="selectin",
    )

    configuration: Mapped["VehicleConfiguration"] = relationship(
        "VehicleConfiguration",
        back_populates="saved_configurations",
        foreign_keys=[configuration_id],
        lazy="selectin",
    )

    # Table constraints and indexes
    __table_args__ = (
        # Composite index for user's configurations
        Index(
            "ix_saved_configurations_user_created",
            "user_id",
            "created_at",
        ),
        # Index for configuration lookup
        Index(
            "ix_saved_configurations_config_user",
            "configuration_id",
            "user_id",
        ),
        # Index for public configurations
        Index(
            "ix_saved_configurations_public",
            "is_public",
            "created_at",
        ),
        # Index for share token lookup
        Index(
            "ix_saved_configurations_share_token",
            "share_token",
        ),
        # Composite index for active configurations
        Index(
            "ix_saved_configurations_active",
            "user_id",
            "deleted_at",
        ),
        # Check constraints for data validation
        CheckConstraint(
            "length(name) >= 1",
            name="ck_saved_configurations_name_min_length",
        ),
        CheckConstraint(
            "length(name) <= 255",
            name="ck_saved_configurations_name_max_length",
        ),
        CheckConstraint(
            "length(share_token) = 32",
            name="ck_saved_configurations_share_token_length",
        ),
        UniqueConstraint("share_token", name="uq_saved_configurations_share_token"),
        {
            "comment": "Saved vehicle configurations with sharing capabilities",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of SavedConfiguration.

        Returns:
            String representation showing key configuration attributes
        """
        return (
            f"<SavedConfiguration(id={self.id}, "
            f"user_id={self.user_id}, name='{self.name}', "
            f"configuration_id={self.configuration_id}, "
            f"is_public={self.is_public})>"
        )

    @property
    def is_active(self) -> bool:
        """
        Check if saved configuration is active (not soft deleted).

        Returns:
            True if configuration is active
        """
        return self.deleted_at is None

    @property
    def share_url(self) -> str:
        """
        Generate shareable URL for configuration.

        Returns:
            URL path with share token
        """
        return f"/configurations/shared/{self.share_token}"

    @property
    def can_be_shared(self) -> bool:
        """
        Check if configuration can be shared.

        Returns:
            True if configuration is active and has valid share token
        """
        return self.is_active and bool(self.share_token)

    def regenerate_share_token(self) -> str:
        """
        Generate new share token for configuration.

        Returns:
            New share token

        Note:
            This invalidates the previous share token
        """
        old_token = self.share_token
        self.share_token = secrets.token_urlsafe(24)[:32]

        logger.info(
            "Share token regenerated",
            saved_configuration_id=str(self.id),
            user_id=str(self.user_id),
            old_token_prefix=old_token[:8] if old_token else None,
            new_token_prefix=self.share_token[:8],
        )

        return self.share_token

    def make_public(self) -> None:
        """Make configuration publicly accessible."""
        if not self.is_public:
            self.is_public = True
            logger.info(
                "Configuration made public",
                saved_configuration_id=str(self.id),
                user_id=str(self.user_id),
                name=self.name,
            )

    def make_private(self) -> None:
        """Make configuration private."""
        if self.is_public:
            self.is_public = False
            logger.info(
                "Configuration made private",
                saved_configuration_id=str(self.id),
                user_id=str(self.user_id),
                name=self.name,
            )

    def update_name(self, new_name: str) -> None:
        """
        Update configuration name with validation.

        Args:
            new_name: New name for configuration

        Raises:
            ValueError: If name is invalid
        """
        if not new_name or len(new_name.strip()) == 0:
            raise ValueError("Configuration name cannot be empty")

        if len(new_name) > 255:
            raise ValueError("Configuration name cannot exceed 255 characters")

        old_name = self.name
        self.name = new_name.strip()

        logger.info(
            "Configuration name updated",
            saved_configuration_id=str(self.id),
            user_id=str(self.user_id),
            old_name=old_name,
            new_name=self.name,
        )

    def archive(self) -> None:
        """Archive configuration by setting deleted_at timestamp."""
        if self.deleted_at is None:
            self.deleted_at = datetime.utcnow()
            logger.info(
                "Configuration archived",
                saved_configuration_id=str(self.id),
                user_id=str(self.user_id),
                name=self.name,
            )

    def restore(self) -> None:
        """Restore archived configuration by clearing deleted_at timestamp."""
        if self.deleted_at is not None:
            self.deleted_at = None
            logger.info(
                "Configuration restored",
                saved_configuration_id=str(self.id),
                user_id=str(self.user_id),
                name=self.name,
            )

    def to_dict(self, include_token: bool = False) -> dict:
        """
        Convert saved configuration to dictionary representation.

        Args:
            include_token: Whether to include share token in output

        Returns:
            Dictionary representation of saved configuration
        """
        data = {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "configuration_id": str(self.configuration_id),
            "name": self.name,
            "is_public": self.is_public,
            "is_active": self.is_active,
            "can_be_shared": self.can_be_shared,
            "share_url": self.share_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_token:
            data["share_token"] = self.share_token

        return data

    @classmethod
    def generate_share_token(cls) -> str:
        """
        Generate a new share token.

        Returns:
            32-character URL-safe token

        Note:
            This is a utility method for generating tokens
        """
        return secrets.token_urlsafe(24)[:32]

    def belongs_to_user(self, user_id: uuid.UUID) -> bool:
        """
        Check if configuration belongs to specified user.

        Args:
            user_id: User ID to check

        Returns:
            True if configuration belongs to user
        """
        return self.user_id == user_id

    def is_accessible_by(self, user_id: Optional[uuid.UUID] = None) -> bool:
        """
        Check if configuration is accessible by user.

        Args:
            user_id: User ID to check (None for anonymous)

        Returns:
            True if configuration is accessible
        """
        if not self.is_active:
            return False

        if self.is_public:
            return True

        if user_id is not None and self.belongs_to_user(user_id):
            return True

        return False