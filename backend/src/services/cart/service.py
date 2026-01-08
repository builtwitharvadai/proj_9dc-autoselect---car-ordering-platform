"""
Shopping cart service orchestrating cart operations.

This module implements the CartService class providing high-level cart operations
including add to cart, get cart, update items, remove items, apply promotional codes,
and cart migration on login. Integrates with inventory reservation system, pricing
calculations, and session management with comprehensive error handling and logging.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.models.cart import Cart, CartItem
from src.database.models.promotional_code import PromotionalCode
from src.database.models.vehicle import Vehicle
from src.database.models.vehicle_configuration import VehicleConfiguration
from src.schemas.cart import (
    AddToCartRequest,
    ApplyPromoRequest,
    CartItemResponse,
    CartResponse,
    CartSummary,
    UpdateCartItemRequest,
)
from src.services.cart.inventory_reservation import (
    InsufficientInventoryError,
    InventoryReservationService,
    ReservationError,
    get_reservation_service,
)
from src.services.cart.repository import CartRepository
from src.services.cart.session_manager import (
    CartSessionError,
    CartSessionManager,
    get_cart_session_manager,
)
from src.services.configuration.pricing_engine import PricingEngine

logger = get_logger(__name__)


class CartServiceError(Exception):
    """Base exception for cart service errors."""

    def __init__(self, message: str, code: str, **context):
        super().__init__(message)
        self.code = code
        self.context = context


class CartNotFoundError(CartServiceError):
    """Raised when cart cannot be found."""

    def __init__(self, cart_id: Optional[str] = None, **context):
        super().__init__(
            f"Cart not found: {cart_id}" if cart_id else "Cart not found",
            code="CART_NOT_FOUND",
            cart_id=cart_id,
            **context,
        )


class CartItemNotFoundError(CartServiceError):
    """Raised when cart item cannot be found."""

    def __init__(self, item_id: str, **context):
        super().__init__(
            f"Cart item not found: {item_id}",
            code="CART_ITEM_NOT_FOUND",
            item_id=item_id,
            **context,
        )


class InvalidPromotionalCodeError(CartServiceError):
    """Raised when promotional code is invalid."""

    def __init__(self, code: str, reason: str, **context):
        super().__init__(
            f"Invalid promotional code '{code}': {reason}",
            code="INVALID_PROMO_CODE",
            promo_code=code,
            reason=reason,
            **context,
        )


class CartService:
    """
    Service for shopping cart operations.

    Orchestrates cart management including item operations, promotional codes,
    inventory reservations, pricing calculations, and cart migration with
    comprehensive error handling and logging.
    """

    DEFAULT_TAX_RATE = Decimal("0.08")
    RESERVATION_MINUTES = 15

    def __init__(
        self,
        session: AsyncSession,
        session_manager: Optional[CartSessionManager] = None,
        reservation_service: Optional[InventoryReservationService] = None,
        pricing_engine: Optional[PricingEngine] = None,
    ):
        """
        Initialize cart service.

        Args:
            session: Async database session
            session_manager: Optional cart session manager
            reservation_service: Optional inventory reservation service
            pricing_engine: Optional pricing engine
        """
        self.session = session
        self.repository = CartRepository(session)
        self._session_manager = session_manager
        self._reservation_service = reservation_service
        self._pricing_engine = pricing_engine

        logger.info(
            "Cart service initialized",
            reservation_minutes=self.RESERVATION_MINUTES,
            default_tax_rate=float(self.DEFAULT_TAX_RATE),
        )

    async def _get_session_manager(self) -> CartSessionManager:
        """Get or create session manager instance."""
        if self._session_manager is None:
            self._session_manager = await get_cart_session_manager()
        return self._session_manager

    async def _get_reservation_service(self) -> InventoryReservationService:
        """Get or create reservation service instance."""
        if self._reservation_service is None:
            self._reservation_service = await get_reservation_service()
        return self._reservation_service

    def _get_pricing_engine(self) -> PricingEngine:
        """Get or create pricing engine instance."""
        if self._pricing_engine is None:
            self._pricing_engine = PricingEngine()
        return self._pricing_engine

    async def _get_or_create_cart(
        self,
        user_id: Optional[uuid.UUID] = None,
        session_id: Optional[str] = None,
    ) -> Cart:
        """
        Get existing cart or create new one.

        Args:
            user_id: Optional user identifier
            session_id: Optional session identifier

        Returns:
            Cart instance

        Raises:
            CartServiceError: If cart retrieval/creation fails
        """
        try:
            session_manager = await self._get_session_manager()

            if user_id:
                cart = await session_manager.get_cart_by_user(self.session, user_id)
                if not cart:
                    cart = await session_manager.create_authenticated_cart(
                        self.session, user_id
                    )
                    await self.session.commit()
            elif session_id:
                cart = await session_manager.get_cart_by_session(
                    self.session, session_id
                )
                if not cart:
                    cart = await session_manager.create_anonymous_cart(
                        self.session, session_id
                    )
                    await self.session.commit()
            else:
                raise CartServiceError(
                    "Either user_id or session_id must be provided",
                    code="INVALID_CART_REQUEST",
                )

            return cart

        except CartSessionError as e:
            logger.error(
                "Failed to get or create cart",
                user_id=str(user_id) if user_id else None,
                session_id=session_id,
                error=str(e),
            )
            raise CartServiceError(
                "Failed to initialize cart",
                code="CART_INIT_FAILED",
                user_id=str(user_id) if user_id else None,
                session_id=session_id,
            ) from e

    async def add_to_cart(
        self,
        request: AddToCartRequest,
        user_id: Optional[uuid.UUID] = None,
        session_id: Optional[str] = None,
    ) -> CartResponse:
        """
        Add configured vehicle to cart with inventory reservation.

        Args:
            request: Add to cart request data
            user_id: Optional authenticated user ID
            session_id: Optional anonymous session ID

        Returns:
            Updated cart response

        Raises:
            CartServiceError: If add to cart operation fails
            InsufficientInventoryError: If inventory unavailable
        """
        try:
            cart = await self._get_or_create_cart(user_id, session_id)

            vehicle = await self.session.get(Vehicle, request.vehicle_id)
            if not vehicle:
                raise CartServiceError(
                    f"Vehicle not found: {request.vehicle_id}",
                    code="VEHICLE_NOT_FOUND",
                    vehicle_id=str(request.vehicle_id),
                )

            configuration = None
            if request.configuration_id:
                configuration = await self.session.get(
                    VehicleConfiguration, request.configuration_id
                )
                if not configuration:
                    raise CartServiceError(
                        f"Configuration not found: {request.configuration_id}",
                        code="CONFIGURATION_NOT_FOUND",
                        configuration_id=str(request.configuration_id),
                    )

            reservation_service = await self._get_reservation_service()
            reservation_id = await reservation_service.create_reservation(
                vehicle_id=str(request.vehicle_id),
                quantity=request.quantity,
                user_id=str(user_id) if user_id else None,
                session_id=session_id,
            )

            pricing_engine = self._get_pricing_engine()
            price = await pricing_engine.calculate_total_price(
                vehicle_id=request.vehicle_id,
                base_price=vehicle.price,
                configuration_id=request.configuration_id,
            )

            cart_item = await self.repository.add_cart_item(
                cart_id=cart.id,
                vehicle_id=request.vehicle_id,
                configuration_id=request.configuration_id,
                quantity=request.quantity,
                price=price,
                reservation_minutes=self.RESERVATION_MINUTES,
            )

            await self.session.commit()

            logger.info(
                "Item added to cart",
                cart_id=str(cart.id),
                cart_item_id=str(cart_item.id),
                vehicle_id=str(request.vehicle_id),
                quantity=request.quantity,
                reservation_id=reservation_id,
            )

            return await self.get_cart(user_id=user_id, session_id=session_id)

        except InsufficientInventoryError:
            await self.session.rollback()
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Failed to add item to cart",
                vehicle_id=str(request.vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise CartServiceError(
                "Failed to add item to cart",
                code="ADD_TO_CART_FAILED",
                vehicle_id=str(request.vehicle_id),
            ) from e

    async def get_cart(
        self,
        user_id: Optional[uuid.UUID] = None,
        session_id: Optional[str] = None,
    ) -> CartResponse:
        """
        Retrieve current cart contents with pricing summary.

        Args:
            user_id: Optional authenticated user ID
            session_id: Optional anonymous session ID

        Returns:
            Cart response with items and summary

        Raises:
            CartNotFoundError: If cart not found
            CartServiceError: If cart retrieval fails
        """
        try:
            session_manager = await self._get_session_manager()

            if user_id:
                cart = await session_manager.get_cart_by_user(self.session, user_id)
            elif session_id:
                cart = await session_manager.get_cart_by_session(
                    self.session, session_id
                )
            else:
                raise CartServiceError(
                    "Either user_id or session_id must be provided",
                    code="INVALID_CART_REQUEST",
                )

            if not cart:
                raise CartNotFoundError(
                    user_id=str(user_id) if user_id else None,
                    session_id=session_id,
                )

            cart_items = []
            for item in cart.items:
                vehicle = await self.session.get(Vehicle, item.vehicle_id)
                if not vehicle:
                    continue

                cart_items.append(
                    CartItemResponse(
                        id=item.id,
                        vehicle_id=item.vehicle_id,
                        configuration_id=item.configuration_id,
                        quantity=item.quantity,
                        unit_price=item.price or Decimal("0.00"),
                        total_price=(item.price or Decimal("0.00")) * item.quantity,
                        vehicle_name=f"{vehicle.year} {vehicle.make} {vehicle.model}",
                        vehicle_year=vehicle.year,
                        vehicle_make=vehicle.make,
                        vehicle_model=vehicle.model,
                        reservation_expires_at=item.reserved_until,
                        added_at=item.created_at,
                    )
                )

            summary = await self._calculate_cart_summary(cart)

            logger.debug(
                "Cart retrieved",
                cart_id=str(cart.id),
                item_count=len(cart_items),
                total=float(summary.total),
            )

            return CartResponse(
                id=cart.id,
                user_id=cart.user_id,
                session_id=cart.session_id,
                items=cart_items,
                summary=summary,
                item_count=sum(item.quantity for item in cart_items),
                created_at=cart.created_at,
                updated_at=cart.updated_at,
                expires_at=cart.expires_at,
            )

        except CartNotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Failed to retrieve cart",
                user_id=str(user_id) if user_id else None,
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise CartServiceError(
                "Failed to retrieve cart",
                code="GET_CART_FAILED",
                user_id=str(user_id) if user_id else None,
                session_id=session_id,
            ) from e

    async def update_cart_item(
        self,
        item_id: uuid.UUID,
        request: UpdateCartItemRequest,
        user_id: Optional[uuid.UUID] = None,
        session_id: Optional[str] = None,
    ) -> CartResponse:
        """
        Update cart item quantity.

        Args:
            item_id: Cart item identifier
            request: Update request with new quantity
            user_id: Optional authenticated user ID
            session_id: Optional anonymous session ID

        Returns:
            Updated cart response

        Raises:
            CartItemNotFoundError: If cart item not found
            CartServiceError: If update operation fails
        """
        try:
            cart_item = await self.repository.get_cart_item(item_id)
            if not cart_item:
                raise CartItemNotFoundError(str(item_id))

            if request.quantity == 0:
                return await self.remove_cart_item(
                    item_id, user_id=user_id, session_id=session_id
                )

            old_quantity = cart_item.quantity
            quantity_delta = request.quantity - old_quantity

            if quantity_delta != 0:
                reservation_service = await self._get_reservation_service()

                if quantity_delta > 0:
                    await reservation_service.create_reservation(
                        vehicle_id=str(cart_item.vehicle_id),
                        quantity=quantity_delta,
                        user_id=str(user_id) if user_id else None,
                        session_id=session_id,
                    )

            await self.repository.update_cart_item_quantity(item_id, request.quantity)
            await self.repository.update_cart_item_reservation(
                item_id, self.RESERVATION_MINUTES
            )

            await self.session.commit()

            logger.info(
                "Cart item quantity updated",
                item_id=str(item_id),
                old_quantity=old_quantity,
                new_quantity=request.quantity,
            )

            return await self.get_cart(user_id=user_id, session_id=session_id)

        except (CartItemNotFoundError, InsufficientInventoryError):
            await self.session.rollback()
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Failed to update cart item",
                item_id=str(item_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise CartServiceError(
                "Failed to update cart item",
                code="UPDATE_CART_ITEM_FAILED",
                item_id=str(item_id),
            ) from e

    async def remove_cart_item(
        self,
        item_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        session_id: Optional[str] = None,
    ) -> CartResponse:
        """
        Remove item from cart and release inventory reservation.

        Args:
            item_id: Cart item identifier
            user_id: Optional authenticated user ID
            session_id: Optional anonymous session ID

        Returns:
            Updated cart response

        Raises:
            CartItemNotFoundError: If cart item not found
            CartServiceError: If removal operation fails
        """
        try:
            cart_item = await self.repository.get_cart_item(item_id)
            if not cart_item:
                raise CartItemNotFoundError(str(item_id))

            deleted = await self.repository.delete_cart_item(item_id)
            if not deleted:
                raise CartItemNotFoundError(str(item_id))

            await self.session.commit()

            logger.info(
                "Cart item removed",
                item_id=str(item_id),
                vehicle_id=str(cart_item.vehicle_id),
            )

            return await self.get_cart(user_id=user_id, session_id=session_id)

        except CartItemNotFoundError:
            await self.session.rollback()
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Failed to remove cart item",
                item_id=str(item_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise CartServiceError(
                "Failed to remove cart item",
                code="REMOVE_CART_ITEM_FAILED",
                item_id=str(item_id),
            ) from e

    async def apply_promotional_code(
        self,
        request: ApplyPromoRequest,
        user_id: Optional[uuid.UUID] = None,
        session_id: Optional[str] = None,
    ) -> CartResponse:
        """
        Apply promotional code to cart.

        Args:
            request: Promotional code request
            user_id: Optional authenticated user ID
            session_id: Optional anonymous session ID

        Returns:
            Updated cart response with discount applied

        Raises:
            InvalidPromotionalCodeError: If promotional code invalid
            CartServiceError: If application fails
        """
        try:
            cart = await self._get_or_create_cart(user_id, session_id)

            subtotal = sum(
                (item.price or Decimal("0.00")) * item.quantity for item in cart.items
            )

            is_valid, error_message = await self.repository.validate_promotional_code(
                code=request.promo_code,
                order_amount=subtotal,
            )

            if not is_valid:
                raise InvalidPromotionalCodeError(
                    request.promo_code,
                    error_message or "Invalid promotional code",
                )

            promo_code = await self.repository.get_promotional_code(request.promo_code)
            if not promo_code:
                raise InvalidPromotionalCodeError(
                    request.promo_code, "Promotional code not found"
                )

            cart.promotional_code_id = promo_code.id
            await self.session.commit()

            logger.info(
                "Promotional code applied",
                cart_id=str(cart.id),
                promo_code=request.promo_code,
                discount_amount=float(promo_code.discount_amount or 0),
            )

            return await self.get_cart(user_id=user_id, session_id=session_id)

        except InvalidPromotionalCodeError:
            await self.session.rollback()
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Failed to apply promotional code",
                promo_code=request.promo_code,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise CartServiceError(
                "Failed to apply promotional code",
                code="APPLY_PROMO_FAILED",
                promo_code=request.promo_code,
            ) from e

    async def migrate_cart_on_login(
        self,
        session_id: str,
        user_id: uuid.UUID,
    ) -> Optional[CartResponse]:
        """
        Migrate anonymous cart to authenticated user on login.

        Args:
            session_id: Anonymous session identifier
            user_id: Authenticated user identifier

        Returns:
            Migrated cart response or None if no cart to migrate

        Raises:
            CartServiceError: If migration fails
        """
        try:
            session_manager = await self._get_session_manager()

            migrated_cart = await session_manager.migrate_cart_on_login(
                self.session, session_id, user_id
            )

            if not migrated_cart:
                logger.debug(
                    "No cart to migrate",
                    session_id=session_id,
                    user_id=str(user_id),
                )
                return None

            await self.session.commit()

            logger.info(
                "Cart migrated on login",
                cart_id=str(migrated_cart.id),
                session_id=session_id,
                user_id=str(user_id),
                item_count=len(migrated_cart.items),
            )

            return await self.get_cart(user_id=user_id)

        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Failed to migrate cart on login",
                session_id=session_id,
                user_id=str(user_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise CartServiceError(
                "Failed to migrate cart on login",
                code="CART_MIGRATION_FAILED",
                session_id=session_id,
                user_id=str(user_id),
            ) from e

    async def _calculate_cart_summary(self, cart: Cart) -> CartSummary:
        """
        Calculate cart pricing summary with taxes and discounts.

        Args:
            cart: Cart instance

        Returns:
            Cart summary with pricing breakdown
        """
        subtotal = sum(
            (item.price or Decimal("0.00")) * item.quantity for item in cart.items
        )

        discount_amount = Decimal("0.00")
        promo_code = None
        promo_discount = None

        if cart.promotional_code_id:
            promo = await self.session.get(
                PromotionalCode, cart.promotional_code_id
            )
            if promo and promo.is_valid(subtotal):
                promo_code = promo.code
                if promo.discount_type == "percentage":
                    discount_amount = subtotal * (promo.discount_amount / 100)
                else:
                    discount_amount = promo.discount_amount
                promo_discount = discount_amount

        taxable_amount = subtotal - discount_amount
        tax_amount = taxable_amount * self.DEFAULT_TAX_RATE
        total = taxable_amount + tax_amount

        return CartSummary(
            subtotal=subtotal,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            tax_rate=self.DEFAULT_TAX_RATE,
            total=total,
            promo_code=promo_code,
            promo_discount=promo_discount,
        )


async def get_cart_service(session: AsyncSession) -> CartService:
    """
    Get cart service instance.

    Args:
        session: Async database session

    Returns:
        Cart service instance
    """
    return CartService(session)