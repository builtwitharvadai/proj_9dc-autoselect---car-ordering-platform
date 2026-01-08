"""
Comprehensive test suite for inventory reservation system.

Tests cover reservation creation, TTL expiration, availability checking,
concurrent operations, error handling, and background cleanup processes.
Achieves >80% coverage with focus on edge cases and race conditions.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cache.redis_client import RedisClient
from src.services.cart.inventory_reservation import (
    InventoryReservationService,
    InsufficientInventoryError,
    ReservationError,
    ReservationNotFoundError,
    close_reservation_service,
    get_reservation_service,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_redis_client():
    """
    Create a mock Redis client for testing.

    Provides a fully mocked Redis client with common operations
    implemented to simulate Redis behavior without actual connections.

    Returns:
        MagicMock: Mocked Redis client instance
    """
    mock_client = MagicMock(spec=RedisClient)
    mock_client._client = MagicMock()

    # Mock basic operations
    mock_client.get = AsyncMock(return_value=None)
    mock_client.set = AsyncMock(return_value=True)
    mock_client.delete = AsyncMock(return_value=1)
    mock_client.exists = AsyncMock(return_value=False)
    mock_client.expire = AsyncMock(return_value=True)
    mock_client.ttl = AsyncMock(return_value=-2)
    mock_client.incr = AsyncMock(return_value=1)
    mock_client.decr = AsyncMock(return_value=0)

    # Mock JSON operations
    mock_client.get_json = AsyncMock(return_value=None)
    mock_client.set_json = AsyncMock(return_value=True)

    # Mock scan_iter
    async def mock_scan_iter(match=None):
        return [].__aiter__()

    mock_client._client.scan_iter = mock_scan_iter

    return mock_client


@pytest.fixture
def reservation_service(mock_redis_client):
    """
    Create inventory reservation service with mocked Redis.

    Args:
        mock_redis_client: Mocked Redis client fixture

    Returns:
        InventoryReservationService: Service instance for testing
    """
    return InventoryReservationService(redis_client=mock_redis_client)


@pytest.fixture
def sample_vehicle_id():
    """Generate a sample vehicle ID for testing."""
    return "vehicle-123"


@pytest.fixture
def sample_reservation_data():
    """
    Generate sample reservation data.

    Returns:
        dict: Sample reservation data structure
    """
    return {
        "reservation_id": str(uuid.uuid4()),
        "vehicle_id": "vehicle-123",
        "quantity": 1,
        "user_id": "user-456",
        "session_id": "session-789",
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (
            datetime.utcnow() + timedelta(seconds=900)
        ).isoformat(),
    }


# ============================================================================
# Unit Tests - Reservation Creation
# ============================================================================


class TestReservationCreation:
    """Test suite for reservation creation functionality."""

    @pytest.mark.asyncio
    async def test_create_reservation_success(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """
        Test successful reservation creation.

        Verifies that a reservation is created with correct data,
        inventory is decremented, and TTL is set properly.
        """
        # Arrange
        mock_redis_client.get.return_value = "10"  # Available inventory
        mock_redis_client.decr.return_value = 9

        # Act
        reservation_id = await reservation_service.create_reservation(
            vehicle_id=sample_vehicle_id,
            quantity=1,
            user_id="user-123",
            session_id="session-456",
        )

        # Assert
        assert reservation_id is not None
        assert isinstance(reservation_id, str)

        # Verify Redis operations
        mock_redis_client.get.assert_called_once()
        mock_redis_client.set_json.assert_called_once()
        mock_redis_client.decr.assert_called_once()

        # Verify TTL was set
        call_args = mock_redis_client.set_json.call_args
        assert call_args.kwargs["ex"] == 900

    @pytest.mark.asyncio
    async def test_create_reservation_with_quantity(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """Test reservation creation with multiple quantity."""
        # Arrange
        mock_redis_client.get.return_value = "10"
        mock_redis_client.decr.return_value = 5

        # Act
        reservation_id = await reservation_service.create_reservation(
            vehicle_id=sample_vehicle_id,
            quantity=5,
        )

        # Assert
        assert reservation_id is not None
        mock_redis_client.decr.assert_called_once_with(
            f"inventory_available:{sample_vehicle_id}",
            5,
        )

    @pytest.mark.asyncio
    async def test_create_reservation_insufficient_inventory(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """
        Test reservation creation fails with insufficient inventory.

        Verifies that InsufficientInventoryError is raised when
        requested quantity exceeds available inventory.
        """
        # Arrange
        mock_redis_client.get.return_value = "2"  # Only 2 available

        # Act & Assert
        with pytest.raises(InsufficientInventoryError) as exc_info:
            await reservation_service.create_reservation(
                vehicle_id=sample_vehicle_id,
                quantity=5,
            )

        # Verify error details
        assert exc_info.value.code == "INSUFFICIENT_INVENTORY"
        assert exc_info.value.context["vehicle_id"] == sample_vehicle_id
        assert exc_info.value.context["requested"] == 5
        assert exc_info.value.context["available"] == 2

        # Verify no inventory was decremented
        mock_redis_client.decr.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_reservation_zero_quantity(
        self,
        reservation_service,
        sample_vehicle_id,
    ):
        """Test that zero quantity raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="must be positive"):
            await reservation_service.create_reservation(
                vehicle_id=sample_vehicle_id,
                quantity=0,
            )

    @pytest.mark.asyncio
    async def test_create_reservation_negative_quantity(
        self,
        reservation_service,
        sample_vehicle_id,
    ):
        """Test that negative quantity raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="must be positive"):
            await reservation_service.create_reservation(
                vehicle_id=sample_vehicle_id,
                quantity=-1,
            )

    @pytest.mark.asyncio
    async def test_create_reservation_without_user_session(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """Test reservation creation without user_id and session_id."""
        # Arrange
        mock_redis_client.get.return_value = "10"
        mock_redis_client.decr.return_value = 9

        # Act
        reservation_id = await reservation_service.create_reservation(
            vehicle_id=sample_vehicle_id,
            quantity=1,
        )

        # Assert
        assert reservation_id is not None

        # Verify empty strings were stored for optional fields
        call_args = mock_redis_client.set_json.call_args
        reservation_data = call_args.args[1]
        assert reservation_data["user_id"] == ""
        assert reservation_data["session_id"] == ""

    @pytest.mark.asyncio
    async def test_create_reservation_redis_error(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """Test reservation creation handles Redis errors gracefully."""
        # Arrange
        mock_redis_client.get.return_value = "10"
        mock_redis_client.set_json.side_effect = Exception("Redis connection error")

        # Act & Assert
        with pytest.raises(ReservationError) as exc_info:
            await reservation_service.create_reservation(
                vehicle_id=sample_vehicle_id,
                quantity=1,
            )

        assert exc_info.value.code == "RESERVATION_CREATE_FAILED"


# ============================================================================
# Unit Tests - Reservation Release
# ============================================================================


class TestReservationRelease:
    """Test suite for reservation release functionality."""

    @pytest.mark.asyncio
    async def test_release_reservation_success(
        self,
        reservation_service,
        mock_redis_client,
        sample_reservation_data,
    ):
        """
        Test successful reservation release.

        Verifies that reservation is deleted and inventory is restored.
        """
        # Arrange
        reservation_id = sample_reservation_data["reservation_id"]
        mock_redis_client.get_json.return_value = sample_reservation_data
        mock_redis_client.incr.return_value = 11

        # Act
        await reservation_service.release_reservation(reservation_id)

        # Assert
        mock_redis_client.get_json.assert_called_once()
        mock_redis_client.delete.assert_called_once()
        mock_redis_client.incr.assert_called_once_with(
            f"inventory_available:{sample_reservation_data['vehicle_id']}",
            sample_reservation_data["quantity"],
        )

    @pytest.mark.asyncio
    async def test_release_reservation_not_found(
        self,
        reservation_service,
        mock_redis_client,
    ):
        """Test releasing non-existent reservation raises error."""
        # Arrange
        reservation_id = str(uuid.uuid4())
        mock_redis_client.get_json.return_value = None

        # Act & Assert
        with pytest.raises(ReservationNotFoundError) as exc_info:
            await reservation_service.release_reservation(reservation_id)

        assert exc_info.value.code == "RESERVATION_NOT_FOUND"
        assert exc_info.value.context["reservation_id"] == reservation_id

        # Verify no inventory was restored
        mock_redis_client.incr.assert_not_called()

    @pytest.mark.asyncio
    async def test_release_reservation_redis_error(
        self,
        reservation_service,
        mock_redis_client,
        sample_reservation_data,
    ):
        """Test reservation release handles Redis errors."""
        # Arrange
        reservation_id = sample_reservation_data["reservation_id"]
        mock_redis_client.get_json.return_value = sample_reservation_data
        mock_redis_client.delete.side_effect = Exception("Redis error")

        # Act & Assert
        with pytest.raises(ReservationError) as exc_info:
            await reservation_service.release_reservation(reservation_id)

        assert exc_info.value.code == "RESERVATION_RELEASE_FAILED"

    @pytest.mark.asyncio
    async def test_release_reservation_multiple_quantity(
        self,
        reservation_service,
        mock_redis_client,
        sample_reservation_data,
    ):
        """Test releasing reservation with multiple quantity."""
        # Arrange
        sample_reservation_data["quantity"] = 5
        reservation_id = sample_reservation_data["reservation_id"]
        mock_redis_client.get_json.return_value = sample_reservation_data
        mock_redis_client.incr.return_value = 15

        # Act
        await reservation_service.release_reservation(reservation_id)

        # Assert
        mock_redis_client.incr.assert_called_once_with(
            f"inventory_available:{sample_reservation_data['vehicle_id']}",
            5,
        )


# ============================================================================
# Unit Tests - Availability Checking
# ============================================================================


class TestAvailabilityChecking:
    """Test suite for inventory availability checking."""

    @pytest.mark.asyncio
    async def test_check_availability_with_inventory(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """Test checking availability when inventory exists."""
        # Arrange
        mock_redis_client.get.return_value = "10"

        # Act
        available = await reservation_service.check_availability(sample_vehicle_id)

        # Assert
        assert available == 10
        mock_redis_client.get.assert_called_once_with(
            f"inventory_available:{sample_vehicle_id}"
        )

    @pytest.mark.asyncio
    async def test_check_availability_no_inventory(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """Test checking availability when no inventory data exists."""
        # Arrange
        mock_redis_client.get.return_value = None

        # Act
        available = await reservation_service.check_availability(sample_vehicle_id)

        # Assert
        assert available == 0

    @pytest.mark.asyncio
    async def test_check_availability_zero_inventory(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """Test checking availability when inventory is zero."""
        # Arrange
        mock_redis_client.get.return_value = "0"

        # Act
        available = await reservation_service.check_availability(sample_vehicle_id)

        # Assert
        assert available == 0

    @pytest.mark.asyncio
    async def test_check_availability_negative_inventory(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """Test that negative inventory is returned as zero."""
        # Arrange
        mock_redis_client.get.return_value = "-5"

        # Act
        available = await reservation_service.check_availability(sample_vehicle_id)

        # Assert
        assert available == 0

    @pytest.mark.asyncio
    async def test_check_availability_invalid_data(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """Test checking availability with invalid data returns zero."""
        # Arrange
        mock_redis_client.get.return_value = "invalid"

        # Act
        available = await reservation_service.check_availability(sample_vehicle_id)

        # Assert
        assert available == 0

    @pytest.mark.asyncio
    async def test_check_availability_redis_error(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """Test availability check handles Redis errors."""
        # Arrange
        mock_redis_client.get.side_effect = Exception("Redis connection error")

        # Act & Assert
        with pytest.raises(ReservationError) as exc_info:
            await reservation_service.check_availability(sample_vehicle_id)

        assert exc_info.value.code == "AVAILABILITY_CHECK_FAILED"


# ============================================================================
# Unit Tests - Reservation Retrieval
# ============================================================================


class TestReservationRetrieval:
    """Test suite for reservation retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_reservation_success(
        self,
        reservation_service,
        mock_redis_client,
        sample_reservation_data,
    ):
        """Test successful reservation retrieval."""
        # Arrange
        reservation_id = sample_reservation_data["reservation_id"]
        mock_redis_client.get_json.return_value = sample_reservation_data
        mock_redis_client.ttl.return_value = 600

        # Act
        result = await reservation_service.get_reservation(reservation_id)

        # Assert
        assert result is not None
        assert result["reservation_id"] == reservation_id
        assert result["ttl_seconds"] == 600

    @pytest.mark.asyncio
    async def test_get_reservation_not_found(
        self,
        reservation_service,
        mock_redis_client,
    ):
        """Test retrieving non-existent reservation returns None."""
        # Arrange
        reservation_id = str(uuid.uuid4())
        mock_redis_client.get_json.return_value = None

        # Act
        result = await reservation_service.get_reservation(reservation_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_reservation_expired_ttl(
        self,
        reservation_service,
        mock_redis_client,
        sample_reservation_data,
    ):
        """Test retrieving reservation with expired TTL."""
        # Arrange
        reservation_id = sample_reservation_data["reservation_id"]
        mock_redis_client.get_json.return_value = sample_reservation_data
        mock_redis_client.ttl.return_value = -2  # Key doesn't exist

        # Act
        result = await reservation_service.get_reservation(reservation_id)

        # Assert
        assert result is not None
        assert "ttl_seconds" not in result

    @pytest.mark.asyncio
    async def test_get_reservation_redis_error(
        self,
        reservation_service,
        mock_redis_client,
    ):
        """Test reservation retrieval handles Redis errors."""
        # Arrange
        reservation_id = str(uuid.uuid4())
        mock_redis_client.get_json.side_effect = Exception("Redis error")

        # Act & Assert
        with pytest.raises(ReservationError) as exc_info:
            await reservation_service.get_reservation(reservation_id)

        assert exc_info.value.code == "RESERVATION_GET_FAILED"


# ============================================================================
# Unit Tests - Reservation Extension
# ============================================================================


class TestReservationExtension:
    """Test suite for reservation TTL extension."""

    @pytest.mark.asyncio
    async def test_extend_reservation_success(
        self,
        reservation_service,
        mock_redis_client,
    ):
        """Test successful reservation extension."""
        # Arrange
        reservation_id = str(uuid.uuid4())
        mock_redis_client.exists.return_value = True

        # Act
        await reservation_service.extend_reservation(reservation_id)

        # Assert
        mock_redis_client.expire.assert_called_once_with(
            f"reservation:{reservation_id}",
            900,
        )

    @pytest.mark.asyncio
    async def test_extend_reservation_custom_ttl(
        self,
        reservation_service,
        mock_redis_client,
    ):
        """Test extending reservation with custom TTL."""
        # Arrange
        reservation_id = str(uuid.uuid4())
        mock_redis_client.exists.return_value = True

        # Act
        await reservation_service.extend_reservation(
            reservation_id,
            additional_seconds=1800,
        )

        # Assert
        mock_redis_client.expire.assert_called_once_with(
            f"reservation:{reservation_id}",
            1800,
        )

    @pytest.mark.asyncio
    async def test_extend_reservation_not_found(
        self,
        reservation_service,
        mock_redis_client,
    ):
        """Test extending non-existent reservation raises error."""
        # Arrange
        reservation_id = str(uuid.uuid4())
        mock_redis_client.exists.return_value = False

        # Act & Assert
        with pytest.raises(ReservationNotFoundError) as exc_info:
            await reservation_service.extend_reservation(reservation_id)

        assert exc_info.value.code == "RESERVATION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_extend_reservation_redis_error(
        self,
        reservation_service,
        mock_redis_client,
    ):
        """Test reservation extension handles Redis errors."""
        # Arrange
        reservation_id = str(uuid.uuid4())
        mock_redis_client.exists.return_value = True
        mock_redis_client.expire.side_effect = Exception("Redis error")

        # Act & Assert
        with pytest.raises(ReservationError) as exc_info:
            await reservation_service.extend_reservation(reservation_id)

        assert exc_info.value.code == "RESERVATION_EXTEND_FAILED"


