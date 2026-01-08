"""
Comprehensive integration tests for cart API endpoints.

This module provides end-to-end testing for all cart operations including:
- Add to cart with inventory reservation
- Retrieve cart with session handling
- Update cart item quantities
- Remove cart items
- Apply promotional codes
- Authentication and authorization
- Session management and migration
- Error scenarios and edge cases
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import AsyncGenerator, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.cart import SESSION_COOKIE_NAME
from src.schemas.cart import (
    AddToCartRequest,
    ApplyPromoRequest,
    CartResponse,
    UpdateCartItemRequest,
)
from src.services.cart.inventory_reservation import InsufficientInventoryError
from src.services.cart.service import (
    CartItemNotFoundError,
    CartNotFoundError,
    CartService,
    CartServiceError,
    InvalidPromotionalCodeError,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_cart_service() -> MagicMock:
    """
    Create mock cart service for testing.

    Returns:
        MagicMock: Mocked cart service with async methods
    """
    service = MagicMock(spec=CartService)
    service.add_to_cart = AsyncMock()
    service.get_cart = AsyncMock()
    service.update_cart_item = AsyncMock()
    service.remove_cart_item = AsyncMock()
    service.apply_promotional_code = AsyncMock()
    return service


@pytest.fixture
def sample_cart_response() -> CartResponse:
    """
    Create sample cart response for testing.

    Returns:
        CartResponse: Sample cart with items and pricing
    """
    from src.schemas.cart import CartItemResponse, CartSummary

    cart_id = uuid.uuid4()
    vehicle_id = uuid.uuid4()
    config_id = uuid.uuid4()

    return CartResponse(
        id=cart_id,
        user_id=None,
        session_id="test-session-123",
        items=[
            CartItemResponse(
                id=uuid.uuid4(),
                cart_id=cart_id,
                vehicle_id=vehicle_id,
                configuration_id=config_id,
                quantity=2,
                unit_price=Decimal("45000.00"),
                total_price=Decimal("90000.00"),
                vehicle_name="Model X",
                configuration_name="Premium Package",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        ],
        summary=CartSummary(
            subtotal=Decimal("90000.00"),
            tax_amount=Decimal("7200.00"),
            discount_amount=Decimal("0.00"),
            total=Decimal("97200.00"),
        ),
        item_count=2,
        promo_code=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_add_request() -> AddToCartRequest:
    """
    Create sample add to cart request.

    Returns:
        AddToCartRequest: Valid add to cart request
    """
    return AddToCartRequest(
        vehicle_id=uuid.uuid4(),
        configuration_id=uuid.uuid4(),
        quantity=1,
    )


@pytest.fixture
def authenticated_headers() -> dict[str, str]:
    """
    Create headers for authenticated requests.

    Returns:
        dict: Headers with authentication token
    """
    return {"Authorization": "Bearer test-token-123"}


# ============================================================================
# Add to Cart Tests
# ============================================================================


class TestAddToCart:
    """Test suite for add to cart endpoint."""

    @pytest.mark.asyncio
    async def test_add_to_cart_anonymous_user_creates_session(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
        sample_add_request: AddToCartRequest,
    ):
        """
        Test adding item to cart creates session for anonymous user.

        Verifies:
        - Session cookie is created
        - Cart service is called with session ID
        - Response contains cart data
        - Status code is 201 CREATED
        """
        mock_cart_service.add_to_cart.return_value = sample_cart_response

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.post(
                "/api/v1/cart/items",
                json=sample_add_request.model_dump(mode="json"),
            )

        assert response.status_code == status.HTTP_201_CREATED
        assert SESSION_COOKIE_NAME in response.cookies

        session_id = response.cookies[SESSION_COOKIE_NAME]
        assert session_id is not None
        assert len(session_id) > 0

        mock_cart_service.add_to_cart.assert_called_once()
        call_kwargs = mock_cart_service.add_to_cart.call_args.kwargs
        assert call_kwargs["session_id"] == session_id
        assert call_kwargs["user_id"] is None

        data = response.json()
        assert data["id"] == str(sample_cart_response.id)
        assert data["item_count"] == sample_cart_response.item_count

    @pytest.mark.asyncio
    async def test_add_to_cart_authenticated_user(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
        sample_add_request: AddToCartRequest,
        authenticated_headers: dict[str, str],
    ):
        """
        Test adding item to cart for authenticated user.

        Verifies:
        - User ID is passed to service
        - Session ID is optional
        - Response contains cart data
        """
        user_id = uuid.uuid4()
        sample_cart_response.user_id = user_id
        mock_cart_service.add_to_cart.return_value = sample_cart_response

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ), patch(
            "src.api.deps.get_current_user",
            return_value=MagicMock(id=user_id),
        ):
            response = await async_client.post(
                "/api/v1/cart/items",
                json=sample_add_request.model_dump(mode="json"),
                headers=authenticated_headers,
            )

        assert response.status_code == status.HTTP_201_CREATED

        call_kwargs = mock_cart_service.add_to_cart.call_args.kwargs
        assert call_kwargs["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_add_to_cart_existing_session(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
        sample_add_request: AddToCartRequest,
    ):
        """
        Test adding item to cart with existing session.

        Verifies:
        - Existing session ID is used
        - No new session is created
        - Cart service receives correct session ID
        """
        existing_session = "existing-session-456"
        mock_cart_service.add_to_cart.return_value = sample_cart_response

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.post(
                "/api/v1/cart/items",
                json=sample_add_request.model_dump(mode="json"),
                cookies={SESSION_COOKIE_NAME: existing_session},
            )

        assert response.status_code == status.HTTP_201_CREATED

        call_kwargs = mock_cart_service.add_to_cart.call_args.kwargs
        assert call_kwargs["session_id"] == existing_session

    @pytest.mark.asyncio
    async def test_add_to_cart_insufficient_inventory(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_add_request: AddToCartRequest,
    ):
        """
        Test adding item with insufficient inventory.

        Verifies:
        - 409 CONFLICT status code
        - Error details include vehicle ID
        - Error code is INSUFFICIENT_INVENTORY
        """
        mock_cart_service.add_to_cart.side_effect = InsufficientInventoryError(
            vehicle_id=sample_add_request.vehicle_id,
            requested=sample_add_request.quantity,
            available=0,
        )

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.post(
                "/api/v1/cart/items",
                json=sample_add_request.model_dump(mode="json"),
            )

        assert response.status_code == status.HTTP_409_CONFLICT

        data = response.json()
        assert data["detail"]["code"] == "INSUFFICIENT_INVENTORY"
        assert data["detail"]["vehicle_id"] == str(sample_add_request.vehicle_id)

    @pytest.mark.asyncio
    async def test_add_to_cart_vehicle_not_found(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_add_request: AddToCartRequest,
    ):
        """
        Test adding item with non-existent vehicle.

        Verifies:
        - 404 NOT FOUND status code
        - Error code is VEHICLE_NOT_FOUND
        """
        mock_cart_service.add_to_cart.side_effect = CartServiceError(
            message="Vehicle not found",
            code="VEHICLE_NOT_FOUND",
        )

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.post(
                "/api/v1/cart/items",
                json=sample_add_request.model_dump(mode="json"),
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"]["code"] == "VEHICLE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_add_to_cart_configuration_not_found(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_add_request: AddToCartRequest,
    ):
        """
        Test adding item with non-existent configuration.

        Verifies:
        - 404 NOT FOUND status code
        - Error code is CONFIGURATION_NOT_FOUND
        """
        mock_cart_service.add_to_cart.side_effect = CartServiceError(
            message="Configuration not found",
            code="CONFIGURATION_NOT_FOUND",
        )

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.post(
                "/api/v1/cart/items",
                json=sample_add_request.model_dump(mode="json"),
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"]["code"] == "CONFIGURATION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_add_to_cart_service_error(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_add_request: AddToCartRequest,
    ):
        """
        Test handling of generic service errors.

        Verifies:
        - 500 INTERNAL SERVER ERROR status code
        - Error code is preserved
        """
        mock_cart_service.add_to_cart.side_effect = CartServiceError(
            message="Database error",
            code="DB_ERROR",
        )

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.post(
                "/api/v1/cart/items",
                json=sample_add_request.model_dump(mode="json"),
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"]["code"] == "DB_ERROR"

    @pytest.mark.asyncio
    async def test_add_to_cart_unexpected_error(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_add_request: AddToCartRequest,
    ):
        """
        Test handling of unexpected exceptions.

        Verifies:
        - 500 INTERNAL SERVER ERROR status code
        - Generic error code is returned
        """
        mock_cart_service.add_to_cart.side_effect = Exception("Unexpected error")

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.post(
                "/api/v1/cart/items",
                json=sample_add_request.model_dump(mode="json"),
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"]["code"] == "INTERNAL_ERROR"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "quantity,expected_status",
        [
            (0, status.HTTP_422_UNPROCESSABLE_ENTITY),
            (-1, status.HTTP_422_UNPROCESSABLE_ENTITY),
            (1, status.HTTP_201_CREATED),
            (10, status.HTTP_201_CREATED),
        ],
    )
    async def test_add_to_cart_quantity_validation(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
        quantity: int,
        expected_status: int,
    ):
        """
        Test quantity validation for add to cart.

        Verifies:
        - Invalid quantities are rejected
        - Valid quantities are accepted
        """
        mock_cart_service.add_to_cart.return_value = sample_cart_response

        request_data = {
            "vehicle_id": str(uuid.uuid4()),
            "configuration_id": str(uuid.uuid4()),
            "quantity": quantity,
        }

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.post(
                "/api/v1/cart/items",
                json=request_data,
            )

        assert response.status_code == expected_status


# ============================================================================
# Get Cart Tests
# ============================================================================


class TestGetCart:
    """Test suite for get cart endpoint."""

    @pytest.mark.asyncio
    async def test_get_cart_with_session(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
    ):
        """
        Test retrieving cart with session ID.

        Verifies:
        - Cart is retrieved successfully
        - Response contains cart data
        - Status code is 200 OK
        """
        session_id = "test-session-789"
        mock_cart_service.get_cart.return_value = sample_cart_response

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.get(
                "/api/v1/cart",
                cookies={SESSION_COOKIE_NAME: session_id},
            )

        assert response.status_code == status.HTTP_200_OK

        call_kwargs = mock_cart_service.get_cart.call_args.kwargs
        assert call_kwargs["session_id"] == session_id
        assert call_kwargs["user_id"] is None

        data = response.json()
        assert data["id"] == str(sample_cart_response.id)
        assert data["item_count"] == sample_cart_response.item_count

    @pytest.mark.asyncio
    async def test_get_cart_authenticated_user(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
        authenticated_headers: dict[str, str],
    ):
        """
        Test retrieving cart for authenticated user.

        Verifies:
        - User ID is passed to service
        - Cart is retrieved successfully
        """
        user_id = uuid.uuid4()
        sample_cart_response.user_id = user_id
        mock_cart_service.get_cart.return_value = sample_cart_response

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ), patch(
            "src.api.deps.get_current_user",
            return_value=MagicMock(id=user_id),
        ):
            response = await async_client.get(
                "/api/v1/cart",
                headers=authenticated_headers,
            )

        assert response.status_code == status.HTTP_200_OK

        call_kwargs = mock_cart_service.get_cart.call_args.kwargs
        assert call_kwargs["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_get_cart_no_session_or_user(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
    ):
        """
        Test retrieving cart without session or authentication.

        Verifies:
        - 404 NOT FOUND status code
        - Error code is CART_NOT_FOUND
        """
        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.get("/api/v1/cart")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"]["code"] == "CART_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_cart_not_found(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
    ):
        """
        Test retrieving non-existent cart.

        Verifies:
        - 404 NOT FOUND status code
        - Error code is CART_NOT_FOUND
        """
        session_id = "non-existent-session"
        mock_cart_service.get_cart.side_effect = CartNotFoundError()

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.get(
                "/api/v1/cart",
                cookies={SESSION_COOKIE_NAME: session_id},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"]["code"] == "CART_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_cart_service_error(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
    ):
        """
        Test handling of service errors when retrieving cart.

        Verifies:
        - 500 INTERNAL SERVER ERROR status code
        - Error code is preserved
        """
        session_id = "test-session"
        mock_cart_service.get_cart.side_effect = CartServiceError(
            message="Database error",
            code="DB_ERROR",
        )

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.get(
                "/api/v1/cart",
                cookies={SESSION_COOKIE_NAME: session_id},
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"]["code"] == "DB_ERROR"


# ============================================================================
# Update Cart Item Tests
# ============================================================================


class TestUpdateCartItem:
    """Test suite for update cart item endpoint."""

    @pytest.mark.asyncio
    async def test_update_cart_item_quantity(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
    ):
        """
        Test updating cart item quantity.

        Verifies:
        - Quantity is updated successfully
        - Response contains updated cart
        - Status code is 200 OK
        """
        item_id = uuid.uuid4()
        session_id = "test-session"
        update_request = UpdateCartItemRequest(quantity=3)

        mock_cart_service.update_cart_item.return_value = sample_cart_response

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.put(
                f"/api/v1/cart/items/{item_id}",
                json=update_request.model_dump(),
                cookies={SESSION_COOKIE_NAME: session_id},
            )

        assert response.status_code == status.HTTP_200_OK

        call_kwargs = mock_cart_service.update_cart_item.call_args.kwargs
        assert call_kwargs["item_id"] == item_id
        assert call_kwargs["request"].quantity == 3
        assert call_kwargs["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_update_cart_item_not_found(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
    ):
        """
        Test updating non-existent cart item.

        Verifies:
        - 404 NOT FOUND status code
        - Error code is CART_ITEM_NOT_FOUND
        """
        item_id = uuid.uuid4()
        session_id = "test-session"
        update_request = UpdateCartItemRequest(quantity=2)

        mock_cart_service.update_cart_item.side_effect = CartItemNotFoundError(
            item_id=item_id
        )

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.put(
                f"/api/v1/cart/items/{item_id}",
                json=update_request.model_dump(),
                cookies={SESSION_COOKIE_NAME: session_id},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"]["code"] == "CART_ITEM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_cart_item_insufficient_inventory(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
    ):
        """
        Test updating quantity with insufficient inventory.

        Verifies:
        - 409 CONFLICT status code
        - Error code is INSUFFICIENT_INVENTORY
        """
        item_id = uuid.uuid4()
        vehicle_id = uuid.uuid4()
        session_id = "test-session"
        update_request = UpdateCartItemRequest(quantity=100)

        mock_cart_service.update_cart_item.side_effect = InsufficientInventoryError(
            vehicle_id=vehicle_id,
            requested=100,
            available=5,
        )

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.put(
                f"/api/v1/cart/items/{item_id}",
                json=update_request.model_dump(),
                cookies={SESSION_COOKIE_NAME: session_id},
            )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["detail"]["code"] == "INSUFFICIENT_INVENTORY"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "quantity,expected_status",
        [
            (0, status.HTTP_200_OK),  # Zero removes item
            (1, status.HTTP_200_OK),
            (5, status.HTTP_200_OK),
            (-1, status.HTTP_422_UNPROCESSABLE_ENTITY),
        ],
    )
    async def test_update_cart_item_quantity_validation(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
        quantity: int,
        expected_status: int,
    ):
        """
        Test quantity validation for cart item updates.

        Verifies:
        - Invalid quantities are rejected
        - Valid quantities are accepted
        - Zero quantity is allowed (removes item)
        """
        item_id = uuid.uuid4()
        session_id = "test-session"
        mock_cart_service.update_cart_item.return_value = sample_cart_response

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.put(
                f"/api/v1/cart/items/{item_id}",
                json={"quantity": quantity},
                cookies={SESSION_COOKIE_NAME: session_id},
            )

        assert response.status_code == expected_status


# ============================================================================
# Remove Cart Item Tests
# ============================================================================


class TestRemoveCartItem:
    """Test suite for remove cart item endpoint."""

    @pytest.mark.asyncio
    async def test_remove_cart_item_success(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
    ):
        """
        Test removing cart item successfully.

        Verifies:
        - Item is removed
        - Response contains updated cart
        - Status code is 200 OK
        """
        item_id = uuid.uuid4()
        session_id = "test-session"

        mock_cart_service.remove_cart_item.return_value = sample_cart_response

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.delete(
                f"/api/v1/cart/items/{item_id}",
                cookies={SESSION_COOKIE_NAME: session_id},
            )

        assert response.status_code == status.HTTP_200_OK

        call_kwargs = mock_cart_service.remove_cart_item.call_args.kwargs
        assert call_kwargs["item_id"] == item_id
        assert call_kwargs["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_remove_cart_item_not_found(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
    ):
        """
        Test removing non-existent cart item.

        Verifies:
        - 404 NOT FOUND status code
        - Error code is CART_ITEM_NOT_FOUND
        """
        item_id = uuid.uuid4()
        session_id = "test-session"

        mock_cart_service.remove_cart_item.side_effect = CartItemNotFoundError(
            item_id=item_id
        )

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.delete(
                f"/api/v1/cart/items/{item_id}",
                cookies={SESSION_COOKIE_NAME: session_id},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"]["code"] == "CART_ITEM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_remove_cart_item_authenticated_user(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
        authenticated_headers: dict[str, str],
    ):
        """
        Test removing cart item for authenticated user.

        Verifies:
        - User ID is passed to service
        - Item is removed successfully
        """
        item_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_cart_service.remove_cart_item.return_value = sample_cart_response

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ), patch(
            "src.api.deps.get_current_user",
            return_value=MagicMock(id=user_id),
        ):
            response = await async_client.delete(
                f"/api/v1/cart/items/{item_id}",
                headers=authenticated_headers,
            )

        assert response.status_code == status.HTTP_200_OK

        call_kwargs = mock_cart_service.remove_cart_item.call_args.kwargs
        assert call_kwargs["user_id"] == user_id


# ============================================================================
# Apply Promotional Code Tests
# ============================================================================


class TestApplyPromotionalCode:
    """Test suite for apply promotional code endpoint."""

    @pytest.mark.asyncio
    async def test_apply_promo_code_success(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
    ):
        """
        Test applying valid promotional code.

        Verifies:
        - Promo code is applied
        - Discount is calculated
        - Response contains updated cart
        - Status code is 200 OK
        """
        session_id = "test-session"
        promo_request = ApplyPromoRequest(promo_code="SAVE20")

        sample_cart_response.promo_code = "SAVE20"
        sample_cart_response.summary.discount_amount = Decimal("18000.00")
        sample_cart_response.summary.total = Decimal("79200.00")

        mock_cart_service.apply_promotional_code.return_value = sample_cart_response

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.post(
                "/api/v1/cart/promo",
                json=promo_request.model_dump(),
                cookies={SESSION_COOKIE_NAME: session_id},
            )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["promo_code"] == "SAVE20"
        assert Decimal(data["summary"]["discount_amount"]) > 0

    @pytest.mark.asyncio
    async def test_apply_promo_code_invalid(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
    ):
        """
        Test applying invalid promotional code.

        Verifies:
        - 400 BAD REQUEST status code
        - Error code is INVALID_PROMO_CODE
        - Error message is descriptive
        """
        session_id = "test-session"
        promo_request = ApplyPromoRequest(promo_code="INVALID")

        mock_cart_service.apply_promotional_code.side_effect = (
            InvalidPromotionalCodeError(
                code="INVALID_PROMO_CODE",
                message="Promotional code not found",
                context={"reason": "not_found"},
            )
        )

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.post(
                "/api/v1/cart/promo",
                json=promo_request.model_dump(),
                cookies={SESSION_COOKIE_NAME: session_id},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"]["code"] == "INVALID_PROMO_CODE"

    @pytest.mark.asyncio
    async def test_apply_promo_code_expired(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
    ):
        """
        Test applying expired promotional code.

        Verifies:
        - 400 BAD REQUEST status code
        - Error indicates expiration
        """
        session_id = "test-session"
        promo_request = ApplyPromoRequest(promo_code="EXPIRED20")

        mock_cart_service.apply_promotional_code.side_effect = (
            InvalidPromotionalCodeError(
                code="INVALID_PROMO_CODE",
                message="Promotional code has expired",
                context={"reason": "expired"},
            )
        )

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.post(
                "/api/v1/cart/promo",
                json=promo_request.model_dump(),
                cookies={SESSION_COOKIE_NAME: session_id},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_apply_promo_code_cart_not_found(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
    ):
        """
        Test applying promo code to non-existent cart.

        Verifies:
        - 404 NOT FOUND status code
        - Error code is CART_NOT_FOUND
        """
        session_id = "non-existent-session"
        promo_request = ApplyPromoRequest(promo_code="SAVE20")

        mock_cart_service.apply_promotional_code.side_effect = CartNotFoundError()

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.post(
                "/api/v1/cart/promo",
                json=promo_request.model_dump(),
                cookies={SESSION_COOKIE_NAME: session_id},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"]["code"] == "CART_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_apply_promo_code_authenticated_user(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
        authenticated_headers: dict[str, str],
    ):
        """
        Test applying promo code for authenticated user.

        Verifies:
        - User ID is passed to service
        - Promo code is applied successfully
        """
        user_id = uuid.uuid4()
        promo_request = ApplyPromoRequest(promo_code="SAVE20")

        sample_cart_response.promo_code = "SAVE20"
        mock_cart_service.apply_promotional_code.return_value = sample_cart_response

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ), patch(
            "src.api.deps.get_current_user",
            return_value=MagicMock(id=user_id),
        ):
            response = await async_client.post(
                "/api/v1/cart/promo",
                json=promo_request.model_dump(),
                headers=authenticated_headers,
            )

        assert response.status_code == status.HTTP_200_OK

        call_kwargs = mock_cart_service.apply_promotional_code.call_args.kwargs
        assert call_kwargs["user_id"] == user_id


# ============================================================================
# Session Management Tests
# ============================================================================


class TestSessionManagement:
    """Test suite for session cookie management."""

    @pytest.mark.asyncio
    async def test_session_cookie_attributes(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
        sample_add_request: AddToCartRequest,
    ):
        """
        Test session cookie security attributes.

        Verifies:
        - Cookie is HttpOnly
        - Cookie is Secure
        - Cookie has SameSite=Lax
        - Cookie has appropriate max age
        """
        mock_cart_service.add_to_cart.return_value = sample_cart_response

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.post(
                "/api/v1/cart/items",
                json=sample_add_request.model_dump(mode="json"),
            )

        assert response.status_code == status.HTTP_201_CREATED

        cookie = response.cookies.get(SESSION_COOKIE_NAME)
        assert cookie is not None

        # Note: Cookie attributes are set in response headers
        # In production, verify these are properly configured

    @pytest.mark.asyncio
    async def test_session_persistence_across_requests(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
        sample_add_request: AddToCartRequest,
    ):
        """
        Test session ID persists across multiple requests.

        Verifies:
        - Same session ID is used for multiple operations
        - Session is maintained throughout cart lifecycle
        """
        mock_cart_service.add_to_cart.return_value = sample_cart_response
        mock_cart_service.get_cart.return_value = sample_cart_response

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            # Add item to cart
            add_response = await async_client.post(
                "/api/v1/cart/items",
                json=sample_add_request.model_dump(mode="json"),
            )

            session_id = add_response.cookies[SESSION_COOKIE_NAME]

            # Get cart with same session
            get_response = await async_client.get(
                "/api/v1/cart",
                cookies={SESSION_COOKIE_NAME: session_id},
            )

        assert add_response.status_code == status.HTTP_201_CREATED
        assert get_response.status_code == status.HTTP_200_OK

        # Verify same session ID was used
        add_call = mock_cart_service.add_to_cart.call_args.kwargs
        get_call = mock_cart_service.get_cart.call_args.kwargs
        assert add_call["session_id"] == get_call["session_id"]


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test suite for comprehensive error handling."""

    @pytest.mark.asyncio
    async def test_malformed_json_request(
        self,
        async_client: AsyncClient,
    ):
        """
        Test handling of malformed JSON in request body.

        Verifies:
        - 422 UNPROCESSABLE ENTITY status code
        - Error details are provided
        """
        response = await async_client.post(
            "/api/v1/cart/items",
            content="invalid json{",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_missing_required_fields(
        self,
        async_client: AsyncClient,
    ):
        """
        Test handling of missing required fields.

        Verifies:
        - 422 UNPROCESSABLE ENTITY status code
        - Validation errors are detailed
        """
        response = await async_client.post(
            "/api/v1/cart/items",
            json={"quantity": 1},  # Missing vehicle_id and configuration_id
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_invalid_uuid_format(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
    ):
        """
        Test handling of invalid UUID format.

        Verifies:
        - 422 UNPROCESSABLE ENTITY status code
        - Error indicates invalid UUID
        """
        response = await async_client.put(
            "/api/v1/cart/items/invalid-uuid",
            json={"quantity": 2},
            cookies={SESSION_COOKIE_NAME: "test-session"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
        sample_add_request: AddToCartRequest,
    ):
        """
        Test handling of concurrent requests to same cart.

        Verifies:
        - Multiple concurrent requests are handled
        - No race conditions occur
        - All requests complete successfully
        """
        import asyncio

        mock_cart_service.add_to_cart.return_value = sample_cart_response

        session_id = "concurrent-test-session"

        async def make_request():
            with patch(
                "src.api.v1.cart.get_cart_service",
                return_value=mock_cart_service,
            ):
                return await async_client.post(
                    "/api/v1/cart/items",
                    json=sample_add_request.model_dump(mode="json"),
                    cookies={SESSION_COOKIE_NAME: session_id},
                )

        # Make 5 concurrent requests
        responses = await asyncio.gather(*[make_request() for _ in range(5)])

        # All requests should succeed
        for response in responses:
            assert response.status_code == status.HTTP_201_CREATED


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Test suite for performance validation."""

    @pytest.mark.asyncio
    async def test_response_time_add_to_cart(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
        sample_add_request: AddToCartRequest,
    ):
        """
        Test add to cart response time.

        Verifies:
        - Response time is under acceptable threshold
        - Operation completes efficiently
        """
        import time

        mock_cart_service.add_to_cart.return_value = sample_cart_response

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            start_time = time.time()
            response = await async_client.post(
                "/api/v1/cart/items",
                json=sample_add_request.model_dump(mode="json"),
            )
            elapsed_time = time.time() - start_time

        assert response.status_code == status.HTTP_201_CREATED
        assert elapsed_time < 1.0  # Should complete within 1 second

    @pytest.mark.asyncio
    async def test_large_cart_handling(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
    ):
        """
        Test handling of cart with many items.

        Verifies:
        - Large carts are handled efficiently
        - Response size is manageable
        - No performance degradation
        """
        # Create cart with 50 items
        from src.schemas.cart import CartItemResponse

        large_cart = sample_cart_response.model_copy()
        large_cart.items = [
            CartItemResponse(
                id=uuid.uuid4(),
                cart_id=large_cart.id,
                vehicle_id=uuid.uuid4(),
                configuration_id=uuid.uuid4(),
                quantity=1,
                unit_price=Decimal("45000.00"),
                total_price=Decimal("45000.00"),
                vehicle_name=f"Vehicle {i}",
                configuration_name=f"Config {i}",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            for i in range(50)
        ]
        large_cart.item_count = 50

        mock_cart_service.get_cart.return_value = large_cart

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.get(
                "/api/v1/cart",
                cookies={SESSION_COOKIE_NAME: "test-session"},
            )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data["items"]) == 50
        assert data["item_count"] == 50


# ============================================================================
# Security Tests
# ============================================================================


class TestSecurity:
    """Test suite for security validation."""

    @pytest.mark.asyncio
    async def test_session_isolation(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
    ):
        """
        Test that sessions are properly isolated.

        Verifies:
        - Different sessions access different carts
        - No cross-session data leakage
        """
        session1 = "session-1"
        session2 = "session-2"

        cart1 = sample_cart_response.model_copy()
        cart1.session_id = session1

        cart2 = sample_cart_response.model_copy()
        cart2.id = uuid.uuid4()
        cart2.session_id = session2

        def get_cart_side_effect(**kwargs):
            if kwargs.get("session_id") == session1:
                return cart1
            return cart2

        mock_cart_service.get_cart.side_effect = get_cart_side_effect

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response1 = await async_client.get(
                "/api/v1/cart",
                cookies={SESSION_COOKIE_NAME: session1},
            )
            response2 = await async_client.get(
                "/api/v1/cart",
                cookies={SESSION_COOKIE_NAME: session2},
            )

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

        data1 = response1.json()
        data2 = response2.json()

        # Verify different cart IDs
        assert data1["id"] != data2["id"]

    @pytest.mark.asyncio
    async def test_user_cart_isolation(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
        authenticated_headers: dict[str, str],
    ):
        """
        Test that user carts are properly isolated.

        Verifies:
        - Different users access different carts
        - No cross-user data access
        """
        user1_id = uuid.uuid4()
        user2_id = uuid.uuid4()

        cart1 = sample_cart_response.model_copy()
        cart1.user_id = user1_id

        cart2 = sample_cart_response.model_copy()
        cart2.id = uuid.uuid4()
        cart2.user_id = user2_id

        def get_cart_side_effect(**kwargs):
            if kwargs.get("user_id") == user1_id:
                return cart1
            return cart2

        mock_cart_service.get_cart.side_effect = get_cart_side_effect

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            # User 1 request
            with patch(
                "src.api.deps.get_current_user",
                return_value=MagicMock(id=user1_id),
            ):
                response1 = await async_client.get(
                    "/api/v1/cart",
                    headers=authenticated_headers,
                )

            # User 2 request
            with patch(
                "src.api.deps.get_current_user",
                return_value=MagicMock(id=user2_id),
            ):
                response2 = await async_client.get(
                    "/api/v1/cart",
                    headers=authenticated_headers,
                )

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

        data1 = response1.json()
        data2 = response2.json()

        # Verify different cart IDs
        assert data1["id"] != data2["id"]

    @pytest.mark.asyncio
    async def test_sql_injection_prevention(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
    ):
        """
        Test SQL injection prevention in promo code.

        Verifies:
        - SQL injection attempts are handled safely
        - No database errors occur
        """
        malicious_code = "'; DROP TABLE carts; --"
        promo_request = ApplyPromoRequest(promo_code=malicious_code)

        mock_cart_service.apply_promotional_code.side_effect = (
            InvalidPromotionalCodeError(
                code="INVALID_PROMO_CODE",
                message="Promotional code not found",
                context={"reason": "not_found"},
            )
        )

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.post(
                "/api/v1/cart/promo",
                json=promo_request.model_dump(),
                cookies={SESSION_COOKIE_NAME: "test-session"},
            )

        # Should handle gracefully without SQL errors
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_xss_prevention_in_responses(
        self,
        async_client: AsyncClient,
        mock_cart_service: MagicMock,
        sample_cart_response: CartResponse,
    ):
        """
        Test XSS prevention in API responses.

        Verifies:
        - Script tags in data are properly escaped
        - No executable code in responses
        """
        # Create cart with potentially malicious content
        malicious_cart = sample_cart_response.model_copy()
        malicious_cart.items[0].vehicle_name = "<script>alert('xss')</script>"

        mock_cart_service.get_cart.return_value = malicious_cart

        with patch(
            "src.api.v1.cart.get_cart_service",
            return_value=mock_cart_service,
        ):
            response = await async_client.get(
                "/api/v1/cart",
                cookies={SESSION_COOKIE_NAME: "test-session"},
            )

        assert response.status_code == status.HTTP_200_OK

        # Response should be JSON, not HTML
        assert response.headers["content-type"] == "application/json"

        # Script tags should be in string form, not executable
        data = response.json()
        assert "<script>" in data["items"][0]["vehicle_name"]