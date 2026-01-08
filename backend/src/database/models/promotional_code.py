"""
Promotional code database model for discount management.

This module defines the PromotionalCode model for managing promotional codes
and discounts in the vehicle ordering system. It includes validation constraints,
discount calculations, and compatibility rules for promotional codes.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.logging import get_logger
from src.database.base import BaseModel

logger = get_logger(__name__)


class DiscountType(str, Enum):
    """Enumeration of discount types."""

    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"

    @classmethod
    def from_string(cls, value: str) -> "DiscountType":
        """
        Convert string to DiscountType enum.

        Args:
            value: String representation of discount type

        Returns:
            DiscountType enum value

        Raises:
            ValueError: If value is not a valid discount type
        """
        try:
            return cls(value.lower())
        except ValueError as e:
            logger.error(
                "Invalid discount type",
                value=value,
                valid_types=[t.value for t in cls],
            )
            raise ValueError(
                f"Invalid discount type: {value}. "
                f"Must be one of: {', '.join(t.value for t in cls)}"
            ) from e


class PromotionalCode(BaseModel):
    """
    Promotional code model for discount management.

    Represents promotional codes that can be applied to vehicle orders
    to provide discounts. Supports both percentage-based and fixed-amount
    discounts with various validation rules and usage limits.

    Attributes:
        id: Unique identifier (UUID)
        code: Unique promotional code string
        discount_type: Type of discount (percentage or fixed_amount)
        discount_value: Discount value (percentage or amount)
        minimum_order_amount: Minimum order amount required
        maximum_discount: Maximum discount amount (for percentage)
        valid_from: Start date of validity period
        valid_until: End date of validity period
        usage_limit: Maximum number of times code can be used
        usage_count: Current number of times code has been used
        applicable_vehicles: List of vehicle IDs code applies to
        is_active: Whether code is currently active
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
    """

    __tablename__ = "promotional_codes"
    __table_args__ = (
        UniqueConstraint("code", name="uq_promotional_codes_code"),
        CheckConstraint(
            "discount_value > 0",
            name="ck_promotional_codes_discount_value_positive",
        ),
        CheckConstraint(
            "minimum_order_amount >= 0",
            name="ck_promotional_codes_minimum_order_amount_non_negative",
        ),
        CheckConstraint(
            "maximum_discount IS NULL OR maximum_discount > 0",
            name="ck_promotional_codes_maximum_discount_positive",
        ),
        CheckConstraint(
            "usage_limit IS NULL OR usage_limit > 0",
            name="ck_promotional_codes_usage_limit_positive",
        ),
        CheckConstraint(
            "usage_count >= 0",
            name="ck_promotional_codes_usage_count_non_negative",
        ),
        CheckConstraint(
            "valid_until > valid_from",
            name="ck_promotional_codes_valid_date_range",
        ),
        CheckConstraint(
            "(discount_type = 'percentage' AND discount_value <= 100) OR "
            "(discount_type = 'fixed_amount')",
            name="ck_promotional_codes_percentage_max_100",
        ),
        Index("ix_promotional_codes_code", "code"),
        Index("ix_promotional_codes_is_active", "is_active"),
        Index("ix_promotional_codes_valid_from", "valid_from"),
        Index("ix_promotional_codes_valid_until", "valid_until"),
        Index(
            "ix_promotional_codes_active_valid",
            "is_active",
            "valid_from",
            "valid_until",
        ),
        {"comment": "Promotional codes for order discounts"},
    )

    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        comment="Unique promotional code string",
    )

    discount_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Type of discount: percentage or fixed_amount",
    )

    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Discount value (percentage or fixed amount)",
    )

    minimum_order_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Minimum order amount required to use code",
    )

    maximum_discount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Maximum discount amount (for percentage discounts)",
    )

    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Start date of validity period",
    )

    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="End date of validity period",
    )

    usage_limit: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum number of times code can be used (NULL = unlimited)",
    )

    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Current number of times code has been used",
    )

    applicable_vehicles: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(UUID(as_uuid=False)),
        nullable=True,
        comment="List of vehicle IDs code applies to (NULL = all vehicles)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether code is currently active",
    )

    def is_valid(self, order_amount: Decimal, vehicle_id: Optional[str] = None) -> bool:
        """
        Check if promotional code is valid for given order.

        Args:
            order_amount: Total order amount
            vehicle_id: Vehicle ID to check applicability

        Returns:
            True if code is valid, False otherwise
        """
        now = datetime.utcnow()

        if not self.is_active:
            logger.debug(
                "Promotional code is inactive",
                code=self.code,
            )
            return False

        if now < self.valid_from or now > self.valid_until:
            logger.debug(
                "Promotional code outside validity period",
                code=self.code,
                valid_from=self.valid_from,
                valid_until=self.valid_until,
                current_time=now,
            )
            return False

        if self.usage_limit is not None and self.usage_count >= self.usage_limit:
            logger.debug(
                "Promotional code usage limit reached",
                code=self.code,
                usage_count=self.usage_count,
                usage_limit=self.usage_limit,
            )
            return False

        if order_amount < self.minimum_order_amount:
            logger.debug(
                "Order amount below minimum",
                code=self.code,
                order_amount=order_amount,
                minimum_order_amount=self.minimum_order_amount,
            )
            return False

        if vehicle_id and self.applicable_vehicles:
            if vehicle_id not in self.applicable_vehicles:
                logger.debug(
                    "Vehicle not applicable for promotional code",
                    code=self.code,
                    vehicle_id=vehicle_id,
                )
                return False

        return True

    def calculate_discount(self, order_amount: Decimal) -> Decimal:
        """
        Calculate discount amount for given order.

        Args:
            order_amount: Total order amount

        Returns:
            Calculated discount amount

        Raises:
            ValueError: If code is not valid for the order amount
        """
        if not self.is_valid(order_amount):
            raise ValueError(
                f"Promotional code {self.code} is not valid for order amount {order_amount}"
            )

        discount_type = DiscountType.from_string(self.discount_type)

        if discount_type == DiscountType.PERCENTAGE:
            discount = order_amount * (self.discount_value / Decimal("100"))
            if self.maximum_discount is not None:
                discount = min(discount, self.maximum_discount)
        else:
            discount = self.discount_value

        discount = min(discount, order_amount)

        logger.info(
            "Discount calculated",
            code=self.code,
            order_amount=order_amount,
            discount_amount=discount,
            discount_type=discount_type.value,
        )

        return discount

    def increment_usage(self) -> None:
        """
        Increment usage count for promotional code.

        Raises:
            ValueError: If usage limit would be exceeded
        """
        if self.usage_limit is not None and self.usage_count >= self.usage_limit:
            raise ValueError(
                f"Promotional code {self.code} has reached usage limit"
            )

        self.usage_count += 1

        logger.info(
            "Promotional code usage incremented",
            code=self.code,
            usage_count=self.usage_count,
            usage_limit=self.usage_limit,
        )

    def deactivate(self) -> None:
        """Deactivate promotional code."""
        self.is_active = False
        logger.info("Promotional code deactivated", code=self.code)

    def activate(self) -> None:
        """Activate promotional code."""
        self.is_active = True
        logger.info("Promotional code activated", code=self.code)

    @property
    def is_expired(self) -> bool:
        """Check if promotional code has expired."""
        return datetime.utcnow() > self.valid_until

    @property
    def is_usage_exhausted(self) -> bool:
        """Check if promotional code usage limit is exhausted."""
        return (
            self.usage_limit is not None and self.usage_count >= self.usage_limit
        )

    @property
    def remaining_uses(self) -> Optional[int]:
        """Get remaining number of uses for promotional code."""
        if self.usage_limit is None:
            return None
        return max(0, self.usage_limit - self.usage_count)

    @property
    def formatted_discount(self) -> str:
        """Get formatted discount string."""
        discount_type = DiscountType.from_string(self.discount_type)
        if discount_type == DiscountType.PERCENTAGE:
            return f"{self.discount_value}%"
        return f"${self.discount_value:.2f}"

    def __repr__(self) -> str:
        """Generate string representation of promotional code."""
        return (
            f"<PromotionalCode(code={self.code!r}, "
            f"discount_type={self.discount_type!r}, "
            f"discount_value={self.discount_value}, "
            f"is_active={self.is_active})>"
        )