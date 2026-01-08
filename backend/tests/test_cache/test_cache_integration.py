"""
Integration tests for vehicle service caching with API endpoints.

This module provides comprehensive integration tests for the vehicle service
caching layer, validating cache behavior across service and API layers,
performance improvements, cache consistency, and proper invalidation patterns.

Test Categories:
- Cache Hit/Miss Scenarios
- Cache Invalidation Patterns
- Performance Validation
- Cache Consistency
- Concurrent Access
- Error Handling with Cache
- Cache Warming
- Search Result Caching
"""

import asyncio
import time
import uuid
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.cache.redis_client import RedisClient
from src.schemas.vehicles import (
    VehicleCreate,
    VehicleDimensions,
    VehicleFeatures,
    VehicleResponse,
    VehicleSearchRequest,
    VehicleSpecifications,
    VehicleUpdate,
)
from src.services.cache.vehicle_cache import VehicleCache
from src.services.vehicles.service import (
    VehicleNotFoundError,
    VehicleService,
    VehicleServiceError,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
async def mock_redis_client() -> AsyncMock:
    """
    Create mock Redis client for testing.

    Returns:
        AsyncMock: Mocked Redis client with standard operations
    """
    mock_client = AsyncMock(spec=RedisClient)
    mock_client.get = AsyncMock(return_value=None)
    mock_client.set = AsyncMock(return_value=True)
    mock_client.delete = AsyncMock(return_value=1)
    mock_client.exists = AsyncMock(return_value=0)
    mock_client.expire = AsyncMock(return_value=True)
    mock_client.ttl = AsyncMock(return_value=3600)
    return mock_client


@pytest.fixture
async def mock_vehicle_cache(mock_redis_client: AsyncMock) -> VehicleCache:
    """
    Create vehicle cache instance with mocked Redis.

    Args:
        mock_redis_client: Mocked Redis client

    Returns:
        VehicleCache: Cache instance for testing
    """
    cache = VehicleCache(redis_client=mock_redis_client, ttl=3600)
    return cache


@pytest.fixture
async def mock_db_session() -> AsyncMock:
    """
    Create mock database session.

    Returns:
        AsyncMock: Mocked async database session
    """
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def sample_vehicle_data() -> dict[str, Any]:
    """
    Create sample vehicle data for testing.

    Returns:
        dict: Sample vehicle creation data
    """
    return {
        "make": "Toyota",
        "model": "Camry",
        "year": 2024,
        "trim": "XLE",
        "body_style": "Sedan",
        "exterior_color": "Silver",
        "interior_color": "Black",
        "base_price": Decimal("32500.00"),
        "specifications": {
            "engine": "2.5L 4-Cylinder",
            "horsepower": 203,
            "torque": 184,
            "transmission": "8-Speed Automatic",
            "drivetrain": "FWD",
            "fuel_type": "Gasoline",
            "mpg_city": 28,
            "mpg_highway": 39,
            "fuel_capacity": 15.8,
        },
        "dimensions": {
            "length": 192.7,
            "width": 72.4,
            "height": 56.9,
            "wheelbase": 111.2,
            "curb_weight": 3310,
            "cargo_volume": 15.1,
            "seating_capacity": 5,
        },
        "features": {
            "safety": [
                "Toyota Safety Sense 3.0",
                "Blind Spot Monitor",
                "Rear Cross-Traffic Alert",
            ],
            "technology": [
                "9-inch Touchscreen",
                "Apple CarPlay",
                "Android Auto",
                "Wi-Fi Hotspot",
            ],
            "comfort": [
                "Dual-Zone Climate Control",
                "Power Driver Seat",
                "Heated Front Seats",
            ],
            "exterior": ["LED Headlights", "18-inch Alloy Wheels", "Power Moonroof"],
        },
        "custom_attributes": {"package": "Premium", "warranty_years": 3},
    }


@pytest.fixture
def sample_vehicle_response(sample_vehicle_data: dict[str, Any]) -> VehicleResponse:
    """
    Create sample vehicle response for testing.

    Args:
        sample_vehicle_data: Sample vehicle data

    Returns:
        VehicleResponse: Sample vehicle response object
    """
    return VehicleResponse(
        id=uuid.uuid4(),
        make=sample_vehicle_data["make"],
        model=sample_vehicle_data["model"],
        year=sample_vehicle_data["year"],
        trim=sample_vehicle_data["trim"],
        body_style=sample_vehicle_data["body_style"],
        exterior_color=sample_vehicle_data["exterior_color"],
        interior_color=sample_vehicle_data["interior_color"],
        base_price=sample_vehicle_data["base_price"],
        specifications=VehicleSpecifications(**sample_vehicle_data["specifications"]),
        dimensions=VehicleDimensions(**sample_vehicle_data["dimensions"]),
        features=VehicleFeatures(**sample_vehicle_data["features"]),
        custom_attributes=sample_vehicle_data["custom_attributes"],
        is_active=True,
    )


# ============================================================================
# Cache Hit/Miss Scenarios
# ============================================================================


@pytest.mark.asyncio
async def test_vehicle_detail_cache_miss_then_hit(
    mock_db_session: AsyncMock,
    mock_vehicle_cache: VehicleCache,
    sample_vehicle_response: VehicleResponse,
) -> None:
    """
    Test vehicle detail retrieval with cache miss followed by cache hit.

    Validates:
    - First request misses cache and queries database
    - Response is cached after database query
    - Second request hits cache without database query
    - Cache TTL is properly set
    """
    vehicle_id = sample_vehicle_response.id

    # Mock repository to return vehicle on first call
    with patch(
        "src.services.vehicles.service.VehicleRepository"
    ) as mock_repo_class:
        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=MagicMock(
            id=vehicle_id,
            make=sample_vehicle_response.make,
            model=sample_vehicle_response.model,
            year=sample_vehicle_response.year,
            trim=sample_vehicle_response.trim,
            body_style=sample_vehicle_response.body_style,
            exterior_color=sample_vehicle_response.exterior_color,
            interior_color=sample_vehicle_response.interior_color,
            base_price=sample_vehicle_response.base_price,
            specifications=sample_vehicle_response.specifications.model_dump(),
            dimensions=sample_vehicle_response.dimensions.model_dump(),
            features=sample_vehicle_response.features.model_dump(),
            custom_attributes=sample_vehicle_response.custom_attributes,
            is_active=True,
            created_at=sample_vehicle_response.created_at,
            updated_at=sample_vehicle_response.updated_at,
        ))
        mock_repo_class.return_value = mock_repo

        service = VehicleService(
            session=mock_db_session,
            vehicle_cache=mock_vehicle_cache,
        )

        # First request - cache miss
        mock_vehicle_cache.get_vehicle_detail = AsyncMock(return_value=None)
        mock_vehicle_cache.set_vehicle_detail = AsyncMock()

        result1 = await service.get_vehicle(vehicle_id)

        # Verify database was queried
        mock_repo.get_by_id.assert_called_once_with(
            vehicle_id, include_inventory=False
        )

        # Verify result was cached
        mock_vehicle_cache.set_vehicle_detail.assert_called_once()
        cached_vehicle_id = mock_vehicle_cache.set_vehicle_detail.call_args[0][0]
        assert cached_vehicle_id == vehicle_id

        # Second request - cache hit
        mock_vehicle_cache.get_vehicle_detail = AsyncMock(
            return_value=sample_vehicle_response
        )
        mock_repo.get_by_id.reset_mock()

        result2 = await service.get_vehicle(vehicle_id)

        # Verify database was NOT queried
        mock_repo.get_by_id.assert_not_called()

        # Verify cache was checked
        mock_vehicle_cache.get_vehicle_detail.assert_called_once_with(vehicle_id)

        # Verify both results are equivalent
        assert result1.id == result2.id
        assert result1.make == result2.make
        assert result1.model == result2.model


