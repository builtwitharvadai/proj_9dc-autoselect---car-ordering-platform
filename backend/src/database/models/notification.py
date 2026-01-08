"""
Notification database models for tracking notification delivery and user preferences.

This module defines SQLAlchemy models for the notification system, including
notification logs for tracking all sent notifications and user preferences for
managing notification settings across different channels.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Text,
    Enum as SQLEnum,
    Index,
    CheckConstraint,
    ForeignKey,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import BaseModel


class NotificationType(str, enum.Enum):
    """Notification type enumeration for categorizing notifications."""

    ORDER_CREATED = "order_created"
    ORDER_CONFIRMED = "order_confirmed"
    ORDER_SHIPPED = "order_shipped"
    ORDER_DELIVERED = "order_delivered"
    ORDER_CANCELLED = "order_cancelled"
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_FAILED = "payment_failed"
    DELIVERY_DELAYED = "delivery_delayed"
    DELIVERY_REMINDER = "delivery_reminder"

    @classmethod
    def from_string(cls, value: str) -> "NotificationType":
        """
        Convert string to NotificationType enum.

        Args:
            value: String representation of notification type

        Returns:
            NotificationType enum value

        Raises:
            ValueError: If value is not a valid notification type
        """
        try:
            return cls[value.upper()]
        except KeyError:
            raise ValueError(f"Invalid notification type: {value}")


class NotificationChannel(str, enum.Enum):
    """Notification channel enumeration for delivery methods."""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"

    @classmethod
    def from_string(cls, value: str) -> "NotificationChannel":
        """
        Convert string to NotificationChannel enum.

        Args:
            value: String representation of channel

        Returns:
            NotificationChannel enum value

        Raises:
            ValueError: If value is not a valid channel
        """
        try:
            return cls[value.upper()]
        except KeyError:
            raise ValueError(f"Invalid notification channel: {value}")


class NotificationStatus(str, enum.Enum):
    """Notification status enumeration for tracking delivery state."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    RETRYING = "retrying"

    @classmethod
    def from_string(cls, value: str) -> "NotificationStatus":
        """
        Convert string to NotificationStatus enum.

        Args:
            value: String representation of status

        Returns:
            NotificationStatus enum value

        Raises:
            ValueError: If value is not a valid status
        """
        try:
            return cls[value.upper()]
        except KeyError:
            raise ValueError(f"Invalid notification status: {value}")

    def is_terminal(self) -> bool:
        """
        Check if status is terminal (no further processing).

        Returns:
            True if status is terminal
        """
        return self in (
            NotificationStatus.DELIVERED,
            NotificationStatus.FAILED,
            NotificationStatus.BOUNCED,
        )

    def is_successful(self) -> bool:
        """
        Check if status indicates successful delivery.

        Returns:
            True if notification was successfully delivered
        """
        return self == NotificationStatus.DELIVERED


