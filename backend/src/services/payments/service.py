"""
Payment service orchestrating Stripe integration and business logic.

This module implements the PaymentService class for managing payment operations
including creating payment intents, processing payments, handling webhooks, and
managing payment status with comprehensive error handling, fraud detection, and
retry logic.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any

import stripe

from src.core.logging import get_logger
from src.database.models.payment import PaymentStatus, PaymentMethodType
from src.services.payments.repository import (
    PaymentRepository,
    PaymentNotFoundError,
    PaymentRepositoryError,
)
from src.services.payments.stripe_client import (
    StripeClient,
    StripeClientError,
    StripePaymentError,
    StripeAuthenticationError,
    StripeRateLimitError,
    StripeConnectionError,
)

logger = get_logger(__name__)


class PaymentServiceError(Exception):
    """Base exception for payment service errors."""

    def __init__(self, message: str, **context: Any):
        super().__init__(message)
        self.context = context


class PaymentProcessingError(PaymentServiceError):
    """Exception for payment processing failures."""

    pass


class PaymentValidationError(PaymentServiceError):
    """Exception for payment validation failures."""

    pass


class FraudDetectionError(PaymentServiceError):
    """Exception for fraud detection failures."""

    pass


class PaymentService:
    """
    Payment service orchestrating Stripe integration and business logic.

    Provides methods for creating payment intents, processing payments,
    handling webhooks, and managing payment status with fraud detection,
    retry logic, and comprehensive error handling.

    Attributes:
        repository: Payment repository for data access
        stripe_client: Stripe API client wrapper
    """

    def __init__(
        self,
        repository: PaymentRepository,
        stripe_client: Optional[StripeClient] = None,
    ):
        """
        Initialize payment service.

        Args:
            repository: Payment repository instance
            stripe_client: Optional Stripe client (creates default if None)
        """
        self.repository = repository
        self.stripe_client = stripe_client or StripeClient()

        logger.info(
            "PaymentService initialized",
            has_custom_stripe_client=stripe_client is not None,
        )

    async def create_payment_intent(
        self,
        order_id: uuid.UUID,
        amount: Decimal,
        currency: str,
        customer_email: Optional[str] = None,
        metadata: Optional[dict[str, str]] = None,
        created_by: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create payment intent for order.

        Args:
            order_id: Order identifier
            amount: Payment amount in currency units
            currency: Three-letter ISO currency code
            customer_email: Customer email for receipt
            metadata: Additional payment metadata
            created_by: User who created this payment

        Returns:
            Dictionary containing payment intent details

        Raises:
            PaymentValidationError: If payment parameters are invalid
            PaymentProcessingError: If payment intent creation fails
        """
        logger.info(
            "Creating payment intent",
            order_id=str(order_id),
            amount=float(amount),
            currency=currency,
        )

        try:
            # Validate payment amount
            self._validate_payment_amount(amount, currency)

            # Convert amount to cents for Stripe
            amount_cents = int(amount * 100)

            # Generate idempotency key for safe retries
            idempotency_key = f"order_{order_id}_intent_{uuid.uuid4()}"

            # Create payment intent with Stripe
            payment_intent = self.stripe_client.create_payment_intent(
                amount=amount_cents,
                currency=currency,
                order_id=order_id,
                customer_email=customer_email,
                metadata=metadata,
                idempotency_key=idempotency_key,
            )

            # Create payment record in database
            payment = await self.repository.create_payment(
                order_id=order_id,
                stripe_payment_intent_id=payment_intent.id,
                amount=amount,
                currency=currency,
                payment_method_type=PaymentMethodType.CARD,
                metadata=metadata or {},
                created_by=created_by,
            )

            logger.info(
                "Payment intent created successfully",
                payment_id=str(payment.id),
                stripe_payment_intent_id=payment_intent.id,
                amount=float(amount),
            )

            return {
                "payment_id": str(payment.id),
                "payment_intent_id": payment_intent.id,
                "client_secret": payment_intent.client_secret,
                "amount": float(amount),
                "currency": currency,
                "status": payment.status.value,
            }

        except (StripeAuthenticationError, StripeRateLimitError) as e:
            logger.error(
                "Stripe API error creating payment intent",
                order_id=str(order_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise PaymentProcessingError(
                "Payment service temporarily unavailable",
                order_id=str(order_id),
                error=str(e),
            ) from e

        except StripeClientError as e:
            logger.error(
                "Stripe client error creating payment intent",
                order_id=str(order_id),
                error=str(e),
                error_code=e.code,
            )
            raise PaymentProcessingError(
                f"Failed to create payment intent: {e}",
                order_id=str(order_id),
                error_code=e.code,
            ) from e

        except PaymentRepositoryError as e:
            logger.error(
                "Database error creating payment record",
                order_id=str(order_id),
                error=str(e),
            )
            raise PaymentProcessingError(
                "Failed to create payment record",
                order_id=str(order_id),
                error=str(e),
            ) from e

    async def process_payment(
        self,
        payment_intent_id: str,
        payment_method_id: str,
        updated_by: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Process payment with payment method.

        Args:
            payment_intent_id: Stripe payment intent ID
            payment_method_id: Stripe payment method ID
            updated_by: User who initiated this payment

        Returns:
            Dictionary containing payment processing result

        Raises:
            PaymentNotFoundError: If payment not found
            PaymentProcessingError: If payment processing fails
            FraudDetectionError: If fraud detected
        """
        logger.info(
            "Processing payment",
            payment_intent_id=payment_intent_id,
            payment_method_id=payment_method_id,
        )

        try:
            # Retrieve payment record
            payment = await self.repository.get_payment_by_stripe_intent_id(
                payment_intent_id
            )

            if not payment:
                raise PaymentNotFoundError(
                    "Payment not found",
                    payment_intent_id=payment_intent_id,
                )

            # Check fraud detection
            await self._check_fraud_detection(payment, payment_method_id)

            # Update payment status to processing
            await self.repository.update_payment_status(
                payment_id=payment.id,
                new_status=PaymentStatus.PROCESSING,
                reason="Payment processing started",
                updated_by=updated_by,
            )

            # Generate idempotency key
            idempotency_key = f"payment_{payment.id}_confirm_{uuid.uuid4()}"

            # Confirm payment with Stripe
            confirmed_intent = self.stripe_client.confirm_payment(
                payment_intent_id=payment_intent_id,
                payment_method_id=payment_method_id,
                idempotency_key=idempotency_key,
            )

            # Update payment status based on result
            new_status = self._map_stripe_status_to_payment_status(
                confirmed_intent.status
            )

            payment = await self.repository.update_payment_status(
                payment_id=payment.id,
                new_status=new_status,
                failure_code=getattr(confirmed_intent, "failure_code", None),
                failure_message=getattr(confirmed_intent, "failure_message", None),
                reason=f"Payment {confirmed_intent.status}",
                updated_by=updated_by,
            )

            # Extract payment method details
            payment_method_details = self._extract_payment_method_details(
                confirmed_intent
            )

            logger.info(
                "Payment processed successfully",
                payment_id=str(payment.id),
                status=new_status.value,
                amount=float(payment.amount),
            )

            return {
                "payment_id": str(payment.id),
                "status": payment.status.value,
                "amount": float(payment.amount),
                "currency": payment.currency,
                "payment_method": payment_method_details,
                "failure_code": payment.failure_code,
                "failure_message": payment.failure_message,
            }

        except PaymentNotFoundError:
            raise

        except FraudDetectionError:
            raise

        except StripePaymentError as e:
            logger.warning(
                "Payment declined by Stripe",
                payment_intent_id=payment_intent_id,
                error=str(e),
                decline_code=e.context.get("decline_code"),
            )

            if payment:
                await self.repository.update_payment_status(
                    payment_id=payment.id,
                    new_status=PaymentStatus.FAILED,
                    failure_code=e.code,
                    failure_message=str(e),
                    reason="Payment declined",
                    updated_by=updated_by,
                )

            raise PaymentProcessingError(
                f"Payment declined: {e}",
                payment_intent_id=payment_intent_id,
                decline_code=e.context.get("decline_code"),
            ) from e

        except StripeClientError as e:
            logger.error(
                "Stripe error processing payment",
                payment_intent_id=payment_intent_id,
                error=str(e),
                error_code=e.code,
            )

            if payment:
                await self.repository.update_payment_status(
                    payment_id=payment.id,
                    new_status=PaymentStatus.FAILED,
                    failure_code=e.code,
                    failure_message=str(e),
                    reason="Stripe processing error",
                    updated_by=updated_by,
                )

            raise PaymentProcessingError(
                f"Payment processing failed: {e}",
                payment_intent_id=payment_intent_id,
                error_code=e.code,
            ) from e

        except PaymentRepositoryError as e:
            logger.error(
                "Database error processing payment",
                payment_intent_id=payment_intent_id,
                error=str(e),
            )
            raise PaymentProcessingError(
                "Failed to update payment status",
                payment_intent_id=payment_intent_id,
                error=str(e),
            ) from e

    async def handle_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> dict[str, Any]:
        """
        Handle Stripe webhook event.

        Args:
            payload: Raw webhook payload bytes
            signature: Stripe signature header value

        Returns:
            Dictionary containing webhook processing result

        Raises:
            PaymentProcessingError: If webhook processing fails
        """
        logger.info("Processing Stripe webhook")

        try:
            # Verify and construct webhook event
            event = self.stripe_client.construct_webhook_event(payload, signature)

            logger.info(
                "Webhook event verified",
                event_id=event.id,
                event_type=event.type,
            )

            # Process event based on type
            result = await self._process_webhook_event(event)

            logger.info(
                "Webhook processed successfully",
                event_id=event.id,
                event_type=event.type,
            )

            return {
                "event_id": event.id,
                "event_type": event.type,
                "processed": True,
                "result": result,
            }

        except StripeClientError as e:
            logger.error(
                "Webhook verification failed",
                error=str(e),
                error_code=e.code,
            )
            raise PaymentProcessingError(
                f"Webhook verification failed: {e}",
                error_code=e.code,
            ) from e

        except Exception as e:
            logger.error(
                "Webhook processing failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise PaymentProcessingError(
                f"Webhook processing failed: {e}",
                error=str(e),
            ) from e

    async def get_payment_status(
        self,
        payment_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Get current payment status.

        Args:
            payment_id: Payment identifier

        Returns:
            Dictionary containing payment status details

        Raises:
            PaymentNotFoundError: If payment not found
            PaymentProcessingError: If status retrieval fails
        """
        logger.debug(
            "Retrieving payment status",
            payment_id=str(payment_id),
        )

        try:
            payment = await self.repository.get_payment_by_id(
                payment_id,
                include_history=True,
            )

            if not payment:
                raise PaymentNotFoundError(
                    "Payment not found",
                    payment_id=str(payment_id),
                )

            return {
                "payment_id": str(payment.id),
                "order_id": str(payment.order_id),
                "status": payment.status.value,
                "amount": float(payment.amount),
                "currency": payment.currency,
                "refund_amount": float(payment.refund_amount),
                "payment_method_type": payment.payment_method_type.value,
                "last_four": payment.last_four,
                "card_brand": payment.card_brand,
                "failure_code": payment.failure_code,
                "failure_message": payment.failure_message,
                "created_at": payment.created_at.isoformat(),
                "updated_at": payment.updated_at.isoformat(),
            }

        except PaymentNotFoundError:
            raise

        except PaymentRepositoryError as e:
            logger.error(
                "Database error retrieving payment status",
                payment_id=str(payment_id),
                error=str(e),
            )
            raise PaymentProcessingError(
                "Failed to retrieve payment status",
                payment_id=str(payment_id),
                error=str(e),
            ) from e

    async def retry_failed_payment(
        self,
        payment_id: uuid.UUID,
        payment_method_id: str,
        updated_by: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Retry failed payment with new payment method.

        Args:
            payment_id: Payment identifier
            payment_method_id: New Stripe payment method ID
            updated_by: User who initiated retry

        Returns:
            Dictionary containing retry result

        Raises:
            PaymentNotFoundError: If payment not found
            PaymentValidationError: If payment cannot be retried
            PaymentProcessingError: If retry fails
        """
        logger.info(
            "Retrying failed payment",
            payment_id=str(payment_id),
            payment_method_id=payment_method_id,
        )

        try:
            payment = await self.repository.get_payment_by_id(payment_id)

            if not payment:
                raise PaymentNotFoundError(
                    "Payment not found",
                    payment_id=str(payment_id),
                )

            # Validate payment can be retried
            if payment.status not in {PaymentStatus.FAILED, PaymentStatus.CANCELED}:
                raise PaymentValidationError(
                    f"Payment cannot be retried in status: {payment.status.value}",
                    payment_id=str(payment_id),
                    current_status=payment.status.value,
                )

            # Process payment with new payment method
            return await self.process_payment(
                payment_intent_id=payment.stripe_payment_intent_id,
                payment_method_id=payment_method_id,
                updated_by=updated_by,
            )

        except (PaymentNotFoundError, PaymentValidationError):
            raise

        except Exception as e:
            logger.error(
                "Payment retry failed",
                payment_id=str(payment_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise PaymentProcessingError(
                f"Payment retry failed: {e}",
                payment_id=str(payment_id),
                error=str(e),
            ) from e

    def _validate_payment_amount(self, amount: Decimal, currency: str) -> None:
        """
        Validate payment amount.

        Args:
            amount: Payment amount
            currency: Currency code

        Raises:
            PaymentValidationError: If amount is invalid
        """
        if amount <= Decimal("0"):
            raise PaymentValidationError(
                "Payment amount must be positive",
                amount=float(amount),
                currency=currency,
            )

        # Minimum amount validation (50 cents)
        min_amount = Decimal("0.50")
        if amount < min_amount:
            raise PaymentValidationError(
                f"Payment amount must be at least {min_amount}",
                amount=float(amount),
                min_amount=float(min_amount),
                currency=currency,
            )

        # Maximum amount validation ($999,999.99)
        max_amount = Decimal("999999.99")
        if amount > max_amount:
            raise PaymentValidationError(
                f"Payment amount cannot exceed {max_amount}",
                amount=float(amount),
                max_amount=float(max_amount),
                currency=currency,
            )

    async def _check_fraud_detection(
        self,
        payment: Any,
        payment_method_id: str,
    ) -> None:
        """
        Check for fraud indicators.

        Args:
            payment: Payment record
            payment_method_id: Payment method ID

        Raises:
            FraudDetectionError: If fraud detected
        """
        # Retrieve payment method details
        try:
            payment_method = self.stripe_client.retrieve_payment_method(
                payment_method_id
            )

            # Check for high-risk indicators
            if hasattr(payment_method, "card"):
                card = payment_method.card

                # Check for high-risk countries
                high_risk_countries = {"XX", "YY"}  # Example codes
                if card.country in high_risk_countries:
                    logger.warning(
                        "High-risk country detected",
                        payment_id=str(payment.id),
                        country=card.country,
                    )

                # Additional fraud checks would go here
                # - Velocity checks
                # - Amount anomaly detection
                # - Device fingerprinting
                # - Address verification

        except StripeClientError as e:
            logger.warning(
                "Failed to retrieve payment method for fraud check",
                payment_id=str(payment.id),
                error=str(e),
            )
            # Don't fail payment if fraud check fails
            pass

    def _map_stripe_status_to_payment_status(
        self,
        stripe_status: str,
    ) -> PaymentStatus:
        """
        Map Stripe payment intent status to internal payment status.

        Args:
            stripe_status: Stripe payment intent status

        Returns:
            Internal payment status
        """
        status_mapping = {
            "requires_payment_method": PaymentStatus.PENDING,
            "requires_confirmation": PaymentStatus.PENDING,
            "requires_action": PaymentStatus.REQUIRES_ACTION,
            "processing": PaymentStatus.PROCESSING,
            "succeeded": PaymentStatus.SUCCEEDED,
            "canceled": PaymentStatus.CANCELED,
        }

        return status_mapping.get(stripe_status, PaymentStatus.FAILED)

    def _extract_payment_method_details(
        self,
        payment_intent: stripe.PaymentIntent,
    ) -> Optional[dict[str, Any]]:
        """
        Extract payment method details from payment intent.

        Args:
            payment_intent: Stripe payment intent

        Returns:
            Dictionary containing payment method details or None
        """
        if not hasattr(payment_intent, "payment_method"):
            return None

        payment_method = payment_intent.payment_method

        if isinstance(payment_method, str):
            # Payment method ID only
            return {"id": payment_method}

        # Extract card details if available
        if hasattr(payment_method, "card"):
            card = payment_method.card
            return {
                "type": "card",
                "brand": card.brand,
                "last4": card.last4,
                "exp_month": card.exp_month,
                "exp_year": card.exp_year,
            }

        return {"type": payment_method.type}

    async def _process_webhook_event(
        self,
        event: stripe.Event,
    ) -> dict[str, Any]:
        """
        Process webhook event based on type.

        Args:
            event: Stripe webhook event

        Returns:
            Dictionary containing processing result
        """
        event_type = event.type
        event_data = event.data.object

        # Payment intent succeeded
        if event_type == "payment_intent.succeeded":
            return await self._handle_payment_succeeded(event_data)

        # Payment intent failed
        elif event_type == "payment_intent.payment_failed":
            return await self._handle_payment_failed(event_data)

        # Payment intent canceled
        elif event_type == "payment_intent.canceled":
            return await self._handle_payment_canceled(event_data)

        # Charge refunded
        elif event_type == "charge.refunded":
            return await self._handle_charge_refunded(event_data)

        # Log unhandled event types
        else:
            logger.info(
                "Unhandled webhook event type",
                event_type=event_type,
                event_id=event.id,
            )
            return {"handled": False, "event_type": event_type}

    async def _handle_payment_succeeded(
        self,
        payment_intent: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle payment intent succeeded event."""
        payment_intent_id = payment_intent["id"]

        payment = await self.repository.get_payment_by_stripe_intent_id(
            payment_intent_id
        )

        if payment:
            await self.repository.update_payment_status(
                payment_id=payment.id,
                new_status=PaymentStatus.SUCCEEDED,
                reason="Payment succeeded via webhook",
            )

        return {"payment_id": str(payment.id) if payment else None}

    async def _handle_payment_failed(
        self,
        payment_intent: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle payment intent failed event."""
        payment_intent_id = payment_intent["id"]

        payment = await self.repository.get_payment_by_stripe_intent_id(
            payment_intent_id
        )

        if payment:
            await self.repository.update_payment_status(
                payment_id=payment.id,
                new_status=PaymentStatus.FAILED,
                failure_code=payment_intent.get("last_payment_error", {}).get("code"),
                failure_message=payment_intent.get("last_payment_error", {}).get(
                    "message"
                ),
                reason="Payment failed via webhook",
            )

        return {"payment_id": str(payment.id) if payment else None}

    async def _handle_payment_canceled(
        self,
        payment_intent: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle payment intent canceled event."""
        payment_intent_id = payment_intent["id"]

        payment = await self.repository.get_payment_by_stripe_intent_id(
            payment_intent_id
        )

        if payment:
            await self.repository.update_payment_status(
                payment_id=payment.id,
                new_status=PaymentStatus.CANCELED,
                reason="Payment canceled via webhook",
            )

        return {"payment_id": str(payment.id) if payment else None}

    async def _handle_charge_refunded(
        self,
        charge: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle charge refunded event."""
        payment_intent_id = charge.get("payment_intent")

        if not payment_intent_id:
            return {"handled": False, "reason": "No payment intent ID"}

        payment = await self.repository.get_payment_by_stripe_intent_id(
            payment_intent_id
        )

        if payment:
            refund_amount = Decimal(charge["amount_refunded"]) / Decimal(100)

            await self.repository.add_refund(
                payment_id=payment.id,
                refund_amount=refund_amount,
                reason="Refund processed via webhook",
            )

        return {"payment_id": str(payment.id) if payment else None}