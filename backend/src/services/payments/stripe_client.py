"""
Stripe API client wrapper with comprehensive error handling and retry logic.

This module provides a production-ready Stripe client implementation with
exponential backoff retry logic, comprehensive error handling, structured
logging, and proper resource management for payment processing operations.
"""

import time
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

import stripe
from stripe.error import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    CardError,
    IdempotencyError,
    InvalidRequestError,
    RateLimitError,
    StripeError,
)

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class StripeClientError(Exception):
    """Base exception for Stripe client errors."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        stripe_error: Optional[StripeError] = None,
        **context: Any,
    ):
        super().__init__(message)
        self.code = code
        self.stripe_error = stripe_error
        self.context = context


class StripePaymentError(StripeClientError):
    """Exception for payment processing errors."""

    pass


class StripeAuthenticationError(StripeClientError):
    """Exception for authentication errors."""

    pass


class StripeRateLimitError(StripeClientError):
    """Exception for rate limit errors."""

    pass


class StripeConnectionError(StripeClientError):
    """Exception for connection errors."""

    pass


class StripeClient:
    """
    Stripe API client with error handling and retry logic.

    This client provides methods for creating payment intents, confirming
    payments, retrieving payment status, and handling webhooks with
    comprehensive error handling and exponential backoff retry logic.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        max_backoff: float = 32.0,
        backoff_multiplier: float = 2.0,
    ):
        """
        Initialize Stripe client with configuration.

        Args:
            api_key: Stripe secret API key (defaults to settings)
            webhook_secret: Stripe webhook signing secret (defaults to settings)
            max_retries: Maximum number of retry attempts
            initial_backoff: Initial backoff delay in seconds
            max_backoff: Maximum backoff delay in seconds
            backoff_multiplier: Backoff multiplier for exponential backoff
        """
        self.api_key = api_key or settings.stripe_secret_key
        self.webhook_secret = webhook_secret or settings.stripe_webhook_secret
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_multiplier = backoff_multiplier

        stripe.api_key = self.api_key
        stripe.max_network_retries = 0

        logger.info(
            "Stripe client initialized",
            max_retries=max_retries,
            initial_backoff=initial_backoff,
            max_backoff=max_backoff,
        )

    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.

        Args:
            attempt: Current retry attempt number (0-indexed)

        Returns:
            Backoff delay in seconds
        """
        delay = min(
            self.initial_backoff * (self.backoff_multiplier**attempt),
            self.max_backoff,
        )
        return delay

    def _should_retry(self, error: StripeError, attempt: int) -> bool:
        """
        Determine if request should be retried.

        Args:
            error: Stripe error that occurred
            attempt: Current retry attempt number

        Returns:
            True if request should be retried, False otherwise
        """
        if attempt >= self.max_retries:
            return False

        retryable_errors = (
            APIConnectionError,
            RateLimitError,
            APIError,
        )

        return isinstance(error, retryable_errors)

    def _execute_with_retry(
        self,
        operation: str,
        func: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute Stripe API call with exponential backoff retry logic.

        Args:
            operation: Operation name for logging
            func: Stripe API function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result from Stripe API call

        Raises:
            StripeClientError: If operation fails after all retries
        """
        last_error: Optional[StripeError] = None

        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    f"Executing Stripe operation: {operation}",
                    attempt=attempt,
                    max_retries=self.max_retries,
                )

                result = func(*args, **kwargs)

                if attempt > 0:
                    logger.info(
                        f"Stripe operation succeeded after retry: {operation}",
                        attempt=attempt,
                    )

                return result

            except AuthenticationError as e:
                logger.error(
                    f"Stripe authentication error: {operation}",
                    error=str(e),
                    code=e.code,
                )
                raise StripeAuthenticationError(
                    f"Authentication failed: {e.user_message or str(e)}",
                    code=e.code,
                    stripe_error=e,
                ) from e

            except CardError as e:
                logger.warning(
                    f"Stripe card error: {operation}",
                    error=str(e),
                    code=e.code,
                    decline_code=e.decline_code,
                )
                raise StripePaymentError(
                    f"Card error: {e.user_message or str(e)}",
                    code=e.code,
                    stripe_error=e,
                    decline_code=e.decline_code,
                ) from e

            except InvalidRequestError as e:
                logger.error(
                    f"Stripe invalid request: {operation}",
                    error=str(e),
                    code=e.code,
                    param=e.param,
                )
                raise StripeClientError(
                    f"Invalid request: {e.user_message or str(e)}",
                    code=e.code,
                    stripe_error=e,
                    param=e.param,
                ) from e

            except IdempotencyError as e:
                logger.error(
                    f"Stripe idempotency error: {operation}",
                    error=str(e),
                    code=e.code,
                )
                raise StripeClientError(
                    f"Idempotency error: {e.user_message or str(e)}",
                    code=e.code,
                    stripe_error=e,
                ) from e

            except RateLimitError as e:
                last_error = e
                if not self._should_retry(e, attempt):
                    logger.error(
                        f"Stripe rate limit exceeded: {operation}",
                        error=str(e),
                        attempt=attempt,
                    )
                    raise StripeRateLimitError(
                        f"Rate limit exceeded: {e.user_message or str(e)}",
                        code=e.code,
                        stripe_error=e,
                    ) from e

                backoff = self._calculate_backoff(attempt)
                logger.warning(
                    f"Rate limit hit, retrying: {operation}",
                    attempt=attempt,
                    backoff_seconds=backoff,
                )
                time.sleep(backoff)

            except APIConnectionError as e:
                last_error = e
                if not self._should_retry(e, attempt):
                    logger.error(
                        f"Stripe connection error: {operation}",
                        error=str(e),
                        attempt=attempt,
                    )
                    raise StripeConnectionError(
                        f"Connection error: {e.user_message or str(e)}",
                        code=e.code,
                        stripe_error=e,
                    ) from e

                backoff = self._calculate_backoff(attempt)
                logger.warning(
                    f"Connection error, retrying: {operation}",
                    attempt=attempt,
                    backoff_seconds=backoff,
                )
                time.sleep(backoff)

            except APIError as e:
                last_error = e
                if not self._should_retry(e, attempt):
                    logger.error(
                        f"Stripe API error: {operation}",
                        error=str(e),
                        code=e.code,
                        attempt=attempt,
                    )
                    raise StripeClientError(
                        f"API error: {e.user_message or str(e)}",
                        code=e.code,
                        stripe_error=e,
                    ) from e

                backoff = self._calculate_backoff(attempt)
                logger.warning(
                    f"API error, retrying: {operation}",
                    attempt=attempt,
                    backoff_seconds=backoff,
                )
                time.sleep(backoff)

            except StripeError as e:
                logger.error(
                    f"Unexpected Stripe error: {operation}",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise StripeClientError(
                    f"Stripe error: {e.user_message or str(e)}",
                    code=getattr(e, "code", None),
                    stripe_error=e,
                ) from e

        logger.error(
            f"Stripe operation failed after all retries: {operation}",
            max_retries=self.max_retries,
            last_error=str(last_error),
        )
        raise StripeClientError(
            f"Operation failed after {self.max_retries} retries",
            stripe_error=last_error,
        )

    def create_payment_intent(
        self,
        amount: int,
        currency: str,
        order_id: Optional[UUID] = None,
        customer_email: Optional[str] = None,
        metadata: Optional[dict[str, str]] = None,
        idempotency_key: Optional[str] = None,
    ) -> stripe.PaymentIntent:
        """
        Create a Stripe payment intent.

        Args:
            amount: Payment amount in cents
            currency: Three-letter ISO currency code
            order_id: Associated order ID for tracking
            customer_email: Customer email for receipt
            metadata: Additional metadata for the payment
            idempotency_key: Idempotency key for safe retries

        Returns:
            Stripe PaymentIntent object

        Raises:
            StripeClientError: If payment intent creation fails
        """
        logger.info(
            "Creating payment intent",
            amount=amount,
            currency=currency,
            order_id=str(order_id) if order_id else None,
        )

        params: dict[str, Any] = {
            "amount": amount,
            "currency": currency.lower(),
            "automatic_payment_methods": {"enabled": True},
        }

        if customer_email:
            params["receipt_email"] = customer_email

        intent_metadata = metadata or {}
        if order_id:
            intent_metadata["order_id"] = str(order_id)

        if intent_metadata:
            params["metadata"] = intent_metadata

        if idempotency_key:
            params["idempotency_key"] = idempotency_key

        payment_intent = self._execute_with_retry(
            "create_payment_intent",
            stripe.PaymentIntent.create,
            **params,
        )

        logger.info(
            "Payment intent created successfully",
            payment_intent_id=payment_intent.id,
            amount=amount,
            currency=currency,
        )

        return payment_intent

    def confirm_payment(
        self,
        payment_intent_id: str,
        payment_method_id: str,
        idempotency_key: Optional[str] = None,
    ) -> stripe.PaymentIntent:
        """
        Confirm a payment intent with a payment method.

        Args:
            payment_intent_id: Stripe payment intent ID
            payment_method_id: Stripe payment method ID
            idempotency_key: Idempotency key for safe retries

        Returns:
            Confirmed Stripe PaymentIntent object

        Raises:
            StripeClientError: If payment confirmation fails
        """
        logger.info(
            "Confirming payment",
            payment_intent_id=payment_intent_id,
            payment_method_id=payment_method_id,
        )

        params: dict[str, Any] = {
            "payment_method": payment_method_id,
        }

        if idempotency_key:
            params["idempotency_key"] = idempotency_key

        payment_intent = self._execute_with_retry(
            "confirm_payment",
            stripe.PaymentIntent.confirm,
            payment_intent_id,
            **params,
        )

        logger.info(
            "Payment confirmed successfully",
            payment_intent_id=payment_intent.id,
            status=payment_intent.status,
        )

        return payment_intent

    def retrieve_payment_intent(
        self,
        payment_intent_id: str,
    ) -> stripe.PaymentIntent:
        """
        Retrieve a payment intent by ID.

        Args:
            payment_intent_id: Stripe payment intent ID

        Returns:
            Stripe PaymentIntent object

        Raises:
            StripeClientError: If retrieval fails
        """
        logger.debug(
            "Retrieving payment intent",
            payment_intent_id=payment_intent_id,
        )

        payment_intent = self._execute_with_retry(
            "retrieve_payment_intent",
            stripe.PaymentIntent.retrieve,
            payment_intent_id,
        )

        logger.debug(
            "Payment intent retrieved successfully",
            payment_intent_id=payment_intent.id,
            status=payment_intent.status,
        )

        return payment_intent

    def cancel_payment_intent(
        self,
        payment_intent_id: str,
        cancellation_reason: Optional[str] = None,
    ) -> stripe.PaymentIntent:
        """
        Cancel a payment intent.

        Args:
            payment_intent_id: Stripe payment intent ID
            cancellation_reason: Reason for cancellation

        Returns:
            Cancelled Stripe PaymentIntent object

        Raises:
            StripeClientError: If cancellation fails
        """
        logger.info(
            "Cancelling payment intent",
            payment_intent_id=payment_intent_id,
            reason=cancellation_reason,
        )

        params: dict[str, Any] = {}
        if cancellation_reason:
            params["cancellation_reason"] = cancellation_reason

        payment_intent = self._execute_with_retry(
            "cancel_payment_intent",
            stripe.PaymentIntent.cancel,
            payment_intent_id,
            **params,
        )

        logger.info(
            "Payment intent cancelled successfully",
            payment_intent_id=payment_intent.id,
            status=payment_intent.status,
        )

        return payment_intent

    def construct_webhook_event(
        self,
        payload: bytes,
        signature: str,
    ) -> stripe.Event:
        """
        Construct and verify a webhook event from Stripe.

        Args:
            payload: Raw webhook payload bytes
            signature: Stripe signature header value

        Returns:
            Verified Stripe Event object

        Raises:
            StripeClientError: If webhook verification fails
        """
        logger.debug("Constructing webhook event")

        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret,
            )

            logger.info(
                "Webhook event verified successfully",
                event_id=event.id,
                event_type=event.type,
            )

            return event

        except ValueError as e:
            logger.error(
                "Invalid webhook payload",
                error=str(e),
            )
            raise StripeClientError(
                "Invalid webhook payload",
                code="INVALID_PAYLOAD",
            ) from e

        except stripe.error.SignatureVerificationError as e:
            logger.error(
                "Webhook signature verification failed",
                error=str(e),
            )
            raise StripeClientError(
                "Webhook signature verification failed",
                code="INVALID_SIGNATURE",
                stripe_error=e,
            ) from e

    def retrieve_payment_method(
        self,
        payment_method_id: str,
    ) -> stripe.PaymentMethod:
        """
        Retrieve a payment method by ID.

        Args:
            payment_method_id: Stripe payment method ID

        Returns:
            Stripe PaymentMethod object

        Raises:
            StripeClientError: If retrieval fails
        """
        logger.debug(
            "Retrieving payment method",
            payment_method_id=payment_method_id,
        )

        payment_method = self._execute_with_retry(
            "retrieve_payment_method",
            stripe.PaymentMethod.retrieve,
            payment_method_id,
        )

        logger.debug(
            "Payment method retrieved successfully",
            payment_method_id=payment_method.id,
            type=payment_method.type,
        )

        return payment_method

    def format_amount(self, amount: int, currency: str) -> str:
        """
        Format payment amount for display.

        Args:
            amount: Amount in cents
            currency: Three-letter ISO currency code

        Returns:
            Formatted amount string
        """
        decimal_amount = Decimal(amount) / Decimal(100)
        return f"{decimal_amount:.2f} {currency.upper()}"


def get_stripe_client() -> StripeClient:
    """
    Get configured Stripe client instance.

    Returns:
        Configured StripeClient instance
    """
    return StripeClient()