class NotificationLog(BaseModel):
    """
    Notification log model for tracking all sent notifications.

    Stores comprehensive information about each notification sent through the
    system, including delivery status, timestamps, and error information for
    failed deliveries. Supports retry tracking and delivery confirmation.

    Attributes:
        id: Unique notification identifier (UUID)
        user_id: Foreign key to user receiving notification
        notification_type: Type of notification (order update, payment, etc.)
        channel: Delivery channel (email, SMS, push, in-app)
        recipient: Recipient address (email, phone number, device token)
        subject: Notification subject line (for email)
        content: Notification content/body
        status: Current delivery status
        sent_at: Timestamp when notification was sent
        delivered_at: Timestamp when delivery was confirmed
        error_message: Error details if delivery failed
        retry_count: Number of retry attempts
        metadata: Additional notification metadata (JSON)
        created_at: Record creation timestamp (from BaseModel)
        updated_at: Last modification timestamp (from BaseModel)
    """

    __tablename__ = "notification_logs"

    # Primary key inherited from BaseModel (id: UUID)

    # Foreign key to user
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User receiving the notification",
    )

    # Notification details
    notification_type: Mapped[NotificationType] = mapped_column(
        SQLEnum(NotificationType, name="notification_type", native_enum=False),
        nullable=False,
        index=True,
        comment="Type of notification",
    )

    channel: Mapped[NotificationChannel] = mapped_column(
        SQLEnum(NotificationChannel, name="notification_channel", native_enum=False),
        nullable=False,
        index=True,
        comment="Delivery channel",
    )

    recipient: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Recipient address (email, phone, device token)",
    )

    subject: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Notification subject (for email)",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Notification content/body",
    )

    # Status tracking
    status: Mapped[NotificationStatus] = mapped_column(
        SQLEnum(NotificationStatus, name="notification_status", native_enum=False),
        nullable=False,
        default=NotificationStatus.PENDING,
        index=True,
        comment="Current delivery status",
    )

    sent_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        index=True,
        comment="Timestamp when notification was sent",
    )

    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="Timestamp when delivery was confirmed",
    )

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error details if delivery failed",
    )

    retry_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Number of retry attempts",
    )

    # Additional metadata
    metadata: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Additional notification metadata (JSON)",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="notifications",
        lazy="selectin",
    )

    # Table constraints
    __table_args__ = (
        Index(
            "ix_notification_logs_user_type",
            "user_id",
            "notification_type",
        ),
        Index(
            "ix_notification_logs_status_sent",
            "status",
            "sent_at",
        ),
        Index(
            "ix_notification_logs_channel_status",
            "channel",
            "status",
        ),
        CheckConstraint(
            "retry_count >= 0",
            name="ck_notification_logs_retry_count_non_negative",
        ),
        CheckConstraint(
            "length(recipient) >= 3",
            name="ck_notification_logs_recipient_min_length",
        ),
        CheckConstraint(
            "length(content) >= 1",
            name="ck_notification_logs_content_not_empty",
        ),
        CheckConstraint(
            "delivered_at IS NULL OR delivered_at >= sent_at",
            name="ck_notification_logs_delivered_after_sent",
        ),
        {
            "comment": "Notification delivery logs with status tracking",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of NotificationLog.

        Returns:
            String representation showing key attributes
        """
        return (
            f"<NotificationLog(id={self.id}, user_id={self.user_id}, "
            f"type={self.notification_type.value}, channel={self.channel.value}, "
            f"status={self.status.value})>"
        )

    @property
    def is_delivered(self) -> bool:
        """
        Check if notification was successfully delivered.

        Returns:
            True if notification was delivered
        """
        return self.status == NotificationStatus.DELIVERED

    @property
    def is_failed(self) -> bool:
        """
        Check if notification delivery failed.

        Returns:
            True if delivery failed or bounced
        """
        return self.status in (NotificationStatus.FAILED, NotificationStatus.BOUNCED)

    @property
    def is_pending(self) -> bool:
        """
        Check if notification is pending delivery.

        Returns:
            True if notification is pending or retrying
        """
        return self.status in (NotificationStatus.PENDING, NotificationStatus.RETRYING)

    def mark_sent(self) -> None:
        """Mark notification as sent."""
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.utcnow()

    def mark_delivered(self) -> None:
        """Mark notification as delivered."""
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = datetime.utcnow()

    def mark_failed(self, error_message: str) -> None:
        """
        Mark notification as failed.

        Args:
            error_message: Error details
        """
        self.status = NotificationStatus.FAILED
        self.error_message = error_message

    def increment_retry(self) -> None:
        """Increment retry counter and update status."""
        self.retry_count += 1
        self.status = NotificationStatus.RETRYING


class NotificationPreference(BaseModel):
    """
    Notification preference model for user notification settings.

    Manages user preferences for receiving notifications across different
    channels and notification types. Allows users to opt-in/opt-out of
    specific notification categories and channels.

    Attributes:
        id: Unique preference identifier (UUID)
        user_id: Foreign key to user
        notification_type: Type of notification
        email_enabled: Enable email notifications
        sms_enabled: Enable SMS notifications
        push_enabled: Enable push notifications
        in_app_enabled: Enable in-app notifications
        created_at: Record creation timestamp (from BaseModel)
        updated_at: Last modification timestamp (from BaseModel)
    """

    __tablename__ = "notification_preferences"

    # Primary key inherited from BaseModel (id: UUID)

    # Foreign key to user
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who owns these preferences",
    )

    # Notification type
    notification_type: Mapped[NotificationType] = mapped_column(
        SQLEnum(NotificationType, name="notification_type", native_enum=False),
        nullable=False,
        comment="Type of notification",
    )

    # Channel preferences
    email_enabled: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Enable email notifications",
    )

    sms_enabled: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Enable SMS notifications",
    )

    push_enabled: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Enable push notifications",
    )

    in_app_enabled: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Enable in-app notifications",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="notification_preferences",
        lazy="selectin",
    )

    # Table constraints
    __table_args__ = (
        Index(
            "ix_notification_preferences_user_type",
            "user_id",
            "notification_type",
            unique=True,
        ),
        {
            "comment": "User notification preferences by type and channel",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of NotificationPreference.

        Returns:
            String representation showing key attributes
        """
        return (
            f"<NotificationPreference(id={self.id}, user_id={self.user_id}, "
            f"type={self.notification_type.value}, "
            f"email={self.email_enabled}, sms={self.sms_enabled})>"
        )

    def is_enabled_for_channel(self, channel: NotificationChannel) -> bool:
        """
        Check if notifications are enabled for specific channel.

        Args:
            channel: Notification channel to check

        Returns:
            True if notifications are enabled for the channel
        """
        channel_map = {
            NotificationChannel.EMAIL: self.email_enabled,
            NotificationChannel.SMS: self.sms_enabled,
            NotificationChannel.PUSH: self.push_enabled,
            NotificationChannel.IN_APP: self.in_app_enabled,
        }
        return channel_map.get(channel, False)

    def enable_channel(self, channel: NotificationChannel) -> None:
        """
        Enable notifications for specific channel.

        Args:
            channel: Notification channel to enable
        """
        if channel == NotificationChannel.EMAIL:
            self.email_enabled = True
        elif channel == NotificationChannel.SMS:
            self.sms_enabled = True
        elif channel == NotificationChannel.PUSH:
            self.push_enabled = True
        elif channel == NotificationChannel.IN_APP:
            self.in_app_enabled = True

    def disable_channel(self, channel: NotificationChannel) -> None:
        """
        Disable notifications for specific channel.

        Args:
            channel: Notification channel to disable
        """
        if channel == NotificationChannel.EMAIL:
            self.email_enabled = False
        elif channel == NotificationChannel.SMS:
            self.sms_enabled = False
        elif channel == NotificationChannel.PUSH:
            self.push_enabled = False
        elif channel == NotificationChannel.IN_APP:
            self.in_app_enabled = False

    def enable_all_channels(self) -> None:
        """Enable notifications for all channels."""
        self.email_enabled = True
        self.sms_enabled = True
        self.push_enabled = True
        self.in_app_enabled = True

    def disable_all_channels(self) -> None:
        """Disable notifications for all channels."""
        self.email_enabled = False
        self.sms_enabled = False
        self.push_enabled = False
        self.in_app_enabled = False

    @property
    def has_any_enabled(self) -> bool:
        """
        Check if any notification channel is enabled.

        Returns:
            True if at least one channel is enabled
        """
        return any(
            [
                self.email_enabled,
                self.sms_enabled,
                self.push_enabled,
                self.in_app_enabled,
            ]
        )

    @property
    def enabled_channels(self) -> list[NotificationChannel]:
        """
        Get list of enabled notification channels.

        Returns:
            List of enabled channels
        """
        channels = []
        if self.email_enabled:
            channels.append(NotificationChannel.EMAIL)
        if self.sms_enabled:
            channels.append(NotificationChannel.SMS)
        if self.push_enabled:
            channels.append(NotificationChannel.PUSH)
        if self.in_app_enabled:
            channels.append(NotificationChannel.IN_APP)
        return channels