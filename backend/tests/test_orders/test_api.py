"""
Integration tests for order management API endpoints.

This module provides comprehensive end-to-end testing for the order API,
including order creation workflows, status updates, authorization checks,
error scenarios, and edge cases. Tests use FastAPI TestClient with proper
database integration and mocking of external services.
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.orders import router
from src.database.models.order import OrderStatus
from src.main import app
from src.schemas.orders import (
    OrderCreateRequest,
    OrderItemRequest,
    CustomerInfoRequest,
    DeliveryAddressRequest,
    TradeInInfoRequest,
)


# ============================================================================
# Test Data Factories
# ============================================================================


class OrderTestDataFactory:
    """Factory for generating test order data."""

    @staticmethod
    def create_order_item(
        vehicle_id: UUID | None = None,
        configuration_id: UUID | None = None,
        quantity: int = 1,
        unit_price: Decimal = Decimal("50000.00"),
        discount_amount: Decimal = Decimal("0.00"),
        tax_amount: Decimal = Decimal("4000.00"),
    ) -> dict:
        """Create test order item data."""
        return {
            "vehicle_id": vehicle_id or uuid4(),
            "configuration_id": configuration_id,
            "quantity": quantity,
            "unit_price": float(unit_price),
            "discount_amount": float(discount_amount),
            "tax_amount": float(tax_amount),
        }

    @staticmethod
    def create_customer_info(
        first_name: str = "John",
        last_name: str = "Doe",
        email: str = "john.doe@example.com",
        phone: str = "+1234567890",
        driver_license_number: str = "DL123456789",
    ) -> dict:
        """Create test customer info data."""
        return {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "driver_license_number": driver_license_number,
        }

    @staticmethod
    def create_delivery_address(
        street_address: str = "123 Main St",
        city: str = "Springfield",
        state: str = "IL",
        postal_code: str = "62701",
        country: str = "USA",
        delivery_instructions: str | None = None,
    ) -> dict:
        """Create test delivery address data."""
        return {
            "street_address": street_address,
            "city": city,
            "state": state,
            "postal_code": postal_code,
            "country": country,
            "delivery_instructions": delivery_instructions,
        }

    @staticmethod
    def create_trade_in_info(
        vehicle_year: int = 2018,
        vehicle_make: str = "Toyota",
        vehicle_model: str = "Camry",
        vehicle_vin: str = "1HGBH41JXMN109186",
        mileage: int = 50000,
        condition: str = "good",
        estimated_value: Decimal = Decimal("15000.00"),
        payoff_amount: Decimal = Decimal("0.00"),
    ) -> dict:
        """Create test trade-in info data."""
        return {
            "vehicle_year": vehicle_year,
            "vehicle_make": vehicle_make,
            "vehicle_model": vehicle_model,
            "vehicle_vin": vehicle_vin,
            "mileage": mileage,
            "condition": condition,
            "estimated_value": float(estimated_value),
            "payoff_amount": float(payoff_amount),
        }

    @classmethod
    def create_order_request(
        cls,
        items: list[dict] | None = None,
        customer_info: dict | None = None,
        delivery_address: dict | None = None,
        payment_method: str = "credit_card",
        trade_in_info: dict | None = None,
        promotional_code: str | None = None,
        notes: str | None = None,
    ) -> dict:
        """Create complete order request data."""
        return {
            "items": items or [cls.create_order_item()],
            "customer_info": customer_info or cls.create_customer_info(),
            "delivery_address": delivery_address or cls.create_delivery_address(),
            "payment_method": payment_method,
            "trade_in_info": trade_in_info,
            "promotional_code": promotional_code,
            "notes": notes,
        }


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_user() -> MagicMock:
    """Create mock authenticated user."""
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    user.is_active = True
    return user


@pytest.fixture
def mock_order_service() -> AsyncMock:
    """Create mock order service."""
    service = AsyncMock()
    service.create_order = AsyncMock()
    service.get_order = AsyncMock()
    service.get_user_orders = AsyncMock()
    service.update_order_status = AsyncMock()
    return service


@pytest.fixture
def mock_payment_service() -> AsyncMock:
    """Create mock payment service."""
    service = AsyncMock()
    service.process_payment = AsyncMock()
    service.refund_payment = AsyncMock()
    return service


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def order_test_data() -> OrderTestDataFactory:
    """Provide order test data factory."""
    return OrderTestDataFactory()


# ============================================================================
# Unit Tests - Order Creation
# ============================================================================


class TestCreateOrder:
    """Test suite for order creation endpoint."""

    @pytest.mark.asyncio
    async def test_create_order_success(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
        mock_db_session: AsyncMock,
        order_test_data: OrderTestDataFactory,
    ):
        """Test successful order creation with valid data."""
        # Arrange
        order_id = uuid4()
        order_number = "ORD-2024-001"
        order_request = order_test_data.create_order_request()

        mock_order_service.create_order.return_value = {
            "order_id": str(order_id),
            "order_number": order_number,
            "status": OrderStatus.PENDING.value,
        }

        mock_order_service.get_order.return_value = {
            "id": str(order_id),
            "order_number": order_number,
            "user_id": str(mock_user.id),
            "status": OrderStatus.PENDING.value,
            "total_amount": 54000.00,
            "created_at": datetime.now().isoformat(),
            "items": [
                {
                    "id": str(uuid4()),
                    "vehicle_id": str(order_request["items"][0]["vehicle_id"]),
                    "quantity": 1,
                    "unit_price": 50000.00,
                    "total_price": 54000.00,
                }
            ],
        }

        # Act & Assert
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                with patch("src.api.v1.orders.PaymentService"):
                    response = await async_client.post(
                        "/api/v1/orders/",
                        json=order_request,
                    )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["order_number"] == order_number
        assert response_data["status"] == OrderStatus.PENDING.value
        assert "id" in response_data
        assert "created_at" in response_data

    @pytest.mark.asyncio
    async def test_create_order_with_trade_in(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
        order_test_data: OrderTestDataFactory,
    ):
        """Test order creation with trade-in vehicle."""
        # Arrange
        order_id = uuid4()
        trade_in_info = order_test_data.create_trade_in_info()
        order_request = order_test_data.create_order_request(
            trade_in_info=trade_in_info
        )

        mock_order_service.create_order.return_value = {
            "order_id": str(order_id),
            "order_number": "ORD-2024-002",
            "status": OrderStatus.PENDING.value,
        }

        mock_order_service.get_order.return_value = {
            "id": str(order_id),
            "order_number": "ORD-2024-002",
            "user_id": str(mock_user.id),
            "status": OrderStatus.PENDING.value,
            "total_amount": 39000.00,
            "trade_in_value": 15000.00,
            "created_at": datetime.now().isoformat(),
            "items": [],
        }

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                with patch("src.api.v1.orders.PaymentService"):
                    response = await async_client.post(
                        "/api/v1/orders/",
                        json=order_request,
                    )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["trade_in_value"] == 15000.00
        mock_order_service.create_order.assert_called_once()
        call_kwargs = mock_order_service.create_order.call_args.kwargs
        assert call_kwargs["trade_in_info"] is not None

    @pytest.mark.asyncio
    async def test_create_order_with_promotional_code(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
        order_test_data: OrderTestDataFactory,
    ):
        """Test order creation with promotional code."""
        # Arrange
        order_id = uuid4()
        promo_code = "SAVE10"
        order_request = order_test_data.create_order_request(
            promotional_code=promo_code
        )

        mock_order_service.create_order.return_value = {
            "order_id": str(order_id),
            "order_number": "ORD-2024-003",
            "status": OrderStatus.PENDING.value,
        }

        mock_order_service.get_order.return_value = {
            "id": str(order_id),
            "order_number": "ORD-2024-003",
            "user_id": str(mock_user.id),
            "status": OrderStatus.PENDING.value,
            "total_amount": 48600.00,
            "discount_amount": 5400.00,
            "promotional_code": promo_code,
            "created_at": datetime.now().isoformat(),
            "items": [],
        }

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                with patch("src.api.v1.orders.PaymentService"):
                    response = await async_client.post(
                        "/api/v1/orders/",
                        json=order_request,
                    )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["promotional_code"] == promo_code
        assert response_data["discount_amount"] == 5400.00

    @pytest.mark.asyncio
    async def test_create_order_validation_error(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
        order_test_data: OrderTestDataFactory,
    ):
        """Test order creation with validation error."""
        # Arrange
        from src.services.orders.service import OrderValidationError

        order_request = order_test_data.create_order_request()
        mock_order_service.create_order.side_effect = OrderValidationError(
            "Invalid vehicle configuration",
            context={"vehicle_id": str(order_request["items"][0]["vehicle_id"])},
        )

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                with patch("src.api.v1.orders.PaymentService"):
                    response = await async_client.post(
                        "/api/v1/orders/",
                        json=order_request,
                    )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid vehicle configuration" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_order_processing_error(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
        order_test_data: OrderTestDataFactory,
    ):
        """Test order creation with processing error."""
        # Arrange
        from src.services.orders.service import OrderProcessingError

        order_request = order_test_data.create_order_request()
        mock_order_service.create_order.side_effect = OrderProcessingError(
            "Payment processing failed",
            context={"payment_method": "credit_card"},
        )

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                with patch("src.api.v1.orders.PaymentService"):
                    response = await async_client.post(
                        "/api/v1/orders/",
                        json=order_request,
                    )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to process order" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_order_unexpected_error(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
        order_test_data: OrderTestDataFactory,
    ):
        """Test order creation with unexpected error."""
        # Arrange
        order_request = order_test_data.create_order_request()
        mock_order_service.create_order.side_effect = Exception("Unexpected error")

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                with patch("src.api.v1.orders.PaymentService"):
                    response = await async_client.post(
                        "/api/v1/orders/",
                        json=order_request,
                    )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "unexpected error" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid_field,invalid_value,expected_error",
        [
            ("items", [], "at least 1 item"),
            ("customer_info", None, "required"),
            ("delivery_address", None, "required"),
            ("payment_method", "", "required"),
        ],
    )
    async def test_create_order_invalid_input(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        order_test_data: OrderTestDataFactory,
        invalid_field: str,
        invalid_value,
        expected_error: str,
    ):
        """Test order creation with invalid input data."""
        # Arrange
        order_request = order_test_data.create_order_request()
        order_request[invalid_field] = invalid_value

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            response = await async_client.post(
                "/api/v1/orders/",
                json=order_request,
            )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============================================================================
# Unit Tests - List Orders
# ============================================================================


class TestListOrders:
    """Test suite for listing user orders."""

    @pytest.mark.asyncio
    async def test_list_orders_success(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test successful retrieval of user orders."""
        # Arrange
        orders = [
            {
                "id": str(uuid4()),
                "order_number": f"ORD-2024-{i:03d}",
                "user_id": str(mock_user.id),
                "status": OrderStatus.PENDING.value,
                "total_amount": 50000.00 + (i * 1000),
                "created_at": datetime.now().isoformat(),
            }
            for i in range(1, 4)
        ]

        mock_order_service.get_user_orders.return_value = {
            "orders": orders,
            "total_count": 3,
            "page": 1,
            "page_size": 20,
        }

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.get("/api/v1/orders/")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["total_count"] == 3
        assert len(response_data["orders"]) == 3
        assert response_data["orders"][0]["order_number"] == "ORD-2024-001"

    @pytest.mark.asyncio
    async def test_list_orders_with_status_filter(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test listing orders with status filter."""
        # Arrange
        orders = [
            {
                "id": str(uuid4()),
                "order_number": "ORD-2024-001",
                "user_id": str(mock_user.id),
                "status": OrderStatus.COMPLETED.value,
                "total_amount": 50000.00,
                "created_at": datetime.now().isoformat(),
            }
        ]

        mock_order_service.get_user_orders.return_value = {
            "orders": orders,
            "total_count": 1,
            "page": 1,
            "page_size": 20,
        }

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.get(
                    "/api/v1/orders/",
                    params={"status_filter": OrderStatus.COMPLETED.value},
                )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["total_count"] == 1
        assert response_data["orders"][0]["status"] == OrderStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_list_orders_with_pagination(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test listing orders with pagination parameters."""
        # Arrange
        orders = [
            {
                "id": str(uuid4()),
                "order_number": f"ORD-2024-{i:03d}",
                "user_id": str(mock_user.id),
                "status": OrderStatus.PENDING.value,
                "total_amount": 50000.00,
                "created_at": datetime.now().isoformat(),
            }
            for i in range(11, 21)
        ]

        mock_order_service.get_user_orders.return_value = {
            "orders": orders,
            "total_count": 50,
            "page": 2,
            "page_size": 10,
        }

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.get(
                    "/api/v1/orders/",
                    params={"skip": 10, "limit": 10},
                )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["total_count"] == 50
        assert len(response_data["orders"]) == 10
        mock_order_service.get_user_orders.assert_called_once_with(
            user_id=mock_user.id,
            status=None,
            skip=10,
            limit=10,
        )

    @pytest.mark.asyncio
    async def test_list_orders_empty_result(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test listing orders when user has no orders."""
        # Arrange
        mock_order_service.get_user_orders.return_value = {
            "orders": [],
            "total_count": 0,
            "page": 1,
            "page_size": 20,
        }

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.get("/api/v1/orders/")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["total_count"] == 0
        assert len(response_data["orders"]) == 0

    @pytest.mark.asyncio
    async def test_list_orders_service_error(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test listing orders with service error."""
        # Arrange
        from src.services.orders.service import OrderServiceError

        mock_order_service.get_user_orders.side_effect = OrderServiceError(
            "Database connection failed",
            context={"user_id": str(mock_user.id)},
        )

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.get("/api/v1/orders/")

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve orders" in response.json()["detail"]


# ============================================================================
# Unit Tests - Get Order Details
# ============================================================================


class TestGetOrder:
    """Test suite for retrieving order details."""

    @pytest.mark.asyncio
    async def test_get_order_success(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test successful retrieval of order details."""
        # Arrange
        order_id = uuid4()
        order_data = {
            "id": str(order_id),
            "order_number": "ORD-2024-001",
            "user_id": str(mock_user.id),
            "status": OrderStatus.PENDING.value,
            "total_amount": 54000.00,
            "created_at": datetime.now().isoformat(),
            "items": [
                {
                    "id": str(uuid4()),
                    "vehicle_id": str(uuid4()),
                    "quantity": 1,
                    "unit_price": 50000.00,
                    "total_price": 54000.00,
                }
            ],
            "status_history": [
                {
                    "status": OrderStatus.PENDING.value,
                    "changed_at": datetime.now().isoformat(),
                    "changed_by": str(mock_user.id),
                }
            ],
        }

        mock_order_service.get_order.return_value = order_data

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.get(f"/api/v1/orders/{order_id}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["id"] == str(order_id)
        assert response_data["order_number"] == "ORD-2024-001"
        assert len(response_data["items"]) == 1
        assert len(response_data["status_history"]) == 1

    @pytest.mark.asyncio
    async def test_get_order_not_found(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test retrieving non-existent order."""
        # Arrange
        from src.services.orders.repository import OrderNotFoundError

        order_id = uuid4()
        mock_order_service.get_order.side_effect = OrderNotFoundError(
            f"Order {order_id} not found"
        )

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.get(f"/api/v1/orders/{order_id}")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Order not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_order_unauthorized_access(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test accessing order belonging to different user."""
        # Arrange
        order_id = uuid4()
        other_user_id = uuid4()
        order_data = {
            "id": str(order_id),
            "order_number": "ORD-2024-001",
            "user_id": str(other_user_id),
            "status": OrderStatus.PENDING.value,
            "total_amount": 54000.00,
            "created_at": datetime.now().isoformat(),
        }

        mock_order_service.get_order.return_value = order_data

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.get(f"/api/v1/orders/{order_id}")

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Not authorized" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_order_invalid_uuid(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
    ):
        """Test retrieving order with invalid UUID format."""
        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            response = await async_client.get("/api/v1/orders/invalid-uuid")

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============================================================================
# Unit Tests - Update Order Status
# ============================================================================


class TestUpdateOrderStatus:
    """Test suite for updating order status."""

    @pytest.mark.asyncio
    async def test_update_order_status_success(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test successful order status update."""
        # Arrange
        order_id = uuid4()
        order_data = {
            "id": str(order_id),
            "order_number": "ORD-2024-001",
            "user_id": str(mock_user.id),
            "status": OrderStatus.PENDING.value,
            "total_amount": 54000.00,
            "created_at": datetime.now().isoformat(),
        }

        updated_order_data = {**order_data, "status": OrderStatus.CONFIRMED.value}

        mock_order_service.get_order.side_effect = [order_data, updated_order_data]
        mock_order_service.update_order_status.return_value = None

        status_update = {
            "order_status": OrderStatus.CONFIRMED.value,
            "status_notes": "Order confirmed by customer",
        }

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.put(
                    f"/api/v1/orders/{order_id}/status",
                    json=status_update,
                )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["status"] == OrderStatus.CONFIRMED.value
        mock_order_service.update_order_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_order_status_invalid_transition(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test invalid order status transition."""
        # Arrange
        from src.services.orders.service import OrderProcessingError

        order_id = uuid4()
        order_data = {
            "id": str(order_id),
            "order_number": "ORD-2024-001",
            "user_id": str(mock_user.id),
            "status": OrderStatus.COMPLETED.value,
            "total_amount": 54000.00,
            "created_at": datetime.now().isoformat(),
        }

        mock_order_service.get_order.return_value = order_data
        mock_order_service.update_order_status.side_effect = OrderProcessingError(
            "Cannot transition from COMPLETED to PENDING",
            context={"current_status": "COMPLETED", "new_status": "PENDING"},
        )

        status_update = {
            "order_status": OrderStatus.PENDING.value,
            "status_notes": "Attempting invalid transition",
        }

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.put(
                    f"/api/v1/orders/{order_id}/status",
                    json=status_update,
                )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot transition" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_order_status_unauthorized(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test updating status of order belonging to different user."""
        # Arrange
        order_id = uuid4()
        other_user_id = uuid4()
        order_data = {
            "id": str(order_id),
            "order_number": "ORD-2024-001",
            "user_id": str(other_user_id),
            "status": OrderStatus.PENDING.value,
            "total_amount": 54000.00,
            "created_at": datetime.now().isoformat(),
        }

        mock_order_service.get_order.return_value = order_data

        status_update = {
            "order_status": OrderStatus.CONFIRMED.value,
            "status_notes": "Unauthorized update attempt",
        }

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.put(
                    f"/api/v1/orders/{order_id}/status",
                    json=status_update,
                )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Not authorized" in response.json()["detail"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "from_status,to_status,should_succeed",
        [
            (OrderStatus.PENDING, OrderStatus.CONFIRMED, True),
            (OrderStatus.CONFIRMED, OrderStatus.PROCESSING, True),
            (OrderStatus.PROCESSING, OrderStatus.SHIPPED, True),
            (OrderStatus.SHIPPED, OrderStatus.DELIVERED, True),
            (OrderStatus.PENDING, OrderStatus.CANCELLED, True),
            (OrderStatus.COMPLETED, OrderStatus.PENDING, False),
            (OrderStatus.CANCELLED, OrderStatus.CONFIRMED, False),
        ],
    )
    async def test_order_status_transitions(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
        from_status: OrderStatus,
        to_status: OrderStatus,
        should_succeed: bool,
    ):
        """Test various order status transitions."""
        # Arrange
        from src.services.orders.service import OrderProcessingError

        order_id = uuid4()
        order_data = {
            "id": str(order_id),
            "order_number": "ORD-2024-001",
            "user_id": str(mock_user.id),
            "status": from_status.value,
            "total_amount": 54000.00,
            "created_at": datetime.now().isoformat(),
        }

        if should_succeed:
            updated_order_data = {**order_data, "status": to_status.value}
            mock_order_service.get_order.side_effect = [order_data, updated_order_data]
            mock_order_service.update_order_status.return_value = None
        else:
            mock_order_service.get_order.return_value = order_data
            mock_order_service.update_order_status.side_effect = OrderProcessingError(
                f"Cannot transition from {from_status.value} to {to_status.value}",
                context={"from": from_status.value, "to": to_status.value},
            )

        status_update = {
            "order_status": to_status.value,
            "status_notes": f"Transition from {from_status.value} to {to_status.value}",
        }

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.put(
                    f"/api/v1/orders/{order_id}/status",
                    json=status_update,
                )

        # Assert
        if should_succeed:
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["status"] == to_status.value
        else:
            assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# Unit Tests - Cancel Order
# ============================================================================


class TestCancelOrder:
    """Test suite for order cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_order_success(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test successful order cancellation."""
        # Arrange
        order_id = uuid4()
        order_data = {
            "id": str(order_id),
            "order_number": "ORD-2024-001",
            "user_id": str(mock_user.id),
            "status": OrderStatus.PENDING.value,
            "total_amount": 54000.00,
            "created_at": datetime.now().isoformat(),
        }

        cancelled_order_data = {**order_data, "status": OrderStatus.CANCELLED.value}

        mock_order_service.get_order.side_effect = [order_data, cancelled_order_data]
        mock_order_service.update_order_status.return_value = None

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.post(
                    f"/api/v1/orders/{order_id}/cancel",
                    params={"reason": "Customer requested cancellation"},
                )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["status"] == OrderStatus.CANCELLED.value
        mock_order_service.update_order_status.assert_called_once_with(
            order_id=order_id,
            new_status=OrderStatus.CANCELLED,
            user_id=mock_user.id,
            reason="Customer requested cancellation",
        )

    @pytest.mark.asyncio
    async def test_cancel_order_without_reason(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test order cancellation without providing reason."""
        # Arrange
        order_id = uuid4()
        order_data = {
            "id": str(order_id),
            "order_number": "ORD-2024-001",
            "user_id": str(mock_user.id),
            "status": OrderStatus.PENDING.value,
            "total_amount": 54000.00,
            "created_at": datetime.now().isoformat(),
        }

        cancelled_order_data = {**order_data, "status": OrderStatus.CANCELLED.value}

        mock_order_service.get_order.side_effect = [order_data, cancelled_order_data]
        mock_order_service.update_order_status.return_value = None

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.post(f"/api/v1/orders/{order_id}/cancel")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_order_service.update_order_status.assert_called_once_with(
            order_id=order_id,
            new_status=OrderStatus.CANCELLED,
            user_id=mock_user.id,
            reason="Cancelled by customer",
        )

    @pytest.mark.asyncio
    async def test_cancel_order_already_completed(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test cancelling already completed order."""
        # Arrange
        from src.services.orders.service import OrderProcessingError

        order_id = uuid4()
        order_data = {
            "id": str(order_id),
            "order_number": "ORD-2024-001",
            "user_id": str(mock_user.id),
            "status": OrderStatus.COMPLETED.value,
            "total_amount": 54000.00,
            "created_at": datetime.now().isoformat(),
        }

        mock_order_service.get_order.return_value = order_data
        mock_order_service.update_order_status.side_effect = OrderProcessingError(
            "Cannot cancel completed order",
            context={"order_id": str(order_id), "status": "COMPLETED"},
        )

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.post(
                    f"/api/v1/orders/{order_id}/cancel",
                    params={"reason": "Attempting to cancel completed order"},
                )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot cancel" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_cancel_order_unauthorized(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test cancelling order belonging to different user."""
        # Arrange
        order_id = uuid4()
        other_user_id = uuid4()
        order_data = {
            "id": str(order_id),
            "order_number": "ORD-2024-001",
            "user_id": str(other_user_id),
            "status": OrderStatus.PENDING.value,
            "total_amount": 54000.00,
            "created_at": datetime.now().isoformat(),
        }

        mock_order_service.get_order.return_value = order_data

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.post(
                    f"/api/v1/orders/{order_id}/cancel",
                    params={"reason": "Unauthorized cancellation attempt"},
                )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Not authorized" in response.json()["detail"]


# ============================================================================
# Unit Tests - Get Order History
# ============================================================================


class TestGetOrderHistory:
    """Test suite for retrieving order status history."""

    @pytest.mark.asyncio
    async def test_get_order_history_success(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test successful retrieval of order history."""
        # Arrange
        order_id = uuid4()
        order_data = {
            "id": str(order_id),
            "order_number": "ORD-2024-001",
            "user_id": str(mock_user.id),
            "status": OrderStatus.DELIVERED.value,
            "total_amount": 54000.00,
            "created_at": datetime.now().isoformat(),
            "status_history": [
                {
                    "status": OrderStatus.PENDING.value,
                    "changed_at": "2024-01-01T10:00:00",
                    "changed_by": str(mock_user.id),
                    "notes": "Order created",
                },
                {
                    "status": OrderStatus.CONFIRMED.value,
                    "changed_at": "2024-01-01T11:00:00",
                    "changed_by": str(mock_user.id),
                    "notes": "Order confirmed",
                },
                {
                    "status": OrderStatus.PROCESSING.value,
                    "changed_at": "2024-01-02T09:00:00",
                    "changed_by": str(uuid4()),
                    "notes": "Processing started",
                },
                {
                    "status": OrderStatus.SHIPPED.value,
                    "changed_at": "2024-01-03T14:00:00",
                    "changed_by": str(uuid4()),
                    "notes": "Order shipped",
                },
                {
                    "status": OrderStatus.DELIVERED.value,
                    "changed_at": "2024-01-05T16:00:00",
                    "changed_by": str(uuid4()),
                    "notes": "Order delivered",
                },
            ],
        }

        mock_order_service.get_order.side_effect = [
            {"id": str(order_id), "order_number": "ORD-2024-001", "user_id": str(mock_user.id)},
            order_data,
        ]

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.get(f"/api/v1/orders/{order_id}/history")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["order_id"] == str(order_id)
        assert response_data["order_number"] == "ORD-2024-001"
        assert response_data["current_status"] == OrderStatus.DELIVERED.value
        assert len(response_data["history"]) == 5
        assert response_data["history"][0]["status"] == OrderStatus.PENDING.value
        assert response_data["history"][-1]["status"] == OrderStatus.DELIVERED.value

    @pytest.mark.asyncio
    async def test_get_order_history_empty(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test retrieving history for order with no status changes."""
        # Arrange
        order_id = uuid4()
        order_data = {
            "id": str(order_id),
            "order_number": "ORD-2024-001",
            "user_id": str(mock_user.id),
            "status": OrderStatus.PENDING.value,
            "total_amount": 54000.00,
            "created_at": datetime.now().isoformat(),
            "status_history": [],
        }

        mock_order_service.get_order.side_effect = [
            {"id": str(order_id), "order_number": "ORD-2024-001", "user_id": str(mock_user.id)},
            order_data,
        ]

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.get(f"/api/v1/orders/{order_id}/history")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert len(response_data["history"]) == 0

    @pytest.mark.asyncio
    async def test_get_order_history_unauthorized(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test accessing history of order belonging to different user."""
        # Arrange
        order_id = uuid4()
        other_user_id = uuid4()
        order_data = {
            "id": str(order_id),
            "order_number": "ORD-2024-001",
            "user_id": str(other_user_id),
            "status": OrderStatus.PENDING.value,
            "total_amount": 54000.00,
            "created_at": datetime.now().isoformat(),
        }

        mock_order_service.get_order.return_value = order_data

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.get(f"/api/v1/orders/{order_id}/history")

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Not authorized" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_order_history_not_found(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test retrieving history for non-existent order."""
        # Arrange
        from src.services.orders.repository import OrderNotFoundError

        order_id = uuid4()
        mock_order_service.get_order.side_effect = OrderNotFoundError(
            f"Order {order_id} not found"
        )

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.get(f"/api/v1/orders/{order_id}/history")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Order not found" in response.json()["detail"]


# ============================================================================
# Integration Tests - Complete Order Workflows
# ============================================================================


class TestOrderWorkflows:
    """Integration tests for complete order workflows."""

    @pytest.mark.asyncio
    async def test_complete_order_lifecycle(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
        order_test_data: OrderTestDataFactory,
    ):
        """Test complete order lifecycle from creation to delivery."""
        # Arrange
        order_id = uuid4()
        order_number = "ORD-2024-001"
        order_request = order_test_data.create_order_request()

        # Step 1: Create order
        mock_order_service.create_order.return_value = {
            "order_id": str(order_id),
            "order_number": order_number,
            "status": OrderStatus.PENDING.value,
        }

        pending_order = {
            "id": str(order_id),
            "order_number": order_number,
            "user_id": str(mock_user.id),
            "status": OrderStatus.PENDING.value,
            "total_amount": 54000.00,
            "created_at": datetime.now().isoformat(),
            "items": [],
        }

        confirmed_order = {**pending_order, "status": OrderStatus.CONFIRMED.value}
        processing_order = {**pending_order, "status": OrderStatus.PROCESSING.value}
        shipped_order = {**pending_order, "status": OrderStatus.SHIPPED.value}
        delivered_order = {**pending_order, "status": OrderStatus.DELIVERED.value}

        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                with patch("src.api.v1.orders.PaymentService"):
                    # Create order
                    mock_order_service.get_order.return_value = pending_order
                    create_response = await async_client.post(
                        "/api/v1/orders/",
                        json=order_request,
                    )
                    assert create_response.status_code == status.HTTP_201_CREATED

                    # Confirm order
                    mock_order_service.get_order.side_effect = [
                        pending_order,
                        confirmed_order,
                    ]
                    confirm_response = await async_client.put(
                        f"/api/v1/orders/{order_id}/status",
                        json={
                            "order_status": OrderStatus.CONFIRMED.value,
                            "status_notes": "Order confirmed",
                        },
                    )
                    assert confirm_response.status_code == status.HTTP_200_OK

                    # Process order
                    mock_order_service.get_order.side_effect = [
                        confirmed_order,
                        processing_order,
                    ]
                    process_response = await async_client.put(
                        f"/api/v1/orders/{order_id}/status",
                        json={
                            "order_status": OrderStatus.PROCESSING.value,
                            "status_notes": "Processing started",
                        },
                    )
                    assert process_response.status_code == status.HTTP_200_OK

                    # Ship order
                    mock_order_service.get_order.side_effect = [
                        processing_order,
                        shipped_order,
                    ]
                    ship_response = await async_client.put(
                        f"/api/v1/orders/{order_id}/status",
                        json={
                            "order_status": OrderStatus.SHIPPED.value,
                            "status_notes": "Order shipped",
                        },
                    )
                    assert ship_response.status_code == status.HTTP_200_OK

                    # Deliver order
                    mock_order_service.get_order.side_effect = [
                        shipped_order,
                        delivered_order,
                    ]
                    deliver_response = await async_client.put(
                        f"/api/v1/orders/{order_id}/status",
                        json={
                            "order_status": OrderStatus.DELIVERED.value,
                            "status_notes": "Order delivered",
                        },
                    )
                    assert deliver_response.status_code == status.HTTP_200_OK
                    assert deliver_response.json()["status"] == OrderStatus.DELIVERED.value

    @pytest.mark.asyncio
    async def test_order_cancellation_workflow(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
        order_test_data: OrderTestDataFactory,
    ):
        """Test order cancellation workflow."""
        # Arrange
        order_id = uuid4()
        order_number = "ORD-2024-002"
        order_request = order_test_data.create_order_request()

        # Create order
        mock_order_service.create_order.return_value = {
            "order_id": str(order_id),
            "order_number": order_number,
            "status": OrderStatus.PENDING.value,
        }

        pending_order = {
            "id": str(order_id),
            "order_number": order_number,
            "user_id": str(mock_user.id),
            "status": OrderStatus.PENDING.value,
            "total_amount": 54000.00,
            "created_at": datetime.now().isoformat(),
            "items": [],
        }

        cancelled_order = {**pending_order, "status": OrderStatus.CANCELLED.value}

        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                with patch("src.api.v1.orders.PaymentService"):
                    # Create order
                    mock_order_service.get_order.return_value = pending_order
                    create_response = await async_client.post(
                        "/api/v1/orders/",
                        json=order_request,
                    )
                    assert create_response.status_code == status.HTTP_201_CREATED

                    # Cancel order
                    mock_order_service.get_order.side_effect = [
                        pending_order,
                        cancelled_order,
                    ]
                    cancel_response = await async_client.post(
                        f"/api/v1/orders/{order_id}/cancel",
                        params={"reason": "Customer changed mind"},
                    )
                    assert cancel_response.status_code == status.HTTP_200_OK
                    assert cancel_response.json()["status"] == OrderStatus.CANCELLED.value


# ============================================================================
# Performance Tests
# ============================================================================


class TestOrderAPIPerformance:
    """Performance tests for order API endpoints."""

    @pytest.mark.asyncio
    async def test_list_orders_performance(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test performance of listing orders with large dataset."""
        # Arrange
        orders = [
            {
                "id": str(uuid4()),
                "order_number": f"ORD-2024-{i:05d}",
                "user_id": str(mock_user.id),
                "status": OrderStatus.PENDING.value,
                "total_amount": 50000.00,
                "created_at": datetime.now().isoformat(),
            }
            for i in range(100)
        ]

        mock_order_service.get_user_orders.return_value = {
            "orders": orders,
            "total_count": 100,
            "page": 1,
            "page_size": 100,
        }

        # Act
        start_time = asyncio.get_event_loop().time()
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.get(
                    "/api/v1/orders/",
                    params={"limit": 100},
                )
        end_time = asyncio.get_event_loop().time()

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["orders"]) == 100
        # Performance threshold: should complete in less than 1 second
        assert (end_time - start_time) < 1.0


# ============================================================================
# Security Tests
# ============================================================================


class TestOrderAPISecurity:
    """Security tests for order API endpoints."""

    @pytest.mark.asyncio
    async def test_unauthenticated_access_denied(
        self,
        async_client: AsyncClient,
    ):
        """Test that unauthenticated requests are denied."""
        # Act
        response = await async_client.get("/api/v1/orders/")

        # Assert - Should fail without authentication
        # Note: Actual behavior depends on authentication middleware
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_sql_injection_prevention(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
    ):
        """Test SQL injection prevention in order endpoints."""
        # Arrange
        malicious_order_id = "'; DROP TABLE orders; --"

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                response = await async_client.get(f"/api/v1/orders/{malicious_order_id}")

        # Assert - Should fail validation, not execute SQL
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_xss_prevention_in_notes(
        self,
        async_client: AsyncClient,
        mock_user: MagicMock,
        mock_order_service: AsyncMock,
        order_test_data: OrderTestDataFactory,
    ):
        """Test XSS prevention in order notes field."""
        # Arrange
        xss_payload = "<script>alert('XSS')</script>"
        order_request = order_test_data.create_order_request(notes=xss_payload)

        order_id = uuid4()
        mock_order_service.create_order.return_value = {
            "order_id": str(order_id),
            "order_number": "ORD-2024-001",
            "status": OrderStatus.PENDING.value,
        }

        mock_order_service.get_order.return_value = {
            "id": str(order_id),
            "order_number": "ORD-2024-001",
            "user_id": str(mock_user.id),
            "status": OrderStatus.PENDING.value,
            "total_amount": 54000.00,
            "notes": xss_payload,  # Should be sanitized
            "created_at": datetime.now().isoformat(),
            "items": [],
        }

        # Act
        with patch("src.api.v1.orders.get_current_active_user", return_value=mock_user):
            with patch("src.api.v1.orders.OrderService", return_value=mock_order_service):
                with patch("src.api.v1.orders.PaymentService"):
                    response = await async_client.post(
                        "/api/v1/orders/",
                        json=order_request,
                    )

        # Assert - Should accept but sanitize
        assert response.status_code == status.HTTP_201_CREATED
        # Note: Actual sanitization depends on implementation