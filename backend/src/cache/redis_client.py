"""
Redis client configuration with connection pooling and async support.

This module provides a production-ready Redis client implementation with
connection pooling, retry logic, health checks, and cache key management
utilities. Supports async operations for high-performance caching.
"""

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional, Union

import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import (
    ConnectionError,
    RedisError,
    TimeoutError,
)

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class RedisClient:
    """
    Async Redis client with connection pooling and retry logic.

    Provides high-level interface for Redis operations with automatic
    connection management, retry logic, and comprehensive error handling.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        max_connections: Optional[int] = None,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        retry_on_timeout: bool = True,
        health_check_interval: int = 30,
    ):
        """
        Initialize Redis client with connection pool.

        Args:
            url: Redis connection URL (defaults to settings.redis_url)
            max_connections: Maximum pool connections (defaults to settings)
            socket_timeout: Socket operation timeout in seconds
            socket_connect_timeout: Socket connection timeout in seconds
            retry_on_timeout: Enable automatic retry on timeout
            health_check_interval: Health check interval in seconds
        """
        self._url = url or settings.redis_url
        self._max_connections = max_connections or settings.redis_max_connections
        self._socket_timeout = socket_timeout
        self._socket_connect_timeout = socket_connect_timeout
        self._retry_on_timeout = retry_on_timeout
        self._health_check_interval = health_check_interval

        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None
        self._is_connected = False

        # Performance monitoring
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_operations = 0

        logger.info(
            "Redis client initialized",
            url=self._sanitize_url(self._url),
            max_connections=self._max_connections,
            socket_timeout=socket_timeout,
        )

    @staticmethod
    def _sanitize_url(url: str) -> str:
        """
        Sanitize Redis URL for logging (remove password).

        Args:
            url: Redis connection URL

        Returns:
            Sanitized URL safe for logging
        """
        if "@" in url:
            protocol, rest = url.split("://", 1)
            if "@" in rest:
                _, host_part = rest.split("@", 1)
                return f"{protocol}://***@{host_part}"
        return url

    async def connect(self) -> None:
        """
        Establish Redis connection with retry logic.

        Creates connection pool and verifies connectivity with ping.

        Raises:
            ConnectionError: If connection cannot be established
        """
        if self._is_connected:
            logger.warning("Redis client already connected")
            return

        try:
            retry = Retry(
                ExponentialBackoff(base=0.1, cap=2.0),
                retries=3,
            )

            self._pool = ConnectionPool.from_url(
                self._url,
                max_connections=self._max_connections,
                socket_timeout=self._socket_timeout,
                socket_connect_timeout=self._socket_connect_timeout,
                retry_on_timeout=self._retry_on_timeout,
                health_check_interval=self._health_check_interval,
                retry=retry,
                decode_responses=True,
            )

            self._client = Redis(connection_pool=self._pool)

            await self._client.ping()
            self._is_connected = True

            logger.info(
                "Redis connection established",
                url=self._sanitize_url(self._url),
                pool_size=self._max_connections,
            )

        except (ConnectionError, TimeoutError) as e:
            logger.error(
                "Failed to connect to Redis",
                error=str(e),
                url=self._sanitize_url(self._url),
            )
            await self.disconnect()
            raise ConnectionError(f"Redis connection failed: {e}") from e

        except Exception as e:
            logger.error(
                "Unexpected error during Redis connection",
                error=str(e),
                error_type=type(e).__name__,
            )
            await self.disconnect()
            raise

    async def disconnect(self) -> None:
        """
        Close Redis connection and cleanup resources.

        Safely closes connection pool and releases all resources.
        """
        if not self._is_connected:
            return

        try:
            if self._client:
                await self._client.aclose()
                self._client = None

            if self._pool:
                await self._pool.aclose()
                self._pool = None

            self._is_connected = False

            logger.info("Redis connection closed")

        except Exception as e:
            logger.error(
                "Error during Redis disconnect",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def health_check(self) -> bool:
        """
        Perform Redis health check.

        Returns:
            True if Redis is healthy and responsive, False otherwise
        """
        if not self._is_connected or not self._client:
            logger.warning("Redis health check failed: not connected")
            return False

        try:
            await self._client.ping()
            logger.debug("Redis health check passed")
            return True

        except (ConnectionError, TimeoutError) as e:
            logger.error(
                "Redis health check failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

        except Exception as e:
            logger.error(
                "Unexpected error during Redis health check",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    def _ensure_connected(self) -> None:
        """
        Ensure Redis client is connected.

        Raises:
            ConnectionError: If client is not connected
        """
        if not self._is_connected or not self._client:
            raise ConnectionError("Redis client is not connected")

    async def get(self, key: str) -> Optional[str]:
        """
        Get value from Redis by key.

        Args:
            key: Cache key

        Returns:
            Cached value or None if key doesn't exist

        Raises:
            ConnectionError: If Redis is not connected
            RedisError: If Redis operation fails
        """
        self._ensure_connected()

        try:
            self._total_operations += 1
            value = await self._client.get(key)
            
            if value is not None:
                self._cache_hits += 1
            else:
                self._cache_misses += 1
            
            logger.debug("Redis GET operation", key=key, found=value is not None)
            return value

        except RedisError as e:
            logger.error("Redis GET operation failed", key=key, error=str(e))
            raise

    async def set(
        self,
        key: str,
        value: Union[str, bytes, int, float],
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        Set value in Redis with optional expiration.

        Args:
            key: Cache key
            value: Value to cache
            ex: Expiration time in seconds
            px: Expiration time in milliseconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists

        Returns:
            True if operation succeeded, False otherwise

        Raises:
            ConnectionError: If Redis is not connected
            RedisError: If Redis operation fails
        """
        self._ensure_connected()

        try:
            self._total_operations += 1
            result = await self._client.set(key, value, ex=ex, px=px, nx=nx, xx=xx)
            logger.debug(
                "Redis SET operation",
                key=key,
                ex=ex,
                px=px,
                nx=nx,
                xx=xx,
                success=bool(result),
            )
            return bool(result)

        except RedisError as e:
            logger.error("Redis SET operation failed", key=key, error=str(e))
            raise

    async def delete(self, *keys: str) -> int:
        """
        Delete one or more keys from Redis.

        Args:
            *keys: Keys to delete

        Returns:
            Number of keys deleted

        Raises:
            ConnectionError: If Redis is not connected
            RedisError: If Redis operation fails
        """
        self._ensure_connected()

        try:
            self._total_operations += 1
            count = await self._client.delete(*keys)
            logger.debug("Redis DELETE operation", keys=keys, count=count)
            return count

        except RedisError as e:
            logger.error("Redis DELETE operation failed", keys=keys, error=str(e))
            raise

    async def exists(self, *keys: str) -> int:
        """
        Check if keys exist in Redis.

        Args:
            *keys: Keys to check

        Returns:
            Number of existing keys

        Raises:
            ConnectionError: If Redis is not connected
            RedisError: If Redis operation fails
        """
        self._ensure_connected()

        try:
            self._total_operations += 1
            count = await self._client.exists(*keys)
            logger.debug("Redis EXISTS operation", keys=keys, count=count)
            return count

        except RedisError as e:
            logger.error("Redis EXISTS operation failed", keys=keys, error=str(e))
            raise

    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration time for a key.

        Args:
            key: Cache key
            seconds: Expiration time in seconds

        Returns:
            True if expiration was set, False if key doesn't exist

        Raises:
            ConnectionError: If Redis is not connected
            RedisError: If Redis operation fails
        """
        self._ensure_connected()

        try:
            result = await self._client.expire(key, seconds)
            logger.debug("Redis EXPIRE operation", key=key, seconds=seconds, success=result)
            return result

        except RedisError as e:
            logger.error("Redis EXPIRE operation failed", key=key, error=str(e))
            raise

    async def ttl(self, key: str) -> int:
        """
        Get time-to-live for a key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist

        Raises:
            ConnectionError: If Redis is not connected
            RedisError: If Redis operation fails
        """
        self._ensure_connected()

        try:
            ttl_value = await self._client.ttl(key)
            logger.debug("Redis TTL operation", key=key, ttl=ttl_value)
            return ttl_value

        except RedisError as e:
            logger.error("Redis TTL operation failed", key=key, error=str(e))
            raise

    async def incr(self, key: str, amount: int = 1) -> int:
        """
        Increment key value by amount.

        Args:
            key: Cache key
            amount: Increment amount

        Returns:
            New value after increment

        Raises:
            ConnectionError: If Redis is not connected
            RedisError: If Redis operation fails
        """
        self._ensure_connected()

        try:
            self._total_operations += 1
            value = await self._client.incrby(key, amount)
            logger.debug("Redis INCR operation", key=key, amount=amount, new_value=value)
            return value

        except RedisError as e:
            logger.error("Redis INCR operation failed", key=key, error=str(e))
            raise

    async def decr(self, key: str, amount: int = 1) -> int:
        """
        Decrement key value by amount.

        Args:
            key: Cache key
            amount: Decrement amount

        Returns:
            New value after decrement

        Raises:
            ConnectionError: If Redis is not connected
            RedisError: If Redis operation fails
        """
        self._ensure_connected()

        try:
            self._total_operations += 1
            value = await self._client.decrby(key, amount)
            logger.debug("Redis DECR operation", key=key, amount=amount, new_value=value)
            return value

        except RedisError as e:
            logger.error("Redis DECR operation failed", key=key, error=str(e))
            raise

    @asynccontextmanager
    async def pipeline(self) -> AsyncIterator[redis.client.Pipeline]:
        """
        Create Redis pipeline for batch operations.

        Yields:
            Redis pipeline for executing multiple commands atomically

        Raises:
            ConnectionError: If Redis is not connected
            RedisError: If pipeline operations fail
        """
        self._ensure_connected()

        pipe = self._client.pipeline()
        try:
            yield pipe
            await pipe.execute()
            logger.debug("Redis pipeline executed successfully")

        except RedisError as e:
            logger.error("Redis pipeline execution failed", error=str(e))
            raise

        finally:
            await pipe.reset()

    async def get_json(self, key: str) -> Optional[dict[str, Any]]:
        """
        Get JSON value from Redis by key.

        Args:
            key: Cache key

        Returns:
            Deserialized JSON value or None if key doesn't exist

        Raises:
            ConnectionError: If Redis is not connected
            RedisError: If Redis operation fails
            json.JSONDecodeError: If value is not valid JSON
        """
        value = await self.get(key)
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error("Failed to decode JSON from cache", key=key, error=str(e))
            raise

    async def set_json(
        self,
        key: str,
        value: dict[str, Any],
        ex: Optional[int] = None,
        px: Optional[int] = None,
    ) -> bool:
        """
        Set JSON value in Redis with optional expiration.

        Args:
            key: Cache key
            value: Dictionary to cache as JSON
            ex: Expiration time in seconds
            px: Expiration time in milliseconds

        Returns:
            True if operation succeeded, False otherwise

        Raises:
            ConnectionError: If Redis is not connected
            RedisError: If Redis operation fails
            TypeError: If value is not JSON serializable
        """
        try:
            json_value = json.dumps(value)
            return await self.set(key, json_value, ex=ex, px=px)
        except (TypeError, ValueError) as e:
            logger.error("Failed to serialize value to JSON", key=key, error=str(e))
            raise

    async def get_many(self, *keys: str) -> dict[str, Optional[str]]:
        """
        Get multiple values from Redis by keys.

        Args:
            *keys: Cache keys to retrieve

        Returns:
            Dictionary mapping keys to their values (None if key doesn't exist)

        Raises:
            ConnectionError: If Redis is not connected
            RedisError: If Redis operation fails
        """
        self._ensure_connected()

        try:
            self._total_operations += len(keys)
            values = await self._client.mget(*keys)
            
            result = dict(zip(keys, values))
            hits = sum(1 for v in values if v is not None)
            self._cache_hits += hits
            self._cache_misses += len(keys) - hits
            
            logger.debug("Redis MGET operation", keys=keys, found=hits)
            return result

        except RedisError as e:
            logger.error("Redis MGET operation failed", keys=keys, error=str(e))
            raise

    async def set_many(
        self,
        mapping: dict[str, Union[str, bytes, int, float]],
        ex: Optional[int] = None,
    ) -> bool:
        """
        Set multiple key-value pairs in Redis.

        Args:
            mapping: Dictionary of key-value pairs to set
            ex: Expiration time in seconds (applied to all keys)

        Returns:
            True if all operations succeeded

        Raises:
            ConnectionError: If Redis is not connected
            RedisError: If Redis operation fails
        """
        self._ensure_connected()

        try:
            self._total_operations += len(mapping)
            
            if ex is None:
                result = await self._client.mset(mapping)
                logger.debug("Redis MSET operation", count=len(mapping))
                return result
            else:
                async with self.pipeline() as pipe:
                    for key, value in mapping.items():
                        pipe.set(key, value, ex=ex)
                logger.debug("Redis MSET with expiration", count=len(mapping), ex=ex)
                return True

        except RedisError as e:
            logger.error("Redis MSET operation failed", error=str(e))
            raise

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Redis key pattern (e.g., "vehicle:*")

        Returns:
            Number of keys deleted

        Raises:
            ConnectionError: If Redis is not connected
            RedisError: If Redis operation fails
        """
        self._ensure_connected()

        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)
            
            if not keys:
                logger.debug("Redis DELETE pattern - no keys found", pattern=pattern)
                return 0
            
            count = await self.delete(*keys)
            logger.debug("Redis DELETE pattern", pattern=pattern, count=count)
            return count

        except RedisError as e:
            logger.error("Redis DELETE pattern failed", pattern=pattern, error=str(e))
            raise

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache performance statistics.

        Returns:
            Dictionary containing cache hit rate and operation counts
        """
        hit_rate = (
            self._cache_hits / self._total_operations * 100
            if self._total_operations > 0
            else 0.0
        )
        
        return {
            "total_operations": self._total_operations,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
        }

    def reset_cache_stats(self) -> None:
        """Reset cache performance statistics."""
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_operations = 0
        logger.info("Cache statistics reset")


class CacheKeyManager:
    """
    Utility class for managing cache keys with consistent naming.

    Provides methods for generating standardized cache keys with
    proper namespacing and formatting.
    """

    def __init__(self, namespace: str = "autoselect"):
        """
        Initialize cache key manager.

        Args:
            namespace: Base namespace for all cache keys
        """
        self.namespace = namespace

    def make_key(self, *parts: Union[str, int]) -> str:
        """
        Generate cache key from parts.

        Args:
            *parts: Key components to join

        Returns:
            Formatted cache key with namespace

        Example:
            >>> manager = CacheKeyManager("app")
            >>> manager.make_key("user", 123, "profile")
            'app:user:123:profile'
        """
        key_parts = [str(part) for part in parts if part]
        key = ":".join([self.namespace] + key_parts)
        return key

    def user_key(self, user_id: Union[str, int]) -> str:
        """Generate cache key for user data."""
        return self.make_key("user", user_id)

    def vehicle_key(self, vehicle_id: Union[str, int]) -> str:
        """Generate cache key for vehicle data."""
        return self.make_key("vehicle", vehicle_id)

    def vehicle_list_key(self, filters: Optional[dict[str, Any]] = None) -> str:
        """
        Generate cache key for vehicle list queries.

        Args:
            filters: Optional filter parameters

        Returns:
            Cache key for vehicle list query
        """
        return self.list_key("vehicles", filters)

    def vehicle_detail_key(self, vehicle_id: Union[str, int]) -> str:
        """Generate cache key for vehicle detail data."""
        return self.make_key("vehicle", vehicle_id, "detail")

    def order_key(self, order_id: Union[str, int]) -> str:
        """Generate cache key for order data."""
        return self.make_key("order", order_id)

    def session_key(self, session_id: str) -> str:
        """Generate cache key for session data."""
        return self.make_key("session", session_id)

    def inventory_key(self, inventory_id: Union[str, int]) -> str:
        """Generate cache key for inventory data."""
        return self.make_key("inventory", inventory_id)

    def list_key(self, entity_type: str, filters: Optional[dict[str, Any]] = None) -> str:
        """
        Generate cache key for list queries.

        Args:
            entity_type: Type of entity (e.g., "vehicles", "orders")
            filters: Optional filter parameters

        Returns:
            Cache key for list query
        """
        parts = ["list", entity_type]
        if filters:
            filter_str = ":".join(f"{k}={v}" for k, v in sorted(filters.items()))
            parts.append(filter_str)
        return self.make_key(*parts)


_redis_client: Optional[RedisClient] = None
_cache_key_manager: Optional[CacheKeyManager] = None


async def get_redis_client() -> RedisClient:
    """
    Get or create global Redis client instance.

    Returns:
        Singleton Redis client instance

    Raises:
        ConnectionError: If Redis connection fails
    """
    global _redis_client

    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()

    return _redis_client


def get_cache_key_manager() -> CacheKeyManager:
    """
    Get or create global cache key manager instance.

    Returns:
        Singleton cache key manager instance
    """
    global _cache_key_manager

    if _cache_key_manager is None:
        _cache_key_manager = CacheKeyManager()

    return _cache_key_manager


async def close_redis_client() -> None:
    """
    Close global Redis client connection.

    Safely closes the global Redis client and releases resources.
    """
    global _redis_client

    if _redis_client is not None:
        await _redis_client.disconnect()
        _redis_client = None