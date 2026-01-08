"""
Cache warming service for vehicle catalog performance optimization.

This module implements background cache warming strategies for frequently accessed
vehicles, popular searches, and inventory data. Provides scheduling capabilities,
monitoring, and intelligent warming based on access patterns and business rules.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from src.cache.redis_client import get_redis_client
from src.core.logging import get_logger
from src.database.connection import get_session
from src.schemas.vehicles import VehicleResponse
from src.services.cache.vehicle_cache import VehicleCache, get_vehicle_cache
from src.services.vehicles.repository import VehicleRepository

logger = get_logger(__name__)


class CacheWarmingService:
    """
    Background cache warming service for vehicle catalog.

    Implements intelligent cache warming strategies based on access patterns,
    popularity metrics, and business rules. Provides scheduling, monitoring,
    and performance tracking capabilities.
    """

    # Warming configuration
    DEFAULT_TOP_VEHICLES_COUNT = 100
    DEFAULT_WARMING_INTERVAL = 3600  # 1 hour
    DEFAULT_BATCH_SIZE = 10
    DEFAULT_BATCH_DELAY = 0.1  # seconds between batches

    # Access pattern thresholds
    POPULAR_VEHICLE_THRESHOLD = 100  # views in last 24h
    TRENDING_VEHICLE_THRESHOLD = 50  # views in last hour

    def __init__(
        self,
        vehicle_cache: Optional[VehicleCache] = None,
        warming_interval: int = DEFAULT_WARMING_INTERVAL,
        top_vehicles_count: int = DEFAULT_TOP_VEHICLES_COUNT,
        batch_size: int = DEFAULT_BATCH_SIZE,
        batch_delay: float = DEFAULT_BATCH_DELAY,
    ):
        """
        Initialize cache warming service.

        Args:
            vehicle_cache: Vehicle cache instance (uses global if None)
            warming_interval: Interval between warming cycles in seconds
            top_vehicles_count: Number of top vehicles to warm
            batch_size: Number of vehicles to warm per batch
            batch_delay: Delay between batches in seconds
        """
        self._vehicle_cache = vehicle_cache
        self._warming_interval = warming_interval
        self._top_vehicles_count = top_vehicles_count
        self._batch_size = batch_size
        self._batch_delay = batch_delay
        self._is_running = False
        self._warming_task: Optional[asyncio.Task] = None
        self._stats = {
            "warming_cycles": 0,
            "vehicles_warmed": 0,
            "failed_warmings": 0,
            "last_warming_time": None,
            "average_warming_duration": 0.0,
        }

        logger.info(
            "Cache warming service initialized",
            warming_interval=warming_interval,
            top_vehicles_count=top_vehicles_count,
            batch_size=batch_size,
        )

    async def _get_vehicle_cache(self) -> VehicleCache:
        """
        Get vehicle cache instance.

        Returns:
            Vehicle cache instance

        Raises:
            ConnectionError: If cache connection fails
        """
        if self._vehicle_cache is None:
            self._vehicle_cache = await get_vehicle_cache()
        return self._vehicle_cache

    async def _get_popular_vehicle_ids(
        self, limit: int
    ) -> list[tuple[UUID, int]]:
        """
        Get most popular vehicle IDs based on access patterns.

        Args:
            limit: Maximum number of vehicle IDs to return

        Returns:
            List of (vehicle_id, access_count) tuples

        Raises:
            ConnectionError: If Redis connection fails
        """
        redis = await get_redis_client()

        try:
            access_key = "vehicle:access_counts"
            popular_vehicles = await redis.client.zrevrange(
                access_key, 0, limit - 1, withscores=True
            )

            vehicle_ids = [
                (UUID(vid.decode()), int(score))
                for vid, score in popular_vehicles
            ]

            logger.debug(
                "Retrieved popular vehicle IDs",
                count=len(vehicle_ids),
                limit=limit,
            )

            return vehicle_ids

        except Exception as e:
            logger.error(
                "Failed to retrieve popular vehicle IDs",
                error=str(e),
                error_type=type(e).__name__,
            )
            return []

    async def _get_trending_vehicle_ids(
        self, limit: int
    ) -> list[tuple[UUID, int]]:
        """
        Get trending vehicle IDs based on recent access patterns.

        Args:
            limit: Maximum number of vehicle IDs to return

        Returns:
            List of (vehicle_id, access_count) tuples

        Raises:
            ConnectionError: If Redis connection fails
        """
        redis = await get_redis_client()

        try:
            trending_key = "vehicle:trending_counts"
            trending_vehicles = await redis.client.zrevrange(
                trending_key, 0, limit - 1, withscores=True
            )

            vehicle_ids = [
                (UUID(vid.decode()), int(score))
                for vid, score in trending_vehicles
            ]

            logger.debug(
                "Retrieved trending vehicle IDs",
                count=len(vehicle_ids),
                limit=limit,
            )

            return vehicle_ids

        except Exception as e:
            logger.error(
                "Failed to retrieve trending vehicle IDs",
                error=str(e),
                error_type=type(e).__name__,
            )
            return []

    async def _get_recently_updated_vehicle_ids(
        self, limit: int
    ) -> list[UUID]:
        """
        Get recently updated vehicle IDs.

        Args:
            limit: Maximum number of vehicle IDs to return

        Returns:
            List of vehicle UUIDs

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            async with get_session() as session:
                repository = VehicleRepository(session)

                vehicles, _ = await repository.search(
                    skip=0,
                    limit=limit,
                    sort_by="updated_at",
                    sort_order="desc",
                )

                vehicle_ids = [vehicle.id for vehicle in vehicles]

                logger.debug(
                    "Retrieved recently updated vehicle IDs",
                    count=len(vehicle_ids),
                    limit=limit,
                )

                return vehicle_ids

        except Exception as e:
            logger.error(
                "Failed to retrieve recently updated vehicle IDs",
                error=str(e),
                error_type=type(e).__name__,
            )
            return []

    async def _load_vehicle_data(
        self, vehicle_ids: list[UUID]
    ) -> dict[UUID, VehicleResponse]:
        """
        Load vehicle data from database.

        Args:
            vehicle_ids: List of vehicle UUIDs to load

        Returns:
            Dictionary mapping vehicle IDs to vehicle responses

        Raises:
            SQLAlchemyError: If database operation fails
        """
        vehicle_data = {}

        try:
            async with get_session() as session:
                repository = VehicleRepository(session)

                for vehicle_id in vehicle_ids:
                    try:
                        vehicle = await repository.get_by_id(
                            vehicle_id, include_inventory=True
                        )

                        if vehicle:
                            vehicle_response = VehicleResponse(
                                id=vehicle.id,
                                make=vehicle.make,
                                model=vehicle.model,
                                year=vehicle.year,
                                trim=vehicle.trim,
                                body_style=vehicle.body_style,
                                fuel_type=vehicle.fuel_type,
                                base_price=vehicle.base_price,
                                msrp=vehicle.msrp,
                                vin=vehicle.vin,
                                specifications=vehicle.specifications or {},
                                features=vehicle.features or {},
                                custom_attributes=vehicle.custom_attributes or {},
                                created_at=vehicle.created_at,
                                updated_at=vehicle.updated_at,
                            )
                            vehicle_data[vehicle_id] = vehicle_response

                    except Exception as e:
                        logger.warning(
                            "Failed to load vehicle data",
                            vehicle_id=str(vehicle_id),
                            error=str(e),
                        )
                        continue

            logger.debug(
                "Loaded vehicle data",
                requested=len(vehicle_ids),
                loaded=len(vehicle_data),
            )

            return vehicle_data

        except Exception as e:
            logger.error(
                "Failed to load vehicle data batch",
                error=str(e),
                error_type=type(e).__name__,
            )
            return vehicle_data

    async def _warm_vehicle_batch(
        self, vehicle_ids: list[UUID], vehicle_data: dict[UUID, VehicleResponse]
    ) -> int:
        """
        Warm cache for a batch of vehicles.

        Args:
            vehicle_ids: List of vehicle UUIDs to warm
            vehicle_data: Dictionary of vehicle data

        Returns:
            Number of vehicles successfully warmed

        Raises:
            ConnectionError: If cache connection fails
        """
        cache = await self._get_vehicle_cache()
        success_count = 0

        try:
            valid_ids = [vid for vid in vehicle_ids if vid in vehicle_data]
            valid_data = [vehicle_data[vid] for vid in valid_ids]

            if valid_ids:
                warmed = await cache.warm_cache_for_vehicles(
                    valid_ids, valid_data
                )
                success_count = warmed

                logger.debug(
                    "Warmed vehicle batch",
                    batch_size=len(valid_ids),
                    success_count=success_count,
                )

        except Exception as e:
            logger.error(
                "Failed to warm vehicle batch",
                batch_size=len(vehicle_ids),
                error=str(e),
                error_type=type(e).__name__,
            )

        return success_count

    async def warm_popular_vehicles(
        self, limit: Optional[int] = None
    ) -> int:
        """
        Warm cache for most popular vehicles.

        Args:
            limit: Maximum number of vehicles to warm (uses default if None)

        Returns:
            Number of vehicles successfully warmed

        Raises:
            ConnectionError: If cache or database connection fails
        """
        limit = limit or self._top_vehicles_count

        try:
            popular_ids = await self._get_popular_vehicle_ids(limit)
            vehicle_ids = [vid for vid, _ in popular_ids]

            if not vehicle_ids:
                logger.info("No popular vehicles to warm")
                return 0

            vehicle_data = await self._load_vehicle_data(vehicle_ids)

            total_warmed = 0
            for i in range(0, len(vehicle_ids), self._batch_size):
                batch = vehicle_ids[i : i + self._batch_size]
                warmed = await self._warm_vehicle_batch(batch, vehicle_data)
                total_warmed += warmed

                if i + self._batch_size < len(vehicle_ids):
                    await asyncio.sleep(self._batch_delay)

            logger.info(
                "Popular vehicles cache warming completed",
                total_warmed=total_warmed,
                requested=len(vehicle_ids),
            )

            return total_warmed

        except Exception as e:
            logger.error(
                "Failed to warm popular vehicles",
                error=str(e),
                error_type=type(e).__name__,
            )
            return 0

    async def warm_trending_vehicles(
        self, limit: Optional[int] = None
    ) -> int:
        """
        Warm cache for trending vehicles.

        Args:
            limit: Maximum number of vehicles to warm (uses default if None)

        Returns:
            Number of vehicles successfully warmed

        Raises:
            ConnectionError: If cache or database connection fails
        """
        limit = limit or (self._top_vehicles_count // 2)

        try:
            trending_ids = await self._get_trending_vehicle_ids(limit)
            vehicle_ids = [vid for vid, _ in trending_ids]

            if not vehicle_ids:
                logger.info("No trending vehicles to warm")
                return 0

            vehicle_data = await self._load_vehicle_data(vehicle_ids)

            total_warmed = 0
            for i in range(0, len(vehicle_ids), self._batch_size):
                batch = vehicle_ids[i : i + self._batch_size]
                warmed = await self._warm_vehicle_batch(batch, vehicle_data)
                total_warmed += warmed

                if i + self._batch_size < len(vehicle_ids):
                    await asyncio.sleep(self._batch_delay)

            logger.info(
                "Trending vehicles cache warming completed",
                total_warmed=total_warmed,
                requested=len(vehicle_ids),
            )

            return total_warmed

        except Exception as e:
            logger.error(
                "Failed to warm trending vehicles",
                error=str(e),
                error_type=type(e).__name__,
            )
            return 0

    async def warm_recently_updated_vehicles(
        self, limit: Optional[int] = None
    ) -> int:
        """
        Warm cache for recently updated vehicles.

        Args:
            limit: Maximum number of vehicles to warm (uses default if None)

        Returns:
            Number of vehicles successfully warmed

        Raises:
            ConnectionError: If cache or database connection fails
        """
        limit = limit or (self._top_vehicles_count // 4)

        try:
            vehicle_ids = await self._get_recently_updated_vehicle_ids(limit)

            if not vehicle_ids:
                logger.info("No recently updated vehicles to warm")
                return 0

            vehicle_data = await self._load_vehicle_data(vehicle_ids)

            total_warmed = 0
            for i in range(0, len(vehicle_ids), self._batch_size):
                batch = vehicle_ids[i : i + self._batch_size]
                warmed = await self._warm_vehicle_batch(batch, vehicle_data)
                total_warmed += warmed

                if i + self._batch_size < len(vehicle_ids):
                    await asyncio.sleep(self._batch_delay)

            logger.info(
                "Recently updated vehicles cache warming completed",
                total_warmed=total_warmed,
                requested=len(vehicle_ids),
            )

            return total_warmed

        except Exception as e:
            logger.error(
                "Failed to warm recently updated vehicles",
                error=str(e),
                error_type=type(e).__name__,
            )
            return 0

    async def _warming_cycle(self) -> None:
        """
        Execute a complete cache warming cycle.

        Warms cache for popular, trending, and recently updated vehicles.
        Updates statistics and handles errors gracefully.
        """
        start_time = datetime.utcnow()

        try:
            logger.info("Starting cache warming cycle")

            popular_warmed = await self.warm_popular_vehicles()
            trending_warmed = await self.warm_trending_vehicles()
            updated_warmed = await self.warm_recently_updated_vehicles()

            total_warmed = popular_warmed + trending_warmed + updated_warmed

            duration = (datetime.utcnow() - start_time).total_seconds()

            self._stats["warming_cycles"] += 1
            self._stats["vehicles_warmed"] += total_warmed
            self._stats["last_warming_time"] = start_time

            avg_duration = self._stats["average_warming_duration"]
            cycles = self._stats["warming_cycles"]
            self._stats["average_warming_duration"] = (
                avg_duration * (cycles - 1) + duration
            ) / cycles

            logger.info(
                "Cache warming cycle completed",
                total_warmed=total_warmed,
                popular=popular_warmed,
                trending=trending_warmed,
                updated=updated_warmed,
                duration_seconds=round(duration, 2),
            )

        except Exception as e:
            self._stats["failed_warmings"] += 1
            logger.error(
                "Cache warming cycle failed",
                error=str(e),
                error_type=type(e).__name__,
            )

    async def _warming_loop(self) -> None:
        """
        Background loop for periodic cache warming.

        Executes warming cycles at configured intervals until stopped.
        """
        logger.info(
            "Cache warming loop started",
            interval_seconds=self._warming_interval,
        )

        while self._is_running:
            try:
                await self._warming_cycle()
                await asyncio.sleep(self._warming_interval)

            except asyncio.CancelledError:
                logger.info("Cache warming loop cancelled")
                break
            except Exception as e:
                logger.error(
                    "Unexpected error in warming loop",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                await asyncio.sleep(60)

    async def start(self) -> None:
        """
        Start background cache warming service.

        Raises:
            RuntimeError: If service is already running
        """
        if self._is_running:
            raise RuntimeError("Cache warming service is already running")

        self._is_running = True
        self._warming_task = asyncio.create_task(self._warming_loop())

        logger.info("Cache warming service started")

    async def stop(self) -> None:
        """
        Stop background cache warming service.

        Waits for current warming cycle to complete before stopping.
        """
        if not self._is_running:
            logger.warning("Cache warming service is not running")
            return

        self._is_running = False

        if self._warming_task:
            self._warming_task.cancel()
            try:
                await self._warming_task
            except asyncio.CancelledError:
                pass

        logger.info("Cache warming service stopped")

    def get_statistics(self) -> dict[str, Any]:
        """
        Get cache warming statistics.

        Returns:
            Dictionary containing warming statistics
        """
        return {
            "warming_cycles": self._stats["warming_cycles"],
            "vehicles_warmed": self._stats["vehicles_warmed"],
            "failed_warmings": self._stats["failed_warmings"],
            "last_warming_time": (
                self._stats["last_warming_time"].isoformat()
                if self._stats["last_warming_time"]
                else None
            ),
            "average_warming_duration_seconds": round(
                self._stats["average_warming_duration"], 2
            ),
            "is_running": self._is_running,
            "configuration": {
                "warming_interval_seconds": self._warming_interval,
                "top_vehicles_count": self._top_vehicles_count,
                "batch_size": self._batch_size,
                "batch_delay_seconds": self._batch_delay,
            },
        }

    def reset_statistics(self) -> None:
        """Reset warming statistics."""
        self._stats = {
            "warming_cycles": 0,
            "vehicles_warmed": 0,
            "failed_warmings": 0,
            "last_warming_time": None,
            "average_warming_duration": 0.0,
        }
        logger.info("Cache warming statistics reset")


_cache_warming_service: Optional[CacheWarmingService] = None


async def get_cache_warming_service() -> CacheWarmingService:
    """
    Get or create global cache warming service instance.

    Returns:
        Singleton cache warming service instance
    """
    global _cache_warming_service

    if _cache_warming_service is None:
        _cache_warming_service = CacheWarmingService()

    return _cache_warming_service