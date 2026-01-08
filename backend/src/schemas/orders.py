"""
Order management Pydantic schemas for API request/response validation.

This module defines comprehensive schemas for order lifecycle management including
order creation, updates, status changes, and nested data structures for customer
information, delivery addresses, and trade-in details.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
)

from src.services.orders.enums import (
    OrderStatus,
    PaymentStatus,
    FulfillmentStatus,
)


class CustomerInfoRequest(BaseModel):
    """Customer information for order placement."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        str_min_length=1,
        validate_assignment=True,
    )

    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Customer first name",
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Customer last name",
    )
    email: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Customer email address",
    )
    phone: str = Field(
        ...,
        min_length=10,
        max_length=20,
        description="Customer phone number",
    )
    driver_license_number: Optional[str] = Field(
        None,
        max_length=50,
        description="Driver license number",
    )

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        """Validate email format."""
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("phone")
    @classmethod
    def validate_phone_format(cls, v: str) -> str:
        """Validate and normalize phone number."""
        digits = "".join(filter(str.isdigit, v))
        if len(digits) < 10:
            raise ValueError("Phone number must contain at least 10 digits")
        return digits


class DeliveryAddressRequest(BaseModel):
    """Delivery address information."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        str_min_length=1,
        validate_assignment=True,
    )

    street_address: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Street address",
    )
    city: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="City",
    )
    state: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="State code (2 letters)",
    )
    postal_code: str = Field(
        ...,
        min_length=5,
        max_length=10,
        description="Postal/ZIP code",
    )
    country: str = Field(
        default="US",
        min_length=2,
        max_length=2,
        description="Country code (2 letters)",
    )
    delivery_instructions: Optional[str] = Field(
        None,
        max_length=500,
        description="Special delivery instructions",
    )

    @field_validator("state")
    @classmethod
    def validate_state_code(cls, v: str) -> str:
        """Validate state code format."""
        return v.upper()

    @field_validator("country")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        """Validate country code format."""
        return v.upper()

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, v: str) -> str:
        """Validate postal code format."""
        digits = "".join(filter(str.isdigit, v))
        if len(digits) < 5:
            raise ValueError("Postal code must contain at least 5 digits")
        return v


class TradeInInfoRequest(BaseModel):
    """Trade-in vehicle information."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    vehicle_year: int = Field(
        ...,
        ge=1900,
        le=2100,
        description="Trade-in vehicle year",
    )
    vehicle_make: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Trade-in vehicle make",
    )
    vehicle_model: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Trade-in vehicle model",
    )
    vehicle_vin: str = Field(
        ...,
        min_length=17,
        max_length=17,
        description="Trade-in vehicle VIN",
    )
    mileage: int = Field(
        ...,
        ge=0,
        le=1000000,
        description="Trade-in vehicle mileage",
    )
    condition: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Trade-in vehicle condition",
    )
    estimated_value: Decimal = Field(
        ...,
        ge=0,
        decimal_places=2,
        description="Estimated trade-in value",
    )
    payoff_amount: Optional[Decimal] = Field(
        None,
        ge=0,
        decimal_places=2,
        description="Outstanding loan payoff amount",
    )

    @field_validator("vehicle_vin")
    @classmethod
    def validate_vin_format(cls, v: str) -> str:
        """Validate VIN format."""
        vin = v.upper()
        if not vin.isalnum():
            raise ValueError("VIN must contain only alphanumeric characters")
        if any(char in vin for char in "IOQ"):
            raise ValueError("VIN cannot contain I, O, or Q")
        return vin


class OrderItemRequest(BaseModel):
    """Order item details."""

    model_config = ConfigDict(validate_assignment=True)

    vehicle_id: UUID = Field(
        ...,
        description="Vehicle ID",
    )
    configuration_id: Optional[UUID] = Field(
        None,
        description="Vehicle configuration ID",
    )
    quantity: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Quantity",
    )
    unit_price: Decimal = Field(
        ...,
        ge=0,
        decimal_places=2,
        description="Unit price",
    )
    discount_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        decimal_places=2,
        description="Discount amount",
    )
    tax_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        decimal_places=2,
        description="Tax amount",
    )

    @model_validator(mode="after")
    def validate_pricing(self) -> "OrderItemRequest":
        """Validate pricing calculations."""
        subtotal = self.unit_price * self.quantity
        if self.discount_amount > subtotal:
            raise ValueError("Discount cannot exceed subtotal")
        return self


