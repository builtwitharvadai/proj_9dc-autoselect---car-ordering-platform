"""
Cart repository for data access operations.

This module implements the CartRepository class providing async methods for cart
CRUD operations, cart item management, promotional code validation, and cart
expiration queries. Includes optimized queries with proper error handling and
comprehensive logging for cart data access operations.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.logging import get_logger
from src.database.models.cart import Cart, CartItem
from src.database.models.promotional_code import PromotionalCode
from src.database.models.vehicle import Vehicle
from src.database.models.vehicle_configuration import VehicleConfiguration

logger = get_logger(__name__)


class CartRepository:
    """
    Repository for cart data access operations.

    Provides async methods for cart CRUD operations, cart item management,
    promotional code validation, and cart expiration queries with optimized
    database queries and comprehensive error handling.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize cart repository.

        Args:
            session: Async database session for operations
        """
        self.session = session
        logger.debug("CartRepository initialized")

    async def get_cart_by_id(self, cart_id: uuid.UUID) -> Optional[Cart]:
        """
        Retrieve cart by ID with items eagerly loaded.

        Args:
            cart_id: Cart identifier

        Returns:
            Cart instance if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = (
                select(Cart)
                .options(selectinload(Cart.items))
                .where(Cart.id == cart_id)
            )
            result = await self.session.execute(stmt)
            cart = result.scalar_one_or_none()

            if cart:
                logger.debug(
                    "Cart retrieved by ID",
                    cart_id=str(cart_id),
                    item_count=len(cart.items),
                )
            else:
                logger.debug("Cart not found", cart_id=str(cart_id))

            return cart
        except SQLAlchemyError as e:
            logger.error(
                "Failed to retrieve cart by ID",
                cart_id=str(cart_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_cart_by_user_id(self, user_id: uuid.UUID) -> Optional[Cart]:
        """
        Retrieve active cart for authenticated user.

        Args:
            user_id: User identifier

        Returns:
            Active cart if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = (
                select(Cart)
                .options(selectinload(Cart.items))
                .where(
                    and_(
                        Cart.user_id == user_id,
                        Cart.expires_at > datetime.utcnow(),
                    )
                )
                .order_by(Cart.created_at.desc())
            )
            result = await self.session.execute(stmt)
            cart = result.scalar_one_or_none()

            if cart:
                logger.debug(
                    "Cart retrieved for user",
                    user_id=str(user_id),
                    cart_id=str(cart.id),
                    item_count=len(cart.items),
                )
            else:
                logger.debug("No active cart found for user", user_id=str(user_id))

            return cart
        except SQLAlchemyError as e:
            logger.error(
                "Failed to retrieve cart for user",
                user_id=str(user_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_cart_by_session_id(self, session_id: str) -> Optional[Cart]:
        """
        Retrieve active cart for anonymous session.

        Args:
            session_id: Session identifier

        Returns:
            Active cart if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = (
                select(Cart)
                .options(selectinload(Cart.items))
                .where(
                    and_(
                        Cart.session_id == session_id,
                        Cart.expires_at > datetime.utcnow(),
                    )
                )
                .order_by(Cart.created_at.desc())
            )
            result = await self.session.execute(stmt)
            cart = result.scalar_one_or_none()

            if cart:
                logger.debug(
                    "Cart retrieved for session",
                    session_id=session_id,
                    cart_id=str(cart.id),
                    item_count=len(cart.items),
                )
            else:
                logger.debug(
                    "No active cart found for session", session_id=session_id
                )

            return cart
        except SQLAlchemyError as e:
            logger.error(
                "Failed to retrieve cart for session",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def create_cart(
        self,
        user_id: Optional[uuid.UUID] = None,
        session_id: Optional[str] = None,
        expiration_days: int = 7,
    ) -> Cart:
        """
        Create new cart for user or session.

        Args:
            user_id: User identifier for authenticated cart
            session_id: Session identifier for anonymous cart
            expiration_days: Days until cart expires (7 for anonymous, 30 for authenticated)

        Returns:
            Created cart instance

        Raises:
            ValueError: If neither user_id nor session_id provided
            SQLAlchemyError: If database operation fails
        """
        if not user_id and not session_id:
            raise ValueError("Either user_id or session_id must be provided")

        if user_id and session_id:
            raise ValueError("Cannot provide both user_id and session_id")

        try:
            expires_at = datetime.utcnow() + timedelta(days=expiration_days)

            cart = Cart(
                user_id=user_id,
                session_id=session_id,
                expires_at=expires_at,
            )

            self.session.add(cart)
            await self.session.flush()

            logger.info(
                "Cart created",
                cart_id=str(cart.id),
                user_id=str(user_id) if user_id else None,
                session_id=session_id,
                expires_at=expires_at.isoformat(),
            )

            return cart
        except IntegrityError as e:
            logger.error(
                "Cart creation failed - integrity error",
                user_id=str(user_id) if user_id else None,
                session_id=session_id,
                error=str(e),
            )
            raise
        except SQLAlchemyError as e:
            logger.error(
                "Cart creation failed",
                user_id=str(user_id) if user_id else None,
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def update_cart_expiration(
        self, cart_id: uuid.UUID, expiration_days: int
    ) -> Optional[Cart]:
        """
        Update cart expiration timestamp.

        Args:
            cart_id: Cart identifier
            expiration_days: Days to extend expiration

        Returns:
            Updated cart if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            new_expires_at = datetime.utcnow() + timedelta(days=expiration_days)

            stmt = (
                update(Cart)
                .where(Cart.id == cart_id)
                .values(expires_at=new_expires_at, updated_at=datetime.utcnow())
                .returning(Cart)
            )

            result = await self.session.execute(stmt)
            cart = result.scalar_one_or_none()

            if cart:
                logger.info(
                    "Cart expiration updated",
                    cart_id=str(cart_id),
                    new_expires_at=new_expires_at.isoformat(),
                )
            else:
                logger.warning("Cart not found for expiration update", cart_id=str(cart_id))

            return cart
        except SQLAlchemyError as e:
            logger.error(
                "Failed to update cart expiration",
                cart_id=str(cart_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def migrate_cart_to_user(
        self, session_id: str, user_id: uuid.UUID
    ) -> Optional[Cart]:
        """
        Migrate anonymous cart to authenticated user.

        Args:
            session_id: Session identifier of anonymous cart
            user_id: User identifier to migrate cart to

        Returns:
            Migrated cart if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            new_expires_at = datetime.utcnow() + timedelta(days=30)

            stmt = (
                update(Cart)
                .where(
                    and_(
                        Cart.session_id == session_id,
                        Cart.expires_at > datetime.utcnow(),
                    )
                )
                .values(
                    user_id=user_id,
                    session_id=None,
                    expires_at=new_expires_at,
                    updated_at=datetime.utcnow(),
                )
                .returning(Cart)
            )

            result = await self.session.execute(stmt)
            cart = result.scalar_one_or_none()

            if cart:
                logger.info(
                    "Cart migrated to user",
                    cart_id=str(cart.id),
                    session_id=session_id,
                    user_id=str(user_id),
                    new_expires_at=new_expires_at.isoformat(),
                )
            else:
                logger.debug(
                    "No cart found to migrate",
                    session_id=session_id,
                    user_id=str(user_id),
                )

            return cart
        except SQLAlchemyError as e:
            logger.error(
                "Failed to migrate cart to user",
                session_id=session_id,
                user_id=str(user_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def delete_cart(self, cart_id: uuid.UUID) -> bool:
        """
        Delete cart and all associated items.

        Args:
            cart_id: Cart identifier

        Returns:
            True if cart was deleted, False if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = delete(Cart).where(Cart.id == cart_id)
            result = await self.session.execute(stmt)

            deleted = result.rowcount > 0

            if deleted:
                logger.info("Cart deleted", cart_id=str(cart_id))
            else:
                logger.debug("Cart not found for deletion", cart_id=str(cart_id))

            return deleted
        except SQLAlchemyError as e:
            logger.error(
                "Failed to delete cart",
                cart_id=str(cart_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def add_cart_item(
        self,
        cart_id: uuid.UUID,
        vehicle_id: uuid.UUID,
        configuration_id: uuid.UUID,
        quantity: int = 1,
        price: Optional[Decimal] = None,
        reservation_minutes: int = 15,
    ) -> CartItem:
        """
        Add item to cart with inventory reservation.

        Args:
            cart_id: Cart identifier
            vehicle_id: Vehicle identifier
            configuration_id: Configuration identifier
            quantity: Item quantity (default 1)
            price: Cached price at time of addition
            reservation_minutes: Minutes to reserve inventory (default 15)

        Returns:
            Created cart item

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            reserved_until = datetime.utcnow() + timedelta(minutes=reservation_minutes)

            cart_item = CartItem(
                cart_id=cart_id,
                vehicle_id=vehicle_id,
                configuration_id=configuration_id,
                quantity=quantity,
                price=price,
                reserved_until=reserved_until,
            )

            self.session.add(cart_item)
            await self.session.flush()

            logger.info(
                "Cart item added",
                cart_item_id=str(cart_item.id),
                cart_id=str(cart_id),
                vehicle_id=str(vehicle_id),
                configuration_id=str(configuration_id),
                quantity=quantity,
                reserved_until=reserved_until.isoformat(),
            )

            return cart_item
        except IntegrityError as e:
            logger.error(
                "Cart item creation failed - integrity error",
                cart_id=str(cart_id),
                vehicle_id=str(vehicle_id),
                error=str(e),
            )
            raise
        except SQLAlchemyError as e:
            logger.error(
                "Cart item creation failed",
                cart_id=str(cart_id),
                vehicle_id=str(vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_cart_item(self, item_id: uuid.UUID) -> Optional[CartItem]:
        """
        Retrieve cart item by ID.

        Args:
            item_id: Cart item identifier

        Returns:
            Cart item if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = select(CartItem).where(CartItem.id == item_id)
            result = await self.session.execute(stmt)
            cart_item = result.scalar_one_or_none()

            if cart_item:
                logger.debug("Cart item retrieved", item_id=str(item_id))
            else:
                logger.debug("Cart item not found", item_id=str(item_id))

            return cart_item
        except SQLAlchemyError as e:
            logger.error(
                "Failed to retrieve cart item",
                item_id=str(item_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def update_cart_item_quantity(
        self, item_id: uuid.UUID, quantity: int
    ) -> Optional[CartItem]:
        """
        Update cart item quantity.

        Args:
            item_id: Cart item identifier
            quantity: New quantity value

        Returns:
            Updated cart item if found, None otherwise

        Raises:
            ValueError: If quantity is invalid
            SQLAlchemyError: If database operation fails
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if quantity > 100:
            raise ValueError("Quantity cannot exceed 100")

        try:
            stmt = (
                update(CartItem)
                .where(CartItem.id == item_id)
                .values(quantity=quantity, updated_at=datetime.utcnow())
                .returning(CartItem)
            )

            result = await self.session.execute(stmt)
            cart_item = result.scalar_one_or_none()

            if cart_item:
                logger.info(
                    "Cart item quantity updated",
                    item_id=str(item_id),
                    new_quantity=quantity,
                )
            else:
                logger.warning(
                    "Cart item not found for quantity update", item_id=str(item_id)
                )

            return cart_item
        except SQLAlchemyError as e:
            logger.error(
                "Failed to update cart item quantity",
                item_id=str(item_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def update_cart_item_reservation(
        self, item_id: uuid.UUID, reservation_minutes: int = 15
    ) -> Optional[CartItem]:
        """
        Update cart item inventory reservation.

        Args:
            item_id: Cart item identifier
            reservation_minutes: Minutes to extend reservation (default 15)

        Returns:
            Updated cart item if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            new_reserved_until = datetime.utcnow() + timedelta(
                minutes=reservation_minutes
            )

            stmt = (
                update(CartItem)
                .where(CartItem.id == item_id)
                .values(
                    reserved_until=new_reserved_until, updated_at=datetime.utcnow()
                )
                .returning(CartItem)
            )

            result = await self.session.execute(stmt)
            cart_item = result.scalar_one_or_none()

            if cart_item:
                logger.info(
                    "Cart item reservation updated",
                    item_id=str(item_id),
                    new_reserved_until=new_reserved_until.isoformat(),
                )
            else:
                logger.warning(
                    "Cart item not found for reservation update", item_id=str(item_id)
                )

            return cart_item
        except SQLAlchemyError as e:
            logger.error(
                "Failed to update cart item reservation",
                item_id=str(item_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def delete_cart_item(self, item_id: uuid.UUID) -> bool:
        """
        Delete cart item.

        Args:
            item_id: Cart item identifier

        Returns:
            True if item was deleted, False if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = delete(CartItem).where(CartItem.id == item_id)
            result = await self.session.execute(stmt)

            deleted = result.rowcount > 0

            if deleted:
                logger.info("Cart item deleted", item_id=str(item_id))
            else:
                logger.debug("Cart item not found for deletion", item_id=str(item_id))

            return deleted
        except SQLAlchemyError as e:
            logger.error(
                "Failed to delete cart item",
                item_id=str(item_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_expired_carts(self, limit: int = 100) -> list[Cart]:
        """
        Retrieve expired carts for cleanup.

        Args:
            limit: Maximum number of carts to retrieve (default 100)

        Returns:
            List of expired carts

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = (
                select(Cart)
                .where(Cart.expires_at <= datetime.utcnow())
                .order_by(Cart.expires_at.asc())
                .limit(limit)
            )

            result = await self.session.execute(stmt)
            carts = list(result.scalars().all())

            logger.debug("Expired carts retrieved", count=len(carts), limit=limit)

            return carts
        except SQLAlchemyError as e:
            logger.error(
                "Failed to retrieve expired carts",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_expired_reservations(self, limit: int = 100) -> list[CartItem]:
        """
        Retrieve cart items with expired reservations.

        Args:
            limit: Maximum number of items to retrieve (default 100)

        Returns:
            List of cart items with expired reservations

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = (
                select(CartItem)
                .where(
                    and_(
                        CartItem.reserved_until.isnot(None),
                        CartItem.reserved_until <= datetime.utcnow(),
                    )
                )
                .order_by(CartItem.reserved_until.asc())
                .limit(limit)
            )

            result = await self.session.execute(stmt)
            items = list(result.scalars().all())

            logger.debug(
                "Expired reservations retrieved", count=len(items), limit=limit
            )

            return items
        except SQLAlchemyError as e:
            logger.error(
                "Failed to retrieve expired reservations",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_promotional_code(self, code: str) -> Optional[PromotionalCode]:
        """
        Retrieve promotional code by code string.

        Args:
            code: Promotional code string

        Returns:
            Promotional code if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = select(PromotionalCode).where(
                func.upper(PromotionalCode.code) == code.upper()
            )
            result = await self.session.execute(stmt)
            promo_code = result.scalar_one_or_none()

            if promo_code:
                logger.debug("Promotional code retrieved", code=code)
            else:
                logger.debug("Promotional code not found", code=code)

            return promo_code
        except SQLAlchemyError as e:
            logger.error(
                "Failed to retrieve promotional code",
                code=code,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def validate_promotional_code(
        self,
        code: str,
        order_amount: Decimal,
        vehicle_id: Optional[uuid.UUID] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate promotional code for order.

        Args:
            code: Promotional code string
            order_amount: Total order amount
            vehicle_id: Vehicle ID to check applicability

        Returns:
            Tuple of (is_valid, error_message)

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            promo_code = await self.get_promotional_code(code)

            if not promo_code:
                return False, "Promotional code not found"

            vehicle_id_str = str(vehicle_id) if vehicle_id else None
            is_valid = promo_code.is_valid(order_amount, vehicle_id_str)

            if not is_valid:
                if not promo_code.is_active:
                    return False, "Promotional code is inactive"
                if promo_code.is_expired:
                    return False, "Promotional code has expired"
                if promo_code.is_usage_exhausted:
                    return False, "Promotional code usage limit reached"
                if order_amount < promo_code.minimum_order_amount:
                    return (
                        False,
                        f"Order amount must be at least ${promo_code.minimum_order_amount}",
                    )
                if vehicle_id_str and promo_code.applicable_vehicles:
                    if vehicle_id_str not in promo_code.applicable_vehicles:
                        return False, "Promotional code not applicable to this vehicle"

                return False, "Promotional code is not valid"

            logger.info(
                "Promotional code validated",
                code=code,
                order_amount=order_amount,
                is_valid=is_valid,
            )

            return True, None
        except SQLAlchemyError as e:
            logger.error(
                "Failed to validate promotional code",
                code=code,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def increment_promotional_code_usage(self, code: str) -> Optional[PromotionalCode]:
        """
        Increment promotional code usage count.

        Args:
            code: Promotional code string

        Returns:
            Updated promotional code if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            promo_code = await self.get_promotional_code(code)

            if not promo_code:
                logger.warning(
                    "Promotional code not found for usage increment", code=code
                )
                return None

            promo_code.increment_usage()
            await self.session.flush()

            logger.info(
                "Promotional code usage incremented",
                code=code,
                usage_count=promo_code.usage_count,
            )

            return promo_code
        except ValueError as e:
            logger.error(
                "Failed to increment promotional code usage - validation error",
                code=code,
                error=str(e),
            )
            raise
        except SQLAlchemyError as e:
            logger.error(
                "Failed to increment promotional code usage",
                code=code,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_cart_statistics(
        self, user_id: Optional[uuid.UUID] = None
    ) -> dict:
        """
        Get cart statistics for analytics.

        Args:
            user_id: Optional user ID to filter statistics

        Returns:
            Dictionary containing cart statistics

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            base_stmt = select(Cart)

            if user_id:
                base_stmt = base_stmt.where(Cart.user_id == user_id)

            total_stmt = select(func.count()).select_from(base_stmt.subquery())
            active_stmt = select(func.count()).select_from(
                base_stmt.where(Cart.expires_at > datetime.utcnow()).subquery()
            )
            expired_stmt = select(func.count()).select_from(
                base_stmt.where(Cart.expires_at <= datetime.utcnow()).subquery()
            )

            total_result = await self.session.execute(total_stmt)
            active_result = await self.session.execute(active_stmt)
            expired_result = await self.session.execute(expired_stmt)

            total_carts = total_result.scalar_one()
            active_carts = active_result.scalar_one()
            expired_carts = expired_result.scalar_one()

            statistics = {
                "total_carts": total_carts,
                "active_carts": active_carts,
                "expired_carts": expired_carts,
                "user_id": str(user_id) if user_id else None,
            }

            logger.debug("Cart statistics retrieved", **statistics)

            return statistics
        except SQLAlchemyError as e:
            logger.error(
                "Failed to retrieve cart statistics",
                user_id=str(user_id) if user_id else None,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise