"""
Shopping cart API router with session management and inventory reservations.

This module implements FastAPI endpoints for cart operations including add to cart,
retrieve cart, update quantities, remove items, and apply promotional codes. Supports
both authenticated users and anonymous sessions with automatic cart migration on login.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import (
    CurrentUser,
    DatabaseSession,
    OptionalUser,
    get_current_user,
    get_optional_user,
)
from src.core.logging import get_logger
from src.database.models.user import User
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
    get_cart_service,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/cart", tags=["cart"])

SESSION_COOKIE_NAME = "cart_session_id"
SESSION_COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days


def _get_session_id(request: Request) -> Optional[str]:
    """
    Extract session ID from cookie.

    Args:
        request: FastAPI request object

    Returns:
        Session ID if present, None otherwise
    """
    return request.cookies.get(SESSION_COOKIE_NAME)


def _set_session_cookie(response: Response, session_id: str) -> None:
    """
    Set session cookie in response.

    Args:
        response: FastAPI response object
        session_id: Session identifier to set
    """
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
    )


@router.post(
    "/items",
    response_model=CartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add item to cart",
    description="Add configured vehicle to cart with inventory reservation",
)
async def add_to_cart(
    request: AddToCartRequest,
    http_request: Request,
    response: Response,
    db: DatabaseSession,
    current_user: OptionalUser,
) -> CartResponse:
    """
    Add configured vehicle to cart.

    Creates inventory reservation for 15 minutes. For authenticated users,
    stores in database. For anonymous users, uses session-based storage.

    Args:
        request: Add to cart request data
        http_request: FastAPI request for session handling
        response: FastAPI response for cookie setting
        db: Database session
        current_user: Optional authenticated user

    Returns:
        Updated cart with new item

    Raises:
        HTTPException: 400 if validation fails, 404 if vehicle not found,
                      409 if insufficient inventory, 500 on service error
    """
    try:
        service = await get_cart_service(db)

        session_id = _get_session_id(http_request)
        user_id = current_user.id if current_user else None

        if not user_id and not session_id:
            import uuid

            session_id = str(uuid.uuid4())
            _set_session_cookie(response, session_id)
            logger.info(
                "Created new cart session",
                session_id=session_id,
            )

        cart_response = await service.add_to_cart(
            request=request,
            user_id=user_id,
            session_id=session_id,
        )

        logger.info(
            "Item added to cart successfully",
            cart_id=str(cart_response.id),
            vehicle_id=str(request.vehicle_id),
            quantity=request.quantity,
            user_id=str(user_id) if user_id else None,
            session_id=session_id,
        )

        return cart_response

    except InsufficientInventoryError as e:
        logger.warning(
            "Insufficient inventory for cart item",
            vehicle_id=str(request.vehicle_id),
            quantity=request.quantity,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "INSUFFICIENT_INVENTORY",
                "message": str(e),
                "vehicle_id": str(request.vehicle_id),
            },
        )
    except CartServiceError as e:
        if e.code == "VEHICLE_NOT_FOUND":
            logger.warning(
                "Vehicle not found for cart",
                vehicle_id=str(request.vehicle_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": e.code,
                    "message": str(e),
                },
            )
        elif e.code == "CONFIGURATION_NOT_FOUND":
            logger.warning(
                "Configuration not found for cart",
                configuration_id=str(request.configuration_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": e.code,
                    "message": str(e),
                },
            )
        else:
            logger.error(
                "Failed to add item to cart",
                vehicle_id=str(request.vehicle_id),
                error=str(e),
                error_code=e.code,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": e.code,
                    "message": "Failed to add item to cart",
                },
            )
    except Exception as e:
        logger.error(
            "Unexpected error adding item to cart",
            vehicle_id=str(request.vehicle_id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        )


@router.get(
    "",
    response_model=CartResponse,
    summary="Get cart",
    description="Retrieve current cart contents with pricing summary",
)
async def get_cart(
    http_request: Request,
    db: DatabaseSession,
    current_user: OptionalUser,
) -> CartResponse:
    """
    Retrieve current cart contents.

    Returns cart items with pricing breakdown including subtotal, taxes,
    discounts, and total. For authenticated users, retrieves from database.
    For anonymous users, retrieves from session storage.

    Args:
        http_request: FastAPI request for session handling
        db: Database session
        current_user: Optional authenticated user

    Returns:
        Cart with items and pricing summary

    Raises:
        HTTPException: 404 if cart not found, 500 on service error
    """
    try:
        service = await get_cart_service(db)

        session_id = _get_session_id(http_request)
        user_id = current_user.id if current_user else None

        if not user_id and not session_id:
            logger.info("No cart session found, returning empty cart")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "CART_NOT_FOUND",
                    "message": "No cart found for this session",
                },
            )

        cart_response = await service.get_cart(
            user_id=user_id,
            session_id=session_id,
        )

        logger.debug(
            "Cart retrieved successfully",
            cart_id=str(cart_response.id),
            item_count=cart_response.item_count,
            user_id=str(user_id) if user_id else None,
            session_id=session_id,
        )

        return cart_response

    except CartNotFoundError:
        logger.info(
            "Cart not found",
            user_id=str(current_user.id) if current_user else None,
            session_id=_get_session_id(http_request),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CART_NOT_FOUND",
                "message": "Cart not found",
            },
        )
    except CartServiceError as e:
        logger.error(
            "Failed to retrieve cart",
            error=str(e),
            error_code=e.code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": e.code,
                "message": "Failed to retrieve cart",
            },
        )
    except Exception as e:
        logger.error(
            "Unexpected error retrieving cart",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        )


@router.put(
    "/items/{item_id}",
    response_model=CartResponse,
    summary="Update cart item",
    description="Update cart item quantity with inventory validation",
)
async def update_cart_item(
    item_id: UUID,
    request: UpdateCartItemRequest,
    http_request: Request,
    db: DatabaseSession,
    current_user: OptionalUser,
) -> CartResponse:
    """
    Update cart item quantity.

    Updates quantity and extends inventory reservation. Setting quantity to 0
    removes the item from cart. Validates inventory availability for increases.

    Args:
        item_id: Cart item identifier
        request: Update request with new quantity
        http_request: FastAPI request for session handling
        db: Database session
        current_user: Optional authenticated user

    Returns:
        Updated cart with modified item

    Raises:
        HTTPException: 404 if item not found, 409 if insufficient inventory,
                      500 on service error
    """
    try:
        service = await get_cart_service(db)

        session_id = _get_session_id(http_request)
        user_id = current_user.id if current_user else None

        cart_response = await service.update_cart_item(
            item_id=item_id,
            request=request,
            user_id=user_id,
            session_id=session_id,
        )

        logger.info(
            "Cart item updated successfully",
            item_id=str(item_id),
            new_quantity=request.quantity,
            cart_id=str(cart_response.id),
        )

        return cart_response

    except CartItemNotFoundError:
        logger.warning(
            "Cart item not found for update",
            item_id=str(item_id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CART_ITEM_NOT_FOUND",
                "message": f"Cart item {item_id} not found",
            },
        )
    except InsufficientInventoryError as e:
        logger.warning(
            "Insufficient inventory for cart item update",
            item_id=str(item_id),
            quantity=request.quantity,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "INSUFFICIENT_INVENTORY",
                "message": str(e),
            },
        )
    except CartServiceError as e:
        logger.error(
            "Failed to update cart item",
            item_id=str(item_id),
            error=str(e),
            error_code=e.code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": e.code,
                "message": "Failed to update cart item",
            },
        )
    except Exception as e:
        logger.error(
            "Unexpected error updating cart item",
            item_id=str(item_id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        )


@router.delete(
    "/items/{item_id}",
    response_model=CartResponse,
    summary="Remove cart item",
    description="Remove item from cart and release inventory reservation",
)
async def remove_cart_item(
    item_id: UUID,
    http_request: Request,
    db: DatabaseSession,
    current_user: OptionalUser,
) -> CartResponse:
    """
    Remove item from cart.

    Removes item and releases associated inventory reservation. Returns
    updated cart with remaining items.

    Args:
        item_id: Cart item identifier
        http_request: FastAPI request for session handling
        db: Database session
        current_user: Optional authenticated user

    Returns:
        Updated cart without removed item

    Raises:
        HTTPException: 404 if item not found, 500 on service error
    """
    try:
        service = await get_cart_service(db)

        session_id = _get_session_id(http_request)
        user_id = current_user.id if current_user else None

        cart_response = await service.remove_cart_item(
            item_id=item_id,
            user_id=user_id,
            session_id=session_id,
        )

        logger.info(
            "Cart item removed successfully",
            item_id=str(item_id),
            cart_id=str(cart_response.id),
        )

        return cart_response

    except CartItemNotFoundError:
        logger.warning(
            "Cart item not found for removal",
            item_id=str(item_id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CART_ITEM_NOT_FOUND",
                "message": f"Cart item {item_id} not found",
            },
        )
    except CartServiceError as e:
        logger.error(
            "Failed to remove cart item",
            item_id=str(item_id),
            error=str(e),
            error_code=e.code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": e.code,
                "message": "Failed to remove cart item",
            },
        )
    except Exception as e:
        logger.error(
            "Unexpected error removing cart item",
            item_id=str(item_id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        )


@router.post(
    "/promo",
    response_model=CartResponse,
    summary="Apply promotional code",
    description="Apply promotional code to cart for discount",
)
async def apply_promotional_code(
    request: ApplyPromoRequest,
    http_request: Request,
    db: DatabaseSession,
    current_user: OptionalUser,
) -> CartResponse:
    """
    Apply promotional code to cart.

    Validates promotional code and applies discount to cart. Code must be
    active, not expired, and meet minimum order requirements.

    Args:
        request: Promotional code request
        http_request: FastAPI request for session handling
        db: Database session
        current_user: Optional authenticated user

    Returns:
        Updated cart with discount applied

    Raises:
        HTTPException: 400 if code invalid, 404 if cart not found,
                      500 on service error
    """
    try:
        service = await get_cart_service(db)

        session_id = _get_session_id(http_request)
        user_id = current_user.id if current_user else None

        cart_response = await service.apply_promotional_code(
            request=request,
            user_id=user_id,
            session_id=session_id,
        )

        logger.info(
            "Promotional code applied successfully",
            promo_code=request.promo_code,
            cart_id=str(cart_response.id),
            discount_amount=float(cart_response.summary.discount_amount),
        )

        return cart_response

    except InvalidPromotionalCodeError as e:
        logger.warning(
            "Invalid promotional code",
            promo_code=request.promo_code,
            reason=e.context.get("reason"),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": e.code,
                "message": str(e),
                "promo_code": request.promo_code,
            },
        )
    except CartNotFoundError:
        logger.warning(
            "Cart not found for promotional code",
            promo_code=request.promo_code,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CART_NOT_FOUND",
                "message": "Cart not found",
            },
        )
    except CartServiceError as e:
        logger.error(
            "Failed to apply promotional code",
            promo_code=request.promo_code,
            error=str(e),
            error_code=e.code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": e.code,
                "message": "Failed to apply promotional code",
            },
        )
    except Exception as e:
        logger.error(
            "Unexpected error applying promotional code",
            promo_code=request.promo_code,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        )