class OrderCreateRequest(BaseModel):
    """Request schema for creating a new order."""

    model_config = ConfigDict(validate_assignment=True)

    customer_info: CustomerInfoRequest = Field(
        ...,
        description="Customer information",
    )
    delivery_address: DeliveryAddressRequest = Field(
        ...,
        description="Delivery address",
    )
    items: list[OrderItemRequest] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Order items",
    )
    payment_method: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Payment method",
    )
    trade_in_info: Optional[TradeInInfoRequest] = Field(
        None,
        description="Trade-in vehicle information",
    )
    promotional_code: Optional[str] = Field(
        None,
        max_length=50,
        description="Promotional code",
    )
    notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Order notes",
    )

    @model_validator(mode="after")
    def validate_order_totals(self) -> "OrderCreateRequest":
        """Validate order total calculations."""
        if not self.items:
            raise ValueError("Order must contain at least one item")

        total_amount = sum(
            (item.unit_price * item.quantity - item.discount_amount + item.tax_amount)
            for item in self.items
        )

        if total_amount <= 0:
            raise ValueError("Order total must be greater than zero")

        return self


class OrderUpdateRequest(BaseModel):
    """Request schema for updating an existing order."""

    model_config = ConfigDict(validate_assignment=True)

    delivery_address: Optional[DeliveryAddressRequest] = Field(
        None,
        description="Updated delivery address",
    )
    notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Updated order notes",
    )
    estimated_delivery_date: Optional[datetime] = Field(
        None,
        description="Updated estimated delivery date",
    )

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "OrderUpdateRequest":
        """Ensure at least one field is provided for update."""
        if not any(
            [
                self.delivery_address,
                self.notes,
                self.estimated_delivery_date,
            ]
        ):
            raise ValueError("At least one field must be provided for update")
        return self


class OrderStatusUpdate(BaseModel):
    """Request schema for updating order status."""

    model_config = ConfigDict(validate_assignment=True)

    order_status: Optional[OrderStatus] = Field(
        None,
        description="New order status",
    )
    payment_status: Optional[PaymentStatus] = Field(
        None,
        description="New payment status",
    )
    fulfillment_status: Optional[FulfillmentStatus] = Field(
        None,
        description="New fulfillment status",
    )
    status_notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Status change notes",
    )

    @model_validator(mode="after")
    def validate_status_update(self) -> "OrderStatusUpdate":
        """Ensure at least one status is provided."""
        if not any(
            [
                self.order_status,
                self.payment_status,
                self.fulfillment_status,
            ]
        ):
            raise ValueError("At least one status must be provided for update")
        return self


class CustomerInfoResponse(BaseModel):
    """Customer information response."""

    model_config = ConfigDict(from_attributes=True)

    first_name: str
    last_name: str
    email: str
    phone: str
    driver_license_number: Optional[str] = None


class DeliveryAddressResponse(BaseModel):
    """Delivery address response."""

    model_config = ConfigDict(from_attributes=True)

    street_address: str
    city: str
    state: str
    postal_code: str
    country: str
    delivery_instructions: Optional[str] = None


class TradeInInfoResponse(BaseModel):
    """Trade-in information response."""

    model_config = ConfigDict(from_attributes=True)

    vehicle_year: int
    vehicle_make: str
    vehicle_model: str
    vehicle_vin: str
    mileage: int
    condition: str
    estimated_value: Decimal
    payoff_amount: Optional[Decimal] = None


class OrderItemResponse(BaseModel):
    """Order item response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vehicle_id: UUID
    configuration_id: Optional[UUID] = None
    quantity: int
    unit_price: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal


class OrderResponse(BaseModel):
    """Complete order response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_number: str
    user_id: Optional[UUID] = None
    dealer_id: Optional[UUID] = None
    customer_info: CustomerInfoResponse
    delivery_address: DeliveryAddressResponse
    items: list[OrderItemResponse]
    order_status: OrderStatus
    payment_status: PaymentStatus
    fulfillment_status: FulfillmentStatus
    payment_method: str
    trade_in_info: Optional[TradeInInfoResponse] = None
    promotional_code: Optional[str] = None
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    notes: Optional[str] = None
    estimated_delivery_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None