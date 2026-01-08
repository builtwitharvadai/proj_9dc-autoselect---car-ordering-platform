"""
Payment processing API endpoints for Stripe integration.

This module implements FastAPI router endpoints for payment operations including
payment intent creation, payment processing, webhook handling, and payment status
retrieval with comprehensive authentication, validation, and error handling.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from fastapi.responses import JSONResponse

from src.api.deps import CurrentUser, DatabaseSession
from src.core.logging import get_logger
from src.schemas.payments import (
    PaymentIntentRequest,
    PaymentProcessRequest,
    PaymentResponse,
)
from src.services.payments.repository import (
    PaymentRepository,
    PaymentNotFoundError,
    PaymentRepositoryError,
)
from src.services.payments.service import (
    PaymentService,
    PaymentServiceError,
    PaymentProcessingError,
    PaymentValidationError,
    FraudDetectionError,
)
from src.services.payments.stripe_client import (
    StripeClient,
    StripeClientError,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


def get_payment_service(
    db: DatabaseSession,
) -> PaymentService:
    """
    Dependency for payment service initialization.

    Args:
        db: Database session

    Returns:
        PaymentService: Configured payment service instance
    """
    repository = PaymentRepository(db)
    stripe_client = StripeClient()
    return PaymentService(repository=repository, stripe_client=stripe_client)


@router.post(
    "/intent",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Create payment intent",
    description="Create a Stripe payment intent for order payment",
)
async def create_payment_intent(
    request: PaymentIntentRequest,
    current_user: CurrentUser,
    service: Annotated[PaymentService, Depends(get_payment_service)],
) -> dict[str, Any]:
    """
    Create payment intent for order.

    Args:
        request: Payment intent creation request
        current_user: Authenticated user
        service: Payment service instance

    Returns:
        Payment intent details including client secret

    Raises:
        HTTPException: 400 for validation errors, 500 for processing errors
    """
    logger.info(
        "Creating payment intent",
        user_id=str(current_user.id),
        amount=request.amount,
        currency=request.currency,
        order_id=str(request.order_id) if request.order_id else None,
    )

    try:
        # Convert amount from cents to decimal
        amount_decimal = request.amount / 100

        result = await service.create_payment_intent(
            order_id=request.order_id,
            amount=amount_decimal,
            currency=request.currency,
            customer_email=request.customer_email or current_user.email,
            metadata=request.metadata,
            created_by=current_user.email,
        )

        logger.info(
            "Payment intent created successfully",
            payment_id=result["payment_id"],
            user_id=str(current_user.id),
        )

        return result

    except PaymentValidationError as e:
        logger.warning(
            "Payment intent validation failed",
            user_id=str(current_user.id),
            error=str(e),
            context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": str(e),
                "code": "VALIDATION_ERROR",
                "context": e.context,
            },
        )

    except PaymentProcessingError as e:
        logger.error(
            "Payment intent creation failed",
            user_id=str(current_user.id),
            error=str(e),
            context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Failed to create payment intent",
                "code": "PROCESSING_ERROR",
            },
        )

    except Exception as e:
        logger.error(
            "Unexpected error creating payment intent",
            user_id=str(current_user.id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "An unexpected error occurred",
                "code": "INTERNAL_ERROR",
            },
        )


@router.post(
    "/process",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Process payment",
    description="Process payment with payment method",
)
async def process_payment(
    request: PaymentProcessRequest,
    current_user: CurrentUser,
    service: Annotated[PaymentService, Depends(get_payment_service)],
) -> dict[str, Any]:
    """
    Process payment with payment method.

    Args:
        request: Payment processing request
        current_user: Authenticated user
        service: Payment service instance

    Returns:
        Payment processing result

    Raises:
        HTTPException: 400 for validation, 403 for fraud, 404 for not found,
                      500 for processing errors
    """
    logger.info(
        "Processing payment",
        user_id=str(current_user.id),
        payment_intent_id=request.payment_intent_id,
    )

    try:
        result = await service.process_payment(
            payment_intent_id=request.payment_intent_id,
            payment_method_id=request.payment_method_id,
            updated_by=current_user.email,
        )

        logger.info(
            "Payment processed successfully",
            payment_id=result["payment_id"],
            status=result["status"],
            user_id=str(current_user.id),
        )

        return result

    except PaymentNotFoundError as e:
        logger.warning(
            "Payment not found",
            user_id=str(current_user.id),
            payment_intent_id=request.payment_intent_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": str(e),
                "code": "PAYMENT_NOT_FOUND",
            },
        )

    except FraudDetectionError as e:
        logger.warning(
            "Fraud detected during payment processing",
            user_id=str(current_user.id),
            payment_intent_id=request.payment_intent_id,
            error=str(e),
            context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Payment declined due to security concerns",
                "code": "FRAUD_DETECTED",
            },
        )

    except PaymentProcessingError as e:
        logger.error(
            "Payment processing failed",
            user_id=str(current_user.id),
            payment_intent_id=request.payment_intent_id,
            error=str(e),
            context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": str(e),
                "code": "PROCESSING_FAILED",
                "context": e.context,
            },
        )

    except Exception as e:
        logger.error(
            "Unexpected error processing payment",
            user_id=str(current_user.id),
            payment_intent_id=request.payment_intent_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "An unexpected error occurred",
                "code": "INTERNAL_ERROR",
            },
        )


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Handle Stripe webhook",
    description="Process Stripe webhook events securely",
)
async def handle_webhook(
    request: Request,
    stripe_signature: Annotated[str, Header(alias="stripe-signature")],
    service: Annotated[PaymentService, Depends(get_payment_service)],
) -> JSONResponse:
    """
    Handle Stripe webhook event.

    Args:
        request: FastAPI request object
        stripe_signature: Stripe signature header
        service: Payment service instance

    Returns:
        JSON response with processing result

    Raises:
        HTTPException: 400 for invalid signature, 500 for processing errors
    """
    logger.info("Received Stripe webhook")

    try:
        # Read raw request body
        payload = await request.body()

        # Process webhook
        result = await service.handle_webhook(
            payload=payload,
            signature=stripe_signature,
        )

        logger.info(
            "Webhook processed successfully",
            event_id=result["event_id"],
            event_type=result["event_type"],
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"received": True, "event_id": result["event_id"]},
        )

    except StripeClientError as e:
        logger.error(
            "Webhook signature verification failed",
            error=str(e),
            error_code=e.code,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Invalid webhook signature",
                "code": "INVALID_SIGNATURE",
            },
        )

    except PaymentProcessingError as e:
        logger.error(
            "Webhook processing failed",
            error=str(e),
            context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Failed to process webhook",
                "code": "WEBHOOK_PROCESSING_ERROR",
            },
        )

    except Exception as e:
        logger.error(
            "Unexpected error processing webhook",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "An unexpected error occurred",
                "code": "INTERNAL_ERROR",
            },
        )


@router.get(
    "/{payment_id}",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get payment status",
    description="Retrieve current payment status and details",
)
async def get_payment_status(
    payment_id: UUID,
    current_user: CurrentUser,
    service: Annotated[PaymentService, Depends(get_payment_service)],
) -> dict[str, Any]:
    """
    Get current payment status.

    Args:
        payment_id: Payment identifier
        current_user: Authenticated user
        service: Payment service instance

    Returns:
        Payment status details

    Raises:
        HTTPException: 404 for not found, 500 for processing errors
    """
    logger.info(
        "Retrieving payment status",
        payment_id=str(payment_id),
        user_id=str(current_user.id),
    )

    try:
        result = await service.get_payment_status(payment_id=payment_id)

        logger.info(
            "Payment status retrieved successfully",
            payment_id=str(payment_id),
            status=result["status"],
            user_id=str(current_user.id),
        )

        return result

    except PaymentNotFoundError as e:
        logger.warning(
            "Payment not found",
            payment_id=str(payment_id),
            user_id=str(current_user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": str(e),
                "code": "PAYMENT_NOT_FOUND",
            },
        )

    except PaymentProcessingError as e:
        logger.error(
            "Failed to retrieve payment status",
            payment_id=str(payment_id),
            user_id=str(current_user.id),
            error=str(e),
            context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Failed to retrieve payment status",
                "code": "RETRIEVAL_ERROR",
            },
        )

    except Exception as e:
        logger.error(
            "Unexpected error retrieving payment status",
            payment_id=str(payment_id),
            user_id=str(current_user.id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "An unexpected error occurred",
                "code": "INTERNAL_ERROR",
            },
        )