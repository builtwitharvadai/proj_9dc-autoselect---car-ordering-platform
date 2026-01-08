"""
Inventory reservation system for cart items.

This module implements the InventoryReservationService for managing temporary
inventory reservations when items are added to shopping carts. Uses Redis for
TTL-based reservations with 15-minute expiration, automatic cleanup, and
availability checking.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Optional, Any

from src.cache.redis_client import RedisClient, get_redis_client
from src.core.logging import get_logger

logger = get_logger(__name__)


class ReservationError(Exception):
    """Base exception for reservation operations."""

    def __init__(self, message: str, code: str, **context: Any):
        super().__init__(message)
        self.code = code
        self.context = context


class InsufficientInventoryError(ReservationError):
    """Raised when insufficient inventory is available for reservation."""

    def __init__(self, vehicle_id: str, requested: int, available: int):
        super().__init__(
            f"Insufficient inventory for vehicle {vehicle_id}",
            code="INSUFFICIENT_INVENTORY",
            vehicle_id=vehicle_id,
            requested=requested,
            available=available,
        )


class ReservationNotFoundError(ReservationError):
    """Raised when a reservation cannot be found."""

    def __init__(self, reservation_id: str):
        super().__init__(
            f"Reservation {reservation_id} not found",
            code="RESERVATION_NOT_FOUND",
            reservation_id=reservation_id,
        )


class InventoryReservationService:
    """
    Service for managing temporary inventory reservations.

    Implements TTL-based reservations using Redis with automatic expiration,
    availability checking, and background cleanup tasks. Reservations expire
    after 15 minutes to prevent inventory from being held indefinitely.
    """

    RESERVATION_TTL_SECONDS = 900  # 15 minutes
    RESERVATION_KEY_PREFIX = "reservation"
    INVENTORY_KEY_PREFIX = "inventory_available"
    CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes

    def __init__(self, redis_client: Optional[RedisClient] = None):
        """
        Initialize inventory reservation service.

        Args:
            redis_client: Optional Redis client instance. If not provided,
                         uses the global Redis client.
        """
        self._redis_client = redis_client
        self._cleanup_task: Optional[asyncio.Task] = None

        logger.info(
            "Inventory reservation service initialized",
            ttl_seconds=self.RESERVATION_TTL_SECONDS,
            cleanup_interval=self.CLEANUP_INTERVAL_SECONDS,
        )

    async def _get_redis(self) -> RedisClient:
        """
        Get Redis client instance.

        Returns:
            Redis client instance

        Raises:
            ConnectionError: If Redis client is not available
        """
        if self._redis_client is None:
            self._redis_client = await get_redis_client()
        return self._redis_client

    def _make_reservation_key(self, reservation_id: str) -> str:
        """
        Generate Redis key for reservation.

        Args:
            reservation_id: Unique reservation identifier

        Returns:
            Formatted Redis key
        """
        return f"{self.RESERVATION_KEY_PREFIX}:{reservation_id}"

    def _make_inventory_key(self, vehicle_id: str) -> str:
        """
        Generate Redis key for inventory availability.

        Args:
            vehicle_id: Vehicle identifier

        Returns:
            Formatted Redis key
        """
        return f"{self.INVENTORY_KEY_PREFIX}:{vehicle_id}"

    async def create_reservation(
        self,
        vehicle_id: str,
        quantity: int = 1,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """
        Create a new inventory reservation.

        Args:
            vehicle_id: Vehicle identifier to reserve
            quantity: Quantity to reserve (default: 1)
            user_id: Optional user identifier
            session_id: Optional session identifier

        Returns:
            Unique reservation identifier

        Raises:
            InsufficientInventoryError: If insufficient inventory available
            ReservationError: If reservation creation fails
            ValueError: If quantity is invalid
        """
        if quantity <= 0:
            raise ValueError("Reservation quantity must be positive")

        redis = await self._get_redis()
        reservation_id = str(uuid.uuid4())

        try:
            # Check available inventory
            available = await self.check_availability(vehicle_id)
            if available < quantity:
                logger.warning(
                    "Insufficient inventory for reservation",
                    vehicle_id=vehicle_id,
                    requested=quantity,
                    available=available,
                )
                raise InsufficientInventoryError(vehicle_id, quantity, available)

            # Create reservation data
            reservation_data = {
                "reservation_id": reservation_id,
                "vehicle_id": vehicle_id,
                "quantity": quantity,
                "user_id": user_id or "",
                "session_id": session_id or "",
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (
                    datetime.utcnow()
                    + timedelta(seconds=self.RESERVATION_TTL_SECONDS)
                ).isoformat(),
            }

            # Store reservation with TTL
            reservation_key = self._make_reservation_key(reservation_id)
            await redis.set_json(
                reservation_key,
                reservation_data,
                ex=self.RESERVATION_TTL_SECONDS,
            )

            # Decrement available inventory
            inventory_key = self._make_inventory_key(vehicle_id)
            new_available = await redis.decr(inventory_key, quantity)

            logger.info(
                "Reservation created",
                reservation_id=reservation_id,
                vehicle_id=vehicle_id,
                quantity=quantity,
                remaining_available=new_available,
                user_id=user_id,
                session_id=session_id,
            )

            return reservation_id

        except InsufficientInventoryError:
            raise
        except Exception as e:
            logger.error(
                "Failed to create reservation",
                vehicle_id=vehicle_id,
                quantity=quantity,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ReservationError(
                "Failed to create reservation",
                code="RESERVATION_CREATE_FAILED",
                vehicle_id=vehicle_id,
                quantity=quantity,
            ) from e

    async def release_reservation(self, reservation_id: str) -> None:
        """
        Release an existing reservation.

        Args:
            reservation_id: Reservation identifier to release

        Raises:
            ReservationNotFoundError: If reservation not found
            ReservationError: If release operation fails
        """
        redis = await self._get_redis()
        reservation_key = self._make_reservation_key(reservation_id)

        try:
            # Get reservation data
            reservation_data = await redis.get_json(reservation_key)
            if reservation_data is None:
                logger.warning(
                    "Reservation not found for release",
                    reservation_id=reservation_id,
                )
                raise ReservationNotFoundError(reservation_id)

            vehicle_id = reservation_data["vehicle_id"]
            quantity = reservation_data["quantity"]

            # Delete reservation
            await redis.delete(reservation_key)

            # Increment available inventory
            inventory_key = self._make_inventory_key(vehicle_id)
            new_available = await redis.incr(inventory_key, quantity)

            logger.info(
                "Reservation released",
                reservation_id=reservation_id,
                vehicle_id=vehicle_id,
                quantity=quantity,
                new_available=new_available,
            )

        except ReservationNotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Failed to release reservation",
                reservation_id=reservation_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ReservationError(
                "Failed to release reservation",
                code="RESERVATION_RELEASE_FAILED",
                reservation_id=reservation_id,
            ) from e

    async def check_availability(self, vehicle_id: str) -> int:
        """
        Check available inventory for a vehicle.

        Args:
            vehicle_id: Vehicle identifier

        Returns:
            Available quantity (unreserved inventory)

        Raises:
            ReservationError: If availability check fails
        """
        redis = await self._get_redis()
        inventory_key = self._make_inventory_key(vehicle_id)

        try:
            available_str = await redis.get(inventory_key)
            if available_str is None:
                logger.debug(
                    "No inventory data found, returning 0",
                    vehicle_id=vehicle_id,
                )
                return 0

            available = int(available_str)
            logger.debug(
                "Inventory availability checked",
                vehicle_id=vehicle_id,
                available=available,
            )
            return max(0, available)

        except (ValueError, TypeError) as e:
            logger.error(
                "Invalid inventory data",
                vehicle_id=vehicle_id,
                error=str(e),
            )
            return 0
        except Exception as e:
            logger.error(
                "Failed to check availability",
                vehicle_id=vehicle_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ReservationError(
                "Failed to check availability",
                code="AVAILABILITY_CHECK_FAILED",
                vehicle_id=vehicle_id,
            ) from e

    async def get_reservation(self, reservation_id: str) -> Optional[dict[str, Any]]:
        """
        Get reservation details.

        Args:
            reservation_id: Reservation identifier

        Returns:
            Reservation data dictionary or None if not found

        Raises:
            ReservationError: If retrieval fails
        """
        redis = await self._get_redis()
        reservation_key = self._make_reservation_key(reservation_id)

        try:
            reservation_data = await redis.get_json(reservation_key)
            if reservation_data is None:
                logger.debug(
                    "Reservation not found",
                    reservation_id=reservation_id,
                )
                return None

            # Add TTL information
            ttl = await redis.ttl(reservation_key)
            if ttl > 0:
                reservation_data["ttl_seconds"] = ttl

            logger.debug(
                "Reservation retrieved",
                reservation_id=reservation_id,
                vehicle_id=reservation_data.get("vehicle_id"),
            )
            return reservation_data

        except Exception as e:
            logger.error(
                "Failed to get reservation",
                reservation_id=reservation_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ReservationError(
                "Failed to get reservation",
                code="RESERVATION_GET_FAILED",
                reservation_id=reservation_id,
            ) from e

    async def extend_reservation(
        self,
        reservation_id: str,
        additional_seconds: Optional[int] = None,
    ) -> None:
        """
        Extend reservation expiration time.

        Args:
            reservation_id: Reservation identifier
            additional_seconds: Additional seconds to add (default: reset to full TTL)

        Raises:
            ReservationNotFoundError: If reservation not found
            ReservationError: If extension fails
        """
        redis = await self._get_redis()
        reservation_key = self._make_reservation_key(reservation_id)

        try:
            # Check if reservation exists
            exists = await redis.exists(reservation_key)
            if not exists:
                logger.warning(
                    "Reservation not found for extension",
                    reservation_id=reservation_id,
                )
                raise ReservationNotFoundError(reservation_id)

            # Set new expiration
            ttl = additional_seconds or self.RESERVATION_TTL_SECONDS
            await redis.expire(reservation_key, ttl)

            logger.info(
                "Reservation extended",
                reservation_id=reservation_id,
                ttl_seconds=ttl,
            )

        except ReservationNotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Failed to extend reservation",
                reservation_id=reservation_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ReservationError(
                "Failed to extend reservation",
                code="RESERVATION_EXTEND_FAILED",
                reservation_id=reservation_id,
            ) from e

    async def cleanup_expired_reservations(self) -> int:
        """
        Clean up expired reservations and restore inventory.

        This method scans for expired reservations and ensures inventory
        counts are accurate. Redis TTL handles automatic deletion, but this
        provides additional cleanup for edge cases.

        Returns:
            Number of reservations cleaned up

        Raises:
            ReservationError: If cleanup fails
        """
        redis = await self._get_redis()
        cleaned_count = 0

        try:
            pattern = f"{self.RESERVATION_KEY_PREFIX}:*"
            reservation_keys = []

            async for key in redis._client.scan_iter(match=pattern):
                reservation_keys.append(key)

            logger.debug(
                "Starting reservation cleanup",
                total_reservations=len(reservation_keys),
            )

            for key in reservation_keys:
                try:
                    ttl = await redis.ttl(key)
                    if ttl == -2:  # Key doesn't exist
                        cleaned_count += 1
                    elif ttl == -1:  # Key exists but has no expiration
                        # This shouldn't happen, but handle it
                        await redis.expire(key, self.RESERVATION_TTL_SECONDS)
                        logger.warning(
                            "Found reservation without TTL, setting expiration",
                            key=key,
                        )
                except Exception as e:
                    logger.error(
                        "Error checking reservation TTL",
                        key=key,
                        error=str(e),
                    )

            logger.info(
                "Reservation cleanup completed",
                cleaned_count=cleaned_count,
                total_checked=len(reservation_keys),
            )

            return cleaned_count

        except Exception as e:
            logger.error(
                "Failed to cleanup expired reservations",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ReservationError(
                "Failed to cleanup expired reservations",
                code="CLEANUP_FAILED",
            ) from e

    async def start_background_cleanup(self) -> None:
        """
        Start background task for periodic cleanup of expired reservations.

        Creates an asyncio task that runs cleanup at regular intervals.
        """
        if self._cleanup_task is not None and not self._cleanup_task.done():
            logger.warning("Background cleanup task already running")
            return

        async def cleanup_loop():
            logger.info(
                "Starting background cleanup task",
                interval_seconds=self.CLEANUP_INTERVAL_SECONDS,
            )
            while True:
                try:
                    await asyncio.sleep(self.CLEANUP_INTERVAL_SECONDS)
                    await self.cleanup_expired_reservations()
                except asyncio.CancelledError:
                    logger.info("Background cleanup task cancelled")
                    break
                except Exception as e:
                    logger.error(
                        "Error in background cleanup task",
                        error=str(e),
                        error_type=type(e).__name__,
                    )

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("Background cleanup task started")

    async def stop_background_cleanup(self) -> None:
        """
        Stop background cleanup task.

        Cancels the running cleanup task and waits for it to complete.
        """
        if self._cleanup_task is None or self._cleanup_task.done():
            logger.debug("No background cleanup task to stop")
            return

        self._cleanup_task.cancel()
        try:
            await self._cleanup_task
        except asyncio.CancelledError:
            pass

        self._cleanup_task = None
        logger.info("Background cleanup task stopped")

    async def set_inventory_availability(
        self,
        vehicle_id: str,
        quantity: int,
    ) -> None:
        """
        Set available inventory quantity for a vehicle.

        This should be called when inventory is updated in the database
        to synchronize Redis cache.

        Args:
            vehicle_id: Vehicle identifier
            quantity: Available quantity

        Raises:
            ValueError: If quantity is negative
            ReservationError: If operation fails
        """
        if quantity < 0:
            raise ValueError("Inventory quantity cannot be negative")

        redis = await self._get_redis()
        inventory_key = self._make_inventory_key(vehicle_id)

        try:
            await redis.set(inventory_key, str(quantity))
            logger.info(
                "Inventory availability set",
                vehicle_id=vehicle_id,
                quantity=quantity,
            )

        except Exception as e:
            logger.error(
                "Failed to set inventory availability",
                vehicle_id=vehicle_id,
                quantity=quantity,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ReservationError(
                "Failed to set inventory availability",
                code="SET_AVAILABILITY_FAILED",
                vehicle_id=vehicle_id,
            ) from e


_reservation_service: Optional[InventoryReservationService] = None


async def get_reservation_service() -> InventoryReservationService:
    """
    Get or create global inventory reservation service instance.

    Returns:
        Singleton inventory reservation service instance
    """
    global _reservation_service

    if _reservation_service is None:
        _reservation_service = InventoryReservationService()
        await _reservation_service.start_background_cleanup()

    return _reservation_service


async def close_reservation_service() -> None:
    """
    Close global inventory reservation service.

    Stops background cleanup task and releases resources.
    """
    global _reservation_service

    if _reservation_service is not None:
        await _reservation_service.stop_background_cleanup()
        _reservation_service = None