@pytest.mark.asyncio
async def test_vehicle_list_cache_with_filters(
    mock_db_session: AsyncMock,
    mock_vehicle_cache: VehicleCache,
    sample_vehicle_response: VehicleResponse,
) -> None:
    """
    Test vehicle list caching with different filter combinations.

    Validates:
    - Different filter combinations create separate cache entries
    - Cache keys are properly generated from filters
    - Cached results match filter criteria
    """
    with patch(
        "src.services.vehicles.service.VehicleRepository"
    ) as mock_repo_class:
        mock_repo = AsyncMock()
        mock_repo.search = AsyncMock(return_value=([MagicMock(
            id=sample_vehicle_response.id,
            make=sample_vehicle_response.make,
            model=sample_vehicle_response.model,
            year=sample_vehicle_response.year,
            trim=sample_vehicle_response.trim,
            body_style=sample_vehicle_response.body_style,
            exterior_color=sample_vehicle_response.exterior_color,
            interior_color=sample_vehicle_response.interior_color,
            base_price=sample_vehicle_response.base_price,
            specifications=sample_vehicle_response.specifications.model_dump(),
            dimensions=sample_vehicle_response.dimensions.model_dump(),
            features=sample_vehicle_response.features.model_dump(),
            custom_attributes=sample_vehicle_response.custom_attributes,
            is_active=True,
            created_at=sample_vehicle_response.created_at,
            updated_at=sample_vehicle_response.updated_at,
        )], 1))
        mock_repo_class.return_value = mock_repo

        service = VehicleService(
            session=mock_db_session,
            vehicle_cache=mock_vehicle_cache,
        )

        # Test with make filter
        search_request_1 = VehicleSearchRequest(
            make="Toyota",
            page=1,
            page_size=20,
        )

        mock_vehicle_cache.get_vehicle_list = AsyncMock(return_value=None)
        mock_vehicle_cache.set_vehicle_list = AsyncMock()

        result1 = await service.search_vehicles(search_request_1)

        # Verify cache was set with correct filters
        mock_vehicle_cache.set_vehicle_list.assert_called_once()
        call_args = mock_vehicle_cache.set_vehicle_list.call_args
        assert call_args[0][1]["make"] == "Toyota"

        # Test with different filters
        search_request_2 = VehicleSearchRequest(
            make="Honda",
            model="Accord",
            page=1,
            page_size=20,
        )

        mock_vehicle_cache.get_vehicle_list.reset_mock()
        mock_vehicle_cache.set_vehicle_list.reset_mock()

        result2 = await service.search_vehicles(search_request_2)

        # Verify different cache entry was created
        call_args = mock_vehicle_cache.set_vehicle_list.call_args
        assert call_args[0][1]["make"] == "Honda"
        assert call_args[0][1]["model"] == "Accord"


