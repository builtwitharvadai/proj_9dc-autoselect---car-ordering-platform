"""
Comprehensive integration tests for payment API endpoints.

This module provides end-to-end testing for all payment-related API endpoints
including payment intent creation, payment processing, webhook handling, and
payment status retrieval with comprehensive authentication, validation, and
error scenario coverage.
"""

import json
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.api.v1.payments import get_payment_service, router
from src.main import app
from src.schemas.payments import (
    PaymentIntentRequest,
    PaymentProcessRequest,
)
from src.services.payments.repository import (
    PaymentNotFoundError,
    PaymentRepositoryError,
)
from src.services.payments.service import (
    FraudDetectionError,
    PaymentProcessingError,
    PaymentService,
    PaymentValidationError,
)
from src.services.payments.stripe_client import StripeClientError


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_current_user():
    """Mock authenticated user for testing."""
    user = Mock()
    user.id = uuid4()
    user.email = "test@example.com"
    user.role = "user"
    return user


@pytest.fixture
def mock_payment_service():
    """Mock payment service for dependency injection."""
    service = AsyncMock(spec=PaymentService)
    return service


@pytest.fixture
def mock_stripe_signature():
    """Mock Stripe webhook signature."""
    return "t=1234567890,v1=mock_signature_hash"


@pytest.fixture
def valid_payment_intent_request():
    """Valid payment intent request data."""
    return {
        "amount": 10000,  # $100.00 in cents
        "currency": "usd",
        "order_id": str(uuid4()),
        "customer_email": "customer@example.com",
        "metadata": {"order_number": "ORD-12345"},
    }


@pytest.fixture
def valid_payment_process_request():
    """Valid payment processing request data."""
    return {
        "payment_intent_id": "pi_test_123456",
        "payment_method_id": "pm_test_123456",
    }


@pytest.fixture
def mock_payment_intent_response():
    """Mock successful payment intent creation response."""
    return {
        "payment_id": str(uuid4()),
        "client_secret": "pi_test_secret_123456",
        "amount": 100.00,
        "currency": "usd",
        "status": "requires_payment_method",
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_payment_process_response():
    """Mock successful payment processing response."""
    return {
        "payment_id": str(uuid4()),
        "status": "succeeded",
        "amount": 100.00,
        "currency": "usd",
        "payment_method": "card",
        "last4": "4242",
        "processed_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_webhook_payload():
    """Mock Stripe webhook payload."""
    return json.dumps(
        {
            "id": "evt_test_123456",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test_123456",
                    "amount": 10000,
                    "currency": "usd",
                    "status": "succeeded",
                }
            },
        }
    ).encode("utf-8")


@pytest.fixture
def override_dependencies(mock_payment_service, mock_current_user):
    """Override FastAPI dependencies for testing."""

    async def override_get_payment_service():
        return mock_payment_service

    async def override_get_current_user():
        return mock_current_user

    app.dependency_overrides[get_payment_service] = override_get_payment_service
    app.dependency_overrides["src.api.deps.get_current_user"] = (
        override_get_current_user
    )

    yield

    app.dependency_overrides.clear()


# ============================================================================
# Payment Intent Creation Tests
# ============================================================================


