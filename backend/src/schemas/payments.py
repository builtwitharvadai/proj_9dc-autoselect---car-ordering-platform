"""
Payment processing schemas for Stripe integration.

This module defines Pydantic schemas for payment API requests and responses,
including payment intent creation, payment processing, webhook events, and
payment status retrieval with comprehensive validation.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)


class PaymentIntentRequest(BaseModel):
    """Request schema for creating a payment intent."""

    amount: int = Field(
        ...,
        gt=0,
        le=99999999,
        description="Payment amount in cents (minimum $0.50, maximum $999,999.99)",
    )
    currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Three-letter ISO currency code (e.g., 'usd')",
    )
    order_id: Optional[UUID] = Field(
        None,
        description="Associated order ID for tracking",
    )
    customer_email: Optional[str] = Field(
        None,
        max_length=255,
        description="Customer email for receipt",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional metadata for the payment",
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        """Validate payment amount meets minimum requirements."""
        if v < 50:
            raise ValueError("Amount must be at least $0.50 (50 cents)")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate and normalize currency code."""
        normalized = v.lower().strip()
        supported_currencies = {"usd", "eur", "gbp", "cad", "aud"}
        if normalized not in supported_currencies:
            raise ValueError(
                f"Currency must be one of: {', '.join(sorted(supported_currencies))}"
            )
        return normalized

    @field_validator("customer_email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format if provided."""
        if v is None:
            return v
        email = v.strip().lower()
        if "@" not in email or "." not in email.split("@")[1]:
            raise ValueError("Invalid email format")
        return email

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate metadata constraints."""
        if len(v) > 50:
            raise ValueError("Metadata cannot exceed 50 key-value pairs")
        for key, value in v.items():
            if len(key) > 40:
                raise ValueError(f"Metadata key '{key}' exceeds 40 characters")
            if len(value) > 500:
                raise ValueError(
                    f"Metadata value for key '{key}' exceeds 500 characters"
                )
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "amount": 50000,
                    "currency": "usd",
                    "order_id": "123e4567-e89b-12d3-a456-426614174000",
                    "customer_email": "customer@example.com",
                    "metadata": {"order_type": "vehicle_purchase"},
                }
            ]
        }
    }


class PaymentMethodDetails(BaseModel):
    """Payment method details for processing."""

    type: str = Field(
        ...,
        description="Payment method type (e.g., 'card', 'bank_account')",
    )
    card_last4: Optional[str] = Field(
        None,
        min_length=4,
        max_length=4,
        description="Last 4 digits of card number",
    )
    card_brand: Optional[str] = Field(
        None,
        description="Card brand (e.g., 'visa', 'mastercard')",
    )
    card_exp_month: Optional[int] = Field(
        None,
        ge=1,
        le=12,
        description="Card expiration month",
    )
    card_exp_year: Optional[int] = Field(
        None,
        ge=2024,
        le=2099,
        description="Card expiration year",
    )

    @field_validator("type")
    @classmethod
    def validate_payment_type(cls, v: str) -> str:
        """Validate payment method type."""
        normalized = v.lower().strip()
        supported_types = {"card", "bank_account", "ach_debit"}
        if normalized not in supported_types:
            raise ValueError(
                f"Payment type must be one of: {', '.join(sorted(supported_types))}"
            )
        return normalized

    @field_validator("card_last4")
    @classmethod
    def validate_card_last4(cls, v: Optional[str]) -> Optional[str]:
        """Validate card last 4 digits."""
        if v is None:
            return v
        if not v.isdigit():
            raise ValueError("Card last 4 must contain only digits")
        return v

    @field_validator("card_brand")
    @classmethod
    def validate_card_brand(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize card brand."""
        if v is None:
            return v
        normalized = v.lower().strip()
        supported_brands = {
            "visa",
            "mastercard",
            "amex",
            "discover",
            "diners",
            "jcb",
            "unionpay",
        }
        if normalized not in supported_brands:
            raise ValueError(
                f"Card brand must be one of: {', '.join(sorted(supported_brands))}"
            )
        return normalized


class PaymentProcessRequest(BaseModel):
    """Request schema for processing a payment."""

    payment_intent_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Stripe payment intent ID",
    )
    payment_method_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Stripe payment method ID",
    )
    save_payment_method: bool = Field(
        default=False,
        description="Whether to save payment method for future use",
    )
    idempotency_key: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Idempotency key for safe retries",
    )

    @field_validator("payment_intent_id", "payment_method_id")
    @classmethod
    def validate_stripe_id(cls, v: str) -> str:
        """Validate Stripe ID format."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Stripe ID cannot be empty")
        if len(stripped) > 255:
            raise ValueError("Stripe ID exceeds maximum length")
        return stripped

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "payment_intent_id": "pi_1234567890abcdef",
                    "payment_method_id": "pm_1234567890abcdef",
                    "save_payment_method": False,
                    "idempotency_key": "order_123_payment_attempt_1",
                }
            ]
        }
    }


class WebhookEventData(BaseModel):
    """Webhook event data payload."""

    object: dict[str, Any] = Field(
        ...,
        description="Stripe event object data",
    )

    @field_validator("object")
    @classmethod
    def validate_object(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate event object structure."""
        if not v:
            raise ValueError("Event object cannot be empty")
        if "id" not in v:
            raise ValueError("Event object must contain 'id' field")
        return v