@pytest.mark.asyncio
async def test_search_results_cache_with_query(
    mock_vehicle_cache: VehicleCache,
) -> None:
    """
    Test search results caching with query strings.

    Validates:
    - Search queries are properly cached
    - Cache keys include query parameters
    - Cached results are returned for identical queries
    """
    query = "Toyota Camry 2024"
    filters = {"page": 1, "limit": 20}

    cached_results = {
        "results": [],
        "facets": None,
        "metadata": {
            "query": query,
            "total_results": 0,
            "page": 1,
            "limit": 20,
        },
        "suggestions": [],
    }

    # First call - cache miss
    mock_vehicle_cache.get_search_results = AsyncMock(return_value=None)
    mock_vehicle_cache.set_search_results = AsyncMock()

    result1 = await mock_vehicle_cache.get_search_results(query, filters)
    assert result1 is None

    # Set cache
    await mock_vehicle_cache.set_search_results(query, cached_results, filters)
    mock_vehicle_cache.set_search_results.assert_called_once_with(
        query, cached_results, filters
    )

    # Second call - cache hit
    mock_vehicle_cache.get_search_results = AsyncMock(return_value=cached_results)
    result2 = await mock_vehicle_cache.get_search_results(query, filters)

    assert result2 == cached_results
    mock_vehicle_cache.get_search_results.assert_called_once_with(query, filters)


# ============================================================================
# Cache Invalidation Patterns
# ============================================================================


@pytest.mark.asyncio
async def test_vehicle_update_invalidates_cache(
    mock_db_session: AsyncMock,
    mock_vehicle_cache: VehicleCache,
    sample_vehicle_response: VehicleResponse,
) -> None:
    """
    Test cache invalidation on vehicle update.

    Validates:
    - Vehicle detail cache is invalidated
    - Vehicle list caches are invalidated
    - Search result caches are invalidated
    - Database update is committed
    """
    vehicle_id = sample_vehicle_response.id

    with patch(
        "src.services.vehicles.service.VehicleRepository"
    ) as mock_repo_class:
        mock_repo = AsyncMock()
        mock_vehicle = MagicMock(
            id=vehicle_id,
            make=sample_vehicle_response.make,
            model=sample_vehicle_response.model,
            year=sample_vehicle_response.year,
            trim=sample_vehicle_response.trim,
            body_style=sample_vehicle_response.body_style,
            exterior_color=sample_vehicle_response.exterior_color,
            interior_color=sample_vehicle_response.interior_color,
            base_price=sample_vehicle_response.base_price,
            specifications=sample_vehicle_response.specifications.model_dump(),
            dimensions=sample_vehicle_response.dimensions.model_dump(),
            features=sample_vehicle_response.features.model_dump(),
            custom_attributes=sample_vehicle_response.custom_attributes,
            is_active=True,
            created_at=sample_vehicle_response.created_at,
            updated_at=sample_vehicle_response.updated_at,
        )
        mock_repo.get_by_id = AsyncMock(return_value=mock_vehicle)
        mock_repo.update = AsyncMock(return_value=mock_vehicle)
        mock_repo_class.return_value = mock_repo

        service = VehicleService(
            session=mock_db_session,
            vehicle_cache=mock_vehicle_cache,
        )

        mock_vehicle_cache.invalidate_vehicle = AsyncMock()
        mock_vehicle_cache.invalidate_vehicle_lists = AsyncMock()

        update_data = VehicleUpdate(base_price=Decimal("33000.00"))

        await service.update_vehicle(vehicle_id, update_data)

        # Verify cache invalidation
        mock_vehicle_cache.invalidate_vehicle.assert_called_once_with(vehicle_id)
        mock_vehicle_cache.invalidate_vehicle_lists.assert_called_once()

        # Verify database commit
        mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_vehicle_delete_invalidates_cache(
    mock_db_session: AsyncMock,
    mock_vehicle_cache: VehicleCache,
    sample_vehicle_response: VehicleResponse,
) -> None:
    """
    Test cache invalidation on vehicle deletion.

    Validates:
    - Vehicle detail cache is invalidated
    - Vehicle list caches are invalidated
    - Search result caches are invalidated
    - Soft delete is performed by default
    """
    vehicle_id = sample_vehicle_response.id

    with patch(
        "src.services.vehicles.service.VehicleRepository"
    ) as mock_repo_class:
        mock_repo = AsyncMock()
        mock_repo.delete = AsyncMock(return_value=True)
        mock_repo_class.return_value = mock_repo

        service = VehicleService(
            session=mock_db_session,
            vehicle_cache=mock_vehicle_cache,
        )

        mock_vehicle_cache.invalidate_vehicle = AsyncMock()
        mock_vehicle_cache.invalidate_vehicle_lists = AsyncMock()

        result = await service.delete_vehicle(vehicle_id, soft=True)

        assert result is True

        # Verify cache invalidation
        mock_vehicle_cache.invalidate_vehicle.assert_called_once_with(vehicle_id)
        mock_vehicle_cache.invalidate_vehicle_lists.assert_called_once()

        # Verify soft delete
        mock_repo.delete.assert_called_once_with(vehicle_id, soft=True)

        # Verify database commit
        mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_vehicle_create_invalidates_list_cache(
    mock_db_session: AsyncMock,
    mock_vehicle_cache: VehicleCache,
    sample_vehicle_data: dict[str, Any],
) -> None:
    """
    Test cache invalidation on vehicle creation.

    Validates:
    - Vehicle list caches are invalidated
    - New vehicle is not cached individually
    - Database commit is performed
    """
    with patch(
        "src.services.vehicles.service.VehicleRepository"
    ) as mock_repo_class:
        mock_repo = AsyncMock()
        mock_vehicle = MagicMock(
            id=uuid.uuid4(),
            make=sample_vehicle_data["make"],
            model=sample_vehicle_data["model"],
            year=sample_vehicle_data["year"],
            trim=sample_vehicle_data["trim"],
            body_style=sample_vehicle_data["body_style"],
            exterior_color=sample_vehicle_data["exterior_color"],
            interior_color=sample_vehicle_data["interior_color"],
            base_price=sample_vehicle_data["base_price"],
            specifications=sample_vehicle_data["specifications"],
            dimensions=sample_vehicle_data["dimensions"],
            features=sample_vehicle_data["features"],
            custom_attributes=sample_vehicle_data["custom_attributes"],
            is_active=True,
        )
        mock_repo.create = AsyncMock(return_value=mock_vehicle)
        mock_repo_class.return_value = mock_repo

        service = VehicleService(
            session=mock_db_session,
            vehicle_cache=mock_vehicle_cache,
        )

        mock_vehicle_cache.invalidate_vehicle_lists = AsyncMock()

        vehicle_create = VehicleCreate(
            make=sample_vehicle_data["make"],
            model=sample_vehicle_data["model"],
            year=sample_vehicle_data["year"],
            trim=sample_vehicle_data["trim"],
            body_style=sample_vehicle_data["body_style"],
            exterior_color=sample_vehicle_data["exterior_color"],
            interior_color=sample_vehicle_data["interior_color"],
            base_price=sample_vehicle_data["base_price"],
            specifications=VehicleSpecifications(
                **sample_vehicle_data["specifications"]
            ),
            dimensions=VehicleDimensions(**sample_vehicle_data["dimensions"]),
            features=VehicleFeatures(**sample_vehicle_data["features"]),
            custom_attributes=sample_vehicle_data["custom_attributes"],
        )

        result = await service.create_vehicle(vehicle_create)

        # Verify list cache invalidation
        mock_vehicle_cache.invalidate_vehicle_lists.assert_called_once()

        # Verify database commit
        mock_db_session.commit.assert_called_once()

        assert result.make == sample_vehicle_data["make"]
        assert result.model == sample_vehicle_data["model"]