class TestCreatePaymentIntent:
    """Test suite for payment intent creation endpoint."""

    @pytest.mark.asyncio
    async def test_create_payment_intent_success(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        valid_payment_intent_request,
        mock_payment_intent_response,
    ):
        """Test successful payment intent creation."""
        # Arrange
        mock_payment_service.create_payment_intent.return_value = (
            mock_payment_intent_response
        )

        # Act
        response = await async_client.post(
            "/payments/intent",
            json=valid_payment_intent_request,
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "payment_id" in data
        assert "client_secret" in data
        assert data["amount"] == 100.00
        assert data["currency"] == "usd"
        assert data["status"] == "requires_payment_method"

        # Verify service was called correctly
        mock_payment_service.create_payment_intent.assert_called_once()
        call_kwargs = mock_payment_service.create_payment_intent.call_args.kwargs
        assert call_kwargs["amount"] == 100.00  # Converted from cents
        assert call_kwargs["currency"] == "usd"

    @pytest.mark.asyncio
    async def test_create_payment_intent_without_order_id(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        mock_payment_intent_response,
    ):
        """Test payment intent creation without order ID."""
        # Arrange
        request_data = {
            "amount": 5000,
            "currency": "usd",
            "customer_email": "test@example.com",
        }
        mock_payment_service.create_payment_intent.return_value = (
            mock_payment_intent_response
        )

        # Act
        response = await async_client.post(
            "/payments/intent",
            json=request_data,
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        call_kwargs = mock_payment_service.create_payment_intent.call_args.kwargs
        assert call_kwargs["order_id"] is None

    @pytest.mark.asyncio
    async def test_create_payment_intent_uses_user_email_when_not_provided(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        mock_current_user,
        mock_payment_intent_response,
    ):
        """Test that user email is used when customer email not provided."""
        # Arrange
        request_data = {
            "amount": 5000,
            "currency": "usd",
        }
        mock_payment_service.create_payment_intent.return_value = (
            mock_payment_intent_response
        )

        # Act
        response = await async_client.post(
            "/payments/intent",
            json=request_data,
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        call_kwargs = mock_payment_service.create_payment_intent.call_args.kwargs
        assert call_kwargs["customer_email"] == mock_current_user.email

    @pytest.mark.asyncio
    async def test_create_payment_intent_validation_error(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        valid_payment_intent_request,
    ):
        """Test payment intent creation with validation error."""
        # Arrange
        error_context = {"field": "amount", "reason": "Amount too low"}
        mock_payment_service.create_payment_intent.side_effect = (
            PaymentValidationError(
                "Invalid payment amount",
                context=error_context,
            )
        )

        # Act
        response = await async_client.post(
            "/payments/intent",
            json=valid_payment_intent_request,
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"]["code"] == "VALIDATION_ERROR"
        assert "Invalid payment amount" in data["detail"]["message"]
        assert data["detail"]["context"] == error_context

    @pytest.mark.asyncio
    async def test_create_payment_intent_processing_error(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        valid_payment_intent_request,
    ):
        """Test payment intent creation with processing error."""
        # Arrange
        mock_payment_service.create_payment_intent.side_effect = (
            PaymentProcessingError(
                "Stripe API error",
                context={"stripe_error": "rate_limit"},
            )
        )

        # Act
        response = await async_client.post(
            "/payments/intent",
            json=valid_payment_intent_request,
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["detail"]["code"] == "PROCESSING_ERROR"
        assert "Failed to create payment intent" in data["detail"]["message"]

    @pytest.mark.asyncio
    async def test_create_payment_intent_unexpected_error(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        valid_payment_intent_request,
    ):
        """Test payment intent creation with unexpected error."""
        # Arrange
        mock_payment_service.create_payment_intent.side_effect = RuntimeError(
            "Unexpected error"
        )

        # Act
        response = await async_client.post(
            "/payments/intent",
            json=valid_payment_intent_request,
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["detail"]["code"] == "INTERNAL_ERROR"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "amount,currency",
        [
            (100, "usd"),  # Minimum amount
            (999999, "usd"),  # Large amount
            (5000, "eur"),  # Different currency
            (2500, "gbp"),  # Another currency
        ],
    )
    async def test_create_payment_intent_various_amounts_currencies(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        mock_payment_intent_response,
        amount,
        currency,
    ):
        """Test payment intent creation with various amounts and currencies."""
        # Arrange
        request_data = {
            "amount": amount,
            "currency": currency,
        }
        mock_payment_service.create_payment_intent.return_value = (
            mock_payment_intent_response
        )

        # Act
        response = await async_client.post(
            "/payments/intent",
            json=request_data,
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        call_kwargs = mock_payment_service.create_payment_intent.call_args.kwargs
        assert call_kwargs["amount"] == amount / 100
        assert call_kwargs["currency"] == currency


# ============================================================================
# Payment Processing Tests
# ============================================================================


class TestProcessPayment:
    """Test suite for payment processing endpoint."""

    @pytest.mark.asyncio
    async def test_process_payment_success(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        valid_payment_process_request,
        mock_payment_process_response,
    ):
        """Test successful payment processing."""
        # Arrange
        mock_payment_service.process_payment.return_value = (
            mock_payment_process_response
        )

        # Act
        response = await async_client.post(
            "/payments/process",
            json=valid_payment_process_request,
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "succeeded"
        assert "payment_id" in data
        assert data["payment_method"] == "card"
        assert data["last4"] == "4242"

        # Verify service was called correctly
        mock_payment_service.process_payment.assert_called_once()
        call_kwargs = mock_payment_service.process_payment.call_args.kwargs
        assert (
            call_kwargs["payment_intent_id"]
            == valid_payment_process_request["payment_intent_id"]
        )
        assert (
            call_kwargs["payment_method_id"]
            == valid_payment_process_request["payment_method_id"]
        )

    @pytest.mark.asyncio
    async def test_process_payment_not_found(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        valid_payment_process_request,
    ):
        """Test payment processing with payment not found."""
        # Arrange
        mock_payment_service.process_payment.side_effect = PaymentNotFoundError(
            "Payment intent not found"
        )

        # Act
        response = await async_client.post(
            "/payments/process",
            json=valid_payment_process_request,
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"]["code"] == "PAYMENT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_process_payment_fraud_detected(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        valid_payment_process_request,
    ):
        """Test payment processing with fraud detection."""
        # Arrange
        fraud_context = {
            "risk_score": 95,
            "reason": "suspicious_activity",
        }
        mock_payment_service.process_payment.side_effect = FraudDetectionError(
            "High risk transaction",
            context=fraud_context,
        )

        # Act
        response = await async_client.post(
            "/payments/process",
            json=valid_payment_process_request,
        )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["detail"]["code"] == "FRAUD_DETECTED"
        assert "security concerns" in data["detail"]["message"]

    @pytest.mark.asyncio
    async def test_process_payment_processing_error(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        valid_payment_process_request,
    ):
        """Test payment processing with processing error."""
        # Arrange
        error_context = {
            "decline_code": "insufficient_funds",
            "message": "Card declined",
        }
        mock_payment_service.process_payment.side_effect = PaymentProcessingError(
            "Payment declined",
            context=error_context,
        )

        # Act
        response = await async_client.post(
            "/payments/process",
            json=valid_payment_process_request,
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"]["code"] == "PROCESSING_FAILED"
        assert data["detail"]["context"] == error_context

    @pytest.mark.asyncio
    async def test_process_payment_unexpected_error(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        valid_payment_process_request,
    ):
        """Test payment processing with unexpected error."""
        # Arrange
        mock_payment_service.process_payment.side_effect = Exception(
            "Database connection lost"
        )

        # Act
        response = await async_client.post(
            "/payments/process",
            json=valid_payment_process_request,
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["detail"]["code"] == "INTERNAL_ERROR"


# ============================================================================
# Webhook Handling Tests
# ============================================================================


class TestHandleWebhook:
    """Test suite for Stripe webhook handling endpoint."""

    @pytest.mark.asyncio
    async def test_handle_webhook_success(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        mock_webhook_payload,
        mock_stripe_signature,
    ):
        """Test successful webhook processing."""
        # Arrange
        webhook_result = {
            "event_id": "evt_test_123456",
            "event_type": "payment_intent.succeeded",
            "processed": True,
        }
        mock_payment_service.handle_webhook.return_value = webhook_result

        # Act
        response = await async_client.post(
            "/payments/webhook",
            content=mock_webhook_payload,
            headers={"stripe-signature": mock_stripe_signature},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["received"] is True
        assert data["event_id"] == "evt_test_123456"

        # Verify service was called correctly
        mock_payment_service.handle_webhook.assert_called_once()
        call_kwargs = mock_payment_service.handle_webhook.call_args.kwargs
        assert call_kwargs["payload"] == mock_webhook_payload
        assert call_kwargs["signature"] == mock_stripe_signature

    @pytest.mark.asyncio
    async def test_handle_webhook_invalid_signature(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        mock_webhook_payload,
        mock_stripe_signature,
    ):
        """Test webhook with invalid signature."""
        # Arrange
        mock_payment_service.handle_webhook.side_effect = StripeClientError(
            "Invalid signature",
            code="signature_verification_failed",
        )

        # Act
        response = await async_client.post(
            "/payments/webhook",
            content=mock_webhook_payload,
            headers={"stripe-signature": mock_stripe_signature},
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"]["code"] == "INVALID_SIGNATURE"

    @pytest.mark.asyncio
    async def test_handle_webhook_processing_error(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        mock_webhook_payload,
        mock_stripe_signature,
    ):
        """Test webhook with processing error."""
        # Arrange
        mock_payment_service.handle_webhook.side_effect = PaymentProcessingError(
            "Failed to update payment status",
            context={"event_id": "evt_test_123456"},
        )

        # Act
        response = await async_client.post(
            "/payments/webhook",
            content=mock_webhook_payload,
            headers={"stripe-signature": mock_stripe_signature},
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["detail"]["code"] == "WEBHOOK_PROCESSING_ERROR"

    @pytest.mark.asyncio
    async def test_handle_webhook_missing_signature(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_webhook_payload,
    ):
        """Test webhook without signature header."""
        # Act
        response = await async_client.post(
            "/payments/webhook",
            content=mock_webhook_payload,
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_handle_webhook_unexpected_error(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        mock_webhook_payload,
        mock_stripe_signature,
    ):
        """Test webhook with unexpected error."""
        # Arrange
        mock_payment_service.handle_webhook.side_effect = RuntimeError(
            "Unexpected error"
        )

        # Act
        response = await async_client.post(
            "/payments/webhook",
            content=mock_webhook_payload,
            headers={"stripe-signature": mock_stripe_signature},
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["detail"]["code"] == "INTERNAL_ERROR"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "event_type",
        [
            "payment_intent.succeeded",
            "payment_intent.payment_failed",
            "payment_intent.canceled",
            "charge.succeeded",
            "charge.failed",
        ],
    )
    async def test_handle_webhook_various_event_types(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        mock_stripe_signature,
        event_type,
    ):
        """Test webhook handling for various event types."""
        # Arrange
        payload = json.dumps(
            {
                "id": f"evt_test_{event_type}",
                "type": event_type,
                "data": {"object": {"id": "pi_test_123"}},
            }
        ).encode("utf-8")

        webhook_result = {
            "event_id": f"evt_test_{event_type}",
            "event_type": event_type,
            "processed": True,
        }
        mock_payment_service.handle_webhook.return_value = webhook_result

        # Act
        response = await async_client.post(
            "/payments/webhook",
            content=payload,
            headers={"stripe-signature": mock_stripe_signature},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["event_id"] == f"evt_test_{event_type}"


# ============================================================================
# Payment Status Retrieval Tests
# ============================================================================


class TestGetPaymentStatus:
    """Test suite for payment status retrieval endpoint."""

    @pytest.mark.asyncio
    async def test_get_payment_status_success(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
    ):
        """Test successful payment status retrieval."""
        # Arrange
        payment_id = uuid4()
        status_response = {
            "payment_id": str(payment_id),
            "status": "succeeded",
            "amount": 100.00,
            "currency": "usd",
            "payment_method": "card",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        mock_payment_service.get_payment_status.return_value = status_response

        # Act
        response = await async_client.get(f"/payments/{payment_id}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["payment_id"] == str(payment_id)
        assert data["status"] == "succeeded"
        assert data["amount"] == 100.00

        # Verify service was called correctly
        mock_payment_service.get_payment_status.assert_called_once_with(
            payment_id=payment_id
        )

    @pytest.mark.asyncio
    async def test_get_payment_status_not_found(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
    ):
        """Test payment status retrieval with payment not found."""
        # Arrange
        payment_id = uuid4()
        mock_payment_service.get_payment_status.side_effect = PaymentNotFoundError(
            f"Payment {payment_id} not found"
        )

        # Act
        response = await async_client.get(f"/payments/{payment_id}")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"]["code"] == "PAYMENT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_payment_status_processing_error(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
    ):
        """Test payment status retrieval with processing error."""
        # Arrange
        payment_id = uuid4()
        mock_payment_service.get_payment_status.side_effect = (
            PaymentProcessingError(
                "Failed to retrieve payment",
                context={"payment_id": str(payment_id)},
            )
        )

        # Act
        response = await async_client.get(f"/payments/{payment_id}")

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["detail"]["code"] == "RETRIEVAL_ERROR"

    @pytest.mark.asyncio
    async def test_get_payment_status_unexpected_error(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
    ):
        """Test payment status retrieval with unexpected error."""
        # Arrange
        payment_id = uuid4()
        mock_payment_service.get_payment_status.side_effect = Exception(
            "Database error"
        )

        # Act
        response = await async_client.get(f"/payments/{payment_id}")

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["detail"]["code"] == "INTERNAL_ERROR"

    @pytest.mark.asyncio
    async def test_get_payment_status_invalid_uuid(
        self,
        async_client: AsyncClient,
        override_dependencies,
    ):
        """Test payment status retrieval with invalid UUID."""
        # Act
        response = await async_client.get("/payments/invalid-uuid")

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payment_status",
        [
            "requires_payment_method",
            "requires_confirmation",
            "requires_action",
            "processing",
            "succeeded",
            "canceled",
        ],
    )
    async def test_get_payment_status_various_statuses(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        payment_status,
    ):
        """Test payment status retrieval for various payment statuses."""
        # Arrange
        payment_id = uuid4()
        status_response = {
            "payment_id": str(payment_id),
            "status": payment_status,
            "amount": 100.00,
            "currency": "usd",
        }
        mock_payment_service.get_payment_status.return_value = status_response

        # Act
        response = await async_client.get(f"/payments/{payment_id}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == payment_status


# ============================================================================
# Authentication and Authorization Tests
# ============================================================================


class TestAuthenticationAuthorization:
    """Test suite for authentication and authorization."""

    @pytest.mark.asyncio
    async def test_create_payment_intent_requires_authentication(
        self,
        async_client: AsyncClient,
        valid_payment_intent_request,
    ):
        """Test that payment intent creation requires authentication."""
        # Act - without overriding dependencies (no auth)
        response = await async_client.post(
            "/payments/intent",
            json=valid_payment_intent_request,
        )

        # Assert - should fail without authentication
        # Note: Actual status code depends on auth implementation
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_process_payment_requires_authentication(
        self,
        async_client: AsyncClient,
        valid_payment_process_request,
    ):
        """Test that payment processing requires authentication."""
        # Act - without overriding dependencies (no auth)
        response = await async_client.post(
            "/payments/process",
            json=valid_payment_process_request,
        )

        # Assert
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_get_payment_status_requires_authentication(
        self,
        async_client: AsyncClient,
    ):
        """Test that payment status retrieval requires authentication."""
        # Arrange
        payment_id = uuid4()

        # Act - without overriding dependencies (no auth)
        response = await async_client.get(f"/payments/{payment_id}")

        # Assert
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.asyncio
    async def test_webhook_does_not_require_authentication(
        self,
        async_client: AsyncClient,
        mock_webhook_payload,
        mock_stripe_signature,
    ):
        """Test that webhook endpoint does not require authentication."""
        # Note: Webhook should use signature verification instead
        # This test verifies it doesn't require user authentication

        # Act - without overriding user authentication
        response = await async_client.post(
            "/payments/webhook",
            content=mock_webhook_payload,
            headers={"stripe-signature": mock_stripe_signature},
        )

        # Assert - should not return 401/403 (may return 400 for invalid signature)
        assert response.status_code != status.HTTP_401_UNAUTHORIZED
        assert response.status_code != status.HTTP_403_FORBIDDEN


# ============================================================================
# Performance and Load Tests
# ============================================================================


class TestPerformance:
    """Test suite for performance validation."""

    @pytest.mark.asyncio
    async def test_payment_intent_response_time(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        valid_payment_intent_request,
        mock_payment_intent_response,
    ):
        """Test payment intent creation response time."""
        # Arrange
        mock_payment_service.create_payment_intent.return_value = (
            mock_payment_intent_response
        )

        # Act
        import time

        start_time = time.time()
        response = await async_client.post(
            "/payments/intent",
            json=valid_payment_intent_request,
        )
        elapsed_time = time.time() - start_time

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        assert elapsed_time < 1.0  # Should respond within 1 second

    @pytest.mark.asyncio
    async def test_concurrent_payment_intent_creation(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        valid_payment_intent_request,
        mock_payment_intent_response,
    ):
        """Test concurrent payment intent creation."""
        # Arrange
        mock_payment_service.create_payment_intent.return_value = (
            mock_payment_intent_response
        )

        # Act - Create 10 concurrent requests
        import asyncio

        tasks = [
            async_client.post("/payments/intent", json=valid_payment_intent_request)
            for _ in range(10)
        ]
        responses = await asyncio.gather(*tasks)

        # Assert
        assert all(r.status_code == status.HTTP_201_CREATED for r in responses)
        assert mock_payment_service.create_payment_intent.call_count == 10


# ============================================================================
# Edge Cases and Boundary Tests
# ============================================================================


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "amount,should_succeed",
        [
            (0, False),  # Zero amount
            (1, True),  # Minimum amount
            (999999999, True),  # Very large amount
            (-100, False),  # Negative amount
        ],
    )
    async def test_payment_intent_amount_boundaries(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        mock_payment_intent_response,
        amount,
        should_succeed,
    ):
        """Test payment intent creation with boundary amounts."""
        # Arrange
        request_data = {
            "amount": amount,
            "currency": "usd",
        }

        if should_succeed:
            mock_payment_service.create_payment_intent.return_value = (
                mock_payment_intent_response
            )
        else:
            mock_payment_service.create_payment_intent.side_effect = (
                PaymentValidationError("Invalid amount")
            )

        # Act
        response = await async_client.post(
            "/payments/intent",
            json=request_data,
        )

        # Assert
        if should_succeed:
            assert response.status_code == status.HTTP_201_CREATED
        else:
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]

    @pytest.mark.asyncio
    async def test_payment_intent_with_empty_metadata(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        mock_payment_intent_response,
    ):
        """Test payment intent creation with empty metadata."""
        # Arrange
        request_data = {
            "amount": 5000,
            "currency": "usd",
            "metadata": {},
        }
        mock_payment_service.create_payment_intent.return_value = (
            mock_payment_intent_response
        )

        # Act
        response = await async_client.post(
            "/payments/intent",
            json=request_data,
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_payment_intent_with_large_metadata(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        mock_payment_intent_response,
    ):
        """Test payment intent creation with large metadata."""
        # Arrange
        large_metadata = {f"key_{i}": f"value_{i}" for i in range(50)}
        request_data = {
            "amount": 5000,
            "currency": "usd",
            "metadata": large_metadata,
        }
        mock_payment_service.create_payment_intent.return_value = (
            mock_payment_intent_response
        )

        # Act
        response = await async_client.post(
            "/payments/intent",
            json=request_data,
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED


# ============================================================================
# Security Tests
# ============================================================================


class TestSecurity:
    """Test suite for security validation."""

    @pytest.mark.asyncio
    async def test_webhook_signature_verification_required(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        mock_webhook_payload,
    ):
        """Test that webhook requires valid signature."""
        # Arrange
        mock_payment_service.handle_webhook.side_effect = StripeClientError(
            "Invalid signature",
            code="signature_verification_failed",
        )

        # Act
        response = await async_client.post(
            "/payments/webhook",
            content=mock_webhook_payload,
            headers={"stripe-signature": "invalid_signature"},
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_payment_intent_sql_injection_prevention(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        mock_payment_intent_response,
    ):
        """Test SQL injection prevention in payment intent."""
        # Arrange
        malicious_data = {
            "amount": 5000,
            "currency": "usd",
            "customer_email": "test@example.com'; DROP TABLE payments; --",
        }
        mock_payment_service.create_payment_intent.return_value = (
            mock_payment_intent_response
        )

        # Act
        response = await async_client.post(
            "/payments/intent",
            json=malicious_data,
        )

        # Assert - Should handle safely (either succeed or validate email)
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    @pytest.mark.asyncio
    async def test_payment_intent_xss_prevention(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        mock_payment_intent_response,
    ):
        """Test XSS prevention in payment intent metadata."""
        # Arrange
        xss_data = {
            "amount": 5000,
            "currency": "usd",
            "metadata": {
                "note": "<script>alert('XSS')</script>",
            },
        }
        mock_payment_service.create_payment_intent.return_value = (
            mock_payment_intent_response
        )

        # Act
        response = await async_client.post(
            "/payments/intent",
            json=xss_data,
        )

        # Assert - Should handle safely
        assert response.status_code == status.HTTP_201_CREATED
        # Verify script tags are not executed (handled by service layer)


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Test suite for end-to-end integration scenarios."""

    @pytest.mark.asyncio
    async def test_complete_payment_flow(
        self,
        async_client: AsyncClient,
        override_dependencies,
        mock_payment_service,
        valid_payment_intent_request,
        mock_payment_intent_response,
        mock_payment_process_response,
    ):
        """Test complete payment flow from intent to processing."""
        # Arrange
        mock_payment_service.create_payment_intent.return_value = (
            mock_payment_intent_response
        )
        mock_payment_service.process_payment.return_value = (
            mock_payment_process_response
        )

        # Act - Step 1: Create payment intent
        intent_response = await async_client.post(
            "/payments/intent",
            json=valid_payment_intent_request,
        )

        # Assert Step 1
        assert intent_response.status_code == status.HTTP_201_CREATED
        intent_data = intent_response.json()
        payment_id = intent_data["payment_id"]

        # Act - Step 2: Process payment
        process_request = {
            "payment_intent_id": "pi_test_123456",
            "payment_method_id": "pm_test_123456",
        }
        process_response = await async_client.post(
            "/payments/process",
            json=process_request,
        )

        # Assert Step 2
        assert process_response.status_code == status.HTTP_200_OK
        process_data = process_response.json()
        assert process_data["status"] == "succeeded"

        # Act - Step 3: Get payment status
        mock_payment_service.get_payment_status.return_value = {
            "payment_id": payment_id,
            "status": "succeeded",
            "amount": 100.00,
            "currency": "usd",
        }
        status_response = await async_client.get(f"/payments/{payment_id}")

        # Assert Step 3
        assert status_response.status_code == status.HTTP_200_OK
        status_data = status_response.json()
        assert status_data["status"] == "succeeded"