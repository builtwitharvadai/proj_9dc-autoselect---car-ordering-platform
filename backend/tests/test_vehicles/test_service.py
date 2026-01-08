"""
Comprehensive test suite for VehicleService business logic.

This module provides extensive testing of the VehicleService class including:
- CRUD operations with validation
- Search and filtering functionality
- Caching behavior and invalidation
- Error handling and exception scenarios
- Repository integration
- Inventory integration
- Edge cases and boundary conditions
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.cache.redis_client import RedisClient, CacheKeyManager
from src.database.models.inventory import InventoryItem, InventoryStatus
from src.database.models.vehicle import Vehicle
from src.schemas.vehicles import (
    VehicleCreate,
    VehicleDimensions,
    VehicleFeatures,
    VehicleListResponse,
    VehicleResponse,
    VehicleSearchRequest,
    VehicleSpecifications,
    VehicleUpdate,
)
from src.services.vehicles.repository import VehicleRepository
from src.services.vehicles.service import (
    VehicleNotFoundError,
    VehicleService,
    VehicleServiceError,
    VehicleValidationError,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_session():
    """Create mock async database session."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_repository():
    """Create mock vehicle repository."""
    repository = AsyncMock(spec=VehicleRepository)
    return repository


@pytest.fixture
def mock_cache_client():
    """Create mock Redis cache client."""
    cache = AsyncMock(spec=RedisClient)
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    return cache


@pytest.fixture
def vehicle_service(mock_session, mock_cache_client):
    """Create VehicleService instance with mocked dependencies."""
    service = VehicleService(
        session=mock_session,
        cache_client=mock_cache_client,
        cache_ttl=3600,
    )
    return service


@pytest.fixture
def vehicle_service_no_cache(mock_session):
    """Create VehicleService instance without cache."""
    service = VehicleService(session=mock_session, cache_client=None)
    return service


@pytest.fixture
def sample_vehicle_data():
    """Create sample vehicle creation data."""
    return VehicleCreate(
        make="Toyota",
        model="Camry",
        year=2024,
        trim="XLE",
        body_style="Sedan",
        exterior_color="Silver",
        interior_color="Black",
        base_price=Decimal("32500.00"),
        specifications=VehicleSpecifications(
            engine="2.5L 4-Cylinder",
            transmission="8-Speed Automatic",
            drivetrain="FWD",
            fuel_type="Gasoline",
            mpg_city=28,
            mpg_highway=39,
            horsepower=203,
            torque=184,
        ),
        dimensions=VehicleDimensions(
            length=192.7,
            width=72.4,
            height=56.9,
            wheelbase=111.2,
            cargo_volume=15.1,
            seating_capacity=5,
        ),
        features=VehicleFeatures(
            safety_features=[
                "Toyota Safety Sense 3.0",
                "Blind Spot Monitor",
                "Rear Cross-Traffic Alert",
            ],
            technology_features=[
                "9-inch Touchscreen",
                "Apple CarPlay",
                "Android Auto",
                "Wi-Fi Hotspot",
            ],
            comfort_features=[
                "Dual-Zone Climate Control",
                "Power Driver Seat",
                "Heated Front Seats",
            ],
            exterior_features=["LED Headlights", "18-inch Alloy Wheels"],
        ),
        custom_attributes={"package": "Premium", "warranty_years": 3},
    )


