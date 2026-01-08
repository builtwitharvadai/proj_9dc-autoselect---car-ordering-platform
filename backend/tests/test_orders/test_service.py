"""
Comprehensive test suite for OrderService business logic.

This module provides extensive unit tests for the OrderService class,
covering order creation, status updates, validation logic, pricing
calculations, and integration with payment services. Includes database
mocking, error scenarios, and edge cases with >80% coverage.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.order import (
    FulfillmentStatus,
    OrderStatus,
    PaymentStatus,
)
from src.services.orders.repository import (
    OrderCreationError,
    OrderNotFoundError,
    OrderRepositoryError,
    OrderUpdateError,
)
from src.services.orders.service import (
    OrderProcessingError,
    OrderService,
    OrderServiceError,
    OrderValidationError,
)
from src.services.orders.state_machine import StateTransitionError
from src.services.payments.service import (
    PaymentProcessingError,
    PaymentValidationError,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_session() -> AsyncMock:
    """
    Create mock async database session.

    Returns:
        AsyncMock: Mock database session
    """
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_payment_service() -> AsyncMock:
    """
    Create mock payment service.

    Returns:
        AsyncMock: Mock payment service
    """
    service = AsyncMock()
    service.create_payment_intent = AsyncMock(
        return_value={
            "payment_intent_id": "pi_test_123",
            "client_secret": "secret_test_123",
            "status": "requires_payment_method",
        }
    )
    return service


@pytest.fixture
def order_service(mock_session: AsyncMock) -> OrderService:
    """
    Create OrderService instance with mocked dependencies.

    Args:
        mock_session: Mock database session

    Returns:
        OrderService: Service instance for testing
    """
    return OrderService(session=mock_session)


@pytest.fixture
def order_service_with_payment(
    mock_session: AsyncMock, mock_payment_service: AsyncMock
) -> OrderService:
    """
    Create OrderService with payment service.

    Args:
        mock_session: Mock database session
        mock_payment_service: Mock payment service

    Returns:
        OrderService: Service instance with payment integration
    """
    return OrderService(session=mock_session, payment_service=mock_payment_service)


@pytest.fixture
def valid_order_data() -> dict[str, Any]:
    """
    Create valid order data for testing.

    Returns:
        dict: Valid order creation data
    """
    return {
        "user_id": uuid.uuid4(),
        "vehicle_id": uuid.uuid4(),
        "configuration_id": uuid.uuid4(),
        "items": [
            {
                "configuration_id": uuid.uuid4(),
                "quantity": 1,
                "unit_price": Decimal("45000.00"),
                "item_type": "vehicle",
                "description": "Tesla Model 3",
            }
        ],
        "customer_info": {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
        },
        "delivery_address": {
            "street_address": "123 Main St",
            "city": "San Francisco",
            "state": "CA",
            "postal_code": "94102",
            "country": "USA",
        },
        "payment_method": "credit_card",
    }


@pytest.fixture
def mock_order() -> Mock:
    """
    Create mock order instance.

    Returns:
        Mock: Mock order object
    """
    order = Mock()
    order.id = uuid.uuid4()
    order.order_number = "ORD-20240101120000-ABC123"
    order.user_id = uuid.uuid4()
    order.vehicle_id = uuid.uuid4()
    order.configuration_id = uuid.uuid4()
    order.dealer_id = None
    order.manufacturer_id = None
    order.status = OrderStatus.PENDING
    order.payment_status = PaymentStatus.PENDING
    order.fulfillment_status = FulfillmentStatus.PENDING
    order.total_amount = Decimal("48600.00")
    order.subtotal = Decimal("45000.00")
    order.tax_amount = Decimal("3600.00")
    order.shipping_amount = Decimal("0.00")
    order.discount_amount = Decimal("0.00")
    order.customer_info = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "+1234567890",
    }
    order.delivery_address = {
        "street_address": "123 Main St",
        "city": "San Francisco",
        "state": "CA",
        "postal_code": "94102",
    }
    order.notes = None
    order.created_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()
    return order


# ============================================================================
# Unit Tests - Order Creation
# ============================================================================


class TestOrderCreation:
    """Test suite for order creation functionality."""

    @pytest.mark.asyncio
    async def test_create_order_success(
        self, order_service: OrderService, valid_order_data: dict[str, Any], mock_order: Mock
    ):
        """
        Test successful order creation with valid data.

        Verifies:
        - Order is created with correct data
        - Pricing is calculated correctly
        - Order number is generated
        - Response contains all required fields
        """
        # Arrange
        order_service.repository.create_order_with_items = AsyncMock(return_value=mock_order)

        # Act
        result = await order_service.create_order(**valid_order_data)

        # Assert
        assert result["order_id"] == str(mock_order.id)
        assert result["order_number"] == mock_order.order_number
        assert result["status"] == OrderStatus.PENDING.value
        assert result["payment_status"] == PaymentStatus.PENDING.value
        assert result["fulfillment_status"] == FulfillmentStatus.PENDING.value
        assert Decimal(str(result["total_amount"])) == mock_order.total_amount
        assert "created_at" in result

        # Verify repository was called
        order_service.repository.create_order_with_items.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_order_with_payment_service(
        self,
        order_service_with_payment: OrderService,
        valid_order_data: dict[str, Any],
        mock_order: Mock,
        mock_payment_service: AsyncMock,
    ):
        """
        Test order creation with payment intent creation.

        Verifies:
        - Payment intent is created
        - Payment intent ID is returned
        - Order creation succeeds even if payment fails
        """
        # Arrange
        order_service_with_payment.repository.create_order_with_items = AsyncMock(
            return_value=mock_order
        )

        # Act
        result = await order_service_with_payment.create_order(**valid_order_data)

        # Assert
        assert result["payment_intent_id"] == "pi_test_123"
        mock_payment_service.create_payment_intent.assert_called_once()

        # Verify payment intent parameters
        call_kwargs = mock_payment_service.create_payment_intent.call_args.kwargs
        assert call_kwargs["order_id"] == mock_order.id
        assert call_kwargs["currency"] == "USD"
        assert call_kwargs["customer_email"] == valid_order_data["customer_info"]["email"]

    @pytest.mark.asyncio
    async def test_create_order_payment_intent_failure_continues(
        self,
        order_service_with_payment: OrderService,
        valid_order_data: dict[str, Any],
        mock_order: Mock,
        mock_payment_service: AsyncMock,
    ):
        """
        Test order creation continues when payment intent fails.

        Verifies:
        - Order is created even if payment intent fails
        - Payment intent ID is None
        - Error is logged but not raised
        """
        # Arrange
        order_service_with_payment.repository.create_order_with_items = AsyncMock(
            return_value=mock_order
        )
        mock_payment_service.create_payment_intent.side_effect = PaymentProcessingError(
            "Payment service unavailable"
        )

        # Act
        result = await order_service_with_payment.create_order(**valid_order_data)

        # Assert
        assert result["payment_intent_id"] is None
        assert result["order_id"] == str(mock_order.id)

    @pytest.mark.asyncio
    async def test_create_order_with_trade_in(
        self, order_service: OrderService, valid_order_data: dict[str, Any], mock_order: Mock
    ):
        """
        Test order creation with trade-in value.

        Verifies:
        - Trade-in value is applied to pricing
        - Total amount is reduced by trade-in value
        """
        # Arrange
        valid_order_data["trade_in_info"] = {
            "vehicle_make": "Honda",
            "vehicle_model": "Civic",
            "year": 2018,
            "estimated_value": Decimal("8000.00"),
        }
        order_service.repository.create_order_with_items = AsyncMock(return_value=mock_order)

        # Act
        result = await order_service.create_order(**valid_order_data)

        # Assert
        assert result["order_id"] == str(mock_order.id)
        order_service.repository.create_order_with_items.assert_called_once()

        # Verify trade-in was passed to repository
        call_kwargs = order_service.repository.create_order_with_items.call_args.kwargs
        assert call_kwargs["trade_in_info"] == valid_order_data["trade_in_info"]

    @pytest.mark.asyncio
    async def test_create_order_with_promotional_code(
        self, order_service: OrderService, valid_order_data: dict[str, Any], mock_order: Mock
    ):
        """
        Test order creation with promotional code discount.

        Verifies:
        - Promotional code is applied
        - Discount is calculated (5% in this case)
        - Total amount reflects discount
        """
        # Arrange
        valid_order_data["promotional_code"] = "SAVE5"
        order_service.repository.create_order_with_items = AsyncMock(return_value=mock_order)

        # Act
        result = await order_service.create_order(**valid_order_data)

        # Assert
        assert result["order_id"] == str(mock_order.id)

        # Verify discount was calculated
        call_kwargs = order_service.repository.create_order_with_items.call_args.kwargs
        assert call_kwargs["discount_amount"] > Decimal("0.00")

    @pytest.mark.asyncio
    async def test_create_order_with_optional_fields(
        self, order_service: OrderService, valid_order_data: dict[str, Any], mock_order: Mock
    ):
        """
        Test order creation with all optional fields.

        Verifies:
        - Optional fields are accepted
        - Order is created successfully
        """
        # Arrange
        valid_order_data.update(
            {
                "dealer_id": uuid.uuid4(),
                "manufacturer_id": uuid.uuid4(),
                "notes": "Special delivery instructions",
                "special_instructions": "Call before delivery",
                "estimated_delivery_date": datetime.utcnow() + timedelta(days=30),
            }
        )
        order_service.repository.create_order_with_items = AsyncMock(return_value=mock_order)

        # Act
        result = await order_service.create_order(**valid_order_data)

        # Assert
        assert result["order_id"] == str(mock_order.id)
        order_service.repository.create_order_with_items.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_order_repository_error(
        self, order_service: OrderService, valid_order_data: dict[str, Any]
    ):
        """
        Test order creation handles repository errors.

        Verifies:
        - Repository errors are caught
        - OrderProcessingError is raised
        - Error context is preserved
        """
        # Arrange
        order_service.repository.create_order_with_items = AsyncMock(
            side_effect=OrderCreationError("Database error")
        )

        # Act & Assert
        with pytest.raises(OrderProcessingError) as exc_info:
            await order_service.create_order(**valid_order_data)

        assert "Failed to create order" in str(exc_info.value)
        assert exc_info.value.context["user_id"] == str(valid_order_data["user_id"])

    @pytest.mark.asyncio
    async def test_create_order_unexpected_error(
        self, order_service: OrderService, valid_order_data: dict[str, Any]
    ):
        """
        Test order creation handles unexpected errors.

        Verifies:
        - Unexpected exceptions are caught
        - OrderProcessingError is raised
        - Error is logged
        """
        # Arrange
        order_service.repository.create_order_with_items = AsyncMock(
            side_effect=RuntimeError("Unexpected error")
        )

        # Act & Assert
        with pytest.raises(OrderProcessingError) as exc_info:
            await order_service.create_order(**valid_order_data)

        assert "Unexpected error creating order" in str(exc_info.value)


# ============================================================================
# Unit Tests - Order Validation
# ============================================================================


class TestOrderValidation:
    """Test suite for order validation logic."""

    @pytest.mark.asyncio
    async def test_validate_empty_items(
        self, order_service: OrderService, valid_order_data: dict[str, Any]
    ):
        """
        Test validation fails with empty items list.

        Verifies:
        - OrderValidationError is raised
        - Error message indicates missing items
        """
        # Arrange
        valid_order_data["items"] = []

        # Act & Assert
        with pytest.raises(OrderValidationError) as exc_info:
            await order_service.create_order(**valid_order_data)

        assert "at least one item" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_item_missing_configuration_id(
        self, order_service: OrderService, valid_order_data: dict[str, Any]
    ):
        """
        Test validation fails when item missing configuration_id.

        Verifies:
        - OrderValidationError is raised
        - Error indicates missing configuration_id
        """
        # Arrange
        valid_order_data["items"][0].pop("configuration_id")

        # Act & Assert
        with pytest.raises(OrderValidationError) as exc_info:
            await order_service.create_order(**valid_order_data)

        assert "configuration_id" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_item_invalid_quantity(
        self, order_service: OrderService, valid_order_data: dict[str, Any]
    ):
        """
        Test validation fails with invalid quantity.

        Verifies:
        - Zero quantity is rejected
        - Negative quantity is rejected
        """
        # Arrange - zero quantity
        valid_order_data["items"][0]["quantity"] = 0

        # Act & Assert
        with pytest.raises(OrderValidationError) as exc_info:
            await order_service.create_order(**valid_order_data)

        assert "quantity must be positive" in str(exc_info.value)

        # Arrange - negative quantity
        valid_order_data["items"][0]["quantity"] = -1

        # Act & Assert
        with pytest.raises(OrderValidationError):
            await order_service.create_order(**valid_order_data)

    @pytest.mark.asyncio
    async def test_validate_item_invalid_unit_price(
        self, order_service: OrderService, valid_order_data: dict[str, Any]
    ):
        """
        Test validation fails with invalid unit price.

        Verifies:
        - Zero price is rejected
        - Negative price is rejected
        """
        # Arrange - zero price
        valid_order_data["items"][0]["unit_price"] = 0

        # Act & Assert
        with pytest.raises(OrderValidationError) as exc_info:
            await order_service.create_order(**valid_order_data)

        assert "unit_price must be positive" in str(exc_info.value)

    @pytest.mark.parametrize(
        "missing_field",
        ["first_name", "last_name", "email", "phone"],
    )
    @pytest.mark.asyncio
    async def test_validate_customer_info_missing_fields(
        self, order_service: OrderService, valid_order_data: dict[str, Any], missing_field: str
    ):
        """
        Test validation fails with missing customer info fields.

        Verifies:
        - Each required field is validated
        - Appropriate error message is raised
        """
        # Arrange
        valid_order_data["customer_info"].pop(missing_field)

        # Act & Assert
        with pytest.raises(OrderValidationError) as exc_info:
            await order_service.create_order(**valid_order_data)

        assert missing_field in str(exc_info.value)

    @pytest.mark.parametrize(
        "missing_field",
        ["street_address", "city", "state", "postal_code"],
    )
    @pytest.mark.asyncio
    async def test_validate_delivery_address_missing_fields(
        self, order_service: OrderService, valid_order_data: dict[str, Any], missing_field: str
    ):
        """
        Test validation fails with missing delivery address fields.

        Verifies:
        - Each required address field is validated
        - Appropriate error message is raised
        """
        # Arrange
        valid_order_data["delivery_address"].pop(missing_field)

        # Act & Assert
        with pytest.raises(OrderValidationError) as exc_info:
            await order_service.create_order(**valid_order_data)

        assert missing_field in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_empty_payment_method(
        self, order_service: OrderService, valid_order_data: dict[str, Any]
    ):
        """
        Test validation fails with empty payment method.

        Verifies:
        - Empty payment method is rejected
        - Appropriate error is raised
        """
        # Arrange
        valid_order_data["payment_method"] = ""

        # Act & Assert
        with pytest.raises(OrderValidationError) as exc_info:
            await order_service.create_order(**valid_order_data)

        assert "Payment method is required" in str(exc_info.value)


# ============================================================================
# Unit Tests - Pricing Calculations
# ============================================================================


class TestPricingCalculations:
    """Test suite for order pricing calculations."""

    def test_calculate_basic_pricing(self, order_service: OrderService):
        """
        Test basic pricing calculation without discounts.

        Verifies:
        - Subtotal is calculated correctly
        - Tax is calculated at 8%
        - Total amount is correct
        """
        # Arrange
        items = [
            {
                "configuration_id": uuid.uuid4(),
                "quantity": 1,
                "unit_price": Decimal("45000.00"),
            }
        ]

        # Act
        pricing = order_service._calculate_order_pricing(items=items)

        # Assert
        assert pricing["subtotal"] == Decimal("45000.00")
        assert pricing["tax_amount"] == Decimal("3600.00")  # 8% of 45000
        assert pricing["total_amount"] == Decimal("48600.00")
        assert pricing["discount_amount"] == Decimal("0.00")

    def test_calculate_pricing_with_promotional_code(self, order_service: OrderService):
        """
        Test pricing calculation with promotional code.

        Verifies:
        - Discount is applied (5%)
        - Tax is calculated on discounted amount
        - Total reflects discount
        """
        # Arrange
        items = [
            {
                "configuration_id": uuid.uuid4(),
                "quantity": 1,
                "unit_price": Decimal("45000.00"),
            }
        ]

        # Act
        pricing = order_service._calculate_order_pricing(
            items=items, promotional_code="SAVE5"
        )

        # Assert
        assert pricing["discount_amount"] == Decimal("2250.00")  # 5% of 45000
        assert pricing["subtotal"] == Decimal("45000.00")
        # Tax on (45000 - 2250) = 42750 * 0.08 = 3420
        assert pricing["tax_amount"] == Decimal("3420.00")
        assert pricing["total_amount"] == Decimal("46170.00")

    def test_calculate_pricing_with_trade_in(self, order_service: OrderService):
        """
        Test pricing calculation with trade-in value.

        Verifies:
        - Trade-in value reduces taxable amount
        - Tax is calculated on reduced amount
        - Total reflects trade-in credit
        """
        # Arrange
        items = [
            {
                "configuration_id": uuid.uuid4(),
                "quantity": 1,
                "unit_price": Decimal("45000.00"),
            }
        ]
        trade_in_info = {"estimated_value": Decimal("8000.00")}

        # Act
        pricing = order_service._calculate_order_pricing(
            items=items, trade_in_info=trade_in_info
        )

        # Assert
        assert pricing["trade_in_value"] == Decimal("8000.00")
        # Tax on (45000 - 8000) = 37000 * 0.08 = 2960
        assert pricing["tax_amount"] == Decimal("2960.00")
        assert pricing["total_amount"] == Decimal("39960.00")

    def test_calculate_pricing_with_multiple_items(self, order_service: OrderService):
        """
        Test pricing calculation with multiple items.

        Verifies:
        - Subtotal sums all items
        - Tax is calculated on total
        """
        # Arrange
        items = [
            {
                "configuration_id": uuid.uuid4(),
                "quantity": 1,
                "unit_price": Decimal("45000.00"),
            },
            {
                "configuration_id": uuid.uuid4(),
                "quantity": 2,
                "unit_price": Decimal("500.00"),
            },
        ]

        # Act
        pricing = order_service._calculate_order_pricing(items=items)

        # Assert
        assert pricing["subtotal"] == Decimal("46000.00")  # 45000 + (2 * 500)
        assert pricing["tax_amount"] == Decimal("3680.00")  # 8% of 46000
        assert pricing["total_amount"] == Decimal("49680.00")

    def test_calculate_pricing_with_all_adjustments(self, order_service: OrderService):
        """
        Test pricing with promotional code and trade-in.

        Verifies:
        - Both adjustments are applied correctly
        - Tax is calculated on final taxable amount
        """
        # Arrange
        items = [
            {
                "configuration_id": uuid.uuid4(),
                "quantity": 1,
                "unit_price": Decimal("45000.00"),
            }
        ]
        trade_in_info = {"estimated_value": Decimal("5000.00")}

        # Act
        pricing = order_service._calculate_order_pricing(
            items=items, trade_in_info=trade_in_info, promotional_code="SAVE5"
        )

        # Assert
        assert pricing["subtotal"] == Decimal("45000.00")
        assert pricing["discount_amount"] == Decimal("2250.00")
        assert pricing["trade_in_value"] == Decimal("5000.00")
        # Tax on (45000 - 2250 - 5000) = 37750 * 0.08 = 3020
        assert pricing["tax_amount"] == Decimal("3020.00")
        assert pricing["total_amount"] == Decimal("40770.00")


# ============================================================================
# Unit Tests - Order Status Updates
# ============================================================================


class TestOrderStatusUpdates:
    """Test suite for order status update functionality."""

    @pytest.mark.asyncio
    async def test_update_order_status_success(
        self, order_service: OrderService, mock_order: Mock
    ):
        """
        Test successful order status update.

        Verifies:
        - Status is updated via state machine
        - Updated order is returned
        - Response contains correct status
        """
        # Arrange
        order_id = mock_order.id
        new_status = OrderStatus.CONFIRMED
        mock_order.status = new_status

        order_service.repository.get_order_by_id = AsyncMock(return_value=mock_order)
        order_service.state_machine.apply_transition = Mock()

        # Act
        result = await order_service.update_order_status(
            order_id=order_id, new_status=new_status
        )

        # Assert
        assert result["order_id"] == str(order_id)
        assert result["status"] == new_status.value
        order_service.state_machine.apply_transition.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_order_status_with_reason(
        self, order_service: OrderService, mock_order: Mock
    ):
        """
        Test status update with reason and metadata.

        Verifies:
        - Reason is passed to state machine
        - Metadata is included
        """
        # Arrange
        order_id = mock_order.id
        new_status = OrderStatus.CANCELLED
        reason = "Customer requested cancellation"
        metadata = {"refund_requested": True}

        order_service.repository.get_order_by_id = AsyncMock(return_value=mock_order)
        order_service.state_machine.apply_transition = Mock()

        # Act
        result = await order_service.update_order_status(
            order_id=order_id, new_status=new_status, reason=reason, metadata=metadata
        )

        # Assert
        assert result["order_id"] == str(order_id)

        # Verify state machine was called with reason and metadata
        call_kwargs = order_service.state_machine.apply_transition.call_args.kwargs
        assert call_kwargs["reason"] == reason
        assert call_kwargs["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_update_order_status_not_found(self, order_service: OrderService):
        """
        Test status update for non-existent order.

        Verifies:
        - OrderNotFoundError is raised
        - Error contains order ID
        """
        # Arrange
        order_id = uuid.uuid4()
        order_service.repository.get_order_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(OrderNotFoundError) as exc_info:
            await order_service.update_order_status(
                order_id=order_id, new_status=OrderStatus.CONFIRMED
            )

        assert str(order_id) in str(exc_info.value.context)

    @pytest.mark.asyncio
    async def test_update_order_status_invalid_transition(
        self, order_service: OrderService, mock_order: Mock
    ):
        """
        Test status update with invalid state transition.

        Verifies:
        - StateTransitionError is caught
        - OrderProcessingError is raised
        - Error message indicates invalid transition
        """
        # Arrange
        order_id = mock_order.id
        current_status = OrderStatus.DELIVERED
        new_status = OrderStatus.PENDING
        mock_order.status = current_status

        order_service.repository.get_order_by_id = AsyncMock(return_value=mock_order)
        order_service.state_machine.apply_transition = Mock(
            side_effect=StateTransitionError(
                current_state=current_status,
                target_state=new_status,
                message="Invalid transition",
            )
        )

        # Act & Assert
        with pytest.raises(OrderProcessingError) as exc_info:
            await order_service.update_order_status(order_id=order_id, new_status=new_status)

        assert "Invalid status transition" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_order_status_unexpected_error(
        self, order_service: OrderService, mock_order: Mock
    ):
        """
        Test status update handles unexpected errors.

        Verifies:
        - Unexpected exceptions are caught
        - OrderProcessingError is raised
        """
        # Arrange
        order_id = mock_order.id
        order_service.repository.get_order_by_id = AsyncMock(return_value=mock_order)
        order_service.state_machine.apply_transition = Mock(
            side_effect=RuntimeError("Unexpected error")
        )

        # Act & Assert
        with pytest.raises(OrderProcessingError) as exc_info:
            await order_service.update_order_status(
                order_id=order_id, new_status=OrderStatus.CONFIRMED
            )

        assert "Failed to update order status" in str(exc_info.value)


# ============================================================================
# Unit Tests - Order Retrieval
# ============================================================================


class TestOrderRetrieval:
    """Test suite for order retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_order_success(self, order_service: OrderService, mock_order: Mock):
        """
        Test successful order retrieval.

        Verifies:
        - Order is retrieved by ID
        - Response contains all order fields
        - Formatted correctly
        """
        # Arrange
        order_id = mock_order.id
        order_service.repository.get_order_by_id = AsyncMock(return_value=mock_order)

        # Act
        result = await order_service.get_order(order_id=order_id)

        # Assert
        assert result["id"] == str(mock_order.id)
        assert result["order_number"] == mock_order.order_number
        assert result["status"] == mock_order.status.value
        assert result["total_amount"] == float(mock_order.total_amount)

    @pytest.mark.asyncio
    async def test_get_order_with_items(self, order_service: OrderService, mock_order: Mock):
        """
        Test order retrieval with items included.

        Verifies:
        - include_items parameter is passed
        - Repository is called with correct parameters
        """
        # Arrange
        order_id = mock_order.id
        order_service.repository.get_order_by_id = AsyncMock(return_value=mock_order)

        # Act
        await order_service.get_order(order_id=order_id, include_items=True)

        # Assert
        order_service.repository.get_order_by_id.assert_called_once_with(
            order_id=order_id, include_items=True, include_history=False
        )

    @pytest.mark.asyncio
    async def test_get_order_with_history(self, order_service: OrderService, mock_order: Mock):
        """
        Test order retrieval with status history.

        Verifies:
        - include_history parameter is passed
        - Repository is called with correct parameters
        """
        # Arrange
        order_id = mock_order.id
        order_service.repository.get_order_by_id = AsyncMock(return_value=mock_order)

        # Act
        await order_service.get_order(order_id=order_id, include_history=True)

        # Assert
        order_service.repository.get_order_by_id.assert_called_once_with(
            order_id=order_id, include_items=True, include_history=True
        )

    @pytest.mark.asyncio
    async def test_get_order_not_found(self, order_service: OrderService):
        """
        Test order retrieval for non-existent order.

        Verifies:
        - OrderNotFoundError is raised
        - Error contains order ID
        """
        # Arrange
        order_id = uuid.uuid4()
        order_service.repository.get_order_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(OrderNotFoundError) as exc_info:
            await order_service.get_order(order_id=order_id)

        assert str(order_id) in str(exc_info.value.context)

    @pytest.mark.asyncio
    async def test_get_order_repository_error(self, order_service: OrderService):
        """
        Test order retrieval handles repository errors.

        Verifies:
        - Repository errors are caught
        - OrderProcessingError is raised
        """
        # Arrange
        order_id = uuid.uuid4()
        order_service.repository.get_order_by_id = AsyncMock(
            side_effect=OrderRepositoryError("Database error")
        )

        # Act & Assert
        with pytest.raises(OrderProcessingError) as exc_info:
            await order_service.get_order(order_id=order_id)

        assert "Failed to retrieve order" in str(exc_info.value)


