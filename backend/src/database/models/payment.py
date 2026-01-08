"""
Payment model for secure payment transaction management.

This module defines the Payment model for managing payment transactions with
comprehensive encryption support, status tracking, and audit trails. Implements
PCI DSS compliance through tokenization and encrypted field storage.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Any

from sqlalchemy import (
    String,
    Numeric,
    ForeignKey,
    Index,
    CheckConstraint,
    Enum as SQLEnum,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import AuditedModel
from src.core.logging import get_logger

logger = get_logger(__name__)


class PaymentStatus(str, Enum):
    """
    Payment status enumeration for tracking payment lifecycle.

    Attributes:
        PENDING: Payment intent created but not yet processed
        PROCESSING: Payment being processed by payment gateway
        REQUIRES_ACTION: Payment requires additional customer action (3DS)
        SUCCEEDED: Payment successfully completed
        FAILED: Payment failed
        CANCELLED: Payment cancelled by customer or system
        REFUNDED: Payment refunded to customer
        PARTIALLY_REFUNDED: Payment partially refunded
    """

    PENDING = "pending"
    PROCESSING = "processing"
    REQUIRES_ACTION = "requires_action"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"

    @classmethod
    def from_string(cls, value: str) -> "PaymentStatus":
        """
        Create PaymentStatus from string value.

        Args:
            value: String representation of status

        Returns:
            PaymentStatus enum value

        Raises:
            ValueError: If value is not a valid status
        """
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(f"Invalid payment status: {value}")

    @property
    def is_terminal(self) -> bool:
        """Check if status is terminal (no further transitions)."""
        return self in (
            PaymentStatus.SUCCEEDED,
            PaymentStatus.FAILED,
            PaymentStatus.CANCELLED,
            PaymentStatus.REFUNDED,
        )

    @property
    def is_successful(self) -> bool:
        """Check if payment is successful."""
        return self in (
            PaymentStatus.SUCCEEDED,
            PaymentStatus.PARTIALLY_REFUNDED,
        )

    @property
    def requires_action(self) -> bool:
        """Check if payment requires customer action."""
        return self == PaymentStatus.REQUIRES_ACTION

    @property
    def can_refund(self) -> bool:
        """Check if payment can be refunded."""
        return self in (
            PaymentStatus.SUCCEEDED,
            PaymentStatus.PARTIALLY_REFUNDED,
        )


class PaymentMethodType(str, Enum):
    """
    Payment method type enumeration.

    Attributes:
        CARD: Credit/debit card payment
        ACH: ACH bank transfer
        WIRE: Wire transfer
        FINANCING: Financing/loan payment
    """

    CARD = "card"
    ACH = "ach"
    WIRE = "wire"
    FINANCING = "financing"

    @classmethod
    def from_string(cls, value: str) -> "PaymentMethodType":
        """
        Create PaymentMethodType from string value.

        Args:
            value: String representation of payment method

        Returns:
            PaymentMethodType enum value

        Raises:
            ValueError: If value is not a valid payment method
        """
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(f"Invalid payment method type: {value}")


class Payment(AuditedModel):
    """
    Payment model for managing payment transactions.

    Manages complete payment lifecycle including intent creation, processing,
    status tracking, and refunds. Implements PCI DSS compliance through
    tokenization and encrypted field storage. All sensitive payment data
    is stored as tokens or encrypted values.

    Attributes:
        id: Unique payment identifier (UUID)
        order_id: Foreign key to associated order
        stripe_payment_intent_id: Stripe payment intent identifier
        amount: Payment amount in cents
        currency: Payment currency code (ISO 4217)
        status: Current payment status (enum)
        payment_method_type: Type of payment method used
        payment_method_token: Tokenized payment method (encrypted)
        last_four: Last 4 digits of card/account (for display)
        card_brand: Card brand (Visa, Mastercard, etc.)
        failure_code: Payment failure code if failed
        failure_message: Payment failure message if failed
        refund_amount: Total amount refunded
        metadata: Additional payment metadata (JSONB)
        created_at: Record creation timestamp (from AuditedModel)
        updated_at: Last modification timestamp (from AuditedModel)
        created_by: User who created this record (from AuditedModel)
        updated_by: User who last modified this record (from AuditedModel)
    """

    __tablename__ = "payments"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique payment identifier",
    )

    # Foreign keys
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated order identifier",
    )

    # Stripe integration
    stripe_payment_intent_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Stripe payment intent identifier",
    )

    # Payment amount
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        comment="Payment amount in cents",
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="usd",
        comment="Payment currency code (ISO 4217)",
    )

    # Payment status
    status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus, name="payment_status", create_constraint=True),
        nullable=False,
        default=PaymentStatus.PENDING,
        index=True,
        comment="Current payment status",
    )

    # Payment method (tokenized for PCI compliance)
    payment_method_type: Mapped[PaymentMethodType] = mapped_column(
        SQLEnum(
            PaymentMethodType,
            name="payment_method_type",
            create_constraint=True,
        ),
        nullable=False,
        comment="Type of payment method used",
    )

    payment_method_token: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Tokenized payment method (encrypted)",
    )

    last_four: Mapped[Optional[str]] = mapped_column(
        String(4),
        nullable=True,
        comment="Last 4 digits of card/account",
    )

    card_brand: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Card brand (Visa, Mastercard, etc.)",
    )

    # Failure information
    failure_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Payment failure code",
    )

    failure_message: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Payment failure message",
    )

    # Refund tracking
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Total amount refunded",
    )

    # Additional metadata
    metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional payment metadata",
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="payments",
        foreign_keys=[order_id],
        lazy="selectin",
    )

    payment_status_history: Mapped[list["PaymentStatusHistory"]] = relationship(
        "PaymentStatusHistory",
        back_populates="payment",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="PaymentStatusHistory.created_at.desc()",
    )

    # Table constraints and indexes
    __table_args__ = (
        # Composite index for order payments
        Index(
            "ix_payments_order_status",
            "order_id",
            "status",
        ),
        # Index for Stripe payment intent lookup
        Index(
            "ix_payments_stripe_intent",
            "stripe_payment_intent_id",
        ),
        # Index for status-based queries
        Index(
            "ix_payments_status_created",
            "status",
            "created_at",
        ),
        # Index for payment method type
        Index(
            "ix_payments_method_type",
            "payment_method_type",
        ),
        # Check constraints for data validation
        CheckConstraint(
            "amount >= 0",
            name="ck_payments_amount_non_negative",
        ),
        CheckConstraint(
            "amount <= 10000000.00",
            name="ck_payments_amount_max",
        ),
        CheckConstraint(
            "refund_amount >= 0",
            name="ck_payments_refund_amount_non_negative",
        ),
        CheckConstraint(
            "refund_amount <= amount",
            name="ck_payments_refund_not_exceed_amount",
        ),
        CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="ck_payments_currency_format",
        ),
        CheckConstraint(
            "last_four IS NULL OR last_four ~ '^[0-9]{4}$'",
            name="ck_payments_last_four_format",
        ),
        {
            "comment": "Payment transactions with encryption and audit trail",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of Payment.

        Returns:
            String representation showing key payment attributes
        """
        return (
            f"<Payment(id={self.id}, order_id={self.order_id}, "
            f"status={self.status.value}, amount={self.amount}, "
            f"currency={self.currency})>"
        )

    @property
    def is_successful(self) -> bool:
        """
        Check if payment is successful.

        Returns:
            True if payment is successful
        """
        return self.status.is_successful

    @property
    def is_terminal(self) -> bool:
        """
        Check if payment is in terminal state.

        Returns:
            True if payment is in terminal state
        """
        return self.status.is_terminal

    @property
    def can_refund(self) -> bool:
        """
        Check if payment can be refunded.

        Returns:
            True if payment can be refunded
        """
        return self.status.can_refund and self.refund_amount < self.amount

    @property
    def formatted_amount(self) -> str:
        """
        Get formatted amount string.

        Returns:
            Amount formatted as currency string
        """
        return f"${self.amount:,.2f}"

    @property
    def formatted_refund_amount(self) -> str:
        """
        Get formatted refund amount string.

        Returns:
            Refund amount formatted as currency string
        """
        return f"${self.refund_amount:,.2f}"

    @property
    def remaining_amount(self) -> Decimal:
        """
        Calculate remaining amount after refunds.

        Returns:
            Remaining amount
        """
        return self.amount - self.refund_amount

    @property
    def formatted_remaining_amount(self) -> str:
        """
        Get formatted remaining amount string.

        Returns:
            Remaining amount formatted as currency string
        """
        return f"${self.remaining_amount:,.2f}"

    @property
    def is_fully_refunded(self) -> bool:
        """
        Check if payment is fully refunded.

        Returns:
            True if payment is fully refunded
        """
        return self.refund_amount >= self.amount

    @property
    def is_partially_refunded(self) -> bool:
        """
        Check if payment is partially refunded.

        Returns:
            True if payment is partially refunded
        """
        return Decimal("0.00") < self.refund_amount < self.amount

    @property
    def masked_payment_method(self) -> Optional[str]:
        """
        Get masked payment method for display.

        Returns:
            Masked payment method string or None
        """
        if not self.last_four:
            return None

        if self.payment_method_type == PaymentMethodType.CARD:
            brand = self.card_brand or "Card"
            return f"{brand} ending in {self.last_four}"
        elif self.payment_method_type == PaymentMethodType.ACH:
            return f"Bank account ending in {self.last_four}"
        else:
            return f"{self.payment_method_type.value} ending in {self.last_four}"

    def update_status(
        self,
        new_status: PaymentStatus,
        failure_code: Optional[str] = None,
        failure_message: Optional[str] = None,
    ) -> None:
        """
        Update payment status with validation.

        Args:
            new_status: New status to set
            failure_code: Failure code if status is FAILED
            failure_message: Failure message if status is FAILED

        Raises:
            ValueError: If status transition is invalid
        """
        if self.status.is_terminal:
            raise ValueError(
                f"Cannot change status from terminal state {self.status.value}"
            )

        if not self._is_valid_transition(new_status):
            raise ValueError(
                f"Invalid status transition from {self.status.value} to {new_status.value}"
            )

        self.status = new_status

        if new_status == PaymentStatus.FAILED:
            self.failure_code = failure_code
            self.failure_message = failure_message
        elif new_status == PaymentStatus.SUCCEEDED:
            self.failure_code = None
            self.failure_message = None

        logger.info(
            "Payment status updated",
            payment_id=str(self.id),
            old_status=self.status.value,
            new_status=new_status.value,
            failure_code=failure_code,
        )

    def _is_valid_transition(self, new_status: PaymentStatus) -> bool:
        """
        Validate status transition.

        Args:
            new_status: Target status

        Returns:
            True if transition is valid
        """
        valid_transitions = {
            PaymentStatus.PENDING: {
                PaymentStatus.PROCESSING,
                PaymentStatus.REQUIRES_ACTION,
                PaymentStatus.CANCELLED,
            },
            PaymentStatus.PROCESSING: {
                PaymentStatus.SUCCEEDED,
                PaymentStatus.FAILED,
                PaymentStatus.REQUIRES_ACTION,
            },
            PaymentStatus.REQUIRES_ACTION: {
                PaymentStatus.PROCESSING,
                PaymentStatus.SUCCEEDED,
                PaymentStatus.FAILED,
                PaymentStatus.CANCELLED,
            },
            PaymentStatus.SUCCEEDED: {
                PaymentStatus.REFUNDED,
                PaymentStatus.PARTIALLY_REFUNDED,
            },
            PaymentStatus.PARTIALLY_REFUNDED: {
                PaymentStatus.REFUNDED,
            },
        }

        return new_status in valid_transitions.get(self.status, set())

    def add_refund(self, refund_amount: Decimal) -> None:
        """
        Add refund amount to payment.

        Args:
            refund_amount: Amount to refund

        Raises:
            ValueError: If refund is invalid
        """
        if not self.can_refund:
            raise ValueError(
                f"Cannot refund payment in status {self.status.value}"
            )

        if refund_amount <= 0:
            raise ValueError("Refund amount must be positive")

        new_refund_total = self.refund_amount + refund_amount

        if new_refund_total > self.amount:
            raise ValueError(
                f"Refund amount {refund_amount} exceeds remaining amount {self.remaining_amount}"
            )

        self.refund_amount = new_refund_total

        if self.is_fully_refunded:
            self.status = PaymentStatus.REFUNDED
        else:
            self.status = PaymentStatus.PARTIALLY_REFUNDED

        logger.info(
            "Refund added to payment",
            payment_id=str(self.id),
            refund_amount=float(refund_amount),
            total_refunded=float(self.refund_amount),
            new_status=self.status.value,
        )

    def set_metadata_value(self, key: str, value: Any) -> None:
        """
        Set metadata value.

        Args:
            key: Metadata key
            value: Metadata value
        """
        if self.metadata is None:
            self.metadata = {}

        self.metadata[key] = value

    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """
        Get metadata value.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        if self.metadata is None:
            return default

        return self.metadata.get(key, default)

    def to_dict(self, include_sensitive: bool = False) -> dict[str, Any]:
        """
        Convert payment to dictionary representation.

        Args:
            include_sensitive: Whether to include sensitive data

        Returns:
            Dictionary representation of payment
        """
        data = {
            "id": str(self.id),
            "order_id": str(self.order_id),
            "stripe_payment_intent_id": self.stripe_payment_intent_id,
            "amount": float(self.amount),
            "currency": self.currency,
            "status": self.status.value,
            "payment_method_type": self.payment_method_type.value,
            "masked_payment_method": self.masked_payment_method,
            "refund_amount": float(self.refund_amount),
            "remaining_amount": float(self.remaining_amount),
            "formatted_amount": self.formatted_amount,
            "formatted_refund_amount": self.formatted_refund_amount,
            "formatted_remaining_amount": self.formatted_remaining_amount,
            "is_successful": self.is_successful,
            "is_terminal": self.is_terminal,
            "can_refund": self.can_refund,
            "is_fully_refunded": self.is_fully_refunded,
            "is_partially_refunded": self.is_partially_refunded,
            "failure_code": self.failure_code,
            "failure_message": self.failure_message,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_sensitive:
            data["payment_method_token"] = self.payment_method_token
            data["last_four"] = self.last_four
            data["card_brand"] = self.card_brand

        return data


class PaymentStatusHistory(AuditedModel):
    """
    Payment status history model for audit trail.

    Tracks all status changes for a payment with timestamps and context.
    Provides complete audit trail for compliance and debugging.

    Attributes:
        id: Unique history record identifier (UUID)
        payment_id: Foreign key to payment
        from_status: Previous payment status
        to_status: New payment status
        reason: Reason for status change
        metadata: Additional context (JSONB)
        created_at: Record creation timestamp (from AuditedModel)
        updated_at: Last modification timestamp (from AuditedModel)
        created_by: User who created this record (from AuditedModel)
        updated_by: User who last modified this record (from AuditedModel)
    """

    __tablename__ = "payment_status_history"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique history record identifier",
    )

    # Foreign keys
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Payment identifier",
    )

    # Status transition
    from_status: Mapped[Optional[PaymentStatus]] = mapped_column(
        SQLEnum(PaymentStatus, name="payment_status", create_constraint=True),
        nullable=True,
        comment="Previous payment status",
    )

    to_status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus, name="payment_status", create_constraint=True),
        nullable=False,
        comment="New payment status",
    )

    # Context
    reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Reason for status change",
    )

    metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional context",
    )

    # Relationships
    payment: Mapped["Payment"] = relationship(
        "Payment",
        back_populates="payment_status_history",
        foreign_keys=[payment_id],
    )

    # Table constraints and indexes
    __table_args__ = (
        # Index for payment history lookup
        Index(
            "ix_payment_status_history_payment_created",
            "payment_id",
            "created_at",
        ),
        # Index for status-based queries
        Index(
            "ix_payment_status_history_to_status",
            "to_status",
            "created_at",
        ),
        {
            "comment": "Payment status change audit trail",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of PaymentStatusHistory.

        Returns:
            String representation showing key attributes
        """
        return (
            f"<PaymentStatusHistory(id={self.id}, payment_id={self.payment_id}, "
            f"from_status={self.from_status.value if self.from_status else None}, "
            f"to_status={self.to_status.value})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert history record to dictionary representation.

        Returns:
            Dictionary representation of history record
        """
        return {
            "id": str(self.id),
            "payment_id": str(self.payment_id),
            "from_status": self.from_status.value if self.from_status else None,
            "to_status": self.to_status.value,
            "reason": self.reason,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
        }