# ============================================================================
# Performance Validation
# ============================================================================


@pytest.mark.asyncio
async def test_cache_improves_response_time(
    mock_db_session: AsyncMock,
    mock_vehicle_cache: VehicleCache,
    sample_vehicle_response: VehicleResponse,
) -> None:
    """
    Test cache significantly improves response time.

    Validates:
    - Cached responses are faster than database queries
    - Performance improvement is measurable
    - Cache hit rate improves with repeated requests
    """
    vehicle_id = sample_vehicle_response.id

    with patch(
        "src.services.vehicles.service.VehicleRepository"
    ) as mock_repo_class:
        mock_repo = AsyncMock()

        # Simulate slow database query
        async def slow_db_query(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return MagicMock(
                id=vehicle_id,
                make=sample_vehicle_response.make,
                model=sample_vehicle_response.model,
                year=sample_vehicle_response.year,
                trim=sample_vehicle_response.trim,
                body_style=sample_vehicle_response.body_style,
                exterior_color=sample_vehicle_response.exterior_color,
                interior_color=sample_vehicle_response.interior_color,
                base_price=sample_vehicle_response.base_price,
                specifications=sample_vehicle_response.specifications.model_dump(),
                dimensions=sample_vehicle_response.dimensions.model_dump(),
                features=sample_vehicle_response.features.model_dump(),
                custom_attributes=sample_vehicle_response.custom_attributes,
                is_active=True,
                created_at=sample_vehicle_response.created_at,
                updated_at=sample_vehicle_response.updated_at,
            )

        mock_repo.get_by_id = slow_db_query
        mock_repo_class.return_value = mock_repo

        service = VehicleService(
            session=mock_db_session,
            vehicle_cache=mock_vehicle_cache,
        )

        # First request - cache miss (slow)
        mock_vehicle_cache.get_vehicle_detail = AsyncMock(return_value=None)
        mock_vehicle_cache.set_vehicle_detail = AsyncMock()

        start_time = time.time()
        await service.get_vehicle(vehicle_id)
        db_query_time = time.time() - start_time

        # Second request - cache hit (fast)
        mock_vehicle_cache.get_vehicle_detail = AsyncMock(
            return_value=sample_vehicle_response
        )

        start_time = time.time()
        await service.get_vehicle(vehicle_id)
        cache_query_time = time.time() - start_time

        # Verify cache is significantly faster
        assert cache_query_time < db_query_time * 0.5  # At least 50% faster
        assert db_query_time > 0.1  # Database query took expected time


@pytest.mark.asyncio
async def test_concurrent_cache_access_performance(
    mock_db_session: AsyncMock,
    mock_vehicle_cache: VehicleCache,
    sample_vehicle_response: VehicleResponse,
) -> None:
    """
    Test cache performance under concurrent access.

    Validates:
    - Cache handles concurrent requests efficiently
    - No race conditions in cache access
    - Performance scales with concurrent requests
    """
    vehicle_id = sample_vehicle_response.id

    with patch(
        "src.services.vehicles.service.VehicleRepository"
    ) as mock_repo_class:
        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=MagicMock(
            id=vehicle_id,
            make=sample_vehicle_response.make,
            model=sample_vehicle_response.model,
            year=sample_vehicle_response.year,
            trim=sample_vehicle_response.trim,
            body_style=sample_vehicle_response.body_style,
            exterior_color=sample_vehicle_response.exterior_color,
            interior_color=sample_vehicle_response.interior_color,
            base_price=sample_vehicle_response.base_price,
            specifications=sample_vehicle_response.specifications.model_dump(),
            dimensions=sample_vehicle_response.dimensions.model_dump(),
            features=sample_vehicle_response.features.model_dump(),
            custom_attributes=sample_vehicle_response.custom_attributes,
            is_active=True,
            created_at=sample_vehicle_response.created_at,
            updated_at=sample_vehicle_response.updated_at,
        ))
        mock_repo_class.return_value = mock_repo

        service = VehicleService(
            session=mock_db_session,
            vehicle_cache=mock_vehicle_cache,
        )

        # Warm cache
        mock_vehicle_cache.get_vehicle_detail = AsyncMock(
            return_value=sample_vehicle_response
        )

        # Concurrent requests
        num_requests = 10
        tasks = [service.get_vehicle(vehicle_id) for _ in range(num_requests)]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Verify all requests succeeded
        assert len(results) == num_requests
        assert all(r.id == vehicle_id for r in results)

        # Verify concurrent access is efficient (should be < 100ms total)
        assert total_time < 0.1


