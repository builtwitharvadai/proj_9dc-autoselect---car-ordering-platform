"""
Cache key management and generation for Redis caching layer.

This module provides centralized cache key generation, versioning, and namespace
management for all cached entities in the vehicle catalog system.
"""

import hashlib
import json
from typing import Any, Optional
from urllib.parse import urlencode

from src.core.logging import get_logger

logger = get_logger(__name__)


class CacheKeyManager:
    """
    Centralized cache key management with versioning and namespace support.
    
    Provides consistent key generation across the application with support for:
    - Namespace isolation
    - Key versioning for cache invalidation
    - Hash-based keys for complex filters
    - Structured key patterns
    """
    
    # Cache key version - increment to invalidate all keys
    VERSION = "v1"
    
    # Namespace prefixes
    NAMESPACE_VEHICLE = "vehicle"
    NAMESPACE_INVENTORY = "inventory"
    NAMESPACE_SEARCH = "search"
    NAMESPACE_USER = "user"
    NAMESPACE_SESSION = "session"
    
    # Key patterns
    PATTERN_VEHICLE_DETAIL = "{namespace}:{version}:detail:{vehicle_id}"
    PATTERN_VEHICLE_LIST = "{namespace}:{version}:list:{hash}"
    PATTERN_VEHICLE_BY_VIN = "{namespace}:{version}:vin:{vin}"
    PATTERN_VEHICLE_AVAILABLE = "{namespace}:{version}:available:{hash}"
    PATTERN_INVENTORY_ITEM = "{namespace}:{version}:item:{item_id}"
    PATTERN_INVENTORY_BY_VEHICLE = "{namespace}:{version}:by_vehicle:{vehicle_id}"
    PATTERN_SEARCH_RESULTS = "{namespace}:{version}:results:{hash}"
    PATTERN_SEARCH_FACETS = "{namespace}:{version}:facets:{hash}"
    PATTERN_USER_PROFILE = "{namespace}:{version}:profile:{user_id}"
    PATTERN_SESSION_DATA = "{namespace}:{version}:session:{session_id}"
    
    def __init__(self, version: Optional[str] = None):
        """
        Initialize cache key manager.
        
        Args:
            version: Optional cache version override. Defaults to class VERSION.
        """
        self.version = version or self.VERSION
        logger.debug(
            "Cache key manager initialized",
            version=self.version
        )
    
    def _generate_hash(self, data: dict[str, Any]) -> str:
        """
        Generate deterministic hash from dictionary data.
        
        Args:
            data: Dictionary to hash
            
        Returns:
            Hexadecimal hash string
        """
        # Sort keys for deterministic hashing
        sorted_data = json.dumps(data, sort_keys=True, default=str)
        hash_obj = hashlib.sha256(sorted_data.encode('utf-8'))
        return hash_obj.hexdigest()[:16]  # Use first 16 chars for brevity
    
    def _sanitize_key_part(self, value: str) -> str:
        """
        Sanitize key part to prevent injection attacks.
        
        Args:
            value: Key part to sanitize
            
        Returns:
            Sanitized key part
        """
        # Remove or replace potentially dangerous characters
        sanitized = str(value).replace(':', '_').replace(' ', '_')
        # Limit length to prevent extremely long keys
        return sanitized[:200]
    
    def vehicle_detail_key(self, vehicle_id: str) -> str:
        """
        Generate cache key for individual vehicle details.
        
        Args:
            vehicle_id: Vehicle UUID
            
        Returns:
            Cache key string
        """
        sanitized_id = self._sanitize_key_part(vehicle_id)
        key = self.PATTERN_VEHICLE_DETAIL.format(
            namespace=self.NAMESPACE_VEHICLE,
            version=self.version,
            vehicle_id=sanitized_id
        )
        logger.debug("Generated vehicle detail key", key=key, vehicle_id=vehicle_id)
        return key
    
    def vehicle_list_key(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[dict[str, Any]] = None,
        sort_by: Optional[str] = None
    ) -> str:
        """
        Generate cache key for vehicle list queries.
        
        Args:
            page: Page number
            page_size: Items per page
            filters: Optional filter parameters
            sort_by: Optional sort field
            
        Returns:
            Cache key string
        """
        params = {
            'page': page,
            'page_size': page_size,
            'sort_by': sort_by or 'created_at'
        }
        
        if filters:
            params['filters'] = filters
        
        param_hash = self._generate_hash(params)
        key = self.PATTERN_VEHICLE_LIST.format(
            namespace=self.NAMESPACE_VEHICLE,
            version=self.version,
            hash=param_hash
        )
        
        logger.debug(
            "Generated vehicle list key",
            key=key,
            page=page,
            page_size=page_size,
            has_filters=bool(filters)
        )
        return key
    
    def vehicle_by_vin_key(self, vin: str) -> str:
        """
        Generate cache key for vehicle lookup by VIN.
        
        Args:
            vin: Vehicle Identification Number
            
        Returns:
            Cache key string
        """
        sanitized_vin = self._sanitize_key_part(vin.upper())
        key = self.PATTERN_VEHICLE_BY_VIN.format(
            namespace=self.NAMESPACE_VEHICLE,
            version=self.version,
            vin=sanitized_vin
        )
        logger.debug("Generated vehicle VIN key", key=key, vin=vin)
        return key
    
    def vehicle_available_key(
        self,
        dealership_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> str:
        """
        Generate cache key for available vehicles query.
        
        Args:
            dealership_id: Optional dealership filter
            page: Page number
            page_size: Items per page
            
        Returns:
            Cache key string
        """
        params = {
            'dealership_id': dealership_id,
            'page': page,
            'page_size': page_size
        }
        
        param_hash = self._generate_hash(params)
        key = self.PATTERN_VEHICLE_AVAILABLE.format(
            namespace=self.NAMESPACE_VEHICLE,
            version=self.version,
            hash=param_hash
        )
        
        logger.debug(
            "Generated available vehicles key",
            key=key,
            dealership_id=dealership_id,
            page=page
        )
        return key
    
    def inventory_item_key(self, item_id: str) -> str:
        """
        Generate cache key for inventory item details.
        
        Args:
            item_id: Inventory item UUID
            
        Returns:
            Cache key string
        """
        sanitized_id = self._sanitize_key_part(item_id)
        key = self.PATTERN_INVENTORY_ITEM.format(
            namespace=self.NAMESPACE_INVENTORY,
            version=self.version,
            item_id=sanitized_id
        )
        logger.debug("Generated inventory item key", key=key, item_id=item_id)
        return key
    
    def inventory_by_vehicle_key(self, vehicle_id: str) -> str:
        """
        Generate cache key for inventory items by vehicle.
        
        Args:
            vehicle_id: Vehicle UUID
            
        Returns:
            Cache key string
        """
        sanitized_id = self._sanitize_key_part(vehicle_id)
        key = self.PATTERN_INVENTORY_BY_VEHICLE.format(
            namespace=self.NAMESPACE_INVENTORY,
            version=self.version,
            vehicle_id=sanitized_id
        )
        logger.debug(
            "Generated inventory by vehicle key",
            key=key,
            vehicle_id=vehicle_id
        )
        return key
    
    def search_results_key(
        self,
        query: str,
        filters: Optional[dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: Optional[str] = None
    ) -> str:
        """
        Generate cache key for search results.
        
        Args:
            query: Search query string
            filters: Optional search filters
            page: Page number
            page_size: Items per page
            sort_by: Optional sort field
            
        Returns:
            Cache key string
        """
        params = {
            'query': query.lower().strip(),
            'page': page,
            'page_size': page_size,
            'sort_by': sort_by or 'relevance'
        }
        
        if filters:
            params['filters'] = filters
        
        param_hash = self._generate_hash(params)
        key = self.PATTERN_SEARCH_RESULTS.format(
            namespace=self.NAMESPACE_SEARCH,
            version=self.version,
            hash=param_hash
        )
        
        logger.debug(
            "Generated search results key",
            key=key,
            query=query,
            page=page,
            has_filters=bool(filters)
        )
        return key
    
    def search_facets_key(
        self,
        query: str,
        filters: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Generate cache key for search facets/aggregations.
        
        Args:
            query: Search query string
            filters: Optional search filters
            
        Returns:
            Cache key string
        """
        params = {
            'query': query.lower().strip(),
            'filters': filters or {}
        }
        
        param_hash = self._generate_hash(params)
        key = self.PATTERN_SEARCH_FACETS.format(
            namespace=self.NAMESPACE_SEARCH,
            version=self.version,
            hash=param_hash
        )
        
        logger.debug(
            "Generated search facets key",
            key=key,
            query=query,
            has_filters=bool(filters)
        )
        return key
    
    def user_profile_key(self, user_id: str) -> str:
        """
        Generate cache key for user profile data.
        
        Args:
            user_id: User UUID
            
        Returns:
            Cache key string
        """
        sanitized_id = self._sanitize_key_part(user_id)
        key = self.PATTERN_USER_PROFILE.format(
            namespace=self.NAMESPACE_USER,
            version=self.version,
            user_id=sanitized_id
        )
        logger.debug("Generated user profile key", key=key, user_id=user_id)
        return key
    
    def session_data_key(self, session_id: str) -> str:
        """
        Generate cache key for session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Cache key string
        """
        sanitized_id = self._sanitize_key_part(session_id)
        key = self.PATTERN_SESSION_DATA.format(
            namespace=self.NAMESPACE_SESSION,
            version=self.version,
            session_id=sanitized_id
        )
        logger.debug("Generated session data key", key=key, session_id=session_id)
        return key
    
    def get_namespace_pattern(self, namespace: str) -> str:
        """
        Get pattern for invalidating all keys in a namespace.
        
        Args:
            namespace: Namespace to target
            
        Returns:
            Redis pattern string for key matching
        """
        pattern = f"{namespace}:{self.version}:*"
        logger.debug("Generated namespace pattern", pattern=pattern, namespace=namespace)
        return pattern
    
    def get_vehicle_patterns(self) -> list[str]:
        """
        Get all patterns for vehicle-related cache keys.
        
        Returns:
            List of Redis patterns for vehicle keys
        """
        patterns = [
            f"{self.NAMESPACE_VEHICLE}:{self.version}:*",
            f"{self.NAMESPACE_INVENTORY}:{self.version}:*"
        ]
        logger.debug("Generated vehicle patterns", patterns=patterns)
        return patterns
    
    def get_search_patterns(self) -> list[str]:
        """
        Get all patterns for search-related cache keys.
        
        Returns:
            List of Redis patterns for search keys
        """
        patterns = [
            f"{self.NAMESPACE_SEARCH}:{self.version}:*"
        ]
        logger.debug("Generated search patterns", patterns=patterns)
        return patterns


# Global cache key manager instance
_cache_key_manager: Optional[CacheKeyManager] = None


def get_cache_key_manager() -> CacheKeyManager:
    """
    Get or create global cache key manager instance.
    
    Returns:
        CacheKeyManager instance
    """
    global _cache_key_manager
    
    if _cache_key_manager is None:
        _cache_key_manager = CacheKeyManager()
        logger.info("Created global cache key manager instance")
    
    return _cache_key_manager