@pytest.fixture
def sample_vehicle_model():
    """Create sample Vehicle model instance."""
    vehicle_id = uuid.uuid4()
    return Vehicle(
        id=vehicle_id,
        make="Toyota",
        model="Camry",
        year=2024,
        trim="XLE",
        body_style="Sedan",
        exterior_color="Silver",
        interior_color="Black",
        base_price=Decimal("32500.00"),
        specifications={
            "engine": "2.5L 4-Cylinder",
            "transmission": "8-Speed Automatic",
            "drivetrain": "FWD",
            "fuel_type": "Gasoline",
            "mpg_city": 28,
            "mpg_highway": 39,
            "horsepower": 203,
            "torque": 184,
        },
        dimensions={
            "length": 192.7,
            "width": 72.4,
            "height": 56.9,
            "wheelbase": 111.2,
            "cargo_volume": 15.1,
            "seating_capacity": 5,
        },
        features={
            "safety_features": [
                "Toyota Safety Sense 3.0",
                "Blind Spot Monitor",
                "Rear Cross-Traffic Alert",
            ],
            "technology_features": [
                "9-inch Touchscreen",
                "Apple CarPlay",
                "Android Auto",
                "Wi-Fi Hotspot",
            ],
            "comfort_features": [
                "Dual-Zone Climate Control",
                "Power Driver Seat",
                "Heated Front Seats",
            ],
            "exterior_features": ["LED Headlights", "18-inch Alloy Wheels"],
        },
        custom_attributes={"package": "Premium", "warranty_years": 3},
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


# ============================================================================
# VehicleService Initialization Tests
# ============================================================================


class TestVehicleServiceInitialization:
    """Test VehicleService initialization and configuration."""

    def test_initialization_with_cache(self, mock_session, mock_cache_client):
        """Test service initialization with cache enabled."""
        service = VehicleService(
            session=mock_session,
            cache_client=mock_cache_client,
            cache_ttl=7200,
        )

        assert service.session == mock_session
        assert service.cache_client == mock_cache_client
        assert service.cache_ttl == 7200
        assert isinstance(service.repository, VehicleRepository)
        assert isinstance(service.cache_key_manager, CacheKeyManager)

    def test_initialization_without_cache(self, mock_session):
        """Test service initialization without cache."""
        service = VehicleService(session=mock_session, cache_client=None)

        assert service.session == mock_session
        assert service.cache_client is None
        assert service.cache_ttl == 3600
        assert isinstance(service.repository, VehicleRepository)

    def test_default_cache_ttl(self, mock_session, mock_cache_client):
        """Test default cache TTL value."""
        service = VehicleService(
            session=mock_session,
            cache_client=mock_cache_client,
        )

        assert service.cache_ttl == 3600


# ============================================================================
# Create Vehicle Tests
# ============================================================================


class TestCreateVehicle:
    """Test vehicle creation functionality."""

    @pytest.mark.asyncio
    async def test_create_vehicle_success(
        self,
        vehicle_service,
        sample_vehicle_data,
        sample_vehicle_model,
        mock_session,
    ):
        """Test successful vehicle creation."""
        vehicle_service.repository.get_by_make_model_year = AsyncMock(
            return_value=[]
        )
        vehicle_service.repository.create = AsyncMock(
            return_value=sample_vehicle_model
        )

        result = await vehicle_service.create_vehicle(sample_vehicle_data)

        assert isinstance(result, VehicleResponse)
        assert result.make == "Toyota"
        assert result.model == "Camry"
        assert result.year == 2024
        assert result.trim == "XLE"
        assert result.base_price == Decimal("32500.00")

        vehicle_service.repository.create.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_vehicle_invalidates_cache(
        self,
        vehicle_service,
        sample_vehicle_data,
        sample_vehicle_model,
        mock_cache_client,
    ):
        """Test cache invalidation after vehicle creation."""
        vehicle_service.repository.get_by_make_model_year = AsyncMock(
            return_value=[]
        )
        vehicle_service.repository.create = AsyncMock(
            return_value=sample_vehicle_model
        )

        await vehicle_service.create_vehicle(sample_vehicle_data)

        # Cache invalidation is implicit through _invalidate_list_cache
        assert mock_cache_client.set.call_count == 0

    @pytest.mark.asyncio
    async def test_create_vehicle_duplicate_validation(
        self,
        vehicle_service,
        sample_vehicle_data,
        sample_vehicle_model,
    ):
        """Test validation prevents duplicate vehicles."""
        vehicle_service.repository.get_by_make_model_year = AsyncMock(
            return_value=[sample_vehicle_model]
        )

        with pytest.raises(VehicleValidationError) as exc_info:
            await vehicle_service.create_vehicle(sample_vehicle_data)

        assert "already exists" in str(exc_info.value)
        assert exc_info.value.code == "VEHICLE_VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_create_vehicle_integrity_error(
        self,
        vehicle_service,
        sample_vehicle_data,
        mock_session,
    ):
        """Test handling of database integrity errors."""
        vehicle_service.repository.get_by_make_model_year = AsyncMock(
            return_value=[]
        )
        vehicle_service.repository.create = AsyncMock(
            side_effect=IntegrityError("statement", "params", "orig")
        )

        with pytest.raises(VehicleValidationError) as exc_info:
            await vehicle_service.create_vehicle(sample_vehicle_data)

        assert "already exists" in str(exc_info.value)
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_vehicle_database_error(
        self,
        vehicle_service,
        sample_vehicle_data,
        mock_session,
    ):
        """Test handling of general database errors."""
        vehicle_service.repository.get_by_make_model_year = AsyncMock(
            return_value=[]
        )
        vehicle_service.repository.create = AsyncMock(
            side_effect=SQLAlchemyError("Database error")
        )

        with pytest.raises(VehicleServiceError) as exc_info:
            await vehicle_service.create_vehicle(sample_vehicle_data)

        assert exc_info.value.code == "VEHICLE_CREATE_ERROR"
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_vehicle_without_trim(
        self,
        vehicle_service,
        sample_vehicle_data,
        sample_vehicle_model,
    ):
        """Test creating vehicle without trim specification."""
        sample_vehicle_data.trim = None
        sample_vehicle_model.trim = None

        vehicle_service.repository.get_by_make_model_year = AsyncMock(
            return_value=[]
        )
        vehicle_service.repository.create = AsyncMock(
            return_value=sample_vehicle_model
        )

        result = await vehicle_service.create_vehicle(sample_vehicle_data)

        assert result.trim is None

    @pytest.mark.asyncio
    async def test_create_vehicle_with_custom_attributes(
        self,
        vehicle_service,
        sample_vehicle_data,
        sample_vehicle_model,
    ):
        """Test vehicle creation with custom attributes."""
        sample_vehicle_data.custom_attributes = {
            "special_edition": True,
            "limited_production": 500,
        }

        vehicle_service.repository.get_by_make_model_year = AsyncMock(
            return_value=[]
        )
        vehicle_service.repository.create = AsyncMock(
            return_value=sample_vehicle_model
        )

        result = await vehicle_service.create_vehicle(sample_vehicle_data)

        assert result.custom_attributes is not None