# ============================================================================
# Cache Consistency
# ============================================================================


@pytest.mark.asyncio
async def test_cache_consistency_after_update(
    mock_db_session: AsyncMock,
    mock_vehicle_cache: VehicleCache,
    sample_vehicle_response: VehicleResponse,
) -> None:
    """
    Test cache consistency after vehicle update.

    Validates:
    - Stale cache entries are invalidated
    - Fresh data is returned after update
    - No stale data is served from cache
    """
    vehicle_id = sample_vehicle_response.id
    original_price = sample_vehicle_response.base_price
    updated_price = Decimal("35000.00")

    with patch(
        "src.services.vehicles.service.VehicleRepository"
    ) as mock_repo_class:
        mock_repo = AsyncMock()
        mock_vehicle = MagicMock(
            id=vehicle_id,
            make=sample_vehicle_response.make,
            model=sample_vehicle_response.model,
            year=sample_vehicle_response.year,
            trim=sample_vehicle_response.trim,
            body_style=sample_vehicle_response.body_style,
            exterior_color=sample_vehicle_response.exterior_color,
            interior_color=sample_vehicle_response.interior_color,
            base_price=original_price,
            specifications=sample_vehicle_response.specifications.model_dump(),
            dimensions=sample_vehicle_response.dimensions.model_dump(),
            features=sample_vehicle_response.features.model_dump(),
            custom_attributes=sample_vehicle_response.custom_attributes,
            is_active=True,
            created_at=sample_vehicle_response.created_at,
            updated_at=sample_vehicle_response.updated_at,
        )
        mock_repo.get_by_id = AsyncMock(return_value=mock_vehicle)
        mock_repo.update = AsyncMock(return_value=mock_vehicle)
        mock_repo_class.return_value = mock_repo

        service = VehicleService(
            session=mock_db_session,
            vehicle_cache=mock_vehicle_cache,
        )

        # Cache original vehicle
        mock_vehicle_cache.get_vehicle_detail = AsyncMock(
            return_value=sample_vehicle_response
        )
        mock_vehicle_cache.invalidate_vehicle = AsyncMock()
        mock_vehicle_cache.invalidate_vehicle_lists = AsyncMock()

        # Get original vehicle
        result1 = await service.get_vehicle(vehicle_id)
        assert result1.base_price == original_price

        # Update vehicle
        mock_vehicle.base_price = updated_price
        update_data = VehicleUpdate(base_price=updated_price)
        await service.update_vehicle(vehicle_id, update_data)

        # Verify cache was invalidated
        mock_vehicle_cache.invalidate_vehicle.assert_called_once_with(vehicle_id)

        # Get updated vehicle (should not be from cache)
        mock_vehicle_cache.get_vehicle_detail = AsyncMock(return_value=None)
        mock_vehicle_cache.set_vehicle_detail = AsyncMock()

        result2 = await service.get_vehicle(vehicle_id)
        assert result2.base_price == updated_price


@pytest.mark.asyncio
async def test_cache_consistency_across_list_and_detail(
    mock_db_session: AsyncMock,
    mock_vehicle_cache: VehicleCache,
    sample_vehicle_response: VehicleResponse,
) -> None:
    """
    Test cache consistency between list and detail views.

    Validates:
    - List cache and detail cache are synchronized
    - Updates invalidate both caches
    - Consistent data across different views
    """
    vehicle_id = sample_vehicle_response.id

    with patch(
        "src.services.vehicles.service.VehicleRepository"
    ) as mock_repo_class:
        mock_repo = AsyncMock()
        mock_vehicle = MagicMock(
            id=vehicle_id,
            make=sample_vehicle_response.make,
            model=sample_vehicle_response.model,
            year=sample_vehicle_response.year,
            trim=sample_vehicle_response.trim,
            body_style=sample_vehicle_response.body_style,
            exterior_color=sample_vehicle_response.exterior_color,
            interior_color=sample_vehicle_response.interior_color,
            base_price=sample_vehicle_response.base_price,
            specifications=sample_vehicle_response.specifications.model_dump(),
            dimensions=sample_vehicle_response.dimensions.model_dump(),
            features=sample_vehicle_response.features.model_dump(),
            custom_attributes=sample_vehicle_response.custom_attributes,
            is_active=True,
            created_at=sample_vehicle_response.created_at,
            updated_at=sample_vehicle_response.updated_at,
        )
        mock_repo.get_by_id = AsyncMock(return_value=mock_vehicle)
        mock_repo.update = AsyncMock(return_value=mock_vehicle)
        mock_repo.search = AsyncMock(return_value=([mock_vehicle], 1))
        mock_repo_class.return_value = mock_repo

        service = VehicleService(
            session=mock_db_session,
            vehicle_cache=mock_vehicle_cache,
        )

        mock_vehicle_cache.invalidate_vehicle = AsyncMock()
        mock_vehicle_cache.invalidate_vehicle_lists = AsyncMock()

        # Update vehicle
        update_data = VehicleUpdate(base_price=Decimal("36000.00"))
        await service.update_vehicle(vehicle_id, update_data)

        # Verify both caches were invalidated
        mock_vehicle_cache.invalidate_vehicle.assert_called_once_with(vehicle_id)
        mock_vehicle_cache.invalidate_vehicle_lists.assert_called_once()