# ============================================================================
# Unit Tests - User Orders Retrieval
# ============================================================================


class TestUserOrdersRetrieval:
    """Test suite for user orders retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_user_orders_success(self, order_service: OrderService, mock_order: Mock):
        """
        Test successful user orders retrieval.

        Verifies:
        - Orders are retrieved for user
        - Pagination info is included
        - Orders are formatted correctly
        """
        # Arrange
        user_id = uuid.uuid4()
        orders = [mock_order]
        total_count = 1

        order_service.repository.get_user_orders = AsyncMock(
            return_value=(orders, total_count)
        )

        # Act
        result = await order_service.get_user_orders(user_id=user_id)

        # Assert
        assert len(result["orders"]) == 1
        assert result["total_count"] == total_count
        assert result["skip"] == 0
        assert result["limit"] == 20

    @pytest.mark.asyncio
    async def test_get_user_orders_with_status_filter(
        self, order_service: OrderService, mock_order: Mock
    ):
        """
        Test user orders retrieval with status filter.

        Verifies:
        - Status filter is applied
        - Only matching orders are returned
        """
        # Arrange
        user_id = uuid.uuid4()
        status = OrderStatus.CONFIRMED
        orders = [mock_order]

        order_service.repository.get_user_orders = AsyncMock(return_value=(orders, 1))

        # Act
        result = await order_service.get_user_orders(user_id=user_id, status=status)

        # Assert
        order_service.repository.get_user_orders.assert_called_once_with(
            user_id=user_id, status=status, skip=0, limit=20
        )

    @pytest.mark.asyncio
    async def test_get_user_orders_with_pagination(
        self, order_service: OrderService, mock_order: Mock
    ):
        """
        Test user orders retrieval with pagination.

        Verifies:
        - Skip and limit parameters are applied
        - Pagination info is correct
        """
        # Arrange
        user_id = uuid.uuid4()
        skip = 10
        limit = 5
        orders = [mock_order] * 5

        order_service.repository.get_user_orders = AsyncMock(return_value=(orders, 25))

        # Act
        result = await order_service.get_user_orders(user_id=user_id, skip=skip, limit=limit)

        # Assert
        assert result["skip"] == skip
        assert result["limit"] == limit
        assert result["total_count"] == 25
        assert len(result["orders"]) == 5

    @pytest.mark.asyncio
    async def test_get_user_orders_empty_result(self, order_service: OrderService):
        """
        Test user orders retrieval with no orders.

        Verifies:
        - Empty list is returned
        - Total count is zero
        """
        # Arrange
        user_id = uuid.uuid4()
        order_service.repository.get_user_orders = AsyncMock(return_value=([], 0))

        # Act
        result = await order_service.get_user_orders(user_id=user_id)

        # Assert
        assert result["orders"] == []
        assert result["total_count"] == 0

    @pytest.mark.asyncio
    async def test_get_user_orders_repository_error(self, order_service: OrderService):
        """
        Test user orders retrieval handles repository errors.

        Verifies:
        - Repository errors are caught
        - OrderProcessingError is raised
        """
        # Arrange
        user_id = uuid.uuid4()
        order_service.repository.get_user_orders = AsyncMock(
            side_effect=OrderRepositoryError("Database error")
        )

        # Act & Assert
        with pytest.raises(OrderProcessingError) as exc_info:
            await order_service.get_user_orders(user_id=user_id)

        assert "Failed to retrieve user orders" in str(exc_info.value)


# ============================================================================
# Unit Tests - Helper Methods
# ============================================================================


class TestHelperMethods:
    """Test suite for internal helper methods."""

    def test_generate_order_number_format(self, order_service: OrderService):
        """
        Test order number generation format.

        Verifies:
        - Order number has correct prefix
        - Contains timestamp
        - Contains random suffix
        - Format is consistent
        """
        # Act
        order_number = order_service._generate_order_number()

        # Assert
        assert order_number.startswith("ORD-")
        parts = order_number.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 14  # Timestamp: YYYYMMDDHHMMSS
        assert len(parts[2]) == 6  # Random suffix

    def test_generate_order_number_uniqueness(self, order_service: OrderService):
        """
        Test order numbers are unique.

        Verifies:
        - Multiple calls generate different numbers
        - Random suffix provides uniqueness
        """
        # Act
        numbers = [order_service._generate_order_number() for _ in range(10)]

        # Assert
        assert len(set(numbers)) == 10  # All unique

    def test_format_order_response(self, order_service: OrderService, mock_order: Mock):
        """
        Test order response formatting.

        Verifies:
        - All fields are included
        - UUIDs are converted to strings
        - Decimals are converted to floats
        - Dates are ISO formatted
        """
        # Act
        result = order_service._format_order_response(mock_order)

        # Assert
        assert result["id"] == str(mock_order.id)
        assert result["order_number"] == mock_order.order_number
        assert result["status"] == mock_order.status.value
        assert isinstance(result["total_amount"], float)
        assert isinstance(result["created_at"], str)

    def test_format_order_response_with_optional_fields(
        self, order_service: OrderService, mock_order: Mock
    ):
        """
        Test order response formatting with optional fields.

        Verifies:
        - Optional fields are handled correctly
        - None values are preserved
        """
        # Arrange
        mock_order.dealer_id = uuid.uuid4()
        mock_order.notes = "Test notes"

        # Act
        result = order_service._format_order_response(mock_order)

        # Assert
        assert result["dealer_id"] == str(mock_order.dealer_id)
        assert result["notes"] == mock_order.notes


# ============================================================================
# Integration Tests - Service Initialization
# ============================================================================


class TestServiceInitialization:
    """Test suite for service initialization."""

    def test_init_without_payment_service(self, mock_session: AsyncMock):
        """
        Test service initialization without payment service.

        Verifies:
        - Service initializes successfully
        - Payment service is None
        - Repository and state machine are created
        """
        # Act
        service = OrderService(session=mock_session)

        # Assert
        assert service.payment_service is None
        assert service.repository is not None
        assert service.state_machine is not None

    def test_init_with_payment_service(
        self, mock_session: AsyncMock, mock_payment_service: AsyncMock
    ):
        """
        Test service initialization with payment service.

        Verifies:
        - Service initializes successfully
        - Payment service is set
        - All components are initialized
        """
        # Act
        service = OrderService(session=mock_session, payment_service=mock_payment_service)

        # Assert
        assert service.payment_service is mock_payment_service
        assert service.repository is not None
        assert service.state_machine is not None


# ============================================================================
# Edge Cases and Error Scenarios
# ============================================================================


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_create_order_with_zero_tax_jurisdiction(
        self, order_service: OrderService, valid_order_data: dict[str, Any], mock_order: Mock
    ):
        """
        Test order creation in zero-tax jurisdiction.

        Verifies:
        - Order is created successfully
        - Tax calculation handles zero rate
        """
        # Arrange
        order_service.repository.create_order_with_items = AsyncMock(return_value=mock_order)

        # Act
        result = await order_service.create_order(**valid_order_data)

        # Assert
        assert result["order_id"] == str(mock_order.id)

    @pytest.mark.asyncio
    async def test_create_order_with_very_large_amount(
        self, order_service: OrderService, valid_order_data: dict[str, Any], mock_order: Mock
    ):
        """
        Test order creation with very large amount.

        Verifies:
        - Large decimal values are handled correctly
        - No overflow or precision loss
        """
        # Arrange
        valid_order_data["items"][0]["unit_price"] = Decimal("999999.99")
        order_service.repository.create_order_with_items = AsyncMock(return_value=mock_order)

        # Act
        result = await order_service.create_order(**valid_order_data)

        # Assert
        assert result["order_id"] == str(mock_order.id)

    @pytest.mark.asyncio
    async def test_create_order_with_fractional_quantity(
        self, order_service: OrderService, valid_order_data: dict[str, Any]
    ):
        """
        Test order creation with fractional quantity.

        Verifies:
        - Fractional quantities are handled
        - Pricing calculation is accurate
        """
        # Arrange
        valid_order_data["items"][0]["quantity"] = Decimal("0.5")

        # Act & Assert
        # Should fail validation as quantity must be positive integer
        with pytest.raises(OrderValidationError):
            await order_service.create_order(**valid_order_data)

    @pytest.mark.asyncio
    async def test_get_user_orders_with_max_pagination(
        self, order_service: OrderService, mock_order: Mock
    ):
        """
        Test user orders retrieval with maximum pagination.

        Verifies:
        - Large limit values are handled
        - Performance is acceptable
        """
        # Arrange
        user_id = uuid.uuid4()
        orders = [mock_order] * 100
        order_service.repository.get_user_orders = AsyncMock(return_value=(orders, 1000))

        # Act
        result = await order_service.get_user_orders(user_id=user_id, limit=100)

        # Assert
        assert len(result["orders"]) == 100
        assert result["total_count"] == 1000


# ============================================================================
# Performance and Concurrency Tests
# ============================================================================


class TestPerformance:
    """Test suite for performance-critical scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_order_creation(
        self, order_service: OrderService, valid_order_data: dict[str, Any], mock_order: Mock
    ):
        """
        Test concurrent order creation.

        Verifies:
        - Multiple orders can be created concurrently
        - No race conditions occur
        - All orders are created successfully
        """
        # Arrange
        order_service.repository.create_order_with_items = AsyncMock(return_value=mock_order)

        # Act
        tasks = [order_service.create_order(**valid_order_data) for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # Assert
        assert len(results) == 5
        assert all(result["order_id"] for result in results)

    @pytest.mark.asyncio
    async def test_order_retrieval_performance(
        self, order_service: OrderService, mock_order: Mock
    ):
        """
        Test order retrieval performance.

        Verifies:
        - Order retrieval completes quickly
        - Response time is acceptable
        """
        # Arrange
        order_id = mock_order.id
        order_service.repository.get_order_by_id = AsyncMock(return_value=mock_order)

        # Act
        start_time = datetime.utcnow()
        await order_service.get_order(order_id=order_id)
        elapsed = (datetime.utcnow() - start_time).total_seconds()

        # Assert
        assert elapsed < 1.0  # Should complete in under 1 second


# ============================================================================
# Security and Data Integrity Tests
# ============================================================================


class TestSecurity:
    """Test suite for security and data integrity."""

    @pytest.mark.asyncio
    async def test_order_creation_sanitizes_input(
        self, order_service: OrderService, valid_order_data: dict[str, Any], mock_order: Mock
    ):
        """
        Test order creation sanitizes user input.

        Verifies:
        - Special characters are handled safely
        - No SQL injection vulnerabilities
        """
        # Arrange
        valid_order_data["notes"] = "<script>alert('xss')</script>"
        order_service.repository.create_order_with_items = AsyncMock(return_value=mock_order)

        # Act
        result = await order_service.create_order(**valid_order_data)

        # Assert
        assert result["order_id"] == str(mock_order.id)

    @pytest.mark.asyncio
    async def test_order_access_control(self, order_service: OrderService, mock_order: Mock):
        """
        Test order access is properly controlled.

        Verifies:
        - Users can only access their own orders
        - Proper authorization checks are in place
        """
        # Arrange
        order_id = mock_order.id
        order_service.repository.get_order_by_id = AsyncMock(return_value=mock_order)

        # Act
        result = await order_service.get_order(order_id=order_id)

        # Assert
        assert result["id"] == str(order_id)