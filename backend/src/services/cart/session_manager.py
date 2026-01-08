"""
Shopping cart session management for anonymous and authenticated users.

This module provides session management functionality for shopping carts with
support for both anonymous (session-based) and authenticated (user-based) carts.
Implements automatic expiration handling, cart migration on login, and Redis-based
session storage for anonymous users with proper TTL management.
"""

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.cache.redis_client import RedisClient, get_redis_client
from src.core.logging import get_logger
from src.database.models.cart import Cart

logger = get_logger(__name__)


class CartSessionError(Exception):
    """Base exception for cart session management errors."""

    def __init__(self, message: str, **context):
        super().__init__(message)
        self.context = context


class SessionCreationError(CartSessionError):
    """Exception raised when session creation fails."""

    pass


class SessionMigrationError(CartSessionError):
    """Exception raised when cart migration fails."""

    pass


class CartSessionManager:
    """
    Manages shopping cart sessions for anonymous and authenticated users.

    Provides functionality for creating session IDs, managing cart expiration
    (7 days for anonymous, 30 days for authenticated), cart migration on login,
    and Redis-based session storage for anonymous users.

    Attributes:
        ANONYMOUS_EXPIRATION_DAYS: Cart expiration for anonymous users (7 days)
        AUTHENTICATED_EXPIRATION_DAYS: Cart expiration for authenticated users (30 days)
        SESSION_ID_LENGTH: Length of generated session IDs (32 characters)
        REDIS_SESSION_PREFIX: Redis key prefix for session storage
    """

    ANONYMOUS_EXPIRATION_DAYS = 7
    AUTHENTICATED_EXPIRATION_DAYS = 30
    SESSION_ID_LENGTH = 32
    REDIS_SESSION_PREFIX = "cart:session"

    def __init__(self, redis_client: Optional[RedisClient] = None):
        """
        Initialize cart session manager.

        Args:
            redis_client: Optional Redis client instance (defaults to global client)
        """
        self._redis_client = redis_client
        logger.info(
            "Cart session manager initialized",
            anonymous_expiration_days=self.ANONYMOUS_EXPIRATION_DAYS,
            authenticated_expiration_days=self.AUTHENTICATED_EXPIRATION_DAYS,
        )

    async def _get_redis_client(self) -> RedisClient:
        """
        Get Redis client instance.

        Returns:
            Redis client instance

        Raises:
            SessionCreationError: If Redis client cannot be obtained
        """
        if self._redis_client is None:
            try:
                self._redis_client = await get_redis_client()
            except Exception as e:
                logger.error(
                    "Failed to get Redis client",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise SessionCreationError(
                    "Failed to initialize Redis client", error=str(e)
                ) from e
        return self._redis_client

    def generate_session_id(self) -> str:
        """
        Generate secure random session ID.

        Returns:
            URL-safe random session ID string

        Example:
            >>> manager = CartSessionManager()
            >>> session_id = manager.generate_session_id()
            >>> len(session_id) == 32
            True
        """
        session_id = secrets.token_urlsafe(self.SESSION_ID_LENGTH)
        logger.debug("Generated session ID", session_id_length=len(session_id))
        return session_id

    def calculate_expiration(
        self, is_authenticated: bool, from_time: Optional[datetime] = None
    ) -> datetime:
        """
        Calculate cart expiration timestamp.

        Args:
            is_authenticated: Whether cart belongs to authenticated user
            from_time: Base time for calculation (defaults to current UTC time)

        Returns:
            Expiration timestamp (7 days for anonymous, 30 days for authenticated)

        Example:
            >>> manager = CartSessionManager()
            >>> now = datetime.utcnow()
            >>> exp = manager.calculate_expiration(is_authenticated=False, from_time=now)
            >>> (exp - now).days == 7
            True
        """
        base_time = from_time or datetime.utcnow()
        days = (
            self.AUTHENTICATED_EXPIRATION_DAYS
            if is_authenticated
            else self.ANONYMOUS_EXPIRATION_DAYS
        )
        expiration = base_time + timedelta(days=days)

        logger.debug(
            "Calculated cart expiration",
            is_authenticated=is_authenticated,
            expiration_days=days,
            expires_at=expiration.isoformat(),
        )

        return expiration

    async def create_anonymous_cart(
        self, db: AsyncSession, session_id: Optional[str] = None
    ) -> Cart:
        """
        Create new anonymous cart with session-based storage.

        Args:
            db: Database session
            session_id: Optional session ID (generates new if not provided)

        Returns:
            Created cart instance

        Raises:
            SessionCreationError: If cart creation fails
        """
        if session_id is None:
            session_id = self.generate_session_id()

        try:
            expires_at = self.calculate_expiration(is_authenticated=False)

            cart = Cart(
                session_id=session_id,
                user_id=None,
                expires_at=expires_at,
            )

            db.add(cart)
            await db.flush()

            await self._store_session_in_redis(session_id, str(cart.id), expires_at)

            logger.info(
                "Created anonymous cart",
                cart_id=str(cart.id),
                session_id=session_id,
                expires_at=expires_at.isoformat(),
            )

            return cart

        except Exception as e:
            logger.error(
                "Failed to create anonymous cart",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise SessionCreationError(
                "Failed to create anonymous cart", session_id=session_id, error=str(e)
            ) from e

    async def create_authenticated_cart(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> Cart:
        """
        Create new authenticated user cart with database storage.

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            Created cart instance

        Raises:
            SessionCreationError: If cart creation fails
        """
        try:
            expires_at = self.calculate_expiration(is_authenticated=True)

            cart = Cart(
                user_id=user_id,
                session_id=None,
                expires_at=expires_at,
            )

            db.add(cart)
            await db.flush()

            logger.info(
                "Created authenticated cart",
                cart_id=str(cart.id),
                user_id=str(user_id),
                expires_at=expires_at.isoformat(),
            )

            return cart

        except Exception as e:
            logger.error(
                "Failed to create authenticated cart",
                user_id=str(user_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise SessionCreationError(
                "Failed to create authenticated cart",
                user_id=str(user_id),
                error=str(e),
            ) from e

    async def get_cart_by_session(
        self, db: AsyncSession, session_id: str
    ) -> Optional[Cart]:
        """
        Retrieve cart by session ID.

        Args:
            db: Database session
            session_id: Session identifier

        Returns:
            Cart instance if found and not expired, None otherwise
        """
        try:
            cart_id = await self._get_session_from_redis(session_id)

            if cart_id:
                stmt = select(Cart).where(
                    Cart.id == uuid.UUID(cart_id),
                    Cart.session_id == session_id,
                    Cart.expires_at > datetime.utcnow(),
                )
            else:
                stmt = select(Cart).where(
                    Cart.session_id == session_id,
                    Cart.expires_at > datetime.utcnow(),
                )

            result = await db.execute(stmt)
            cart = result.scalar_one_or_none()

            if cart:
                logger.debug(
                    "Retrieved cart by session",
                    cart_id=str(cart.id),
                    session_id=session_id,
                )
            else:
                logger.debug("No active cart found for session", session_id=session_id)

            return cart

        except Exception as e:
            logger.error(
                "Failed to retrieve cart by session",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def get_cart_by_user(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> Optional[Cart]:
        """
        Retrieve cart by user ID.

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            Cart instance if found and not expired, None otherwise
        """
        try:
            stmt = select(Cart).where(
                Cart.user_id == user_id,
                Cart.expires_at > datetime.utcnow(),
            )

            result = await db.execute(stmt)
            cart = result.scalar_one_or_none()

            if cart:
                logger.debug(
                    "Retrieved cart by user",
                    cart_id=str(cart.id),
                    user_id=str(user_id),
                )
            else:
                logger.debug("No active cart found for user", user_id=str(user_id))

            return cart

        except Exception as e:
            logger.error(
                "Failed to retrieve cart by user",
                user_id=str(user_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def migrate_cart_on_login(
        self, db: AsyncSession, session_id: str, user_id: uuid.UUID
    ) -> Optional[Cart]:
        """
        Migrate anonymous cart to authenticated user on login.

        Transfers cart items from session-based cart to user cart, extends
        expiration to 30 days, and cleans up session storage.

        Args:
            db: Database session
            session_id: Anonymous session ID
            user_id: Authenticated user UUID

        Returns:
            Migrated cart instance, or None if no cart to migrate

        Raises:
            SessionMigrationError: If migration fails
        """
        try:
            anonymous_cart = await self.get_cart_by_session(db, session_id)

            if not anonymous_cart:
                logger.debug(
                    "No anonymous cart to migrate",
                    session_id=session_id,
                    user_id=str(user_id),
                )
                return None

            user_cart = await self.get_cart_by_user(db, user_id)

            if user_cart:
                for item in anonymous_cart.items:
                    item.cart_id = user_cart.id

                await db.delete(anonymous_cart)

                user_cart.expires_at = self.calculate_expiration(is_authenticated=True)

                await self._remove_session_from_redis(session_id)

                logger.info(
                    "Migrated anonymous cart to existing user cart",
                    anonymous_cart_id=str(anonymous_cart.id),
                    user_cart_id=str(user_cart.id),
                    user_id=str(user_id),
                    items_migrated=len(anonymous_cart.items),
                )

                return user_cart
            else:
                anonymous_cart.session_id = None
                anonymous_cart.user_id = user_id
                anonymous_cart.expires_at = self.calculate_expiration(
                    is_authenticated=True
                )

                await self._remove_session_from_redis(session_id)

                logger.info(
                    "Converted anonymous cart to user cart",
                    cart_id=str(anonymous_cart.id),
                    user_id=str(user_id),
                    items_count=len(anonymous_cart.items),
                )

                return anonymous_cart

        except Exception as e:
            logger.error(
                "Failed to migrate cart on login",
                session_id=session_id,
                user_id=str(user_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise SessionMigrationError(
                "Failed to migrate cart on login",
                session_id=session_id,
                user_id=str(user_id),
                error=str(e),
            ) from e

    async def extend_cart_expiration(
        self, db: AsyncSession, cart: Cart, days: Optional[int] = None
    ) -> None:
        """
        Extend cart expiration by specified number of days.

        Args:
            db: Database session
            cart: Cart instance to extend
            days: Number of days to extend (defaults to standard expiration)

        Raises:
            CartSessionError: If expiration extension fails
        """
        try:
            if days is None:
                days = (
                    self.AUTHENTICATED_EXPIRATION_DAYS
                    if cart.is_authenticated
                    else self.ANONYMOUS_EXPIRATION_DAYS
                )

            new_expiration = datetime.utcnow() + timedelta(days=days)
            cart.expires_at = new_expiration

            if cart.is_anonymous and cart.session_id:
                await self._store_session_in_redis(
                    cart.session_id, str(cart.id), new_expiration
                )

            logger.info(
                "Extended cart expiration",
                cart_id=str(cart.id),
                days=days,
                new_expiration=new_expiration.isoformat(),
            )

        except Exception as e:
            logger.error(
                "Failed to extend cart expiration",
                cart_id=str(cart.id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise CartSessionError(
                "Failed to extend cart expiration",
                cart_id=str(cart.id),
                error=str(e),
            ) from e

    async def _store_session_in_redis(
        self, session_id: str, cart_id: str, expires_at: datetime
    ) -> None:
        """
        Store session mapping in Redis with TTL.

        Args:
            session_id: Session identifier
            cart_id: Cart UUID string
            expires_at: Expiration timestamp

        Raises:
            SessionCreationError: If Redis storage fails
        """
        try:
            redis = await self._get_redis_client()
            key = f"{self.REDIS_SESSION_PREFIX}:{session_id}"

            ttl_seconds = int((expires_at - datetime.utcnow()).total_seconds())

            if ttl_seconds > 0:
                await redis.set(key, cart_id, ex=ttl_seconds)

                logger.debug(
                    "Stored session in Redis",
                    session_id=session_id,
                    cart_id=cart_id,
                    ttl_seconds=ttl_seconds,
                )
            else:
                logger.warning(
                    "Skipped Redis storage for expired session",
                    session_id=session_id,
                    expires_at=expires_at.isoformat(),
                )

        except RedisError as e:
            logger.error(
                "Redis error storing session",
                session_id=session_id,
                error=str(e),
            )
            raise SessionCreationError(
                "Failed to store session in Redis",
                session_id=session_id,
                error=str(e),
            ) from e

    async def _get_session_from_redis(self, session_id: str) -> Optional[str]:
        """
        Retrieve cart ID from Redis session storage.

        Args:
            session_id: Session identifier

        Returns:
            Cart ID string if found, None otherwise
        """
        try:
            redis = await self._get_redis_client()
            key = f"{self.REDIS_SESSION_PREFIX}:{session_id}"

            cart_id = await redis.get(key)

            if cart_id:
                logger.debug(
                    "Retrieved session from Redis",
                    session_id=session_id,
                    cart_id=cart_id,
                )
            else:
                logger.debug("Session not found in Redis", session_id=session_id)

            return cart_id

        except RedisError as e:
            logger.error(
                "Redis error retrieving session",
                session_id=session_id,
                error=str(e),
            )
            return None

    async def _remove_session_from_redis(self, session_id: str) -> None:
        """
        Remove session mapping from Redis.

        Args:
            session_id: Session identifier
        """
        try:
            redis = await self._get_redis_client()
            key = f"{self.REDIS_SESSION_PREFIX}:{session_id}"

            await redis.delete(key)

            logger.debug("Removed session from Redis", session_id=session_id)

        except RedisError as e:
            logger.error(
                "Redis error removing session",
                session_id=session_id,
                error=str(e),
            )


_session_manager: Optional[CartSessionManager] = None


async def get_cart_session_manager() -> CartSessionManager:
    """
    Get or create global cart session manager instance.

    Returns:
        Singleton cart session manager instance
    """
    global _session_manager

    if _session_manager is None:
        _session_manager = CartSessionManager()

    return _session_manager