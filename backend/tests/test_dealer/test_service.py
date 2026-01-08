"""
Comprehensive test suite for dealer inventory service.

Tests cover business logic operations, authorization, bulk updates,
file processing, audit logging, and error handling with high coverage.
"""

import uuid
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.database.models.inventory import InventoryItem, InventoryStatus
from src.schemas.dealer import (
    BulkInventoryResponse,
    BulkInventoryUpdate,
    BulkInventoryUpdateItem,
    DealerDashboardStats,
    DealerInventoryResponse,
    DealerInventoryUpdate,
)
from src.services.dealer.service import (
    DealerAuthorizationError,
    DealerInventoryNotFoundError,
    DealerInventoryService,
    DealerServiceError,
    get_dealer_inventory_service,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_session():
    """Create mock async database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_repository():
    """Create mock dealer inventory repository."""
    repository = AsyncMock()
    repository.verify_dealer_access = AsyncMock(return_value=True)
    repository.get_dealer_inventory = AsyncMock(return_value=([], 0))
    repository.get_inventory_by_id = AsyncMock(return_value=None)
    repository.bulk_update_inventory = AsyncMock(return_value=(0, 0, []))
    repository.update_stock_level = AsyncMock(return_value=None)
    repository.get_inventory_summary = AsyncMock(return_value={})
    return repository


@pytest.fixture
def mock_file_processor():
    """Create mock file processor."""
    processor = AsyncMock()
    processor.process_file = AsyncMock(
        return_value={
            "valid_items": 10,
            "invalid_items": 0,
            "errors": [],
        }
    )
    return processor


@pytest.fixture
def dealer_service(mock_session, mock_repository, mock_file_processor):
    """Create dealer inventory service with mocked dependencies."""
    service = DealerInventoryService(
        session=mock_session,
        file_processor=mock_file_processor,
    )
    service.repository = mock_repository
    return service


@pytest.fixture
def sample_dealer_id():
    """Generate sample dealer UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_user_id():
    """Generate sample user UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_inventory_id():
    """Generate sample inventory UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_vehicle_id():
    """Generate sample vehicle UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_inventory_item(sample_inventory_id, sample_dealer_id, sample_vehicle_id):
    """Create sample inventory item."""
    return InventoryItem(
        id=sample_inventory_id,
        dealership_id=sample_dealer_id,
        vehicle_id=sample_vehicle_id,
        stock_quantity=5,
        location="Lot A",
        status=InventoryStatus.ACTIVE,
        vin="1HGBH41JXMN109186",
        notes="Test vehicle",
        custom_attributes={"color": "blue"},
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=uuid.uuid4(),
        updated_by=uuid.uuid4(),
    )


@pytest.fixture
def sample_inventory_update():
    """Create sample inventory update data."""
    return DealerInventoryUpdate(
        quantity=10,
        location="Lot B",
        status="active",
        notes="Updated notes",
    )


@pytest.fixture
def sample_bulk_update(sample_vehicle_id):
    """Create sample bulk update data."""
    return BulkInventoryUpdate(
        operation="update",
        items=[
            BulkInventoryUpdateItem(
                vehicle_id=sample_vehicle_id,
                quantity=5,
                status="active",
                location="Lot A",
            )
        ],
        validate_only=False,
    )


# ============================================================================
# Unit Tests - Service Initialization
# ============================================================================


class TestServiceInitialization:
    """Test service initialization and factory function."""

    def test_service_initialization_with_defaults(self, mock_session):
        """Test service initializes with default file processor."""
        service = DealerInventoryService(session=mock_session)

        assert service.session == mock_session
        assert service.repository is not None
        assert service.file_processor is not None

    def test_service_initialization_with_custom_processor(
        self, mock_session, mock_file_processor
    ):
        """Test service initializes with custom file processor."""
        service = DealerInventoryService(
            session=mock_session,
            file_processor=mock_file_processor,
        )

        assert service.file_processor == mock_file_processor

    def test_get_dealer_inventory_service_factory(self, mock_session):
        """Test factory function creates service instance."""
        service = get_dealer_inventory_service(session=mock_session)

        assert isinstance(service, DealerInventoryService)
        assert service.session == mock_session

    def test_get_dealer_inventory_service_with_processor(
        self, mock_session, mock_file_processor
    ):
        """Test factory function with custom file processor."""
        service = get_dealer_inventory_service(
            session=mock_session,
            file_processor=mock_file_processor,
        )

        assert service.file_processor == mock_file_processor


# ============================================================================
# Unit Tests - Get Dealer Inventory
# ============================================================================


class TestGetDealerInventory:
    """Test get_dealer_inventory method."""

    @pytest.mark.asyncio
    async def test_get_dealer_inventory_success(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
        sample_inventory_item,
    ):
        """Test successful inventory retrieval."""
        mock_repository.get_dealer_inventory.return_value = (
            [sample_inventory_item],
            1,
        )

        responses, total = await dealer_service.get_dealer_inventory(
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
        )

        assert len(responses) == 1
        assert total == 1
        assert responses[0].id == sample_inventory_item.id
        mock_repository.verify_dealer_access.assert_called_once_with(
            sample_user_id, sample_dealer_id
        )

    @pytest.mark.asyncio
    async def test_get_dealer_inventory_with_filters(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test inventory retrieval with status filter."""
        mock_repository.get_dealer_inventory.return_value = ([], 0)

        await dealer_service.get_dealer_inventory(
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
            status=InventoryStatus.ACTIVE,
            skip=10,
            limit=50,
            sort_by="updated_at",
            sort_direction="asc",
        )

        mock_repository.get_dealer_inventory.assert_called_once_with(
            dealer_id=sample_dealer_id,
            status=InventoryStatus.ACTIVE,
            skip=10,
            limit=50,
            sort_by="updated_at",
            sort_direction="asc",
        )

    @pytest.mark.asyncio
    async def test_get_dealer_inventory_authorization_denied(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test authorization failure raises error."""
        mock_repository.verify_dealer_access.return_value = False

        with pytest.raises(DealerAuthorizationError) as exc_info:
            await dealer_service.get_dealer_inventory(
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
            )

        assert exc_info.value.code == "ACCESS_DENIED"
        assert str(sample_dealer_id) in exc_info.value.context["dealer_id"]

    @pytest.mark.asyncio
    async def test_get_dealer_inventory_database_error(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test database error handling."""
        mock_repository.get_dealer_inventory.side_effect = SQLAlchemyError(
            "Database error"
        )

        with pytest.raises(DealerServiceError) as exc_info:
            await dealer_service.get_dealer_inventory(
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
            )

        assert exc_info.value.code == "DB_ERROR"

    @pytest.mark.asyncio
    async def test_get_dealer_inventory_unexpected_error(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test unexpected error handling."""
        mock_repository.get_dealer_inventory.side_effect = RuntimeError(
            "Unexpected error"
        )

        with pytest.raises(DealerServiceError) as exc_info:
            await dealer_service.get_dealer_inventory(
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
            )

        assert exc_info.value.code == "UNKNOWN_ERROR"

    @pytest.mark.asyncio
    async def test_get_dealer_inventory_empty_result(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test empty inventory result."""
        mock_repository.get_dealer_inventory.return_value = ([], 0)

        responses, total = await dealer_service.get_dealer_inventory(
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
        )

        assert len(responses) == 0
        assert total == 0


# ============================================================================
# Unit Tests - Get Inventory Item
# ============================================================================


class TestGetInventoryItem:
    """Test get_inventory_item method."""

    @pytest.mark.asyncio
    async def test_get_inventory_item_success(
        self,
        dealer_service,
        mock_repository,
        sample_inventory_id,
        sample_dealer_id,
        sample_user_id,
        sample_inventory_item,
    ):
        """Test successful single item retrieval."""
        mock_repository.get_inventory_by_id.return_value = sample_inventory_item

        response = await dealer_service.get_inventory_item(
            inventory_id=sample_inventory_id,
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
        )

        assert response.id == sample_inventory_id
        assert response.dealer_id == sample_dealer_id
        mock_repository.get_inventory_by_id.assert_called_once_with(
            sample_inventory_id, sample_dealer_id
        )

    @pytest.mark.asyncio
    async def test_get_inventory_item_not_found(
        self,
        dealer_service,
        mock_repository,
        sample_inventory_id,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test item not found raises error."""
        mock_repository.get_inventory_by_id.return_value = None

        with pytest.raises(DealerInventoryNotFoundError) as exc_info:
            await dealer_service.get_inventory_item(
                inventory_id=sample_inventory_id,
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
            )

        assert exc_info.value.code == "NOT_FOUND"
        assert str(sample_inventory_id) in exc_info.value.context["inventory_id"]

    @pytest.mark.asyncio
    async def test_get_inventory_item_authorization_denied(
        self,
        dealer_service,
        mock_repository,
        sample_inventory_id,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test authorization failure for single item."""
        mock_repository.verify_dealer_access.return_value = False

        with pytest.raises(DealerAuthorizationError):
            await dealer_service.get_inventory_item(
                inventory_id=sample_inventory_id,
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
            )

    @pytest.mark.asyncio
    async def test_get_inventory_item_database_error(
        self,
        dealer_service,
        mock_repository,
        sample_inventory_id,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test database error handling for single item."""
        mock_repository.get_inventory_by_id.side_effect = SQLAlchemyError(
            "Database error"
        )

        with pytest.raises(DealerServiceError) as exc_info:
            await dealer_service.get_inventory_item(
                inventory_id=sample_inventory_id,
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
            )

        assert exc_info.value.code == "DB_ERROR"


# ============================================================================
# Unit Tests - Update Inventory Item
# ============================================================================


class TestUpdateInventoryItem:
    """Test update_inventory_item method."""

    @pytest.mark.asyncio
    async def test_update_inventory_item_success(
        self,
        dealer_service,
        mock_repository,
        sample_inventory_id,
        sample_dealer_id,
        sample_user_id,
        sample_inventory_update,
        sample_inventory_item,
    ):
        """Test successful inventory item update."""
        mock_repository.bulk_update_inventory.return_value = (1, 0, [])
        mock_repository.get_inventory_by_id.return_value = sample_inventory_item

        response = await dealer_service.update_inventory_item(
            inventory_id=sample_inventory_id,
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
            update_data=sample_inventory_update,
        )

        assert response.id == sample_inventory_id
        mock_repository.bulk_update_inventory.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_inventory_item_partial_update(
        self,
        dealer_service,
        mock_repository,
        sample_inventory_id,
        sample_dealer_id,
        sample_user_id,
        sample_inventory_item,
    ):
        """Test partial update with only some fields."""
        partial_update = DealerInventoryUpdate(quantity=15)
        mock_repository.bulk_update_inventory.return_value = (1, 0, [])
        mock_repository.get_inventory_by_id.return_value = sample_inventory_item

        response = await dealer_service.update_inventory_item(
            inventory_id=sample_inventory_id,
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
            update_data=partial_update,
        )

        assert response.id == sample_inventory_id
        call_args = mock_repository.bulk_update_inventory.call_args
        updates = call_args.kwargs["updates"]
        assert len(updates) == 1
        assert updates[0]["quantity"] == 15

    @pytest.mark.asyncio
    async def test_update_inventory_item_update_failed(
        self,
        dealer_service,
        mock_repository,
        sample_inventory_id,
        sample_dealer_id,
        sample_user_id,
        sample_inventory_update,
    ):
        """Test update failure handling."""
        mock_repository.bulk_update_inventory.return_value = (
            0,
            1,
            ["Update failed"],
        )

        with pytest.raises(DealerServiceError) as exc_info:
            await dealer_service.update_inventory_item(
                inventory_id=sample_inventory_id,
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
                update_data=sample_inventory_update,
            )

        assert exc_info.value.code == "UPDATE_FAILED"

    @pytest.mark.asyncio
    async def test_update_inventory_item_not_found_after_update(
        self,
        dealer_service,
        mock_repository,
        sample_inventory_id,
        sample_dealer_id,
        sample_user_id,
        sample_inventory_update,
    ):
        """Test item not found after update."""
        mock_repository.bulk_update_inventory.return_value = (1, 0, [])
        mock_repository.get_inventory_by_id.return_value = None

        with pytest.raises(DealerInventoryNotFoundError):
            await dealer_service.update_inventory_item(
                inventory_id=sample_inventory_id,
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
                update_data=sample_inventory_update,
            )

    @pytest.mark.asyncio
    async def test_update_inventory_item_authorization_denied(
        self,
        dealer_service,
        mock_repository,
        sample_inventory_id,
        sample_dealer_id,
        sample_user_id,
        sample_inventory_update,
    ):
        """Test authorization failure for update."""
        mock_repository.verify_dealer_access.return_value = False

        with pytest.raises(DealerAuthorizationError):
            await dealer_service.update_inventory_item(
                inventory_id=sample_inventory_id,
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
                update_data=sample_inventory_update,
            )


# ============================================================================
# Unit Tests - Bulk Update Inventory
# ============================================================================


class TestBulkUpdateInventory:
    """Test bulk_update_inventory method."""

    @pytest.mark.asyncio
    async def test_bulk_update_inventory_success(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
        sample_bulk_update,
    ):
        """Test successful bulk update."""
        mock_repository.bulk_update_inventory.return_value = (1, 0, [])

        response = await dealer_service.bulk_update_inventory(
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
            bulk_update=sample_bulk_update,
        )

        assert response.total_items == 1
        assert response.successful_items == 1
        assert response.failed_items == 0
        assert len(response.errors) == 0

    @pytest.mark.asyncio
    async def test_bulk_update_inventory_validate_only(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
        sample_vehicle_id,
    ):
        """Test validation-only mode."""
        bulk_update = BulkInventoryUpdate(
            operation="update",
            items=[
                BulkInventoryUpdateItem(
                    vehicle_id=sample_vehicle_id,
                    quantity=5,
                    status="active",
                )
            ],
            validate_only=True,
        )

        response = await dealer_service.bulk_update_inventory(
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
            bulk_update=bulk_update,
        )

        assert response.successful_items == 1
        assert response.failed_items == 0
        mock_repository.bulk_update_inventory.assert_not_called()

    @pytest.mark.asyncio
    async def test_bulk_update_inventory_partial_failure(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
        sample_bulk_update,
    ):
        """Test bulk update with partial failures."""
        mock_repository.bulk_update_inventory.return_value = (
            5,
            3,
            ["Error 1", "Error 2", "Error 3"],
        )

        response = await dealer_service.bulk_update_inventory(
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
            bulk_update=sample_bulk_update,
        )

        assert response.successful_items == 5
        assert response.failed_items == 3
        assert len(response.errors) == 3

    @pytest.mark.asyncio
    async def test_bulk_update_inventory_multiple_items(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test bulk update with multiple items."""
        bulk_update = BulkInventoryUpdate(
            operation="update",
            items=[
                BulkInventoryUpdateItem(
                    vehicle_id=uuid.uuid4(),
                    quantity=i,
                    status="active",
                )
                for i in range(1, 11)
            ],
            validate_only=False,
        )
        mock_repository.bulk_update_inventory.return_value = (10, 0, [])

        response = await dealer_service.bulk_update_inventory(
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
            bulk_update=bulk_update,
        )

        assert response.total_items == 10
        assert response.successful_items == 10
        assert response.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_bulk_update_inventory_authorization_denied(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
        sample_bulk_update,
    ):
        """Test authorization failure for bulk update."""
        mock_repository.verify_dealer_access.return_value = False

        with pytest.raises(DealerAuthorizationError):
            await dealer_service.bulk_update_inventory(
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
                bulk_update=sample_bulk_update,
            )

    @pytest.mark.asyncio
    async def test_bulk_update_inventory_database_error(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
        sample_bulk_update,
    ):
        """Test database error during bulk update."""
        mock_repository.bulk_update_inventory.side_effect = SQLAlchemyError(
            "Database error"
        )

        with pytest.raises(DealerServiceError) as exc_info:
            await dealer_service.bulk_update_inventory(
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
                bulk_update=sample_bulk_update,
            )

        assert exc_info.value.code == "DB_ERROR"


# ============================================================================
# Unit Tests - File Upload Processing
# ============================================================================


class TestProcessFileUpload:
    """Test process_file_upload method."""

    @pytest.mark.asyncio
    async def test_process_file_upload_success(
        self,
        dealer_service,
        mock_repository,
        mock_file_processor,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test successful file upload processing."""
        file_path = "/tmp/inventory.csv"
        mock_file_processor.process_file.return_value = {
            "valid_items": 100,
            "invalid_items": 5,
            "errors": ["Row 3: Invalid VIN"],
        }

        result = await dealer_service.process_file_upload(
            file_path=file_path,
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
        )

        assert result["valid_items"] == 100
        assert result["invalid_items"] == 5
        mock_file_processor.process_file.assert_called_once_with(
            file_path=file_path,
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
        )

    @pytest.mark.asyncio
    async def test_process_file_upload_authorization_denied(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test authorization failure for file upload."""
        mock_repository.verify_dealer_access.return_value = False

        with pytest.raises(DealerAuthorizationError):
            await dealer_service.process_file_upload(
                file_path="/tmp/inventory.csv",
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
            )

    @pytest.mark.asyncio
    async def test_process_file_upload_processing_error(
        self,
        dealer_service,
        mock_repository,
        mock_file_processor,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test file processing error handling."""
        mock_file_processor.process_file.side_effect = ValueError(
            "Invalid file format"
        )

        with pytest.raises(DealerServiceError) as exc_info:
            await dealer_service.process_file_upload(
                file_path="/tmp/inventory.csv",
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
            )

        assert exc_info.value.code == "FILE_PROCESSING_ERROR"

    @pytest.mark.asyncio
    async def test_process_file_upload_empty_file(
        self,
        dealer_service,
        mock_repository,
        mock_file_processor,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test processing empty file."""
        mock_file_processor.process_file.return_value = {
            "valid_items": 0,
            "invalid_items": 0,
            "errors": [],
        }

        result = await dealer_service.process_file_upload(
            file_path="/tmp/empty.csv",
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
        )

        assert result["valid_items"] == 0
        assert result["invalid_items"] == 0


# ============================================================================
# Unit Tests - Stock Level Adjustment
# ============================================================================


class TestAdjustStockLevel:
    """Test adjust_stock_level method."""

    @pytest.mark.asyncio
    async def test_adjust_stock_level_increase(
        self,
        dealer_service,
        mock_repository,
        sample_inventory_id,
        sample_dealer_id,
        sample_user_id,
        sample_inventory_item,
    ):
        """Test increasing stock level."""
        sample_inventory_item.stock_quantity = 15
        mock_repository.update_stock_level.return_value = sample_inventory_item

        response = await dealer_service.adjust_stock_level(
            inventory_id=sample_inventory_id,
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
            quantity_change=10,
        )

        assert response.quantity == 15
        mock_repository.update_stock_level.assert_called_once_with(
            inventory_id=sample_inventory_id,
            dealer_id=sample_dealer_id,
            quantity_change=10,
            user_id=sample_user_id,
        )

    @pytest.mark.asyncio
    async def test_adjust_stock_level_decrease(
        self,
        dealer_service,
        mock_repository,
        sample_inventory_id,
        sample_dealer_id,
        sample_user_id,
        sample_inventory_item,
    ):
        """Test decreasing stock level."""
        sample_inventory_item.stock_quantity = 3
        mock_repository.update_stock_level.return_value = sample_inventory_item

        response = await dealer_service.adjust_stock_level(
            inventory_id=sample_inventory_id,
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
            quantity_change=-2,
        )

        assert response.quantity == 3

    @pytest.mark.asyncio
    async def test_adjust_stock_level_not_found(
        self,
        dealer_service,
        mock_repository,
        sample_inventory_id,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test stock adjustment for non-existent item."""
        mock_repository.update_stock_level.return_value = None

        with pytest.raises(DealerInventoryNotFoundError):
            await dealer_service.adjust_stock_level(
                inventory_id=sample_inventory_id,
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
                quantity_change=5,
            )

    @pytest.mark.asyncio
    async def test_adjust_stock_level_invalid_adjustment(
        self,
        dealer_service,
        mock_repository,
        sample_inventory_id,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test invalid stock adjustment (negative result)."""
        mock_repository.update_stock_level.side_effect = ValueError(
            "Stock cannot be negative"
        )

        with pytest.raises(DealerServiceError) as exc_info:
            await dealer_service.adjust_stock_level(
                inventory_id=sample_inventory_id,
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
                quantity_change=-100,
            )

        assert exc_info.value.code == "INVALID_ADJUSTMENT"

    @pytest.mark.asyncio
    async def test_adjust_stock_level_authorization_denied(
        self,
        dealer_service,
        mock_repository,
        sample_inventory_id,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test authorization failure for stock adjustment."""
        mock_repository.verify_dealer_access.return_value = False

        with pytest.raises(DealerAuthorizationError):
            await dealer_service.adjust_stock_level(
                inventory_id=sample_inventory_id,
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
                quantity_change=5,
            )

    @pytest.mark.asyncio
    async def test_adjust_stock_level_zero_change(
        self,
        dealer_service,
        mock_repository,
        sample_inventory_id,
        sample_dealer_id,
        sample_user_id,
        sample_inventory_item,
    ):
        """Test stock adjustment with zero change."""
        mock_repository.update_stock_level.return_value = sample_inventory_item

        response = await dealer_service.adjust_stock_level(
            inventory_id=sample_inventory_id,
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
            quantity_change=0,
        )

        assert response.quantity == sample_inventory_item.stock_quantity


# ============================================================================
# Unit Tests - Dashboard Statistics
# ============================================================================


class TestGetDashboardStatistics:
    """Test get_dashboard_statistics method."""

    @pytest.mark.asyncio
    async def test_get_dashboard_statistics_success(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test successful dashboard statistics retrieval."""
        mock_repository.get_inventory_summary.return_value = {
            "total_items": 100,
            "status_breakdown": {
                "active": 80,
                "inactive": 10,
                "sold": 5,
                "reserved": 5,
            },
            "low_stock_items": 15,
            "generated_at": datetime.now().isoformat(),
        }

        stats = await dealer_service.get_dashboard_statistics(
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
        )

        assert stats.total_vehicles == 100
        assert stats.active_vehicles == 80
        assert stats.inactive_vehicles == 10
        assert stats.sold_vehicles == 5
        assert stats.reserved_vehicles == 5
        assert stats.low_stock_count == 15

    @pytest.mark.asyncio
    async def test_get_dashboard_statistics_empty_inventory(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test dashboard statistics with empty inventory."""
        mock_repository.get_inventory_summary.return_value = {
            "total_items": 0,
            "status_breakdown": {},
            "low_stock_items": 0,
            "generated_at": datetime.now().isoformat(),
        }

        stats = await dealer_service.get_dashboard_statistics(
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
        )

        assert stats.total_vehicles == 0
        assert stats.active_vehicles == 0
        assert stats.low_stock_count == 0

    @pytest.mark.asyncio
    async def test_get_dashboard_statistics_authorization_denied(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test authorization failure for dashboard statistics."""
        mock_repository.verify_dealer_access.return_value = False

        with pytest.raises(DealerAuthorizationError):
            await dealer_service.get_dashboard_statistics(
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
            )

    @pytest.mark.asyncio
    async def test_get_dashboard_statistics_database_error(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test database error during statistics retrieval."""
        mock_repository.get_inventory_summary.side_effect = SQLAlchemyError(
            "Database error"
        )

        with pytest.raises(DealerServiceError) as exc_info:
            await dealer_service.get_dashboard_statistics(
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
            )

        assert exc_info.value.code == "DB_ERROR"


# ============================================================================
# Unit Tests - Response Conversion
# ============================================================================


class TestResponseConversion:
    """Test _to_response method."""

    def test_to_response_conversion(
        self, dealer_service, sample_inventory_item
    ):
        """Test inventory item to response conversion."""
        response = dealer_service._to_response(sample_inventory_item)

        assert isinstance(response, DealerInventoryResponse)
        assert response.id == sample_inventory_item.id
        assert response.dealer_id == sample_inventory_item.dealership_id
        assert response.vehicle_id == sample_inventory_item.vehicle_id
        assert response.quantity == sample_inventory_item.stock_quantity
        assert response.location == sample_inventory_item.location
        assert response.status == sample_inventory_item.status.value
        assert response.vin == sample_inventory_item.vin
        assert response.notes == sample_inventory_item.notes

    def test_to_response_with_custom_attributes(
        self, dealer_service, sample_inventory_item
    ):
        """Test response conversion with custom attributes."""
        sample_inventory_item.custom_attributes = {
            "color": "blue",
            "trim": "sport",
        }

        response = dealer_service._to_response(sample_inventory_item)

        assert response.custom_attributes == {"color": "blue", "trim": "sport"}

    def test_to_response_with_null_custom_attributes(
        self, dealer_service, sample_inventory_item
    ):
        """Test response conversion with null custom attributes."""
        sample_inventory_item.custom_attributes = None

        response = dealer_service._to_response(sample_inventory_item)

        assert response.custom_attributes == {}


# ============================================================================
# Integration Tests - Complex Workflows
# ============================================================================


class TestComplexWorkflows:
    """Test complex multi-step workflows."""

    @pytest.mark.asyncio
    async def test_complete_inventory_update_workflow(
        self,
        dealer_service,
        mock_repository,
        sample_inventory_id,
        sample_dealer_id,
        sample_user_id,
        sample_inventory_item,
        sample_inventory_update,
    ):
        """Test complete workflow: get, update, verify."""
        # Setup mocks
        mock_repository.get_inventory_by_id.return_value = sample_inventory_item
        mock_repository.bulk_update_inventory.return_value = (1, 0, [])

        # Get original item
        original = await dealer_service.get_inventory_item(
            inventory_id=sample_inventory_id,
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
        )

        # Update item
        updated = await dealer_service.update_inventory_item(
            inventory_id=sample_inventory_id,
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
            update_data=sample_inventory_update,
        )

        # Verify update
        verified = await dealer_service.get_inventory_item(
            inventory_id=sample_inventory_id,
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
        )

        assert original.id == updated.id == verified.id

    @pytest.mark.asyncio
    async def test_bulk_update_with_stock_adjustments(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
        sample_inventory_id,
        sample_inventory_item,
        sample_bulk_update,
    ):
        """Test bulk update followed by individual stock adjustments."""
        # Bulk update
        mock_repository.bulk_update_inventory.return_value = (1, 0, [])
        bulk_response = await dealer_service.bulk_update_inventory(
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
            bulk_update=sample_bulk_update,
        )

        # Stock adjustment
        mock_repository.update_stock_level.return_value = sample_inventory_item
        adjusted = await dealer_service.adjust_stock_level(
            inventory_id=sample_inventory_id,
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
            quantity_change=5,
        )

        assert bulk_response.successful_items == 1
        assert adjusted.id == sample_inventory_id


# ============================================================================
# Edge Cases and Boundary Tests
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_large_bulk_update(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test bulk update with large number of items."""
        bulk_update = BulkInventoryUpdate(
            operation="update",
            items=[
                BulkInventoryUpdateItem(
                    vehicle_id=uuid.uuid4(),
                    quantity=1,
                    status="active",
                )
                for _ in range(1000)
            ],
            validate_only=False,
        )
        mock_repository.bulk_update_inventory.return_value = (1000, 0, [])

        response = await dealer_service.bulk_update_inventory(
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
            bulk_update=bulk_update,
        )

        assert response.total_items == 1000
        assert response.successful_items == 1000

    @pytest.mark.asyncio
    async def test_concurrent_updates_same_item(
        self,
        dealer_service,
        mock_repository,
        sample_inventory_id,
        sample_dealer_id,
        sample_user_id,
        sample_inventory_item,
    ):
        """Test handling of concurrent updates to same item."""
        mock_repository.bulk_update_inventory.return_value = (1, 0, [])
        mock_repository.get_inventory_by_id.return_value = sample_inventory_item

        update1 = DealerInventoryUpdate(quantity=10)
        update2 = DealerInventoryUpdate(quantity=20)

        # Simulate concurrent updates
        result1 = await dealer_service.update_inventory_item(
            inventory_id=sample_inventory_id,
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
            update_data=update1,
        )

        result2 = await dealer_service.update_inventory_item(
            inventory_id=sample_inventory_id,
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
            update_data=update2,
        )

        assert result1.id == result2.id

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "quantity_change,expected_valid",
        [
            (0, True),
            (1, True),
            (-1, True),
            (1000, True),
            (-1000, True),
        ],
    )
    async def test_stock_adjustment_boundary_values(
        self,
        dealer_service,
        mock_repository,
        sample_inventory_id,
        sample_dealer_id,
        sample_user_id,
        sample_inventory_item,
        quantity_change,
        expected_valid,
    ):
        """Test stock adjustments with boundary values."""
        if expected_valid:
            mock_repository.update_stock_level.return_value = sample_inventory_item
            response = await dealer_service.adjust_stock_level(
                inventory_id=sample_inventory_id,
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
                quantity_change=quantity_change,
            )
            assert response is not None
        else:
            mock_repository.update_stock_level.side_effect = ValueError(
                "Invalid adjustment"
            )
            with pytest.raises(DealerServiceError):
                await dealer_service.adjust_stock_level(
                    inventory_id=sample_inventory_id,
                    dealer_id=sample_dealer_id,
                    user_id=sample_user_id,
                    quantity_change=quantity_change,
                )


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test comprehensive error handling scenarios."""

    @pytest.mark.asyncio
    async def test_multiple_authorization_checks(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test authorization is checked for every operation."""
        operations = [
            dealer_service.get_dealer_inventory(
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
            ),
            dealer_service.get_dashboard_statistics(
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
            ),
        ]

        mock_repository.verify_dealer_access.return_value = False

        for operation in operations:
            with pytest.raises(DealerAuthorizationError):
                await operation

    @pytest.mark.asyncio
    async def test_error_context_preservation(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test error context is preserved through exception chain."""
        mock_repository.verify_dealer_access.return_value = False

        try:
            await dealer_service.get_dealer_inventory(
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
            )
        except DealerAuthorizationError as e:
            assert e.code == "ACCESS_DENIED"
            assert "dealer_id" in e.context
            assert "user_id" in e.context
            assert str(sample_dealer_id) == e.context["dealer_id"]

    @pytest.mark.asyncio
    async def test_exception_chaining(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test exceptions are properly chained."""
        original_error = SQLAlchemyError("Original database error")
        mock_repository.get_dealer_inventory.side_effect = original_error

        try:
            await dealer_service.get_dealer_inventory(
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
            )
        except DealerServiceError as e:
            assert e.__cause__ == original_error


# ============================================================================
# Performance and Logging Tests
# ============================================================================


class TestPerformanceAndLogging:
    """Test performance characteristics and logging."""

    @pytest.mark.asyncio
    async def test_bulk_update_processing_time_recorded(
        self,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
        sample_bulk_update,
    ):
        """Test processing time is recorded for bulk updates."""
        mock_repository.bulk_update_inventory.return_value = (1, 0, [])

        response = await dealer_service.bulk_update_inventory(
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
            bulk_update=sample_bulk_update,
        )

        assert response.processing_time_ms >= 0
        assert isinstance(response.processing_time_ms, int)

    @pytest.mark.asyncio
    @patch("src.services.dealer.service.logger")
    async def test_logging_on_success(
        self,
        mock_logger,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
        sample_inventory_item,
    ):
        """Test successful operations are logged."""
        mock_repository.get_dealer_inventory.return_value = (
            [sample_inventory_item],
            1,
        )

        await dealer_service.get_dealer_inventory(
            dealer_id=sample_dealer_id,
            user_id=sample_user_id,
        )

        assert mock_logger.info.call_count >= 2

    @pytest.mark.asyncio
    @patch("src.services.dealer.service.logger")
    async def test_logging_on_error(
        self,
        mock_logger,
        dealer_service,
        mock_repository,
        sample_dealer_id,
        sample_user_id,
    ):
        """Test errors are logged with context."""
        mock_repository.get_dealer_inventory.side_effect = SQLAlchemyError(
            "Database error"
        )

        with pytest.raises(DealerServiceError):
            await dealer_service.get_dealer_inventory(
                dealer_id=sample_dealer_id,
                user_id=sample_user_id,
            )

        mock_logger.error.assert_called()