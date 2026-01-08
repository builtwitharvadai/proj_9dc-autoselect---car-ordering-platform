"""
Order management API endpoints for AutoSelect platform.

This module implements FastAPI router for order lifecycle management including
order creation, status updates, cancellation, and history tracking. Provides
comprehensive authentication, authorization, input validation, and error handling
with structured logging and audit trails.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import (
    CurrentActiveUser,
    DatabaseSession,
    get_current_active_user,
)
from src.core.logging import get_logger
from src.database.models.order import OrderStatus
from src.database.models.user import User
from src.schemas.orders import (
    OrderCreateRequest,
    OrderResponse,
    OrderStatusUpdate,
)
from src.services.orders.service import (
    OrderService,
    OrderServiceError,
    OrderValidationError,
    OrderProcessingError,
)
from src.services.orders.repository import OrderNotFoundError
from src.services.payments.service import PaymentService

logger = get_logger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new order",
    description="Create a new order with complete order placement and atomic transactions",
)
async def create_order(
    request: OrderCreateRequest,
    current_user: CurrentActiveUser,
    db: DatabaseSession,
) -> OrderResponse:
    """
    Create new order with validation and payment processing.

    Args:
        request: Order creation request with items and customer info
        current_user: Authenticated user placing the order
        db: Database session

    Returns:
        OrderResponse: Created order details

    Raises:
        HTTPException: 400 if validation fails, 500 if creation fails
    """
    logger.info(
        "Creating order",
        user_id=str(current_user.id),
        item_count=len(request.items),
    )

    try:
        # Initialize services
        payment_service = PaymentService(db)
        order_service = OrderService(db, payment_service)

        # Extract first item for vehicle and configuration
        first_item = request.items[0]
        vehicle_id = first_item.vehicle_id
        configuration_id = first_item.configuration_id

        # Prepare items data
        items_data = [
            {
                "vehicle_id": str(item.vehicle_id),
                "configuration_id": str(item.configuration_id) if item.configuration_id else None,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "discount_amount": item.discount_amount,
                "tax_amount": item.tax_amount,
            }
            for item in request.items
        ]

        # Create order
        order_result = await order_service.create_order(
            user_id=current_user.id,
            vehicle_id=vehicle_id,
            configuration_id=configuration_id or vehicle_id,
            items=items_data,
            customer_info={
                "first_name": request.customer_info.first_name,
                "last_name": request.customer_info.last_name,
                "email": request.customer_info.email,
                "phone": request.customer_info.phone,
                "driver_license_number": request.customer_info.driver_license_number,
            },
            delivery_address={
                "street_address": request.delivery_address.street_address,
                "city": request.delivery_address.city,
                "state": request.delivery_address.state,
                "postal_code": request.delivery_address.postal_code,
                "country": request.delivery_address.country,
                "delivery_instructions": request.delivery_address.delivery_instructions,
            },
            payment_method=request.payment_method,
            trade_in_info={
                "vehicle_year": request.trade_in_info.vehicle_year,
                "vehicle_make": request.trade_in_info.vehicle_make,
                "vehicle_model": request.trade_in_info.vehicle_model,
                "vehicle_vin": request.trade_in_info.vehicle_vin,
                "mileage": request.trade_in_info.mileage,
                "condition": request.trade_in_info.condition,
                "estimated_value": request.trade_in_info.estimated_value,
                "payoff_amount": request.trade_in_info.payoff_amount,
            } if request.trade_in_info else None,
            promotional_code=request.promotional_code,
            notes=request.notes,
        )

        logger.info(
            "Order created successfully",
            order_id=order_result["order_id"],
            order_number=order_result["order_number"],
            user_id=str(current_user.id),
        )

        # Get full order details for response
        order = await order_service.get_order(
            order_id=UUID(order_result["order_id"]),
            include_items=True,
        )

        return OrderResponse(**order)

    except OrderValidationError as e:
        logger.warning(
            "Order validation failed",
            user_id=str(current_user.id),
            error=str(e),
            context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except OrderProcessingError as e:
        logger.error(
            "Order processing failed",
            user_id=str(current_user.id),
            error=str(e),
            context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process order",
        ) from e

    except Exception as e:
        logger.error(
            "Unexpected error creating order",
            user_id=str(current_user.id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.get(
    "/",
    response_model=dict,
    summary="List user orders",
    description="Get paginated list of orders for authenticated user",
)
async def list_orders(
    current_user: CurrentActiveUser,
    db: DatabaseSession,
    status_filter: Optional[OrderStatus] = Query(None, description="Filter by order status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
) -> dict:
    """
    List orders for authenticated user with pagination.

    Args:
        current_user: Authenticated user
        db: Database session
        status_filter: Optional status filter
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        dict: Orders list with pagination info

    Raises:
        HTTPException: 500 if retrieval fails
    """
    logger.info(
        "Listing orders",
        user_id=str(current_user.id),
        status_filter=status_filter.value if status_filter else None,
        skip=skip,
        limit=limit,
    )

    try:
        order_service = OrderService(db)

        result = await order_service.get_user_orders(
            user_id=current_user.id,
            status=status_filter,
            skip=skip,
            limit=limit,
        )

        logger.info(
            "Orders retrieved successfully",
            user_id=str(current_user.id),
            count=len(result["orders"]),
            total_count=result["total_count"],
        )

        return result

    except OrderServiceError as e:
        logger.error(
            "Failed to retrieve orders",
            user_id=str(current_user.id),
            error=str(e),
            context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve orders",
        ) from e

    except Exception as e:
        logger.error(
            "Unexpected error listing orders",
            user_id=str(current_user.id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get order details",
    description="Get detailed information about a specific order",
)
async def get_order(
    order_id: UUID,
    current_user: CurrentActiveUser,
    db: DatabaseSession,
) -> OrderResponse:
    """
    Get order details by ID.

    Args:
        order_id: Order identifier
        current_user: Authenticated user
        db: Database session

    Returns:
        OrderResponse: Order details

    Raises:
        HTTPException: 404 if order not found, 403 if unauthorized, 500 if retrieval fails
    """
    logger.info(
        "Retrieving order",
        order_id=str(order_id),
        user_id=str(current_user.id),
    )

    try:
        order_service = OrderService(db)

        order = await order_service.get_order(
            order_id=order_id,
            include_items=True,
            include_history=True,
        )

        # Verify order ownership
        if order.get("user_id") and UUID(order["user_id"]) != current_user.id:
            logger.warning(
                "Unauthorized order access attempt",
                order_id=str(order_id),
                user_id=str(current_user.id),
                order_user_id=order["user_id"],
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this order",
            )

        logger.info(
            "Order retrieved successfully",
            order_id=str(order_id),
            user_id=str(current_user.id),
        )

        return OrderResponse(**order)

    except OrderNotFoundError as e:
        logger.warning(
            "Order not found",
            order_id=str(order_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        ) from e

    except HTTPException:
        raise

    except OrderServiceError as e:
        logger.error(
            "Failed to retrieve order",
            order_id=str(order_id),
            user_id=str(current_user.id),
            error=str(e),
            context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve order",
        ) from e

    except Exception as e:
        logger.error(
            "Unexpected error retrieving order",
            order_id=str(order_id),
            user_id=str(current_user.id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.put(
    "/{order_id}/status",
    response_model=OrderResponse,
    summary="Update order status",
    description="Update order status with state machine validation",
)
async def update_order_status(
    order_id: UUID,
    request: OrderStatusUpdate,
    current_user: CurrentActiveUser,
    db: DatabaseSession,
) -> OrderResponse:
    """
    Update order status with validation.

    Args:
        order_id: Order identifier
        request: Status update request
        current_user: Authenticated user
        db: Database session

    Returns:
        OrderResponse: Updated order details

    Raises:
        HTTPException: 404 if order not found, 403 if unauthorized, 400 if invalid transition, 500 if update fails
    """
    logger.info(
        "Updating order status",
        order_id=str(order_id),
        user_id=str(current_user.id),
        new_status=request.order_status.value if request.order_status else None,
    )

    try:
        order_service = OrderService(db)

        # Verify order ownership
        order = await order_service.get_order(order_id=order_id)
        if order.get("user_id") and UUID(order["user_id"]) != current_user.id:
            logger.warning(
                "Unauthorized order status update attempt",
                order_id=str(order_id),
                user_id=str(current_user.id),
                order_user_id=order["user_id"],
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this order",
            )

        # Update status if provided
        if request.order_status:
            await order_service.update_order_status(
                order_id=order_id,
                new_status=request.order_status,
                user_id=current_user.id,
                reason=request.status_notes,
            )

        # Get updated order
        updated_order = await order_service.get_order(
            order_id=order_id,
            include_items=True,
            include_history=True,
        )

        logger.info(
            "Order status updated successfully",
            order_id=str(order_id),
            user_id=str(current_user.id),
            new_status=request.order_status.value if request.order_status else None,
        )

        return OrderResponse(**updated_order)

    except OrderNotFoundError as e:
        logger.warning(
            "Order not found for status update",
            order_id=str(order_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        ) from e

    except HTTPException:
        raise

    except OrderProcessingError as e:
        logger.warning(
            "Invalid order status transition",
            order_id=str(order_id),
            user_id=str(current_user.id),
            error=str(e),
            context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except OrderServiceError as e:
        logger.error(
            "Failed to update order status",
            order_id=str(order_id),
            user_id=str(current_user.id),
            error=str(e),
            context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update order status",
        ) from e

    except Exception as e:
        logger.error(
            "Unexpected error updating order status",
            order_id=str(order_id),
            user_id=str(current_user.id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
    summary="Cancel order",
    description="Cancel an order if it's in a cancellable state",
)
async def cancel_order(
    order_id: UUID,
    current_user: CurrentActiveUser,
    db: DatabaseSession,
    reason: Optional[str] = Query(None, max_length=500, description="Cancellation reason"),
) -> OrderResponse:
    """
    Cancel order with validation.

    Args:
        order_id: Order identifier
        current_user: Authenticated user
        db: Database session
        reason: Optional cancellation reason

    Returns:
        OrderResponse: Cancelled order details

    Raises:
        HTTPException: 404 if order not found, 403 if unauthorized, 400 if cannot cancel, 500 if cancellation fails
    """
    logger.info(
        "Cancelling order",
        order_id=str(order_id),
        user_id=str(current_user.id),
        reason=reason,
    )

    try:
        order_service = OrderService(db)

        # Verify order ownership
        order = await order_service.get_order(order_id=order_id)
        if order.get("user_id") and UUID(order["user_id"]) != current_user.id:
            logger.warning(
                "Unauthorized order cancellation attempt",
                order_id=str(order_id),
                user_id=str(current_user.id),
                order_user_id=order["user_id"],
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to cancel this order",
            )

        # Cancel order
        await order_service.update_order_status(
            order_id=order_id,
            new_status=OrderStatus.CANCELLED,
            user_id=current_user.id,
            reason=reason or "Cancelled by customer",
        )

        # Get updated order
        cancelled_order = await order_service.get_order(
            order_id=order_id,
            include_items=True,
            include_history=True,
        )

        logger.info(
            "Order cancelled successfully",
            order_id=str(order_id),
            user_id=str(current_user.id),
        )

        return OrderResponse(**cancelled_order)

    except OrderNotFoundError as e:
        logger.warning(
            "Order not found for cancellation",
            order_id=str(order_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        ) from e

    except HTTPException:
        raise

    except OrderProcessingError as e:
        logger.warning(
            "Cannot cancel order",
            order_id=str(order_id),
            user_id=str(current_user.id),
            error=str(e),
            context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except OrderServiceError as e:
        logger.error(
            "Failed to cancel order",
            order_id=str(order_id),
            user_id=str(current_user.id),
            error=str(e),
            context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel order",
        ) from e

    except Exception as e:
        logger.error(
            "Unexpected error cancelling order",
            order_id=str(order_id),
            user_id=str(current_user.id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.get(
    "/{order_id}/history",
    response_model=dict,
    summary="Get order status history",
    description="Get complete status change history for an order",
)
async def get_order_history(
    order_id: UUID,
    current_user: CurrentActiveUser,
    db: DatabaseSession,
) -> dict:
    """
    Get order status history.

    Args:
        order_id: Order identifier
        current_user: Authenticated user
        db: Database session

    Returns:
        dict: Order status history

    Raises:
        HTTPException: 404 if order not found, 403 if unauthorized, 500 if retrieval fails
    """
    logger.info(
        "Retrieving order history",
        order_id=str(order_id),
        user_id=str(current_user.id),
    )

    try:
        order_service = OrderService(db)

        # Verify order ownership
        order = await order_service.get_order(order_id=order_id)
        if order.get("user_id") and UUID(order["user_id"]) != current_user.id:
            logger.warning(
                "Unauthorized order history access attempt",
                order_id=str(order_id),
                user_id=str(current_user.id),
                order_user_id=order["user_id"],
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this order history",
            )

        # Get order with history
        order_with_history = await order_service.get_order(
            order_id=order_id,
            include_history=True,
        )

        logger.info(
            "Order history retrieved successfully",
            order_id=str(order_id),
            user_id=str(current_user.id),
        )

        return {
            "order_id": str(order_id),
            "order_number": order_with_history["order_number"],
            "current_status": order_with_history["status"],
            "history": order_with_history.get("status_history", []),
        }

    except OrderNotFoundError as e:
        logger.warning(
            "Order not found for history retrieval",
            order_id=str(order_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        ) from e

    except HTTPException:
        raise

    except OrderServiceError as e:
        logger.error(
            "Failed to retrieve order history",
            order_id=str(order_id),
            user_id=str(current_user.id),
            error=str(e),
            context=e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve order history",
        ) from e

    except Exception as e:
        logger.error(
            "Unexpected error retrieving order history",
            order_id=str(order_id),
            user_id=str(current_user.id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e