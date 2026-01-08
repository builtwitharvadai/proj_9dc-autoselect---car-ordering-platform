"""
Cart schemas for shopping cart API requests and responses.

This module defines Pydantic schemas for cart operations including adding items,
updating quantities, applying promotional codes, and retrieving cart summaries.
Includes comprehensive validation for cart operations and promotional codes.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class CartItemRequest(BaseModel):
    """Schema for adding or updating a cart item."""

    vehicle_id: UUID = Field(
        ...,
        description="ID of the vehicle to add to cart",
    )
    configuration_id: Optional[UUID] = Field(
        None,
        description="ID of the vehicle configuration",
    )
    quantity: int = Field(
        default=1,
        description="Quantity of items",
        ge=1,
        le=10,
    )

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        """Validate quantity is within acceptable range."""
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        if v > 10:
            raise ValueError("Quantity cannot exceed 10")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "vehicle_id": "123e4567-e89b-12d3-a456-426614174000",
                "configuration_id": "123e4567-e89b-12d3-a456-426614174001",
                "quantity": 1,
            }
        }
    }


class AddToCartRequest(BaseModel):
    """Schema for adding items to cart."""

    vehicle_id: UUID = Field(
        ...,
        description="ID of the vehicle to add to cart",
    )
    configuration_id: Optional[UUID] = Field(
        None,
        description="ID of the vehicle configuration",
    )
    quantity: int = Field(
        default=1,
        description="Quantity of items to add",
        ge=1,
        le=10,
    )

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        """Validate quantity is within acceptable range."""
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        if v > 10:
            raise ValueError("Quantity cannot exceed 10")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "vehicle_id": "123e4567-e89b-12d3-a456-426614174000",
                "configuration_id": "123e4567-e89b-12d3-a456-426614174001",
                "quantity": 1,
            }
        }
    }


class UpdateCartItemRequest(BaseModel):
    """Schema for updating cart item quantity."""

    quantity: int = Field(
        ...,
        description="New quantity for the cart item",
        ge=0,
        le=10,
    )

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        """Validate quantity is within acceptable range."""
        if v < 0:
            raise ValueError("Quantity cannot be negative")
        if v > 10:
            raise ValueError("Quantity cannot exceed 10")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "quantity": 2,
            }
        }
    }


class ApplyPromoRequest(BaseModel):
    """Schema for applying promotional code to cart."""

    promo_code: str = Field(
        ...,
        description="Promotional code to apply",
        min_length=1,
        max_length=50,
    )

    @field_validator("promo_code")
    @classmethod
    def validate_promo_code(cls, v: str) -> str:
        """Validate and normalize promotional code."""
        if not v or not v.strip():
            raise ValueError("Promotional code cannot be empty or whitespace")
        
        cleaned = v.strip().upper()
        
        if not cleaned.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Promotional code can only contain letters, numbers, hyphens, and underscores"
            )
        
        return cleaned

    model_config = {
        "json_schema_extra": {
            "example": {
                "promo_code": "SUMMER2026",
            }
        }
    }


class CartItemResponse(BaseModel):
    """Schema for cart item in response."""

    id: UUID = Field(
        ...,
        description="Unique identifier for the cart item",
    )
    vehicle_id: UUID = Field(
        ...,
        description="ID of the vehicle",
    )
    configuration_id: Optional[UUID] = Field(
        None,
        description="ID of the vehicle configuration",
    )
    quantity: int = Field(
        ...,
        description="Quantity of items",
        ge=1,
    )
    unit_price: Decimal = Field(
        ...,
        description="Price per unit",
        ge=0,
        decimal_places=2,
    )
    total_price: Decimal = Field(
        ...,
        description="Total price for this item (unit_price * quantity)",
        ge=0,
        decimal_places=2,
    )
    vehicle_name: str = Field(
        ...,
        description="Display name of the vehicle",
        min_length=1,
        max_length=200,
    )
    vehicle_year: int = Field(
        ...,
        description="Year of the vehicle",
        ge=1900,
        le=2100,
    )
    vehicle_make: str = Field(
        ...,
        description="Make of the vehicle",
        min_length=1,
        max_length=100,
    )
    vehicle_model: str = Field(
        ...,
        description="Model of the vehicle",
        min_length=1,
        max_length=100,
    )
    reservation_expires_at: Optional[datetime] = Field(
        None,
        description="Timestamp when inventory reservation expires",
    )
    added_at: datetime = Field(
        ...,
        description="Timestamp when item was added to cart",
    )

    @model_validator(mode="after")
    def validate_total_price(self) -> "CartItemResponse":
        """Validate that total price matches unit price * quantity."""
        expected_total = self.unit_price * Decimal(str(self.quantity))
        
        if abs(self.total_price - expected_total) > Decimal("0.01"):
            raise ValueError(
                f"Total price mismatch: expected {expected_total}, got {self.total_price}"
            )
        
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174003",
                "vehicle_id": "123e4567-e89b-12d3-a456-426614174000",
                "configuration_id": "123e4567-e89b-12d3-a456-426614174001",
                "quantity": 1,
                "unit_price": "35000.00",
                "total_price": "35000.00",
                "vehicle_name": "2026 Tesla Model 3",
                "vehicle_year": 2026,
                "vehicle_make": "Tesla",
                "vehicle_model": "Model 3",
                "reservation_expires_at": "2026-01-07T23:00:00Z",
                "added_at": "2026-01-07T22:45:00Z",
            }
        }
    }


class CartSummary(BaseModel):
    """Schema for cart pricing summary."""

    subtotal: Decimal = Field(
        ...,
        description="Subtotal before discounts and taxes",
        ge=0,
        decimal_places=2,
    )
    discount_amount: Decimal = Field(
        default=Decimal("0.00"),
        description="Total discount amount applied",
        ge=0,
        decimal_places=2,
    )
    tax_amount: Decimal = Field(
        ...,
        description="Total tax amount",
        ge=0,
        decimal_places=2,
    )
    tax_rate: Decimal = Field(
        ...,
        description="Tax rate applied (as decimal, e.g., 0.08 for 8%)",
        ge=0,
        le=1,
        decimal_places=4,
    )
    total: Decimal = Field(
        ...,
        description="Final total including discounts and taxes",
        ge=0,
        decimal_places=2,
    )
    promo_code: Optional[str] = Field(
        None,
        description="Applied promotional code",
        max_length=50,
    )
    promo_discount: Optional[Decimal] = Field(
        None,
        description="Discount amount from promotional code",
        ge=0,
        decimal_places=2,
    )

    @model_validator(mode="after")
    def validate_pricing_calculation(self) -> "CartSummary":
        """Validate pricing calculations are correct."""
        taxable_amount = self.subtotal - self.discount_amount
        
        expected_tax = taxable_amount * self.tax_rate
        if abs(self.tax_amount - expected_tax) > Decimal("0.01"):
            raise ValueError(
                f"Tax amount mismatch: expected {expected_tax}, got {self.tax_amount}"
            )
        
        expected_total = taxable_amount + self.tax_amount
        if abs(self.total - expected_total) > Decimal("0.01"):
            raise ValueError(
                f"Total mismatch: expected {expected_total}, got {self.total}"
            )
        
        if self.promo_code and not self.promo_discount:
            raise ValueError("Promo code applied but no discount amount specified")
        
        if self.promo_discount and not self.promo_code:
            raise ValueError("Promo discount specified but no promo code applied")
        
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "subtotal": "35000.00",
                "discount_amount": "1000.00",
                "tax_amount": "2720.00",
                "tax_rate": "0.0800",
                "total": "36720.00",
                "promo_code": "SUMMER2026",
                "promo_discount": "1000.00",
            }
        }
    }


class CartResponse(BaseModel):
    """Schema for cart response."""

    id: UUID = Field(
        ...,
        description="Unique identifier for the cart",
    )
    user_id: Optional[UUID] = Field(
        None,
        description="ID of the authenticated user (null for anonymous)",
    )
    session_id: Optional[str] = Field(
        None,
        description="Session ID for anonymous users",
        max_length=255,
    )
    items: list[CartItemResponse] = Field(
        default_factory=list,
        description="List of items in the cart",
    )
    summary: CartSummary = Field(
        ...,
        description="Cart pricing summary",
    )
    item_count: int = Field(
        ...,
        description="Total number of items in cart",
        ge=0,
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when cart was created",
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp when cart was last updated",
    )
    expires_at: datetime = Field(
        ...,
        description="Timestamp when cart expires",
    )

    @model_validator(mode="after")
    def validate_cart_consistency(self) -> "CartResponse":
        """Validate cart data consistency."""
        if not self.user_id and not self.session_id:
            raise ValueError("Cart must have either user_id or session_id")
        
        if self.user_id and self.session_id:
            raise ValueError("Cart cannot have both user_id and session_id")
        
        calculated_item_count = sum(item.quantity for item in self.items)
        if self.item_count != calculated_item_count:
            raise ValueError(
                f"Item count mismatch: expected {calculated_item_count}, got {self.item_count}"
            )
        
        calculated_subtotal = sum(item.total_price for item in self.items)
        if abs(self.summary.subtotal - calculated_subtotal) > Decimal("0.01"):
            raise ValueError(
                f"Subtotal mismatch: expected {calculated_subtotal}, got {self.summary.subtotal}"
            )
        
        if self.expires_at <= self.created_at:
            raise ValueError("Cart expiration must be after creation time")
        
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174004",
                "user_id": "123e4567-e89b-12d3-a456-426614174005",
                "session_id": None,
                "items": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174003",
                        "vehicle_id": "123e4567-e89b-12d3-a456-426614174000",
                        "configuration_id": "123e4567-e89b-12d3-a456-426614174001",
                        "quantity": 1,
                        "unit_price": "35000.00",
                        "total_price": "35000.00",
                        "vehicle_name": "2026 Tesla Model 3",
                        "vehicle_year": 2026,
                        "vehicle_make": "Tesla",
                        "vehicle_model": "Model 3",
                        "reservation_expires_at": "2026-01-07T23:00:00Z",
                        "added_at": "2026-01-07T22:45:00Z",
                    }
                ],
                "summary": {
                    "subtotal": "35000.00",
                    "discount_amount": "1000.00",
                    "tax_amount": "2720.00",
                    "tax_rate": "0.0800",
                    "total": "36720.00",
                    "promo_code": "SUMMER2026",
                    "promo_discount": "1000.00",
                },
                "item_count": 1,
                "created_at": "2026-01-07T22:45:00Z",
                "updated_at": "2026-01-07T22:45:00Z",
                "expires_at": "2026-02-06T22:45:00Z",
            }
        }
    }