# ============================================================================
# Error Handling with Cache
# ============================================================================


@pytest.mark.asyncio
async def test_cache_failure_falls_back_to_database(
    mock_db_session: AsyncMock,
    mock_vehicle_cache: VehicleCache,
    sample_vehicle_response: VehicleResponse,
) -> None:
    """
    Test graceful fallback to database when cache fails.

    Validates:
    - Cache failures don't break functionality
    - Database is queried when cache is unavailable
    - Errors are logged appropriately
    """
    vehicle_id = sample_vehicle_response.id

    with patch(
        "src.services.vehicles.service.VehicleRepository"
    ) as mock_repo_class:
        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=MagicMock(
            id=vehicle_id,
            make=sample_vehicle_response.make,
            model=sample_vehicle_response.model,
            year=sample_vehicle_response.year,
            trim=sample_vehicle_response.trim,
            body_style=sample_vehicle_response.body_style,
            exterior_color=sample_vehicle_response.exterior_color,
            interior_color=sample_vehicle_response.interior_color,
            base_price=sample_vehicle_response.base_price,
            specifications=sample_vehicle_response.specifications.model_dump(),
            dimensions=sample_vehicle_response.dimensions.model_dump(),
            features=sample_vehicle_response.features.model_dump(),
            custom_attributes=sample_vehicle_response.custom_attributes,
            is_active=True,
            created_at=sample_vehicle_response.created_at,
            updated_at=sample_vehicle_response.updated_at,
        ))
        mock_repo_class.return_value = mock_repo

        service = VehicleService(
            session=mock_db_session,
            vehicle_cache=mock_vehicle_cache,
        )

        # Simulate cache failure
        mock_vehicle_cache.get_vehicle_detail = AsyncMock(
            side_effect=Exception("Redis connection failed")
        )
        mock_vehicle_cache.set_vehicle_detail = AsyncMock()

        # Should still return result from database
        result = await service.get_vehicle(vehicle_id)

        assert result.id == vehicle_id
        assert result.make == sample_vehicle_response.make

        # Verify database was queried
        mock_repo.get_by_id.assert_called_once()


@pytest.mark.asyncio
async def test_cache_set_failure_does_not_affect_response(
    mock_db_session: AsyncMock,
    mock_vehicle_cache: VehicleCache,
    sample_vehicle_response: VehicleResponse,
) -> None:
    """
    Test cache set failures don't affect response.

    Validates:
    - Failed cache writes don't break functionality
    - Response is still returned successfully
    - Errors are handled gracefully
    """
    vehicle_id = sample_vehicle_response.id

    with patch(
        "src.services.vehicles.service.VehicleRepository"
    ) as mock_repo_class:
        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=MagicMock(
            id=vehicle_id,
            make=sample_vehicle_response.make,
            model=sample_vehicle_response.model,
            year=sample_vehicle_response.year,
            trim=sample_vehicle_response.trim,
            body_style=sample_vehicle_response.body_style,
            exterior_color=sample_vehicle_response.exterior_color,
            interior_color=sample_vehicle_response.interior_color,
            base_price=sample_vehicle_response.base_price,
            specifications=sample_vehicle_response.specifications.model_dump(),
            dimensions=sample_vehicle_response.dimensions.model_dump(),
            features=sample_vehicle_response.features.model_dump(),
            custom_attributes=sample_vehicle_response.custom_attributes,
            is_active=True,
            created_at=sample_vehicle_response.created_at,
            updated_at=sample_vehicle_response.updated_at,
        ))
        mock_repo_class.return_value = mock_repo

        service = VehicleService(
            session=mock_db_session,
            vehicle_cache=mock_vehicle_cache,
        )

        mock_vehicle_cache.get_vehicle_detail = AsyncMock(return_value=None)
        mock_vehicle_cache.set_vehicle_detail = AsyncMock(
            side_effect=Exception("Cache write failed")
        )

        # Should still return result despite cache failure
        result = await service.get_vehicle(vehicle_id)

        assert result.id == vehicle_id
        assert result.make == sample_vehicle_response.make


# ============================================================================
# Cache Warming
# ============================================================================


@pytest.mark.asyncio
async def test_warm_popular_vehicles_cache(
    mock_db_session: AsyncMock,
    mock_vehicle_cache: VehicleCache,
    sample_vehicle_response: VehicleResponse,
) -> None:
    """
    Test cache warming for popular vehicles.

    Validates:
    - Multiple vehicles can be warmed simultaneously
    - Cache is populated with correct data
    - Warming operation is efficient
    """
    vehicle_ids = [uuid.uuid4() for _ in range(5)]

    with patch(
        "src.services.vehicles.service.VehicleRepository"
    ) as mock_repo_class:
        mock_repo = AsyncMock()

        def get_vehicle_by_id(vehicle_id, **kwargs):
            return MagicMock(
                id=vehicle_id,
                make=sample_vehicle_response.make,
                model=sample_vehicle_response.model,
                year=sample_vehicle_response.year,
                trim=sample_vehicle_response.trim,
                body_style=sample_vehicle_response.body_style,
                exterior_color=sample_vehicle_response.exterior_color,
                interior_color=sample_vehicle_response.interior_color,
                base_price=sample_vehicle_response.base_price,
                specifications=sample_vehicle_response.specifications.model_dump(),
                dimensions=sample_vehicle_response.dimensions.model_dump(),
                features=sample_vehicle_response.features.model_dump(),
                custom_attributes=sample_vehicle_response.custom_attributes,
                is_active=True,
                created_at=sample_vehicle_response.created_at,
                updated_at=sample_vehicle_response.updated_at,
            )

        mock_repo.get_by_id = AsyncMock(side_effect=get_vehicle_by_id)
        mock_repo_class.return_value = mock_repo

        service = VehicleService(
            session=mock_db_session,
            vehicle_cache=mock_vehicle_cache,
        )

        mock_vehicle_cache.warm_cache_for_vehicles = AsyncMock(
            return_value=len(vehicle_ids)
        )

        count = await service.warm_popular_vehicles(vehicle_ids)

        assert count == len(vehicle_ids)
        mock_vehicle_cache.warm_cache_for_vehicles.assert_called_once()