class WebhookEvent(BaseModel):
    """Stripe webhook event schema."""

    id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Stripe event ID",
    )
    type: str = Field(
        ...,
        description="Event type (e.g., 'payment_intent.succeeded')",
    )
    data: WebhookEventData = Field(
        ...,
        description="Event data payload",
    )
    created: int = Field(
        ...,
        gt=0,
        description="Unix timestamp of event creation",
    )
    livemode: bool = Field(
        ...,
        description="Whether event occurred in live mode",
    )
    api_version: Optional[str] = Field(
        None,
        description="Stripe API version",
    )

    @field_validator("type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate event type format."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Event type cannot be empty")
        if "." not in stripped:
            raise ValueError("Event type must contain a period separator")
        return stripped

    @field_validator("created")
    @classmethod
    def validate_created_timestamp(cls, v: int) -> int:
        """Validate timestamp is reasonable."""
        min_timestamp = 1577836800  # 2020-01-01
        max_timestamp = 4102444800  # 2100-01-01
        if v < min_timestamp or v > max_timestamp:
            raise ValueError("Event timestamp is outside valid range")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "evt_1234567890abcdef",
                    "type": "payment_intent.succeeded",
                    "data": {
                        "object": {
                            "id": "pi_1234567890abcdef",
                            "amount": 50000,
                            "currency": "usd",
                            "status": "succeeded",
                        }
                    },
                    "created": 1234567890,
                    "livemode": False,
                    "api_version": "2023-10-16",
                }
            ]
        }
    }


class PaymentResponse(BaseModel):
    """Response schema for payment operations."""

    id: UUID = Field(
        ...,
        description="Internal payment record ID",
    )
    payment_intent_id: str = Field(
        ...,
        description="Stripe payment intent ID",
    )
    amount: int = Field(
        ...,
        description="Payment amount in cents",
    )
    currency: str = Field(
        ...,
        description="Three-letter ISO currency code",
    )
    status: str = Field(
        ...,
        description="Payment status",
    )
    payment_method: Optional[PaymentMethodDetails] = Field(
        None,
        description="Payment method details",
    )
    order_id: Optional[UUID] = Field(
        None,
        description="Associated order ID",
    )
    customer_email: Optional[str] = Field(
        None,
        description="Customer email",
    )
    failure_code: Optional[str] = Field(
        None,
        description="Failure code if payment failed",
    )
    failure_message: Optional[str] = Field(
        None,
        description="Human-readable failure message",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Payment metadata",
    )
    created_at: datetime = Field(
        ...,
        description="Payment creation timestamp",
    )
    updated_at: datetime = Field(
        ...,
        description="Payment last update timestamp",
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate payment status."""
        normalized = v.lower().strip()
        valid_statuses = {
            "pending",
            "processing",
            "requires_action",
            "requires_payment_method",
            "succeeded",
            "failed",
            "canceled",
        }
        if normalized not in valid_statuses:
            raise ValueError(
                f"Status must be one of: {', '.join(sorted(valid_statuses))}"
            )
        return normalized

    @model_validator(mode="after")
    def validate_failure_fields(self) -> "PaymentResponse":
        """Validate failure fields are present when status is failed."""
        if self.status == "failed":
            if not self.failure_code and not self.failure_message:
                raise ValueError(
                    "Failed payments must have failure_code or failure_message"
                )
        return self

    @property
    def amount_decimal(self) -> Decimal:
        """Get amount as decimal value in currency units."""
        return Decimal(self.amount) / Decimal(100)

    @property
    def is_successful(self) -> bool:
        """Check if payment was successful."""
        return self.status == "succeeded"

    @property
    def is_pending(self) -> bool:
        """Check if payment is pending."""
        return self.status in {"pending", "processing", "requires_action"}

    @property
    def requires_action(self) -> bool:
        """Check if payment requires customer action."""
        return self.status in {"requires_action", "requires_payment_method"}

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "payment_intent_id": "pi_1234567890abcdef",
                    "amount": 50000,
                    "currency": "usd",
                    "status": "succeeded",
                    "payment_method": {
                        "type": "card",
                        "card_last4": "4242",
                        "card_brand": "visa",
                        "card_exp_month": 12,
                        "card_exp_year": 2025,
                    },
                    "order_id": "123e4567-e89b-12d3-a456-426614174001",
                    "customer_email": "customer@example.com",
                    "metadata": {"order_type": "vehicle_purchase"},
                    "created_at": "2024-01-07T22:34:38.719104Z",
                    "updated_at": "2024-01-07T22:34:38.719104Z",
                }
            ]
        }
    }