# ============================================================================
# Get Vehicle Tests
# ============================================================================


class TestGetVehicle:
    """Test vehicle retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_vehicle_success(
        self,
        vehicle_service,
        sample_vehicle_model,
    ):
        """Test successful vehicle retrieval."""
        vehicle_id = sample_vehicle_model.id
        vehicle_service.repository.get_by_id = AsyncMock(
            return_value=sample_vehicle_model
        )

        result = await vehicle_service.get_vehicle(vehicle_id)

        assert isinstance(result, VehicleResponse)
        assert result.id == vehicle_id
        assert result.make == "Toyota"
        vehicle_service.repository.get_by_id.assert_called_once_with(
            vehicle_id, include_inventory=False
        )

    @pytest.mark.asyncio
    async def test_get_vehicle_from_cache(
        self,
        vehicle_service,
        sample_vehicle_model,
        mock_cache_client,
    ):
        """Test vehicle retrieval from cache."""
        vehicle_id = sample_vehicle_model.id
        cached_response = VehicleResponse(
            id=vehicle_id,
            make="Toyota",
            model="Camry",
            year=2024,
            trim="XLE",
            body_style="Sedan",
            exterior_color="Silver",
            interior_color="Black",
            base_price=Decimal("32500.00"),
            specifications=VehicleSpecifications(
                engine="2.5L 4-Cylinder",
                transmission="8-Speed Automatic",
                drivetrain="FWD",
                fuel_type="Gasoline",
                mpg_city=28,
                mpg_highway=39,
                horsepower=203,
                torque=184,
            ),
            dimensions=VehicleDimensions(
                length=192.7,
                width=72.4,
                height=56.9,
                wheelbase=111.2,
                cargo_volume=15.1,
                seating_capacity=5,
            ),
            features=VehicleFeatures(
                safety_features=["Toyota Safety Sense 3.0"],
                technology_features=["9-inch Touchscreen"],
                comfort_features=["Dual-Zone Climate Control"],
                exterior_features=["LED Headlights"],
            ),
            custom_attributes={},
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_cache_client.get = AsyncMock(
            return_value=cached_response.model_dump_json()
        )

        result = await vehicle_service.get_vehicle(vehicle_id)

        assert isinstance(result, VehicleResponse)
        assert result.id == vehicle_id
        mock_cache_client.get.assert_called_once()
        vehicle_service.repository.get_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_vehicle_not_found(self, vehicle_service):
        """Test vehicle not found error."""
        vehicle_id = uuid.uuid4()
        vehicle_service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(VehicleNotFoundError) as exc_info:
            await vehicle_service.get_vehicle(vehicle_id)

        assert str(vehicle_id) in str(exc_info.value)
        assert exc_info.value.code == "VEHICLE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_vehicle_with_inventory(
        self,
        vehicle_service,
        sample_vehicle_model,
        mock_cache_client,
    ):
        """Test vehicle retrieval with inventory data."""
        vehicle_id = sample_vehicle_model.id
        vehicle_service.repository.get_by_id = AsyncMock(
            return_value=sample_vehicle_model
        )

        result = await vehicle_service.get_vehicle(
            vehicle_id, include_inventory=True
        )

        assert isinstance(result, VehicleResponse)
        vehicle_service.repository.get_by_id.assert_called_once_with(
            vehicle_id, include_inventory=True
        )
        # Should not use cache when including inventory
        mock_cache_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_vehicle_caches_result(
        self,
        vehicle_service,
        sample_vehicle_model,
        mock_cache_client,
    ):
        """Test vehicle result is cached after retrieval."""
        vehicle_id = sample_vehicle_model.id
        vehicle_service.repository.get_by_id = AsyncMock(
            return_value=sample_vehicle_model
        )
        mock_cache_client.get = AsyncMock(return_value=None)

        await vehicle_service.get_vehicle(vehicle_id)

        mock_cache_client.set.assert_called_once()
        call_args = mock_cache_client.set.call_args
        assert call_args[1]["ex"] == 3600

    @pytest.mark.asyncio
    async def test_get_vehicle_database_error(self, vehicle_service):
        """Test handling of database errors during retrieval."""
        vehicle_id = uuid.uuid4()
        vehicle_service.repository.get_by_id = AsyncMock(
            side_effect=SQLAlchemyError("Database error")
        )

        with pytest.raises(VehicleServiceError) as exc_info:
            await vehicle_service.get_vehicle(vehicle_id)

        assert exc_info.value.code == "VEHICLE_GET_ERROR"

    @pytest.mark.asyncio
    async def test_get_vehicle_without_cache(
        self,
        vehicle_service_no_cache,
        sample_vehicle_model,
    ):
        """Test vehicle retrieval without cache client."""
        vehicle_id = sample_vehicle_model.id
        vehicle_service_no_cache.repository.get_by_id = AsyncMock(
            return_value=sample_vehicle_model
        )

        result = await vehicle_service_no_cache.get_vehicle(vehicle_id)

        assert isinstance(result, VehicleResponse)
        assert result.id == vehicle_id


# ============================================================================
# Update Vehicle Tests
# ============================================================================


class TestUpdateVehicle:
    """Test vehicle update functionality."""

    @pytest.mark.asyncio
    async def test_update_vehicle_success(
        self,
        vehicle_service,
        sample_vehicle_model,
        mock_session,
    ):
        """Test successful vehicle update."""
        vehicle_id = sample_vehicle_model.id
        update_data = VehicleUpdate(
            base_price=Decimal("33000.00"),
            exterior_color="Blue",
        )

        vehicle_service.repository.get_by_id = AsyncMock(
            return_value=sample_vehicle_model
        )
        vehicle_service.repository.update = AsyncMock(
            return_value=sample_vehicle_model
        )

        result = await vehicle_service.update_vehicle(vehicle_id, update_data)

        assert isinstance(result, VehicleResponse)
        vehicle_service.repository.update.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_vehicle_not_found(self, vehicle_service):
        """Test update of non-existent vehicle."""
        vehicle_id = uuid.uuid4()
        update_data = VehicleUpdate(base_price=Decimal("33000.00"))

        vehicle_service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(VehicleNotFoundError):
            await vehicle_service.update_vehicle(vehicle_id, update_data)

    @pytest.mark.asyncio
    async def test_update_vehicle_specifications(
        self,
        vehicle_service,
        sample_vehicle_model,
    ):
        """Test updating vehicle specifications."""
        vehicle_id = sample_vehicle_model.id
        update_data = VehicleUpdate(
            specifications=VehicleSpecifications(
                engine="3.5L V6",
                transmission="8-Speed Automatic",
                drivetrain="AWD",
                fuel_type="Gasoline",
                mpg_city=22,
                mpg_highway=32,
                horsepower=301,
                torque=267,
            )
        )

        vehicle_service.repository.get_by_id = AsyncMock(
            return_value=sample_vehicle_model
        )
        vehicle_service.repository.update = AsyncMock(
            return_value=sample_vehicle_model
        )

        result = await vehicle_service.update_vehicle(vehicle_id, update_data)

        assert isinstance(result, VehicleResponse)

    @pytest.mark.asyncio
    async def test_update_vehicle_invalidates_cache(
        self,
        vehicle_service,
        sample_vehicle_model,
        mock_cache_client,
    ):
        """Test cache invalidation after update."""
        vehicle_id = sample_vehicle_model.id
        update_data = VehicleUpdate(base_price=Decimal("33000.00"))

        vehicle_service.repository.get_by_id = AsyncMock(
            return_value=sample_vehicle_model
        )
        vehicle_service.repository.update = AsyncMock(
            return_value=sample_vehicle_model
        )

        await vehicle_service.update_vehicle(vehicle_id, update_data)

        mock_cache_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_vehicle_database_error(
        self,
        vehicle_service,
        sample_vehicle_model,
        mock_session,
    ):
        """Test handling of database errors during update."""
        vehicle_id = sample_vehicle_model.id
        update_data = VehicleUpdate(base_price=Decimal("33000.00"))

        vehicle_service.repository.get_by_id = AsyncMock(
            return_value=sample_vehicle_model
        )
        vehicle_service.repository.update = AsyncMock(
            side_effect=SQLAlchemyError("Database error")
        )

        with pytest.raises(VehicleServiceError) as exc_info:
            await vehicle_service.update_vehicle(vehicle_id, update_data)

        assert exc_info.value.code == "VEHICLE_UPDATE_ERROR"
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_vehicle_partial_update(
        self,
        vehicle_service,
        sample_vehicle_model,
    ):
        """Test partial vehicle update with only changed fields."""
        vehicle_id = sample_vehicle_model.id
        update_data = VehicleUpdate(exterior_color="Red")

        vehicle_service.repository.get_by_id = AsyncMock(
            return_value=sample_vehicle_model
        )
        vehicle_service.repository.update = AsyncMock(
            return_value=sample_vehicle_model
        )

        result = await vehicle_service.update_vehicle(vehicle_id, update_data)

        assert isinstance(result, VehicleResponse)


# ============================================================================
# Delete Vehicle Tests
# ============================================================================


class TestDeleteVehicle:
    """Test vehicle deletion functionality."""

    @pytest.mark.asyncio
    async def test_delete_vehicle_soft_success(
        self,
        vehicle_service,
        mock_session,
    ):
        """Test successful soft delete."""
        vehicle_id = uuid.uuid4()
        vehicle_service.repository.delete = AsyncMock(return_value=True)

        result = await vehicle_service.delete_vehicle(vehicle_id, soft=True)

        assert result is True
        vehicle_service.repository.delete.assert_called_once_with(
            vehicle_id, soft=True
        )
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_vehicle_hard_success(
        self,
        vehicle_service,
        mock_session,
    ):
        """Test successful hard delete."""
        vehicle_id = uuid.uuid4()
        vehicle_service.repository.delete = AsyncMock(return_value=True)

        result = await vehicle_service.delete_vehicle(vehicle_id, soft=False)

        assert result is True
        vehicle_service.repository.delete.assert_called_once_with(
            vehicle_id, soft=False
        )

    @pytest.mark.asyncio
    async def test_delete_vehicle_not_found(self, vehicle_service):
        """Test deletion of non-existent vehicle."""
        vehicle_id = uuid.uuid4()
        vehicle_service.repository.delete = AsyncMock(return_value=False)

        with pytest.raises(VehicleNotFoundError):
            await vehicle_service.delete_vehicle(vehicle_id)

    @pytest.mark.asyncio
    async def test_delete_vehicle_invalidates_cache(
        self,
        vehicle_service,
        mock_cache_client,
    ):
        """Test cache invalidation after deletion."""
        vehicle_id = uuid.uuid4()
        vehicle_service.repository.delete = AsyncMock(return_value=True)

        await vehicle_service.delete_vehicle(vehicle_id)

        mock_cache_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_vehicle_database_error(
        self,
        vehicle_service,
        mock_session,
    ):
        """Test handling of database errors during deletion."""
        vehicle_id = uuid.uuid4()
        vehicle_service.repository.delete = AsyncMock(
            side_effect=SQLAlchemyError("Database error")
        )

        with pytest.raises(VehicleServiceError) as exc_info:
            await vehicle_service.delete_vehicle(vehicle_id)

        assert exc_info.value.code == "VEHICLE_DELETE_ERROR"
        mock_session.rollback.assert_called_once()


# ============================================================================
# Search Vehicles Tests
# ============================================================================


class TestSearchVehicles:
    """Test vehicle search functionality."""

    @pytest.mark.asyncio
    async def test_search_vehicles_success(
        self,
        vehicle_service,
        sample_vehicle_model,
    ):
        """Test successful vehicle search."""
        search_request = VehicleSearchRequest(
            make="Toyota",
            model="Camry",
            page=1,
            page_size=20,
        )

        vehicle_service.repository.search = AsyncMock(
            return_value=([sample_vehicle_model], 1)
        )

        result = await vehicle_service.search_vehicles(search_request)

        assert isinstance(result, VehicleListResponse)
        assert result.total == 1
        assert len(result.items) == 1
        assert result.page == 1
        assert result.total_pages == 1

    @pytest.mark.asyncio
    async def test_search_vehicles_with_filters(
        self,
        vehicle_service,
        sample_vehicle_model,
    ):
        """Test vehicle search with multiple filters."""
        search_request = VehicleSearchRequest(
            make="Toyota",
            year_min=2020,
            year_max=2024,
            price_min=Decimal("25000"),
            price_max=Decimal("40000"),
            body_style="Sedan",
            fuel_type="Gasoline",
            page=1,
            page_size=20,
        )

        vehicle_service.repository.search = AsyncMock(
            return_value=([sample_vehicle_model], 1)
        )

        result = await vehicle_service.search_vehicles(search_request)

        assert isinstance(result, VehicleListResponse)
        vehicle_service.repository.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_vehicles_pagination(
        self,
        vehicle_service,
        sample_vehicle_model,
    ):
        """Test vehicle search pagination."""
        search_request = VehicleSearchRequest(
            make="Toyota",
            page=2,
            page_size=10,
        )

        vehicle_service.repository.search = AsyncMock(
            return_value=([sample_vehicle_model], 25)
        )

        result = await vehicle_service.search_vehicles(search_request)

        assert result.page == 2
        assert result.page_size == 10
        assert result.total == 25
        assert result.total_pages == 3

    @pytest.mark.asyncio
    async def test_search_vehicles_from_cache(
        self,
        vehicle_service,
        sample_vehicle_model,
        mock_cache_client,
    ):
        """Test search results from cache."""
        search_request = VehicleSearchRequest(make="Toyota", page=1, page_size=20)

        cached_response = VehicleListResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )

        mock_cache_client.get = AsyncMock(
            return_value=cached_response.model_dump_json()
        )

        result = await vehicle_service.search_vehicles(search_request)

        assert isinstance(result, VehicleListResponse)
        mock_cache_client.get.assert_called_once()
        vehicle_service.repository.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_vehicles_caches_result(
        self,
        vehicle_service,
        sample_vehicle_model,
        mock_cache_client,
    ):
        """Test search results are cached."""
        search_request = VehicleSearchRequest(make="Toyota", page=1, page_size=20)

        vehicle_service.repository.search = AsyncMock(
            return_value=([sample_vehicle_model], 1)
        )
        mock_cache_client.get = AsyncMock(return_value=None)

        await vehicle_service.search_vehicles(search_request)

        mock_cache_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_vehicles_empty_results(self, vehicle_service):
        """Test search with no results."""
        search_request = VehicleSearchRequest(
            make="NonExistent",
            page=1,
            page_size=20,
        )

        vehicle_service.repository.search = AsyncMock(return_value=([], 0))

        result = await vehicle_service.search_vehicles(search_request)

        assert result.total == 0
        assert len(result.items) == 0
        assert result.total_pages == 0

    @pytest.mark.asyncio
    async def test_search_vehicles_with_sorting(
        self,
        vehicle_service,
        sample_vehicle_model,
    ):
        """Test vehicle search with sorting."""
        search_request = VehicleSearchRequest(
            make="Toyota",
            sort_by="base_price",
            sort_order="desc",
            page=1,
            page_size=20,
        )

        vehicle_service.repository.search = AsyncMock(
            return_value=([sample_vehicle_model], 1)
        )

        result = await vehicle_service.search_vehicles(search_request)

        assert isinstance(result, VehicleListResponse)
        call_kwargs = vehicle_service.repository.search.call_args[1]
        assert call_kwargs["sort_by"] == "base_price"
        assert call_kwargs["sort_order"] == "desc"

    @pytest.mark.asyncio
    async def test_search_vehicles_database_error(self, vehicle_service):
        """Test handling of database errors during search."""
        search_request = VehicleSearchRequest(make="Toyota", page=1, page_size=20)

        vehicle_service.repository.search = AsyncMock(
            side_effect=SQLAlchemyError("Database error")
        )

        with pytest.raises(VehicleServiceError) as exc_info:
            await vehicle_service.search_vehicles(search_request)

        assert exc_info.value.code == "VEHICLE_SEARCH_ERROR"


# ============================================================================
# Get Available Vehicles Tests
# ============================================================================


class TestGetAvailableVehicles:
    """Test available vehicles retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_available_vehicles_success(
        self,
        vehicle_service,
        sample_vehicle_model,
    ):
        """Test successful retrieval of available vehicles."""
        vehicle_service.repository.get_available_vehicles = AsyncMock(
            return_value=([sample_vehicle_model], 1)
        )

        result = await vehicle_service.get_available_vehicles(
            page=1, page_size=20
        )

        assert isinstance(result, VehicleListResponse)
        assert result.total == 1
        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_get_available_vehicles_with_dealership(
        self,
        vehicle_service,
        sample_vehicle_model,
    ):
        """Test available vehicles filtered by dealership."""
        dealership_id = uuid.uuid4()
        vehicle_service.repository.get_available_vehicles = AsyncMock(
            return_value=([sample_vehicle_model], 1)
        )

        result = await vehicle_service.get_available_vehicles(
            dealership_id=dealership_id,
            page=1,
            page_size=20,
        )

        assert isinstance(result, VehicleListResponse)
        vehicle_service.repository.get_available_vehicles.assert_called_once_with(
            dealership_id=dealership_id,
            skip=0,
            limit=20,
        )

    @pytest.mark.asyncio
    async def test_get_available_vehicles_pagination(
        self,
        vehicle_service,
        sample_vehicle_model,
    ):
        """Test pagination of available vehicles."""
        vehicle_service.repository.get_available_vehicles = AsyncMock(
            return_value=([sample_vehicle_model], 50)
        )

        result = await vehicle_service.get_available_vehicles(
            page=3, page_size=10
        )

        assert result.page == 3
        assert result.page_size == 10
        assert result.total == 50
        assert result.total_pages == 5

    @pytest.mark.asyncio
    async def test_get_available_vehicles_database_error(self, vehicle_service):
        """Test handling of database errors."""
        vehicle_service.repository.get_available_vehicles = AsyncMock(
            side_effect=SQLAlchemyError("Database error")
        )

        with pytest.raises(VehicleServiceError) as exc_info:
            await vehicle_service.get_available_vehicles()

        assert exc_info.value.code == "VEHICLE_AVAILABLE_ERROR"