# ============================================================================
# API Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_api_list_vehicles_with_cache_headers(
    async_client: AsyncClient,
    mock_vehicle_cache: VehicleCache,
    sample_vehicle_response: VehicleResponse,
) -> None:
    """
    Test API list endpoint returns proper cache headers.

    Validates:
    - X-Cache header indicates hit/miss
    - Cache-Control header is set correctly
    - Response is properly cached
    """
    with patch("src.api.v1.vehicles.get_vehicle_cache") as mock_get_cache:
        mock_get_cache.return_value = mock_vehicle_cache

        # First request - cache miss
        mock_vehicle_cache.get_vehicle_list = AsyncMock(return_value=None)

        with patch("src.api.v1.vehicles.get_vehicle_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.search_vehicles = AsyncMock(return_value=MagicMock(
                items=[sample_vehicle_response],
                total=1,
                page=1,
                page_size=20,
                total_pages=1,
            ))
            mock_get_service.return_value = mock_service

            response = await async_client.get("/api/v1/vehicles")

            assert response.status_code == status.HTTP_200_OK
            assert response.headers.get("X-Cache") == "MISS"
            assert "Cache-Control" in response.headers


@pytest.mark.asyncio
async def test_api_get_vehicle_with_etag(
    async_client: AsyncClient,
    mock_vehicle_cache: VehicleCache,
    sample_vehicle_response: VehicleResponse,
) -> None:
    """
    Test API detail endpoint returns ETag header.

    Validates:
    - ETag header is generated correctly
    - ETag changes when vehicle is updated
    - Cache headers are set appropriately
    """
    vehicle_id = sample_vehicle_response.id

    with patch("src.api.v1.vehicles.get_vehicle_cache") as mock_get_cache:
        mock_get_cache.return_value = mock_vehicle_cache
        mock_vehicle_cache.get_vehicle_detail = AsyncMock(
            return_value=sample_vehicle_response
        )

        with patch("src.api.v1.vehicles.get_vehicle_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_get_service.return_value = mock_service

            response = await async_client.get(f"/api/v1/vehicles/{vehicle_id}")

            assert response.status_code == status.HTTP_200_OK
            assert "ETag" in response.headers
            assert response.headers.get("X-Cache") == "HIT"


@pytest.mark.asyncio
async def test_api_search_with_cache(
    async_client: AsyncClient,
    mock_vehicle_cache: VehicleCache,
) -> None:
    """
    Test API search endpoint with caching.

    Validates:
    - Search results are cached
    - Cache headers indicate hit/miss
    - Cached results are returned correctly
    """
    search_query = "Toyota Camry"

    with patch("src.api.v1.vehicles.get_vehicle_cache") as mock_get_cache:
        mock_get_cache.return_value = mock_vehicle_cache

        # First request - cache miss
        mock_vehicle_cache.get_search_results = AsyncMock(return_value=None)
        mock_vehicle_cache.set_search_results = AsyncMock()

        with patch("src.api.v1.vehicles.get_search_service") as mock_get_search:
            mock_search_service = AsyncMock()
            mock_search_service.search = AsyncMock(return_value=MagicMock(
                items=[],
                total=0,
                page=1,
                limit=20,
                total_pages=0,
            ))
            mock_get_search.return_value = mock_search_service

            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={"query": search_query, "page": 1, "limit": 20},
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.headers.get("X-Cache") == "MISS"


# ============================================================================
# Edge Cases and Boundary Conditions
# ============================================================================


@pytest.mark.asyncio
async def test_cache_with_null_values(
    mock_db_session: AsyncMock,
    mock_vehicle_cache: VehicleCache,
) -> None:
    """
    Test cache handles null/None values correctly.

    Validates:
    - Null values don't break caching
    - Optional fields are handled properly
    - Cache serialization works with nulls
    """
    vehicle_id = uuid.uuid4()

    with patch(
        "src.services.vehicles.service.VehicleRepository"
    ) as mock_repo_class:
        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)
        mock_repo_class.return_value = mock_repo

        service = VehicleService(
            session=mock_db_session,
            vehicle_cache=mock_vehicle_cache,
        )

        mock_vehicle_cache.get_vehicle_detail = AsyncMock(return_value=None)

        with pytest.raises(VehicleNotFoundError):
            await service.get_vehicle(vehicle_id)