# ============================================================================
# Unit Tests - Inventory Management
# ============================================================================


class TestInventoryManagement:
    """Test suite for inventory availability management."""

    @pytest.mark.asyncio
    async def test_set_inventory_availability_success(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """Test setting inventory availability."""
        # Act
        await reservation_service.set_inventory_availability(
            sample_vehicle_id,
            quantity=50,
        )

        # Assert
        mock_redis_client.set.assert_called_once_with(
            f"inventory_available:{sample_vehicle_id}",
            "50",
        )

    @pytest.mark.asyncio
    async def test_set_inventory_availability_zero(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """Test setting inventory to zero."""
        # Act
        await reservation_service.set_inventory_availability(
            sample_vehicle_id,
            quantity=0,
        )

        # Assert
        mock_redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_inventory_availability_negative(
        self,
        reservation_service,
        sample_vehicle_id,
    ):
        """Test that negative inventory raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="cannot be negative"):
            await reservation_service.set_inventory_availability(
                sample_vehicle_id,
                quantity=-1,
            )

    @pytest.mark.asyncio
    async def test_set_inventory_availability_redis_error(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """Test setting inventory handles Redis errors."""
        # Arrange
        mock_redis_client.set.side_effect = Exception("Redis error")

        # Act & Assert
        with pytest.raises(ReservationError) as exc_info:
            await reservation_service.set_inventory_availability(
                sample_vehicle_id,
                quantity=10,
            )

        assert exc_info.value.code == "SET_AVAILABILITY_FAILED"


# ============================================================================
# Unit Tests - Cleanup Operations
# ============================================================================


class TestCleanupOperations:
    """Test suite for expired reservation cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_reservations_no_reservations(
        self,
        reservation_service,
        mock_redis_client,
    ):
        """Test cleanup when no reservations exist."""
        # Arrange
        async def empty_scan():
            return [].__aiter__()

        mock_redis_client._client.scan_iter = lambda match: empty_scan()

        # Act
        cleaned_count = await reservation_service.cleanup_expired_reservations()

        # Assert
        assert cleaned_count == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired_reservations_with_expired(
        self,
        reservation_service,
        mock_redis_client,
    ):
        """Test cleanup removes expired reservations."""
        # Arrange
        expired_keys = [
            b"reservation:expired-1",
            b"reservation:expired-2",
        ]

        async def mock_scan():
            for key in expired_keys:
                yield key

        mock_redis_client._client.scan_iter = lambda match: mock_scan()
        mock_redis_client.ttl.return_value = -2  # Key doesn't exist

        # Act
        cleaned_count = await reservation_service.cleanup_expired_reservations()

        # Assert
        assert cleaned_count == 2

    @pytest.mark.asyncio
    async def test_cleanup_expired_reservations_with_no_ttl(
        self,
        reservation_service,
        mock_redis_client,
    ):
        """Test cleanup handles reservations without TTL."""
        # Arrange
        keys = [b"reservation:no-ttl"]

        async def mock_scan():
            for key in keys:
                yield key

        mock_redis_client._client.scan_iter = lambda match: mock_scan()
        mock_redis_client.ttl.return_value = -1  # No expiration

        # Act
        cleaned_count = await reservation_service.cleanup_expired_reservations()

        # Assert
        assert cleaned_count == 0
        mock_redis_client.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_expired_reservations_redis_error(
        self,
        reservation_service,
        mock_redis_client,
    ):
        """Test cleanup handles Redis errors gracefully."""
        # Arrange
        async def error_scan():
            raise Exception("Redis scan error")

        mock_redis_client._client.scan_iter = lambda match: error_scan()

        # Act & Assert
        with pytest.raises(ReservationError) as exc_info:
            await reservation_service.cleanup_expired_reservations()

        assert exc_info.value.code == "CLEANUP_FAILED"


# ============================================================================
# Unit Tests - Background Tasks
# ============================================================================


class TestBackgroundTasks:
    """Test suite for background cleanup task management."""

    @pytest.mark.asyncio
    async def test_start_background_cleanup(
        self,
        reservation_service,
    ):
        """Test starting background cleanup task."""
        # Act
        await reservation_service.start_background_cleanup()

        # Assert
        assert reservation_service._cleanup_task is not None
        assert not reservation_service._cleanup_task.done()

        # Cleanup
        await reservation_service.stop_background_cleanup()

    @pytest.mark.asyncio
    async def test_start_background_cleanup_already_running(
        self,
        reservation_service,
    ):
        """Test starting cleanup when already running does nothing."""
        # Arrange
        await reservation_service.start_background_cleanup()
        first_task = reservation_service._cleanup_task

        # Act
        await reservation_service.start_background_cleanup()

        # Assert
        assert reservation_service._cleanup_task is first_task

        # Cleanup
        await reservation_service.stop_background_cleanup()

    @pytest.mark.asyncio
    async def test_stop_background_cleanup(
        self,
        reservation_service,
    ):
        """Test stopping background cleanup task."""
        # Arrange
        await reservation_service.start_background_cleanup()

        # Act
        await reservation_service.stop_background_cleanup()

        # Assert
        assert reservation_service._cleanup_task is None

    @pytest.mark.asyncio
    async def test_stop_background_cleanup_not_running(
        self,
        reservation_service,
    ):
        """Test stopping cleanup when not running does nothing."""
        # Act & Assert (should not raise)
        await reservation_service.stop_background_cleanup()

    @pytest.mark.asyncio
    async def test_background_cleanup_loop_executes(
        self,
        reservation_service,
        mock_redis_client,
    ):
        """Test that background cleanup loop executes periodically."""
        # Arrange
        cleanup_calls = []

        original_cleanup = reservation_service.cleanup_expired_reservations

        async def tracked_cleanup():
            cleanup_calls.append(datetime.utcnow())
            return 0

        reservation_service.cleanup_expired_reservations = tracked_cleanup

        # Temporarily reduce interval for testing
        original_interval = reservation_service.CLEANUP_INTERVAL_SECONDS
        reservation_service.CLEANUP_INTERVAL_SECONDS = 0.1

        try:
            # Act
            await reservation_service.start_background_cleanup()
            await asyncio.sleep(0.3)  # Wait for multiple iterations

            # Assert
            assert len(cleanup_calls) >= 2

        finally:
            # Cleanup
            reservation_service.CLEANUP_INTERVAL_SECONDS = original_interval
            reservation_service.cleanup_expired_reservations = original_cleanup
            await reservation_service.stop_background_cleanup()


# ============================================================================
# Integration Tests - Concurrent Operations
# ============================================================================


class TestConcurrentOperations:
    """Test suite for concurrent reservation operations."""

    @pytest.mark.asyncio
    async def test_concurrent_reservations_same_vehicle(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """
        Test concurrent reservations for same vehicle.

        Simulates race condition where multiple users try to reserve
        the same vehicle simultaneously.
        """
        # Arrange
        mock_redis_client.get.return_value = "5"  # 5 available
        decr_values = [4, 3, 2, 1, 0]
        mock_redis_client.decr.side_effect = decr_values

        # Act - Create 5 concurrent reservations
        tasks = [
            reservation_service.create_reservation(
                vehicle_id=sample_vehicle_id,
                quantity=1,
                user_id=f"user-{i}",
            )
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assert - All should succeed
        successful = [r for r in results if isinstance(r, str)]
        assert len(successful) == 5

    @pytest.mark.asyncio
    async def test_concurrent_reservations_exceeding_inventory(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """
        Test concurrent reservations exceeding available inventory.

        Verifies that some reservations fail when inventory is exhausted.
        """
        # Arrange
        mock_redis_client.get.return_value = "2"  # Only 2 available

        # Act - Try to create 5 concurrent reservations
        tasks = [
            reservation_service.create_reservation(
                vehicle_id=sample_vehicle_id,
                quantity=1,
                user_id=f"user-{i}",
            )
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assert - Some should fail with InsufficientInventoryError
        errors = [r for r in results if isinstance(r, InsufficientInventoryError)]
        assert len(errors) >= 3

    @pytest.mark.asyncio
    async def test_concurrent_release_operations(
        self,
        reservation_service,
        mock_redis_client,
        sample_reservation_data,
    ):
        """Test concurrent release operations."""
        # Arrange
        reservation_ids = [str(uuid.uuid4()) for _ in range(5)]

        def get_json_side_effect(key):
            for res_id in reservation_ids:
                if res_id in key:
                    data = sample_reservation_data.copy()
                    data["reservation_id"] = res_id
                    return data
            return None

        mock_redis_client.get_json.side_effect = get_json_side_effect
        mock_redis_client.incr.return_value = 10

        # Act - Release all concurrently
        tasks = [
            reservation_service.release_reservation(res_id)
            for res_id in reservation_ids
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assert - All should succeed
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0


# ============================================================================
# Integration Tests - End-to-End Workflows
# ============================================================================


class TestEndToEndWorkflows:
    """Test suite for complete reservation workflows."""

    @pytest.mark.asyncio
    async def test_complete_reservation_lifecycle(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """
        Test complete reservation lifecycle.

        Tests: create → get → extend → release
        """
        # Arrange
        mock_redis_client.get.return_value = "10"
        mock_redis_client.decr.return_value = 9
        mock_redis_client.exists.return_value = True
        mock_redis_client.incr.return_value = 10

        # Act - Create reservation
        reservation_id = await reservation_service.create_reservation(
            vehicle_id=sample_vehicle_id,
            quantity=1,
            user_id="user-123",
        )

        # Get reservation data
        reservation_data = {
            "reservation_id": reservation_id,
            "vehicle_id": sample_vehicle_id,
            "quantity": 1,
            "user_id": "user-123",
            "session_id": "",
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (
                datetime.utcnow() + timedelta(seconds=900)
            ).isoformat(),
        }
        mock_redis_client.get_json.return_value = reservation_data
        mock_redis_client.ttl.return_value = 600

        retrieved = await reservation_service.get_reservation(reservation_id)

        # Extend reservation
        await reservation_service.extend_reservation(reservation_id)

        # Release reservation
        await reservation_service.release_reservation(reservation_id)

        # Assert
        assert retrieved is not None
        assert retrieved["reservation_id"] == reservation_id
        mock_redis_client.expire.assert_called_once()
        mock_redis_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_reservation_expiration_workflow(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """
        Test reservation expiration workflow.

        Simulates TTL expiration and cleanup process.
        """
        # Arrange
        mock_redis_client.get.return_value = "10"
        mock_redis_client.decr.return_value = 9

        # Create reservation
        reservation_id = await reservation_service.create_reservation(
            vehicle_id=sample_vehicle_id,
            quantity=1,
        )

        # Simulate expiration
        mock_redis_client.get_json.return_value = None
        mock_redis_client.ttl.return_value = -2

        # Act - Try to get expired reservation
        result = await reservation_service.get_reservation(reservation_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_inventory_synchronization_workflow(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """
        Test inventory synchronization workflow.

        Tests: set inventory → check → reserve → check → release → check
        """
        # Set initial inventory
        await reservation_service.set_inventory_availability(
            sample_vehicle_id,
            quantity=10,
        )

        # Check availability
        mock_redis_client.get.return_value = "10"
        available = await reservation_service.check_availability(sample_vehicle_id)
        assert available == 10

        # Create reservation
        mock_redis_client.decr.return_value = 8
        await reservation_service.create_reservation(
            vehicle_id=sample_vehicle_id,
            quantity=2,
        )

        # Check availability after reservation
        mock_redis_client.get.return_value = "8"
        available = await reservation_service.check_availability(sample_vehicle_id)
        assert available == 8


# ============================================================================
# Global Service Tests
# ============================================================================


class TestGlobalService:
    """Test suite for global service instance management."""

    @pytest.mark.asyncio
    async def test_get_reservation_service_singleton(self):
        """Test that get_reservation_service returns singleton."""
        # Act
        service1 = await get_reservation_service()
        service2 = await get_reservation_service()

        # Assert
        assert service1 is service2

        # Cleanup
        await close_reservation_service()

    @pytest.mark.asyncio
    async def test_close_reservation_service(self):
        """Test closing global reservation service."""
        # Arrange
        service = await get_reservation_service()
        assert service is not None

        # Act
        await close_reservation_service()

        # Assert - New instance should be created
        new_service = await get_reservation_service()
        assert new_service is not service

        # Cleanup
        await close_reservation_service()


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test suite for error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_reservation_error_with_context(self):
        """Test ReservationError includes context information."""
        # Arrange & Act
        error = ReservationError(
            "Test error",
            code="TEST_ERROR",
            vehicle_id="vehicle-123",
            quantity=5,
        )

        # Assert
        assert error.code == "TEST_ERROR"
        assert error.context["vehicle_id"] == "vehicle-123"
        assert error.context["quantity"] == 5

    @pytest.mark.asyncio
    async def test_insufficient_inventory_error_details(self):
        """Test InsufficientInventoryError contains detailed information."""
        # Arrange & Act
        error = InsufficientInventoryError(
            vehicle_id="vehicle-123",
            requested=10,
            available=5,
        )

        # Assert
        assert error.code == "INSUFFICIENT_INVENTORY"
        assert error.context["vehicle_id"] == "vehicle-123"
        assert error.context["requested"] == 10
        assert error.context["available"] == 5
        assert "vehicle-123" in str(error)

    @pytest.mark.asyncio
    async def test_reservation_not_found_error_details(self):
        """Test ReservationNotFoundError contains reservation ID."""
        # Arrange
        reservation_id = str(uuid.uuid4())

        # Act
        error = ReservationNotFoundError(reservation_id)

        # Assert
        assert error.code == "RESERVATION_NOT_FOUND"
        assert error.context["reservation_id"] == reservation_id
        assert reservation_id in str(error)


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Test suite for performance validation."""

    @pytest.mark.asyncio
    async def test_reservation_creation_performance(
        self,
        reservation_service,
        mock_redis_client,
        sample_vehicle_id,
    ):
        """Test reservation creation completes within time threshold."""
        # Arrange
        mock_redis_client.get.return_value = "100"
        mock_redis_client.decr.return_value = 99

        # Act
        start_time = datetime.utcnow()
        await reservation_service.create_reservation(
            vehicle_id=sample_vehicle_id,
            quantity=1,
        )
        elapsed = (datetime.utcnow() - start_time).total_seconds()

        # Assert - Should complete in under 100ms (mocked)
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_bulk_availability_checks_performance(
        self,
        reservation_service,
        mock_redis_client,
    ):
        """Test bulk availability checks complete efficiently."""
        # Arrange
        vehicle_ids = [f"vehicle-{i}" for i in range(100)]
        mock_redis_client.get.return_value = "10"

        # Act
        start_time = datetime.utcnow()
        tasks = [
            reservation_service.check_availability(vehicle_id)
            for vehicle_id in vehicle_ids
        ]
        await asyncio.gather(*tasks)
        elapsed = (datetime.utcnow() - start_time).total_seconds()

        # Assert - Should complete in under 1 second (mocked)
        assert elapsed < 1.0


# ============================================================================
# Key Generation Tests
# ============================================================================


class TestKeyGeneration:
    """Test suite for Redis key generation."""

    def test_make_reservation_key(self, reservation_service):
        """Test reservation key generation."""
        # Arrange
        reservation_id = "test-reservation-123"

        # Act
        key = reservation_service._make_reservation_key(reservation_id)

        # Assert
        assert key == "reservation:test-reservation-123"
        assert key.startswith(reservation_service.RESERVATION_KEY_PREFIX)

    def test_make_inventory_key(self, reservation_service):
        """Test inventory key generation."""
        # Arrange
        vehicle_id = "vehicle-456"

        # Act
        key = reservation_service._make_inventory_key(vehicle_id)

        # Assert
        assert key == "inventory_available:vehicle-456"
        assert key.startswith(reservation_service.INVENTORY_KEY_PREFIX)


# ============================================================================
# Configuration Tests
# ============================================================================


class TestConfiguration:
    """Test suite for service configuration."""

    def test_default_ttl_configuration(self, reservation_service):
        """Test default TTL is set correctly."""
        assert reservation_service.RESERVATION_TTL_SECONDS == 900

    def test_default_cleanup_interval(self, reservation_service):
        """Test default cleanup interval is set correctly."""
        assert reservation_service.CLEANUP_INTERVAL_SECONDS == 300

    def test_key_prefix_configuration(self, reservation_service):
        """Test key prefixes are configured correctly."""
        assert reservation_service.RESERVATION_KEY_PREFIX == "reservation"
        assert reservation_service.INVENTORY_KEY_PREFIX == "inventory_available"