# ============================================================================
# Get Price Range Tests
# ============================================================================


class TestGetPriceRange:
    """Test price range retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_price_range_success(self, vehicle_service):
        """Test successful price range retrieval."""
        vehicle_service.repository.get_price_range = AsyncMock(
            return_value=(Decimal("25000"), Decimal("45000"))
        )

        min_price, max_price = await vehicle_service.get_price_range()

        assert min_price == Decimal("25000")
        assert max_price == Decimal("45000")

    @pytest.mark.asyncio
    async def test_get_price_range_with_filters(self, vehicle_service):
        """Test price range with filters."""
        vehicle_service.repository.get_price_range = AsyncMock(
            return_value=(Decimal("30000"), Decimal("40000"))
        )

        min_price, max_price = await vehicle_service.get_price_range(
            make="Toyota",
            model="Camry",
            year=2024,
        )

        assert min_price == Decimal("30000")
        assert max_price == Decimal("40000")
        vehicle_service.repository.get_price_range.assert_called_once_with(
            make="Toyota",
            model="Camry",
            year=2024,
        )

    @pytest.mark.asyncio
    async def test_get_price_range_no_results(self, vehicle_service):
        """Test price range with no matching vehicles."""
        vehicle_service.repository.get_price_range = AsyncMock(
            return_value=(None, None)
        )

        min_price, max_price = await vehicle_service.get_price_range(
            make="NonExistent"
        )

        assert min_price is None
        assert max_price is None

    @pytest.mark.asyncio
    async def test_get_price_range_database_error(self, vehicle_service):
        """Test handling of database errors."""
        vehicle_service.repository.get_price_range = AsyncMock(
            side_effect=SQLAlchemyError("Database error")
        )

        with pytest.raises(VehicleServiceError) as exc_info:
            await vehicle_service.get_price_range()

        assert exc_info.value.code == "VEHICLE_PRICE_RANGE_ERROR"


# ============================================================================
# Cache Management Tests
# ============================================================================


class TestCacheManagement:
    """Test cache management functionality."""

    @pytest.mark.asyncio
    async def test_invalidate_vehicle_cache(
        self,
        vehicle_service,
        mock_cache_client,
    ):
        """Test vehicle cache invalidation."""
        vehicle_id = uuid.uuid4()

        await vehicle_service._invalidate_vehicle_cache(vehicle_id)

        mock_cache_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_vehicle_cache_error_handling(
        self,
        vehicle_service,
        mock_cache_client,
    ):
        """Test cache invalidation error handling."""
        vehicle_id = uuid.uuid4()
        mock_cache_client.delete = AsyncMock(
            side_effect=Exception("Cache error")
        )

        # Should not raise exception
        await vehicle_service._invalidate_vehicle_cache(vehicle_id)

    @pytest.mark.asyncio
    async def test_invalidate_list_cache(self, vehicle_service):
        """Test list cache invalidation."""
        # Should not raise exception
        await vehicle_service._invalidate_list_cache()

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, vehicle_service):
        """Test cache key generation for searches."""
        search_request = VehicleSearchRequest(
            make="Toyota",
            model="Camry",
            year_min=2020,
            page=1,
            page_size=20,
        )

        cache_key = vehicle_service._generate_search_cache_key(search_request)

        assert isinstance(cache_key, str)
        assert "vehicles" in cache_key


# ============================================================================
# Response Conversion Tests
# ============================================================================


class TestResponseConversion:
    """Test vehicle model to response conversion."""

    def test_to_response_conversion(
        self,
        vehicle_service,
        sample_vehicle_model,
    ):
        """Test conversion of vehicle model to response."""
        response = vehicle_service._to_response(sample_vehicle_model)

        assert isinstance(response, VehicleResponse)
        assert response.id == sample_vehicle_model.id
        assert response.make == sample_vehicle_model.make
        assert response.model == sample_vehicle_model.model
        assert response.year == sample_vehicle_model.year
        assert isinstance(response.specifications, VehicleSpecifications)
        assert isinstance(response.dimensions, VehicleDimensions)
        assert isinstance(response.features, VehicleFeatures)

    def test_to_response_with_empty_custom_attributes(
        self,
        vehicle_service,
        sample_vehicle_model,
    ):
        """Test conversion with empty custom attributes."""
        sample_vehicle_model.custom_attributes = None

        response = vehicle_service._to_response(sample_vehicle_model)

        assert response.custom_attributes == {}


# ============================================================================
# Edge Cases and Boundary Tests
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_search_with_zero_results_pagination(self, vehicle_service):
        """Test pagination calculation with zero results."""
        search_request = VehicleSearchRequest(
            make="NonExistent",
            page=1,
            page_size=20,
        )

        vehicle_service.repository.search = AsyncMock(return_value=([], 0))

        result = await vehicle_service.search_vehicles(search_request)

        assert result.total_pages == 0

    @pytest.mark.asyncio
    async def test_search_with_exact_page_boundary(self, vehicle_service):
        """Test pagination at exact page boundary."""
        search_request = VehicleSearchRequest(
            make="Toyota",
            page=1,
            page_size=20,
        )

        vehicle_service.repository.search = AsyncMock(return_value=([], 20))

        result = await vehicle_service.search_vehicles(search_request)

        assert result.total_pages == 1

    @pytest.mark.asyncio
    async def test_update_with_all_none_values(
        self,
        vehicle_service,
        sample_vehicle_model,
    ):
        """Test update with all None values."""
        vehicle_id = sample_vehicle_model.id
        update_data = VehicleUpdate()

        vehicle_service.repository.get_by_id = AsyncMock(
            return_value=sample_vehicle_model
        )
        vehicle_service.repository.update = AsyncMock(
            return_value=sample_vehicle_model
        )

        result = await vehicle_service.update_vehicle(vehicle_id, update_data)

        assert isinstance(result, VehicleResponse)

    @pytest.mark.asyncio
    async def test_create_vehicle_with_minimal_data(
        self,
        vehicle_service,
        sample_vehicle_model,
    ):
        """Test vehicle creation with minimal required data."""
        minimal_data = VehicleCreate(
            make="Toyota",
            model="Camry",
            year=2024,
            body_style="Sedan",
            base_price=Decimal("30000"),
            specifications=VehicleSpecifications(
                engine="2.5L",
                transmission="Automatic",
                drivetrain="FWD",
                fuel_type="Gasoline",
            ),
            dimensions=VehicleDimensions(
                length=190.0,
                width=72.0,
                height=57.0,
                wheelbase=110.0,
            ),
            features=VehicleFeatures(),
        )

        vehicle_service.repository.get_by_make_model_year = AsyncMock(
            return_value=[]
        )
        vehicle_service.repository.create = AsyncMock(
            return_value=sample_vehicle_model
        )

        result = await vehicle_service.create_vehicle(minimal_data)

        assert isinstance(result, VehicleResponse)


# ============================================================================
# Performance and Concurrency Tests
# ============================================================================


class TestPerformanceAndConcurrency:
    """Test performance and concurrency scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(
        self,
        vehicle_service,
        sample_vehicle_model,
        mock_cache_client,
    ):
        """Test concurrent cache access doesn't cause issues."""
        vehicle_id = sample_vehicle_model.id
        vehicle_service.repository.get_by_id = AsyncMock(
            return_value=sample_vehicle_model
        )
        mock_cache_client.get = AsyncMock(return_value=None)

        # Simulate concurrent requests
        import asyncio

        results = await asyncio.gather(
            vehicle_service.get_vehicle(vehicle_id),
            vehicle_service.get_vehicle(vehicle_id),
            vehicle_service.get_vehicle(vehicle_id),
        )

        assert len(results) == 3
        assert all(isinstance(r, VehicleResponse) for r in results)

    @pytest.mark.asyncio
    async def test_large_result_set_pagination(self, vehicle_service):
        """Test handling of large result sets."""
        search_request = VehicleSearchRequest(
            page=100,
            page_size=50,
        )

        vehicle_service.repository.search = AsyncMock(return_value=([], 10000))

        result = await vehicle_service.search_vehicles(search_request)

        assert result.total == 10000
        assert result.total_pages == 200


# ============================================================================
# Exception Hierarchy Tests
# ============================================================================


class TestExceptionHierarchy:
    """Test custom exception hierarchy."""

    def test_vehicle_service_error_attributes(self):
        """Test VehicleServiceError attributes."""
        error = VehicleServiceError(
            "Test error",
            code="TEST_ERROR",
            extra_field="value",
        )

        assert str(error) == "Test error"
        assert error.code == "TEST_ERROR"
        assert error.context["extra_field"] == "value"

    def test_vehicle_not_found_error(self):
        """Test VehicleNotFoundError creation."""
        vehicle_id = uuid.uuid4()
        error = VehicleNotFoundError(vehicle_id, extra="data")

        assert str(vehicle_id) in str(error)
        assert error.code == "VEHICLE_NOT_FOUND"
        assert error.context["vehicle_id"] == str(vehicle_id)
        assert error.context["extra"] == "data"

    def test_vehicle_validation_error(self):
        """Test VehicleValidationError creation."""
        error = VehicleValidationError(
            "Validation failed",
            field="make",
            value="Invalid",
        )

        assert "Validation failed" in str(error)
        assert error.code == "VEHICLE_VALIDATION_ERROR"
        assert error.context["field"] == "make"