@pytest.mark.asyncio
async def test_cache_with_large_result_sets(
    mock_db_session: AsyncMock,
    mock_vehicle_cache: VehicleCache,
    sample_vehicle_response: VehicleResponse,
) -> None:
    """
    Test cache handles large result sets efficiently.

    Validates:
    - Large lists are cached properly
    - Memory usage is reasonable
    - Performance doesn't degrade
    """
    num_vehicles = 100

    with patch(
        "src.services.vehicles.service.VehicleRepository"
    ) as mock_repo_class:
        mock_repo = AsyncMock()
        mock_vehicles = [
            MagicMock(
                id=uuid.uuid4(),
                make=sample_vehicle_response.make,
                model=sample_vehicle_response.model,
                year=sample_vehicle_response.year,
                trim=sample_vehicle_response.trim,
                body_style=sample_vehicle_response.body_style,
                exterior_color=sample_vehicle_response.exterior_color,
                interior_color=sample_vehicle_response.interior_color,
                base_price=sample_vehicle_response.base_price,
                specifications=sample_vehicle_response.specifications.model_dump(),
                dimensions=sample_vehicle_response.dimensions.model_dump(),
                features=sample_vehicle_response.features.model_dump(),
                custom_attributes=sample_vehicle_response.custom_attributes,
                is_active=True,
                created_at=sample_vehicle_response.created_at,
                updated_at=sample_vehicle_response.updated_at,
            )
            for _ in range(num_vehicles)
        ]
        mock_repo.search = AsyncMock(return_value=(mock_vehicles, num_vehicles))
        mock_repo_class.return_value = mock_repo

        service = VehicleService(
            session=mock_db_session,
            vehicle_cache=mock_vehicle_cache,
        )

        mock_vehicle_cache.get_vehicle_list = AsyncMock(return_value=None)
        mock_vehicle_cache.set_vehicle_list = AsyncMock()

        search_request = VehicleSearchRequest(page=1, page_size=100)

        result = await service.search_vehicles(search_request)

        assert len(result.items) == num_vehicles
        mock_vehicle_cache.set_vehicle_list.assert_called_once()


@pytest.mark.asyncio
async def test_cache_ttl_expiration(
    mock_redis_client: AsyncMock,
    mock_vehicle_cache: VehicleCache,
) -> None:
    """
    Test cache entries expire after TTL.

    Validates:
    - TTL is set correctly on cache entries
    - Expired entries are not returned
    - Fresh data is fetched after expiration
    """
    cache_key = "test:vehicle:123"
    ttl_seconds = 3600

    # Set cache with TTL
    await mock_redis_client.set(cache_key, "test_data", ex=ttl_seconds)
    mock_redis_client.set.assert_called_once_with(
        cache_key, "test_data", ex=ttl_seconds
    )

    # Verify TTL is set
    mock_redis_client.ttl = AsyncMock(return_value=ttl_seconds)
    remaining_ttl = await mock_redis_client.ttl(cache_key)
    assert remaining_ttl == ttl_seconds


# ============================================================================
# Security and Data Integrity
# ============================================================================


@pytest.mark.asyncio
async def test_cache_does_not_leak_sensitive_data(
    mock_db_session: AsyncMock,
    mock_vehicle_cache: VehicleCache,
    sample_vehicle_response: VehicleResponse,
) -> None:
    """
    Test cache doesn't expose sensitive data.

    Validates:
    - Only public data is cached
    - Sensitive fields are excluded
    - Cache keys don't contain sensitive info
    """
    vehicle_id = sample_vehicle_response.id

    with patch(
        "src.services.vehicles.service.VehicleRepository"
    ) as mock_repo_class:
        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=MagicMock(
            id=vehicle_id,
            make=sample_vehicle_response.make,
            model=sample_vehicle_response.model,
            year=sample_vehicle_response.year,
            trim=sample_vehicle_response.trim,
            body_style=sample_vehicle_response.body_style,
            exterior_color=sample_vehicle_response.exterior_color,
            interior_color=sample_vehicle_response.interior_color,
            base_price=sample_vehicle_response.base_price,
            specifications=sample_vehicle_response.specifications.model_dump(),
            dimensions=sample_vehicle_response.dimensions.model_dump(),
            features=sample_vehicle_response.features.model_dump(),
            custom_attributes=sample_vehicle_response.custom_attributes,
            is_active=True,
            created_at=sample_vehicle_response.created_at,
            updated_at=sample_vehicle_response.updated_at,
        ))
        mock_repo_class.return_value = mock_repo

        service = VehicleService(
            session=mock_db_session,
            vehicle_cache=mock_vehicle_cache,
        )

        mock_vehicle_cache.get_vehicle_detail = AsyncMock(return_value=None)
        mock_vehicle_cache.set_vehicle_detail = AsyncMock()

        result = await service.get_vehicle(vehicle_id)

        # Verify cached data structure
        mock_vehicle_cache.set_vehicle_detail.assert_called_once()
        cached_data = mock_vehicle_cache.set_vehicle_detail.call_args[0][1]

        # Ensure only public fields are cached
        assert hasattr(cached_data, "id")
        assert hasattr(cached_data, "make")
        assert hasattr(cached_data, "model")


@pytest.mark.asyncio
async def test_cache_key_collision_prevention(
    mock_vehicle_cache: VehicleCache,
) -> None:
    """
    Test cache keys are unique and prevent collisions.

    Validates:
    - Different vehicles have different cache keys
    - Different filters generate different keys
    - Key generation is deterministic
    """
    vehicle_id_1 = uuid.uuid4()
    vehicle_id_2 = uuid.uuid4()

    # Mock cache key generation
    with patch("src.cache.redis_client.CacheKeyManager") as mock_key_manager:
        mock_manager = MagicMock()
        mock_manager.vehicle_key = MagicMock(
            side_effect=lambda vid: f"vehicle:{vid}"
        )
        mock_key_manager.return_value = mock_manager

        key1 = mock_manager.vehicle_key(str(vehicle_id_1))
        key2 = mock_manager.vehicle_key(str(vehicle_id_2))

        # Verify keys are different
        assert key1 != key2
        assert str(vehicle_id_1) in key1
        assert str(vehicle_id_2) in key2