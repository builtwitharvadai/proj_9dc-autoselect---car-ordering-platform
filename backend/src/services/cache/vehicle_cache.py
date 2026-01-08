"""
Vehicle-specific caching service with cache-aside pattern implementation.

This module provides a comprehensive caching layer for vehicle catalog operations
with TTL management, cache warming, and intelligent invalidation strategies.
Implements cache-aside pattern for optimal performance and data consistency.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from src.cache.redis_client import (
    CacheKeyManager,
    RedisClient,
    get_cache_key_manager,
    get_redis_client,
)
from src.core.logging import get_logger
from src.schemas.vehicles import VehicleListResponse, VehicleResponse

logger = get_logger(__name__)


class VehicleCache:
    """
    Vehicle-specific caching service with cache-aside pattern.

    Provides high-level caching operations for vehicle catalog with automatic
    TTL management, cache warming for popular vehicles, and intelligent
    invalidation on data updates.
    """

    # Cache TTL configurations (in seconds)
    VEHICLE_LIST_TTL = 3600  # 1 hour for vehicle lists
    VEHICLE_DETAIL_TTL = 86400  # 24 hours for individual vehicles
    SEARCH_RESULTS_TTL = 1800  # 30 minutes for search results
    INVENTORY_TTL = 300  # 5 minutes for inventory data
    PRICE_RANGE_TTL = 3600  # 1 hour for price range queries

    # Cache key prefixes
    LIST_PREFIX = "vehicles:list"
    DETAIL_PREFIX = "vehicles:detail"
    SEARCH_PREFIX = "vehicles:search"
    INVENTORY_PREFIX = "vehicles:inventory"
    PRICE_RANGE_PREFIX = "vehicles:price_range"

    def __init__(
        self,
        redis_client: Optional[RedisClient] = None,
        key_manager: Optional[CacheKeyManager] = None,
    ):
        """
        Initialize vehicle cache service.

        Args:
            redis_client: Redis client instance (uses global if None)
            key_manager: Cache key manager (uses global if None)
        """
        self._redis_client = redis_client
        self._key_manager = key_manager or get_cache_key_manager()
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0,
            "warming_operations": 0,
        }

        logger.info(
            "Vehicle cache service initialized",
            list_ttl=self.VEHICLE_LIST_TTL,
            detail_ttl=self.VEHICLE_DETAIL_TTL,
        )

    async def _get_redis_client(self) -> RedisClient:
        """
        Get Redis client instance.

        Returns:
            Redis client instance

        Raises:
            ConnectionError: If Redis connection fails
        """
        if self._redis_client is None:
            self._redis_client = await get_redis_client()
        return self._redis_client

    def _make_list_key(self, filters: Optional[dict[str, Any]] = None) -> str:
        """
        Generate cache key for vehicle list queries.

        Args:
            filters: Optional filter parameters

        Returns:
            Cache key for vehicle list
        """
        if not filters:
            return self._key_manager.make_key(self.LIST_PREFIX, "all")

        filter_parts = []
        for key in sorted(filters.keys()):
            value = filters[key]
            if value is not None:
                filter_parts.append(f"{key}:{value}")

        filter_str = ":".join(filter_parts) if filter_parts else "all"
        return self._key_manager.make_key(self.LIST_PREFIX, filter_str)

    def _make_detail_key(self, vehicle_id: UUID) -> str:
        """
        Generate cache key for vehicle detail.

        Args:
            vehicle_id: Vehicle UUID

        Returns:
            Cache key for vehicle detail
        """
        return self._key_manager.make_key(self.DETAIL_PREFIX, str(vehicle_id))

    def _make_search_key(self, query: str, filters: Optional[dict[str, Any]] = None) -> str:
        """
        Generate cache key for search results.

        Args:
            query: Search query string
            filters: Optional filter parameters

        Returns:
            Cache key for search results
        """
        key_parts = [self.SEARCH_PREFIX, query]

        if filters:
            filter_str = ":".join(
                f"{k}:{v}" for k, v in sorted(filters.items()) if v is not None
            )
            if filter_str:
                key_parts.append(filter_str)

        return self._key_manager.make_key(*key_parts)

    def _make_inventory_key(self, vehicle_id: UUID) -> str:
        """
        Generate cache key for vehicle inventory.

        Args:
            vehicle_id: Vehicle UUID

        Returns:
            Cache key for inventory data
        """
        return self._key_manager.make_key(self.INVENTORY_PREFIX, str(vehicle_id))

    def _make_price_range_key(self, filters: Optional[dict[str, Any]] = None) -> str:
        """
        Generate cache key for price range queries.

        Args:
            filters: Optional filter parameters

        Returns:
            Cache key for price range
        """
        if not filters:
            return self._key_manager.make_key(self.PRICE_RANGE_PREFIX, "all")

        filter_str = ":".join(
            f"{k}:{v}" for k, v in sorted(filters.items()) if v is not None
        )
        return self._key_manager.make_key(
            self.PRICE_RANGE_PREFIX, filter_str or "all"
        )

    async def get_vehicle_list(
        self, filters: Optional[dict[str, Any]] = None
    ) -> Optional[VehicleListResponse]:
        """
        Get cached vehicle list.

        Args:
            filters: Optional filter parameters

        Returns:
            Cached vehicle list response or None if not cached

        Raises:
            ConnectionError: If Redis connection fails
        """
        redis = await self._get_redis_client()
        cache_key = self._make_list_key(filters)

        try:
            cached_data = await redis.get_json(cache_key)

            if cached_data is not None:
                self._cache_stats["hits"] += 1
                logger.debug(
                    "Vehicle list cache hit",
                    cache_key=cache_key,
                    filters=filters,
                )
                return VehicleListResponse(**cached_data)

            self._cache_stats["misses"] += 1
            logger.debug(
                "Vehicle list cache miss",
                cache_key=cache_key,
                filters=filters,
            )
            return None

        except Exception as e:
            logger.error(
                "Failed to get vehicle list from cache",
                cache_key=cache_key,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def set_vehicle_list(
        self,
        data: VehicleListResponse,
        filters: Optional[dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache vehicle list with TTL.

        Args:
            data: Vehicle list response to cache
            filters: Optional filter parameters
            ttl: Time-to-live in seconds (uses default if None)

        Returns:
            True if cached successfully, False otherwise

        Raises:
            ConnectionError: If Redis connection fails
        """
        redis = await self._get_redis_client()
        cache_key = self._make_list_key(filters)
        ttl = ttl or self.VEHICLE_LIST_TTL

        try:
            cache_data = data.model_dump(mode="json")
            success = await redis.set_json(cache_key, cache_data, ex=ttl)

            if success:
                logger.debug(
                    "Vehicle list cached",
                    cache_key=cache_key,
                    ttl=ttl,
                    count=len(data.items),
                )
            else:
                logger.warning(
                    "Failed to cache vehicle list",
                    cache_key=cache_key,
                )

            return success

        except Exception as e:
            logger.error(
                "Failed to set vehicle list in cache",
                cache_key=cache_key,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    async def get_vehicle_detail(self, vehicle_id: UUID) -> Optional[VehicleResponse]:
        """
        Get cached vehicle detail.

        Args:
            vehicle_id: Vehicle UUID

        Returns:
            Cached vehicle response or None if not cached

        Raises:
            ConnectionError: If Redis connection fails
        """
        redis = await self._get_redis_client()
        cache_key = self._make_detail_key(vehicle_id)

        try:
            cached_data = await redis.get_json(cache_key)

            if cached_data is not None:
                self._cache_stats["hits"] += 1
                logger.debug(
                    "Vehicle detail cache hit",
                    cache_key=cache_key,
                    vehicle_id=str(vehicle_id),
                )
                return VehicleResponse(**cached_data)

            self._cache_stats["misses"] += 1
            logger.debug(
                "Vehicle detail cache miss",
                cache_key=cache_key,
                vehicle_id=str(vehicle_id),
            )
            return None

        except Exception as e:
            logger.error(
                "Failed to get vehicle detail from cache",
                cache_key=cache_key,
                vehicle_id=str(vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def set_vehicle_detail(
        self,
        vehicle_id: UUID,
        data: VehicleResponse,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache vehicle detail with TTL.

        Args:
            vehicle_id: Vehicle UUID
            data: Vehicle response to cache
            ttl: Time-to-live in seconds (uses default if None)

        Returns:
            True if cached successfully, False otherwise

        Raises:
            ConnectionError: If Redis connection fails
        """
        redis = await self._get_redis_client()
        cache_key = self._make_detail_key(vehicle_id)
        ttl = ttl or self.VEHICLE_DETAIL_TTL

        try:
            cache_data = data.model_dump(mode="json")
            success = await redis.set_json(cache_key, cache_data, ex=ttl)

            if success:
                logger.debug(
                    "Vehicle detail cached",
                    cache_key=cache_key,
                    vehicle_id=str(vehicle_id),
                    ttl=ttl,
                )
            else:
                logger.warning(
                    "Failed to cache vehicle detail",
                    cache_key=cache_key,
                    vehicle_id=str(vehicle_id),
                )

            return success

        except Exception as e:
            logger.error(
                "Failed to set vehicle detail in cache",
                cache_key=cache_key,
                vehicle_id=str(vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    async def get_search_results(
        self, query: str, filters: Optional[dict[str, Any]] = None
    ) -> Optional[dict[str, Any]]:
        """
        Get cached search results.

        Args:
            query: Search query string
            filters: Optional filter parameters

        Returns:
            Cached search results or None if not cached

        Raises:
            ConnectionError: If Redis connection fails
        """
        redis = await self._get_redis_client()
        cache_key = self._make_search_key(query, filters)

        try:
            cached_data = await redis.get_json(cache_key)

            if cached_data is not None:
                self._cache_stats["hits"] += 1
                logger.debug(
                    "Search results cache hit",
                    cache_key=cache_key,
                    query=query,
                )
                return cached_data

            self._cache_stats["misses"] += 1
            logger.debug(
                "Search results cache miss",
                cache_key=cache_key,
                query=query,
            )
            return None

        except Exception as e:
            logger.error(
                "Failed to get search results from cache",
                cache_key=cache_key,
                query=query,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def set_search_results(
        self,
        query: str,
        data: dict[str, Any],
        filters: Optional[dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache search results with TTL.

        Args:
            query: Search query string
            data: Search results to cache
            filters: Optional filter parameters
            ttl: Time-to-live in seconds (uses default if None)

        Returns:
            True if cached successfully, False otherwise

        Raises:
            ConnectionError: If Redis connection fails
        """
        redis = await self._get_redis_client()
        cache_key = self._make_search_key(query, filters)
        ttl = ttl or self.SEARCH_RESULTS_TTL

        try:
            success = await redis.set_json(cache_key, data, ex=ttl)

            if success:
                logger.debug(
                    "Search results cached",
                    cache_key=cache_key,
                    query=query,
                    ttl=ttl,
                )
            else:
                logger.warning(
                    "Failed to cache search results",
                    cache_key=cache_key,
                    query=query,
                )

            return success

        except Exception as e:
            logger.error(
                "Failed to set search results in cache",
                cache_key=cache_key,
                query=query,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    async def get_inventory_data(self, vehicle_id: UUID) -> Optional[dict[str, Any]]:
        """
        Get cached inventory data.

        Args:
            vehicle_id: Vehicle UUID

        Returns:
            Cached inventory data or None if not cached

        Raises:
            ConnectionError: If Redis connection fails
        """
        redis = await self._get_redis_client()
        cache_key = self._make_inventory_key(vehicle_id)

        try:
            cached_data = await redis.get_json(cache_key)

            if cached_data is not None:
                self._cache_stats["hits"] += 1
                logger.debug(
                    "Inventory data cache hit",
                    cache_key=cache_key,
                    vehicle_id=str(vehicle_id),
                )
                return cached_data

            self._cache_stats["misses"] += 1
            logger.debug(
                "Inventory data cache miss",
                cache_key=cache_key,
                vehicle_id=str(vehicle_id),
            )
            return None

        except Exception as e:
            logger.error(
                "Failed to get inventory data from cache",
                cache_key=cache_key,
                vehicle_id=str(vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def set_inventory_data(
        self,
        vehicle_id: UUID,
        data: dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache inventory data with TTL.

        Args:
            vehicle_id: Vehicle UUID
            data: Inventory data to cache
            ttl: Time-to-live in seconds (uses default if None)

        Returns:
            True if cached successfully, False otherwise

        Raises:
            ConnectionError: If Redis connection fails
        """
        redis = await self._get_redis_client()
        cache_key = self._make_inventory_key(vehicle_id)
        ttl = ttl or self.INVENTORY_TTL

        try:
            success = await redis.set_json(cache_key, data, ex=ttl)

            if success:
                logger.debug(
                    "Inventory data cached",
                    cache_key=cache_key,
                    vehicle_id=str(vehicle_id),
                    ttl=ttl,
                )
            else:
                logger.warning(
                    "Failed to cache inventory data",
                    cache_key=cache_key,
                    vehicle_id=str(vehicle_id),
                )

            return success

        except Exception as e:
            logger.error(
                "Failed to set inventory data in cache",
                cache_key=cache_key,
                vehicle_id=str(vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    async def get_price_range(
        self, filters: Optional[dict[str, Any]] = None
    ) -> Optional[dict[str, Any]]:
        """
        Get cached price range data.

        Args:
            filters: Optional filter parameters

        Returns:
            Cached price range or None if not cached

        Raises:
            ConnectionError: If Redis connection fails
        """
        redis = await self._get_redis_client()
        cache_key = self._make_price_range_key(filters)

        try:
            cached_data = await redis.get_json(cache_key)

            if cached_data is not None:
                self._cache_stats["hits"] += 1
                logger.debug(
                    "Price range cache hit",
                    cache_key=cache_key,
                    filters=filters,
                )
                return cached_data

            self._cache_stats["misses"] += 1
            logger.debug(
                "Price range cache miss",
                cache_key=cache_key,
                filters=filters,
            )
            return None

        except Exception as e:
            logger.error(
                "Failed to get price range from cache",
                cache_key=cache_key,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def set_price_range(
        self,
        data: dict[str, Any],
        filters: Optional[dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache price range data with TTL.

        Args:
            data: Price range data to cache
            filters: Optional filter parameters
            ttl: Time-to-live in seconds (uses default if None)

        Returns:
            True if cached successfully, False otherwise

        Raises:
            ConnectionError: If Redis connection fails
        """
        redis = await self._get_redis_client()
        cache_key = self._make_price_range_key(filters)
        ttl = ttl or self.PRICE_RANGE_TTL

        try:
            success = await redis.set_json(cache_key, data, ex=ttl)

            if success:
                logger.debug(
                    "Price range cached",
                    cache_key=cache_key,
                    ttl=ttl,
                )
            else:
                logger.warning(
                    "Failed to cache price range",
                    cache_key=cache_key,
                )

            return success

        except Exception as e:
            logger.error(
                "Failed to set price range in cache",
                cache_key=cache_key,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    async def invalidate_vehicle(self, vehicle_id: UUID) -> int:
        """
        Invalidate all cache entries for a specific vehicle.

        Args:
            vehicle_id: Vehicle UUID

        Returns:
            Number of cache entries invalidated

        Raises:
            ConnectionError: If Redis connection fails
        """
        redis = await self._get_redis_client()

        try:
            detail_key = self._make_detail_key(vehicle_id)
            inventory_key = self._make_inventory_key(vehicle_id)

            count = await redis.delete(detail_key, inventory_key)
            self._cache_stats["invalidations"] += count

            logger.info(
                "Vehicle cache invalidated",
                vehicle_id=str(vehicle_id),
                keys_deleted=count,
            )

            return count

        except Exception as e:
            logger.error(
                "Failed to invalidate vehicle cache",
                vehicle_id=str(vehicle_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            return 0

    async def invalidate_vehicle_lists(self) -> int:
        """
        Invalidate all vehicle list caches.

        Returns:
            Number of cache entries invalidated

        Raises:
            ConnectionError: If Redis connection fails
        """
        redis = await self._get_redis_client()

        try:
            pattern = self._key_manager.make_key(self.LIST_PREFIX, "*")
            count = await redis.delete_pattern(pattern)
            self._cache_stats["invalidations"] += count

            logger.info(
                "Vehicle list caches invalidated",
                pattern=pattern,
                keys_deleted=count,
            )

            return count

        except Exception as e:
            logger.error(
                "Failed to invalidate vehicle list caches",
                error=str(e),
                error_type=type(e).__name__,
            )
            return 0

    async def invalidate_search_results(self) -> int:
        """
        Invalidate all search result caches.

        Returns:
            Number of cache entries invalidated

        Raises:
            ConnectionError: If Redis connection fails
        """
        redis = await self._get_redis_client()

        try:
            pattern = self._key_manager.make_key(self.SEARCH_PREFIX, "*")
            count = await redis.delete_pattern(pattern)
            self._cache_stats["invalidations"] += count

            logger.info(
                "Search result caches invalidated",
                pattern=pattern,
                keys_deleted=count,
            )

            return count

        except Exception as e:
            logger.error(
                "Failed to invalidate search result caches",
                error=str(e),
                error_type=type(e).__name__,
            )
            return 0

    async def invalidate_all_vehicle_caches(self) -> int:
        """
        Invalidate all vehicle-related caches.

        Returns:
            Total number of cache entries invalidated

        Raises:
            ConnectionError: If Redis connection fails
        """
        redis = await self._get_redis_client()

        try:
            patterns = [
                self._key_manager.make_key(self.LIST_PREFIX, "*"),
                self._key_manager.make_key(self.DETAIL_PREFIX, "*"),
                self._key_manager.make_key(self.SEARCH_PREFIX, "*"),
                self._key_manager.make_key(self.INVENTORY_PREFIX, "*"),
                self._key_manager.make_key(self.PRICE_RANGE_PREFIX, "*"),
            ]

            total_count = 0
            for pattern in patterns:
                count = await redis.delete_pattern(pattern)
                total_count += count

            self._cache_stats["invalidations"] += total_count

            logger.info(
                "All vehicle caches invalidated",
                keys_deleted=total_count,
            )

            return total_count

        except Exception as e:
            logger.error(
                "Failed to invalidate all vehicle caches",
                error=str(e),
                error_type=type(e).__name__,
            )
            return 0

    async def warm_cache_for_vehicles(
        self, vehicle_ids: list[UUID], vehicle_data: list[VehicleResponse]
    ) -> int:
        """
        Warm cache with vehicle data for popular vehicles.

        Args:
            vehicle_ids: List of vehicle UUIDs to warm
            vehicle_data: Corresponding vehicle response data

        Returns:
            Number of vehicles successfully cached

        Raises:
            ConnectionError: If Redis connection fails
            ValueError: If vehicle_ids and vehicle_data lengths don't match
        """
        if len(vehicle_ids) != len(vehicle_data):
            raise ValueError(
                "vehicle_ids and vehicle_data must have the same length"
            )

        redis = await self._get_redis_client()
        success_count = 0

        try:
            async with redis.pipeline() as pipe:
                for vehicle_id, data in zip(vehicle_ids, vehicle_data):
                    cache_key = self._make_detail_key(vehicle_id)
                    cache_data = data.model_dump(mode="json")
                    pipe.set(
                        cache_key,
                        json.dumps(cache_data),
                        ex=self.VEHICLE_DETAIL_TTL,
                    )

            success_count = len(vehicle_ids)
            self._cache_stats["warming_operations"] += success_count

            logger.info(
                "Cache warmed for vehicles",
                count=success_count,
                vehicle_ids=[str(vid) for vid in vehicle_ids],
            )

            return success_count

        except Exception as e:
            logger.error(
                "Failed to warm cache for vehicles",
                error=str(e),
                error_type=type(e).__name__,
            )
            return success_count

    async def get_cache_statistics(self) -> dict[str, Any]:
        """
        Get cache performance statistics.

        Returns:
            Dictionary containing cache statistics including hit rate

        Raises:
            ConnectionError: If Redis connection fails
        """
        redis = await self._get_redis_client()

        try:
            redis_stats = redis.get_cache_stats()

            total_operations = self._cache_stats["hits"] + self._cache_stats["misses"]
            hit_rate = (
                (self._cache_stats["hits"] / total_operations * 100)
                if total_operations > 0
                else 0.0
            )

            return {
                "cache_hits": self._cache_stats["hits"],
                "cache_misses": self._cache_stats["misses"],
                "hit_rate_percent": round(hit_rate, 2),
                "invalidations": self._cache_stats["invalidations"],
                "warming_operations": self._cache_stats["warming_operations"],
                "redis_stats": redis_stats,
            }

        except Exception as e:
            logger.error(
                "Failed to get cache statistics",
                error=str(e),
                error_type=type(e).__name__,
            )
            return {
                "cache_hits": self._cache_stats["hits"],
                "cache_misses": self._cache_stats["misses"],
                "hit_rate_percent": 0.0,
                "invalidations": self._cache_stats["invalidations"],
                "warming_operations": self._cache_stats["warming_operations"],
                "error": str(e),
            }

    def reset_statistics(self) -> None:
        """Reset cache performance statistics."""
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0,
            "warming_operations": 0,
        }
        logger.info("Cache statistics reset")


_vehicle_cache: Optional[VehicleCache] = None


async def get_vehicle_cache() -> VehicleCache:
    """
    Get or create global vehicle cache instance.

    Returns:
        Singleton vehicle cache instance

    Raises:
        ConnectionError: If Redis connection fails
    """
    global _vehicle_cache

    if _vehicle_cache is None:
        _vehicle_cache = VehicleCache()

    return _vehicle_cache