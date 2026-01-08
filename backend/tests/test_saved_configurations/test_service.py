"""
Comprehensive test suite for SavedConfigurationService.

Tests cover saving, retrieving, updating, deleting configurations,
share token generation, authorization, validation, and error handling.
Achieves >80% coverage with proper isolation and mocking.
"""

import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.models.saved_configuration import SavedConfiguration
from src.database.models.user import User
from src.database.models.vehicle_configuration import VehicleConfiguration
from src.services.saved_configurations.service import (
    ConfigurationNotFoundError,
    InvalidShareTokenError,
    SavedConfigurationError,
    SavedConfigurationService,
    UnauthorizedAccessError,
    get_saved_configuration_service,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def user_id() -> UUID:
    """Generate test user ID."""
    return uuid4()


@pytest.fixture
def other_user_id() -> UUID:
    """Generate another test user ID."""
    return uuid4()


@pytest.fixture
def configuration_id() -> UUID:
    """Generate test configuration ID."""
    return uuid4()


@pytest.fixture
def saved_config_id() -> UUID:
    """Generate test saved configuration ID."""
    return uuid4()


@pytest.fixture
def share_token() -> str:
    """Generate test share token."""
    return SavedConfiguration.generate_share_token()


@pytest.fixture
async def mock_session() -> AsyncMock:
    """Create mock async database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.delete = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def service(mock_session: AsyncMock) -> SavedConfigurationService:
    """Create SavedConfigurationService instance with mock session."""
    return SavedConfigurationService(session=mock_session)


@pytest.fixture
def mock_vehicle_config(configuration_id: UUID) -> VehicleConfiguration:
    """Create mock vehicle configuration."""
    config = MagicMock(spec=VehicleConfiguration)
    config.id = configuration_id
    config.deleted_at = None
    return config


@pytest.fixture
def mock_saved_config(
    saved_config_id: UUID,
    user_id: UUID,
    configuration_id: UUID,
    share_token: str,
) -> SavedConfiguration:
    """Create mock saved configuration."""
    config = MagicMock(spec=SavedConfiguration)
    config.id = saved_config_id
    config.user_id = user_id
    config.configuration_id = configuration_id
    config.name = "Test Configuration"
    config.is_public = False
    config.share_token = share_token
    config.created_at = datetime.utcnow()
    config.updated_at = datetime.utcnow()
    config.deleted_at = None
    config.can_be_shared = True
    
    # Mock methods
    config.belongs_to_user = MagicMock(return_value=True)
    config.is_accessible_by = MagicMock(return_value=True)
    config.update_name = MagicMock()
    config.make_public = MagicMock()
    config.make_private = MagicMock()
    config.archive = MagicMock()
    config.regenerate_share_token = MagicMock(return_value=share_token)
    
    return config


# ============================================================================
# Unit Tests - Service Initialization
# ============================================================================


class TestServiceInitialization:
    """Test SavedConfigurationService initialization."""

    def test_service_initialization(self, mock_session: AsyncMock):
        """Test service initializes with session."""
        service = SavedConfigurationService(session=mock_session)
        
        assert service.session is mock_session

    def test_factory_function(self, mock_session: AsyncMock):
        """Test factory function creates service instance."""
        service = get_saved_configuration_service(session=mock_session)
        
        assert isinstance(service, SavedConfigurationService)
        assert service.session is mock_session


# ============================================================================
# Unit Tests - Save Configuration
# ============================================================================


class TestSaveConfiguration:
    """Test saving vehicle configurations."""

    @pytest.mark.asyncio
    async def test_save_configuration_success(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        user_id: UUID,
        configuration_id: UUID,
        mock_vehicle_config: VehicleConfiguration,
    ):
        """Test successfully saving a configuration."""
        # Arrange
        config_result = AsyncMock()
        config_result.scalar_one_or_none = MagicMock(
            return_value=mock_vehicle_config
        )
        mock_session.execute.return_value = config_result

        # Act
        result = await service.save_configuration(
            user_id=user_id,
            configuration_id=configuration_id,
            name="My Test Config",
            is_public=False,
        )

        # Assert
        assert result is not None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_configuration_with_public_flag(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        user_id: UUID,
        configuration_id: UUID,
        mock_vehicle_config: VehicleConfiguration,
    ):
        """Test saving a public configuration."""
        # Arrange
        config_result = AsyncMock()
        config_result.scalar_one_or_none = MagicMock(
            return_value=mock_vehicle_config
        )
        mock_session.execute.return_value = config_result

        # Act
        result = await service.save_configuration(
            user_id=user_id,
            configuration_id=configuration_id,
            name="Public Config",
            is_public=True,
        )

        # Assert
        assert result is not None
        saved_config_call = mock_session.add.call_args[0][0]
        assert saved_config_call.is_public is True

    @pytest.mark.asyncio
    async def test_save_configuration_strips_name(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        user_id: UUID,
        configuration_id: UUID,
        mock_vehicle_config: VehicleConfiguration,
    ):
        """Test configuration name is stripped of whitespace."""
        # Arrange
        config_result = AsyncMock()
        config_result.scalar_one_or_none = MagicMock(
            return_value=mock_vehicle_config
        )
        mock_session.execute.return_value = config_result

        # Act
        result = await service.save_configuration(
            user_id=user_id,
            configuration_id=configuration_id,
            name="  Padded Name  ",
            is_public=False,
        )

        # Assert
        saved_config_call = mock_session.add.call_args[0][0]
        assert saved_config_call.name == "Padded Name"

    @pytest.mark.asyncio
    async def test_save_configuration_generates_share_token(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        user_id: UUID,
        configuration_id: UUID,
        mock_vehicle_config: VehicleConfiguration,
    ):
        """Test share token is generated on save."""
        # Arrange
        config_result = AsyncMock()
        config_result.scalar_one_or_none = MagicMock(
            return_value=mock_vehicle_config
        )
        mock_session.execute.return_value = config_result

        # Act
        result = await service.save_configuration(
            user_id=user_id,
            configuration_id=configuration_id,
            name="Test Config",
            is_public=False,
        )

        # Assert
        saved_config_call = mock_session.add.call_args[0][0]
        assert saved_config_call.share_token is not None
        assert len(saved_config_call.share_token) == 32

    @pytest.mark.asyncio
    async def test_save_configuration_not_found(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        user_id: UUID,
        configuration_id: UUID,
    ):
        """Test error when configuration doesn't exist."""
        # Arrange
        config_result = AsyncMock()
        config_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute.return_value = config_result

        # Act & Assert
        with pytest.raises(SavedConfigurationError) as exc_info:
            await service.save_configuration(
                user_id=user_id,
                configuration_id=configuration_id,
                name="Test Config",
                is_public=False,
            )

        assert exc_info.value.code == "CONFIG_NOT_FOUND"
        assert str(configuration_id) in exc_info.value.context["configuration_id"]

    @pytest.mark.asyncio
    async def test_save_configuration_integrity_error(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        user_id: UUID,
        configuration_id: UUID,
        mock_vehicle_config: VehicleConfiguration,
    ):
        """Test handling of database integrity errors."""
        # Arrange
        config_result = AsyncMock()
        config_result.scalar_one_or_none = MagicMock(
            return_value=mock_vehicle_config
        )
        mock_session.execute.return_value = config_result
        mock_session.flush.side_effect = IntegrityError("", "", "")

        # Act & Assert
        with pytest.raises(SavedConfigurationError) as exc_info:
            await service.save_configuration(
                user_id=user_id,
                configuration_id=configuration_id,
                name="Test Config",
                is_public=False,
            )

        assert exc_info.value.code == "INTEGRITY_ERROR"
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_configuration_database_error(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        user_id: UUID,
        configuration_id: UUID,
        mock_vehicle_config: VehicleConfiguration,
    ):
        """Test handling of general database errors."""
        # Arrange
        config_result = AsyncMock()
        config_result.scalar_one_or_none = MagicMock(
            return_value=mock_vehicle_config
        )
        mock_session.execute.return_value = config_result
        mock_session.flush.side_effect = SQLAlchemyError("Database error")

        # Act & Assert
        with pytest.raises(SavedConfigurationError) as exc_info:
            await service.save_configuration(
                user_id=user_id,
                configuration_id=configuration_id,
                name="Test Config",
                is_public=False,
            )

        assert exc_info.value.code == "DATABASE_ERROR"
        mock_session.rollback.assert_called_once()


# ============================================================================
# Unit Tests - Get User Configurations
# ============================================================================


class TestGetUserConfigurations:
    """Test retrieving user configurations."""

    @pytest.mark.asyncio
    async def test_get_user_configurations_success(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        user_id: UUID,
        mock_saved_config: SavedConfiguration,
    ):
        """Test successfully retrieving user configurations."""
        # Arrange
        result = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all = MagicMock(return_value=[mock_saved_config])
        result.scalars = MagicMock(return_value=scalars_result)
        mock_session.execute.return_value = result

        # Act
        configurations = await service.get_user_configurations(user_id=user_id)

        # Assert
        assert len(configurations) == 1
        assert configurations[0] == mock_saved_config
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_configurations_with_pagination(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        user_id: UUID,
    ):
        """Test pagination parameters are applied."""
        # Arrange
        result = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all = MagicMock(return_value=[])
        result.scalars = MagicMock(return_value=scalars_result)
        mock_session.execute.return_value = result

        # Act
        configurations = await service.get_user_configurations(
            user_id=user_id,
            skip=10,
            limit=20,
        )

        # Assert
        assert configurations == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_configurations_exclude_deleted(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        user_id: UUID,
    ):
        """Test deleted configurations are excluded by default."""
        # Arrange
        result = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all = MagicMock(return_value=[])
        result.scalars = MagicMock(return_value=scalars_result)
        mock_session.execute.return_value = result

        # Act
        configurations = await service.get_user_configurations(
            user_id=user_id,
            include_deleted=False,
        )

        # Assert
        assert configurations == []

    @pytest.mark.asyncio
    async def test_get_user_configurations_include_deleted(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        user_id: UUID,
        mock_saved_config: SavedConfiguration,
    ):
        """Test deleted configurations can be included."""
        # Arrange
        mock_saved_config.deleted_at = datetime.utcnow()
        result = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all = MagicMock(return_value=[mock_saved_config])
        result.scalars = MagicMock(return_value=scalars_result)
        mock_session.execute.return_value = result

        # Act
        configurations = await service.get_user_configurations(
            user_id=user_id,
            include_deleted=True,
        )

        # Assert
        assert len(configurations) == 1

    @pytest.mark.asyncio
    async def test_get_user_configurations_database_error(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        user_id: UUID,
    ):
        """Test handling of database errors."""
        # Arrange
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Act & Assert
        with pytest.raises(SavedConfigurationError) as exc_info:
            await service.get_user_configurations(user_id=user_id)

        assert exc_info.value.code == "DATABASE_ERROR"


# ============================================================================
# Unit Tests - Get Configuration
# ============================================================================


class TestGetConfiguration:
    """Test retrieving individual configurations."""

    @pytest.mark.asyncio
    async def test_get_configuration_success(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        saved_config_id: UUID,
        user_id: UUID,
        mock_saved_config: SavedConfiguration,
    ):
        """Test successfully retrieving a configuration."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_saved_config)
        mock_session.execute.return_value = result

        # Act
        config = await service.get_configuration(
            config_id=saved_config_id,
            user_id=user_id,
        )

        # Assert
        assert config == mock_saved_config
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_configuration_without_user_id(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        saved_config_id: UUID,
        mock_saved_config: SavedConfiguration,
    ):
        """Test retrieving configuration without authorization check."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_saved_config)
        mock_session.execute.return_value = result

        # Act
        config = await service.get_configuration(config_id=saved_config_id)

        # Assert
        assert config == mock_saved_config
        mock_saved_config.is_accessible_by.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_configuration_not_found(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        saved_config_id: UUID,
    ):
        """Test error when configuration not found."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute.return_value = result

        # Act & Assert
        with pytest.raises(ConfigurationNotFoundError) as exc_info:
            await service.get_configuration(config_id=saved_config_id)

        assert exc_info.value.code == "CONFIG_NOT_FOUND"
        assert str(saved_config_id) in exc_info.value.context["config_id"]

    @pytest.mark.asyncio
    async def test_get_configuration_unauthorized(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        saved_config_id: UUID,
        user_id: UUID,
        mock_saved_config: SavedConfiguration,
    ):
        """Test unauthorized access to configuration."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_saved_config)
        mock_session.execute.return_value = result
        mock_saved_config.is_accessible_by.return_value = False

        # Act & Assert
        with pytest.raises(UnauthorizedAccessError) as exc_info:
            await service.get_configuration(
                config_id=saved_config_id,
                user_id=user_id,
            )

        assert exc_info.value.code == "UNAUTHORIZED_ACCESS"
        assert str(user_id) in exc_info.value.context["user_id"]

    @pytest.mark.asyncio
    async def test_get_configuration_database_error(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        saved_config_id: UUID,
    ):
        """Test handling of database errors."""
        # Arrange
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Act & Assert
        with pytest.raises(SavedConfigurationError) as exc_info:
            await service.get_configuration(config_id=saved_config_id)

        assert exc_info.value.code == "DATABASE_ERROR"


# ============================================================================
# Unit Tests - Update Configuration
# ============================================================================


class TestUpdateConfiguration:
    """Test updating configurations."""

    @pytest.mark.asyncio
    async def test_update_configuration_name(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        saved_config_id: UUID,
        user_id: UUID,
        mock_saved_config: SavedConfiguration,
    ):
        """Test updating configuration name."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_saved_config)
        mock_session.execute.return_value = result

        # Act
        updated_config = await service.update_configuration(
            config_id=saved_config_id,
            user_id=user_id,
            name="Updated Name",
        )

        # Assert
        assert updated_config == mock_saved_config
        mock_saved_config.update_name.assert_called_once_with("Updated Name")
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_configuration_make_public(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        saved_config_id: UUID,
        user_id: UUID,
        mock_saved_config: SavedConfiguration,
    ):
        """Test making configuration public."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_saved_config)
        mock_session.execute.return_value = result

        # Act
        updated_config = await service.update_configuration(
            config_id=saved_config_id,
            user_id=user_id,
            is_public=True,
        )

        # Assert
        mock_saved_config.make_public.assert_called_once()
        mock_saved_config.make_private.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_configuration_make_private(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        saved_config_id: UUID,
        user_id: UUID,
        mock_saved_config: SavedConfiguration,
    ):
        """Test making configuration private."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_saved_config)
        mock_session.execute.return_value = result

        # Act
        updated_config = await service.update_configuration(
            config_id=saved_config_id,
            user_id=user_id,
            is_public=False,
        )

        # Assert
        mock_saved_config.make_private.assert_called_once()
        mock_saved_config.make_public.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_configuration_both_fields(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        saved_config_id: UUID,
        user_id: UUID,
        mock_saved_config: SavedConfiguration,
    ):
        """Test updating both name and public status."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_saved_config)
        mock_session.execute.return_value = result

        # Act
        updated_config = await service.update_configuration(
            config_id=saved_config_id,
            user_id=user_id,
            name="New Name",
            is_public=True,
        )

        # Assert
        mock_saved_config.update_name.assert_called_once()
        mock_saved_config.make_public.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_configuration_unauthorized(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        saved_config_id: UUID,
        user_id: UUID,
        mock_saved_config: SavedConfiguration,
    ):
        """Test unauthorized update attempt."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_saved_config)
        mock_session.execute.return_value = result
        mock_saved_config.belongs_to_user.return_value = False

        # Act & Assert
        with pytest.raises(UnauthorizedAccessError):
            await service.update_configuration(
                config_id=saved_config_id,
                user_id=user_id,
                name="New Name",
            )

    @pytest.mark.asyncio
    async def test_update_configuration_database_error(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        saved_config_id: UUID,
        user_id: UUID,
        mock_saved_config: SavedConfiguration,
    ):
        """Test handling of database errors during update."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_saved_config)
        mock_session.execute.return_value = result
        mock_session.flush.side_effect = SQLAlchemyError("Database error")

        # Act & Assert
        with pytest.raises(SavedConfigurationError) as exc_info:
            await service.update_configuration(
                config_id=saved_config_id,
                user_id=user_id,
                name="New Name",
            )

        assert exc_info.value.code == "DATABASE_ERROR"
        mock_session.rollback.assert_called_once()


# ============================================================================
# Unit Tests - Delete Configuration
# ============================================================================


class TestDeleteConfiguration:
    """Test deleting configurations."""

    @pytest.mark.asyncio
    async def test_delete_configuration_soft_delete(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        saved_config_id: UUID,
        user_id: UUID,
        mock_saved_config: SavedConfiguration,
    ):
        """Test soft deleting a configuration."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_saved_config)
        mock_session.execute.return_value = result

        # Act
        await service.delete_configuration(
            config_id=saved_config_id,
            user_id=user_id,
            hard_delete=False,
        )

        # Assert
        mock_saved_config.archive.assert_called_once()
        mock_session.delete.assert_not_called()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_configuration_hard_delete(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        saved_config_id: UUID,
        user_id: UUID,
        mock_saved_config: SavedConfiguration,
    ):
        """Test hard deleting a configuration."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_saved_config)
        mock_session.execute.return_value = result

        # Act
        await service.delete_configuration(
            config_id=saved_config_id,
            user_id=user_id,
            hard_delete=True,
        )

        # Assert
        mock_session.delete.assert_called_once_with(mock_saved_config)
        mock_saved_config.archive.assert_not_called()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_configuration_unauthorized(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        saved_config_id: UUID,
        user_id: UUID,
        mock_saved_config: SavedConfiguration,
    ):
        """Test unauthorized delete attempt."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_saved_config)
        mock_session.execute.return_value = result
        mock_saved_config.belongs_to_user.return_value = False

        # Act & Assert
        with pytest.raises(UnauthorizedAccessError):
            await service.delete_configuration(
                config_id=saved_config_id,
                user_id=user_id,
            )

    @pytest.mark.asyncio
    async def test_delete_configuration_database_error(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        saved_config_id: UUID,
        user_id: UUID,
        mock_saved_config: SavedConfiguration,
    ):
        """Test handling of database errors during deletion."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_saved_config)
        mock_session.execute.return_value = result
        mock_session.flush.side_effect = SQLAlchemyError("Database error")

        # Act & Assert
        with pytest.raises(SavedConfigurationError) as exc_info:
            await service.delete_configuration(
                config_id=saved_config_id,
                user_id=user_id,
            )

        assert exc_info.value.code == "DATABASE_ERROR"
        mock_session.rollback.assert_called_once()


# ============================================================================
# Unit Tests - Share Token Operations
# ============================================================================


class TestShareTokenOperations:
    """Test share token generation and retrieval."""

    @pytest.mark.asyncio
    async def test_generate_share_token_success(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        saved_config_id: UUID,
        user_id: UUID,
        mock_saved_config: SavedConfiguration,
        share_token: str,
    ):
        """Test generating share token."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_saved_config)
        mock_session.execute.return_value = result

        # Act
        token = await service.generate_share_token(
            config_id=saved_config_id,
            user_id=user_id,
        )

        # Assert
        assert token == share_token
        mock_saved_config.regenerate_share_token.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_share_token_unauthorized(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        saved_config_id: UUID,
        user_id: UUID,
        mock_saved_config: SavedConfiguration,
    ):
        """Test unauthorized token generation attempt."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_saved_config)
        mock_session.execute.return_value = result
        mock_saved_config.belongs_to_user.return_value = False

        # Act & Assert
        with pytest.raises(UnauthorizedAccessError):
            await service.generate_share_token(
                config_id=saved_config_id,
                user_id=user_id,
            )

    @pytest.mark.asyncio
    async def test_get_by_share_token_success(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        share_token: str,
        mock_saved_config: SavedConfiguration,
    ):
        """Test retrieving configuration by share token."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_saved_config)
        mock_session.execute.return_value = result

        # Act
        config = await service.get_by_share_token(share_token=share_token)

        # Assert
        assert config == mock_saved_config
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_share_token_not_found(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        share_token: str,
    ):
        """Test invalid share token."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute.return_value = result

        # Act & Assert
        with pytest.raises(InvalidShareTokenError) as exc_info:
            await service.get_by_share_token(share_token=share_token)

        assert exc_info.value.code == "INVALID_SHARE_TOKEN"

    @pytest.mark.asyncio
    async def test_get_by_share_token_not_shareable(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        share_token: str,
        mock_saved_config: SavedConfiguration,
    ):
        """Test accessing non-shareable configuration."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_saved_config)
        mock_session.execute.return_value = result
        mock_saved_config.can_be_shared = False

        # Act & Assert
        with pytest.raises(InvalidShareTokenError) as exc_info:
            await service.get_by_share_token(share_token=share_token)

        assert "not shareable" in exc_info.value.context.get("reason", "")

    @pytest.mark.asyncio
    async def test_get_by_share_token_database_error(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        share_token: str,
    ):
        """Test handling of database errors."""
        # Arrange
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Act & Assert
        with pytest.raises(SavedConfigurationError) as exc_info:
            await service.get_by_share_token(share_token=share_token)

        assert exc_info.value.code == "DATABASE_ERROR"


# ============================================================================
# Unit Tests - Statistics
# ============================================================================


class TestStatistics:
    """Test configuration statistics retrieval."""

    @pytest.mark.asyncio
    async def test_get_statistics_all_users(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
    ):
        """Test getting statistics for all users."""
        # Arrange
        total_result = AsyncMock()
        total_result.scalar = MagicMock(return_value=100)
        
        public_result = AsyncMock()
        public_result.scalar = MagicMock(return_value=30)
        
        mock_session.execute.side_effect = [total_result, public_result]

        # Act
        stats = await service.get_statistics()

        # Assert
        assert stats["total_configurations"] == 100
        assert stats["public_configurations"] == 30
        assert stats["private_configurations"] == 70
        assert "user_id" not in stats

    @pytest.mark.asyncio
    async def test_get_statistics_specific_user(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        user_id: UUID,
    ):
        """Test getting statistics for specific user."""
        # Arrange
        total_result = AsyncMock()
        total_result.scalar = MagicMock(return_value=10)
        
        public_result = AsyncMock()
        public_result.scalar = MagicMock(return_value=3)
        
        mock_session.execute.side_effect = [total_result, public_result]

        # Act
        stats = await service.get_statistics(user_id=user_id)

        # Assert
        assert stats["total_configurations"] == 10
        assert stats["public_configurations"] == 3
        assert stats["private_configurations"] == 7
        assert stats["user_id"] == str(user_id)

    @pytest.mark.asyncio
    async def test_get_statistics_zero_configurations(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
    ):
        """Test statistics with no configurations."""
        # Arrange
        total_result = AsyncMock()
        total_result.scalar = MagicMock(return_value=0)
        
        public_result = AsyncMock()
        public_result.scalar = MagicMock(return_value=0)
        
        mock_session.execute.side_effect = [total_result, public_result]

        # Act
        stats = await service.get_statistics()

        # Assert
        assert stats["total_configurations"] == 0
        assert stats["public_configurations"] == 0
        assert stats["private_configurations"] == 0

    @pytest.mark.asyncio
    async def test_get_statistics_database_error(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
    ):
        """Test handling of database errors."""
        # Arrange
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Act & Assert
        with pytest.raises(SavedConfigurationError) as exc_info:
            await service.get_statistics()

        assert exc_info.value.code == "DATABASE_ERROR"


# ============================================================================
# Integration Tests - Exception Hierarchy
# ============================================================================


class TestExceptionHierarchy:
    """Test custom exception classes."""

    def test_saved_configuration_error_base(self):
        """Test base exception class."""
        error = SavedConfigurationError(
            "Test error",
            code="TEST_ERROR",
            extra_field="value",
        )
        
        assert str(error) == "Test error"
        assert error.code == "TEST_ERROR"
        assert error.context["extra_field"] == "value"

    def test_configuration_not_found_error(self):
        """Test ConfigurationNotFoundError."""
        config_id = uuid4()
        error = ConfigurationNotFoundError(config_id)
        
        assert error.code == "CONFIG_NOT_FOUND"
        assert str(config_id) in error.context["config_id"]
        assert str(config_id) in str(error)

    def test_unauthorized_access_error(self):
        """Test UnauthorizedAccessError."""
        user_id = uuid4()
        config_id = uuid4()
        error = UnauthorizedAccessError(user_id, config_id)
        
        assert error.code == "UNAUTHORIZED_ACCESS"
        assert str(user_id) in error.context["user_id"]
        assert str(config_id) in error.context["config_id"]

    def test_invalid_share_token_error(self):
        """Test InvalidShareTokenError."""
        token = "test_token_12345678"
        error = InvalidShareTokenError(token)
        
        assert error.code == "INVALID_SHARE_TOKEN"
        assert error.context["token_prefix"] == "test_tok"


# ============================================================================
# Edge Cases and Boundary Tests
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_save_configuration_empty_name(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        user_id: UUID,
        configuration_id: UUID,
        mock_vehicle_config: VehicleConfiguration,
    ):
        """Test saving configuration with empty name after stripping."""
        # Arrange
        config_result = AsyncMock()
        config_result.scalar_one_or_none = MagicMock(
            return_value=mock_vehicle_config
        )
        mock_session.execute.return_value = config_result

        # Act
        result = await service.save_configuration(
            user_id=user_id,
            configuration_id=configuration_id,
            name="   ",  # Only whitespace
            is_public=False,
        )

        # Assert
        saved_config_call = mock_session.add.call_args[0][0]
        assert saved_config_call.name == ""

    @pytest.mark.asyncio
    async def test_get_user_configurations_zero_limit(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        user_id: UUID,
    ):
        """Test pagination with zero limit."""
        # Arrange
        result = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all = MagicMock(return_value=[])
        result.scalars = MagicMock(return_value=scalars_result)
        mock_session.execute.return_value = result

        # Act
        configurations = await service.get_user_configurations(
            user_id=user_id,
            limit=0,
        )

        # Assert
        assert configurations == []

    @pytest.mark.asyncio
    async def test_update_configuration_no_changes(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        saved_config_id: UUID,
        user_id: UUID,
        mock_saved_config: SavedConfiguration,
    ):
        """Test update with no actual changes."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_saved_config)
        mock_session.execute.return_value = result

        # Act
        updated_config = await service.update_configuration(
            config_id=saved_config_id,
            user_id=user_id,
            name=None,
            is_public=None,
        )

        # Assert
        assert updated_config == mock_saved_config
        mock_saved_config.update_name.assert_not_called()
        mock_saved_config.make_public.assert_not_called()
        mock_saved_config.make_private.assert_not_called()


# ============================================================================
# Performance and Concurrency Tests
# ============================================================================


class TestPerformanceAndConcurrency:
    """Test performance characteristics and concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_save_operations(
        self,
        mock_session: AsyncMock,
        user_id: UUID,
        mock_vehicle_config: VehicleConfiguration,
    ):
        """Test multiple concurrent save operations."""
        # Arrange
        service = SavedConfigurationService(session=mock_session)
        config_result = AsyncMock()
        config_result.scalar_one_or_none = MagicMock(
            return_value=mock_vehicle_config
        )
        mock_session.execute.return_value = config_result

        # Act
        tasks = [
            service.save_configuration(
                user_id=user_id,
                configuration_id=uuid4(),
                name=f"Config {i}",
                is_public=False,
            )
            for i in range(5)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assert
        assert len(results) == 5
        assert all(not isinstance(r, Exception) for r in results)

    @pytest.mark.asyncio
    async def test_get_user_configurations_large_result_set(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        user_id: UUID,
    ):
        """Test retrieving large number of configurations."""
        # Arrange
        mock_configs = [
            MagicMock(spec=SavedConfiguration) for _ in range(1000)
        ]
        result = AsyncMock()
        scalars_result = MagicMock()
        scalars_result.all = MagicMock(return_value=mock_configs)
        result.scalars = MagicMock(return_value=scalars_result)
        mock_session.execute.return_value = result

        # Act
        configurations = await service.get_user_configurations(
            user_id=user_id,
            limit=1000,
        )

        # Assert
        assert len(configurations) == 1000


# ============================================================================
# Security Tests
# ============================================================================


class TestSecurity:
    """Test security-related functionality."""

    @pytest.mark.asyncio
    async def test_share_token_uniqueness(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        user_id: UUID,
        configuration_id: UUID,
        mock_vehicle_config: VehicleConfiguration,
    ):
        """Test that share tokens are unique."""
        # Arrange
        config_result = AsyncMock()
        config_result.scalar_one_or_none = MagicMock(
            return_value=mock_vehicle_config
        )
        mock_session.execute.return_value = config_result

        # Act
        config1 = await service.save_configuration(
            user_id=user_id,
            configuration_id=configuration_id,
            name="Config 1",
            is_public=False,
        )
        
        config2 = await service.save_configuration(
            user_id=user_id,
            configuration_id=configuration_id,
            name="Config 2",
            is_public=False,
        )

        # Assert
        token1 = mock_session.add.call_args_list[0][0][0].share_token
        token2 = mock_session.add.call_args_list[1][0][0].share_token
        assert token1 != token2

    @pytest.mark.asyncio
    async def test_authorization_check_on_all_operations(
        self,
        service: SavedConfigurationService,
        mock_session: AsyncMock,
        saved_config_id: UUID,
        user_id: UUID,
        other_user_id: UUID,
        mock_saved_config: SavedConfiguration,
    ):
        """Test authorization is checked on all sensitive operations."""
        # Arrange
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=mock_saved_config)
        mock_session.execute.return_value = result
        mock_saved_config.belongs_to_user.return_value = False

        # Act & Assert - Update
        with pytest.raises(UnauthorizedAccessError):
            await service.update_configuration(
                config_id=saved_config_id,
                user_id=other_user_id,
                name="Hacked",
            )

        # Act & Assert - Delete
        with pytest.raises(UnauthorizedAccessError):
            await service.delete_configuration(
                config_id=saved_config_id,
                user_id=other_user_id,
            )

        # Act & Assert - Generate Token
        with pytest.raises(UnauthorizedAccessError):
            await service.generate_share_token(
                config_id=saved_config_id,
                user_id=other_user_id,
            )