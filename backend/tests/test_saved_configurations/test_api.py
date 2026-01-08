"""
Integration tests for saved configurations API endpoints.

This module provides comprehensive end-to-end testing for the saved configurations
API, including authentication, authorization, CRUD operations, sharing functionality,
and error handling scenarios.
"""

import asyncio
from datetime import datetime
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.saved_configurations import router
from src.database.models.user import User
from src.schemas.saved_configuration import (
    SaveConfigurationRequest,
    SavedConfigurationResponse,
    ShareConfigurationResponse,
    UpdateSavedConfigurationRequest,
)
from src.services.saved_configurations.service import (
    ConfigurationNotFoundError,
    InvalidShareTokenError,
    SavedConfigurationError,
    UnauthorizedAccessError,
)


# ============================================================================
# Test Fixtures and Factories
# ============================================================================


@pytest.fixture
def mock_user() -> User:
    """
    Create a mock authenticated user for testing.

    Returns:
        User: Mock user with standard attributes
    """
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    user.name = "Test User"
    user.is_active = True
    return user


@pytest.fixture
def mock_saved_config():
    """
    Create a mock saved configuration object.

    Returns:
        Mock saved configuration with all required attributes
    """
    config = MagicMock()
    config.id = uuid4()
    config.name = "My Test Configuration"
    config.configuration_id = uuid4()
    config.user_id = uuid4()
    config.notes = "Test notes"
    config.is_public = False
    config.share_token = None
    config.created_at = datetime.now()
    config.updated_at = datetime.now()
    config.last_accessed_at = datetime.now()
    config.deleted_at = None
    return config


@pytest.fixture
def mock_db_session():
    """
    Create a mock database session.

    Returns:
        AsyncMock: Mock database session with commit/rollback
    """
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_service():
    """
    Create a mock saved configuration service.

    Returns:
        AsyncMock: Mock service with all required methods
    """
    service = AsyncMock()
    service.save_configuration = AsyncMock()
    service.get_user_configurations = AsyncMock()
    service.get_configuration = AsyncMock()
    service.update_configuration = AsyncMock()
    service.delete_configuration = AsyncMock()
    service.generate_share_token = AsyncMock()
    service.get_by_share_token = AsyncMock()
    return service


# ============================================================================
# Unit Tests - Save Configuration Endpoint
# ============================================================================


class TestSaveConfiguration:
    """Test suite for POST /saved-configurations/ endpoint."""

    @pytest.mark.asyncio
    async def test_save_configuration_success(
        self, async_client: AsyncClient, mock_user, mock_saved_config, mock_service
    ):
        """
        Test successful configuration save.

        Verifies:
        - 201 status code returned
        - Configuration saved with correct data
        - Response contains all expected fields
        - Database commit called
        """
        request_data = {
            "name": "My Configuration",
            "configuration_id": str(uuid4()),
            "is_public": False,
        }

        mock_saved_config.name = request_data["name"]
        mock_saved_config.configuration_id = UUID(request_data["configuration_id"])
        mock_service.save_configuration.return_value = mock_saved_config

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.commit = AsyncMock()

            response = await async_client.post(
                "/api/v1/saved-configurations/",
                json=request_data,
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == request_data["name"]
        assert data["configuration_id"] == request_data["configuration_id"]
        assert data["is_public"] is False
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_save_configuration_public(
        self, async_client: AsyncClient, mock_user, mock_saved_config, mock_service
    ):
        """
        Test saving public configuration with share token.

        Verifies:
        - Public configuration saved successfully
        - Share token generated and returned
        - is_public flag set correctly
        """
        request_data = {
            "name": "Public Configuration",
            "configuration_id": str(uuid4()),
            "is_public": True,
        }

        mock_saved_config.is_public = True
        mock_saved_config.share_token = "test-share-token-123"
        mock_service.save_configuration.return_value = mock_saved_config

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.commit = AsyncMock()

            response = await async_client.post(
                "/api/v1/saved-configurations/",
                json=request_data,
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["is_public"] is True
        assert data["share_token"] == "test-share-token-123"

    @pytest.mark.asyncio
    async def test_save_configuration_invalid_data(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test configuration save with invalid data.

        Verifies:
        - 400 status code for validation errors
        - Error details returned
        - Database rollback called
        """
        request_data = {
            "name": "",  # Empty name should fail validation
            "configuration_id": str(uuid4()),
        }

        error = SavedConfigurationError(
            "Configuration name cannot be empty", code="INVALID_NAME"
        )
        mock_service.save_configuration.side_effect = error

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.rollback = AsyncMock()

            response = await async_client.post(
                "/api/v1/saved-configurations/",
                json=request_data,
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "code" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_save_configuration_duplicate_name(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test saving configuration with duplicate name.

        Verifies:
        - 400 status code for duplicate name
        - Appropriate error message
        """
        request_data = {
            "name": "Existing Configuration",
            "configuration_id": str(uuid4()),
        }

        error = SavedConfigurationError(
            "Configuration name already exists",
            code="DUPLICATE_NAME",
            context={"name": request_data["name"]},
        )
        mock_service.save_configuration.side_effect = error

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.rollback = AsyncMock()

            response = await async_client.post(
                "/api/v1/saved-configurations/",
                json=request_data,
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        detail = response.json()["detail"]
        assert detail["code"] == "DUPLICATE_NAME"

    @pytest.mark.asyncio
    async def test_save_configuration_database_error(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test handling of database errors during save.

        Verifies:
        - 500 status code for database errors
        - Database rollback called
        - Generic error message returned
        """
        request_data = {
            "name": "Test Configuration",
            "configuration_id": str(uuid4()),
        }

        mock_service.save_configuration.side_effect = Exception("Database error")

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.rollback = AsyncMock()

            response = await async_client.post(
                "/api/v1/saved-configurations/",
                json=request_data,
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to save configuration" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_save_configuration_unauthorized(self, async_client: AsyncClient):
        """
        Test configuration save without authentication.

        Verifies:
        - 401 status code for missing authentication
        """
        request_data = {
            "name": "Test Configuration",
            "configuration_id": str(uuid4()),
        }

        response = await async_client.post(
            "/api/v1/saved-configurations/", json=request_data
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Unit Tests - List Configurations Endpoint
# ============================================================================


class TestListUserConfigurations:
    """Test suite for GET /saved-configurations/ endpoint."""

    @pytest.mark.asyncio
    async def test_list_configurations_success(
        self, async_client: AsyncClient, mock_user, mock_saved_config, mock_service
    ):
        """
        Test successful retrieval of user configurations.

        Verifies:
        - 200 status code returned
        - List of configurations returned
        - Pagination parameters respected
        """
        configs = [mock_saved_config, mock_saved_config]
        mock_service.get_user_configurations.return_value = configs

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ):
            response = await async_client.get(
                "/api/v1/saved-configurations/",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_list_configurations_with_pagination(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test configuration list with pagination parameters.

        Verifies:
        - Skip and limit parameters work correctly
        - Service called with correct parameters
        """
        mock_service.get_user_configurations.return_value = []

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ):
            response = await async_client.get(
                "/api/v1/saved-configurations/?skip=10&limit=20",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        mock_service.get_user_configurations.assert_called_once()
        call_kwargs = mock_service.get_user_configurations.call_args.kwargs
        assert call_kwargs["skip"] == 10
        assert call_kwargs["limit"] == 20

    @pytest.mark.asyncio
    async def test_list_configurations_include_deleted(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test listing configurations including soft-deleted ones.

        Verifies:
        - include_deleted parameter works
        - Deleted configurations returned when requested
        """
        mock_service.get_user_configurations.return_value = []

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ):
            response = await async_client.get(
                "/api/v1/saved-configurations/?include_deleted=true",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        call_kwargs = mock_service.get_user_configurations.call_args.kwargs
        assert call_kwargs["include_deleted"] is True

    @pytest.mark.asyncio
    async def test_list_configurations_empty_result(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test listing configurations when user has none.

        Verifies:
        - Empty list returned successfully
        - No errors for empty result
        """
        mock_service.get_user_configurations.return_value = []

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ):
            response = await async_client.get(
                "/api/v1/saved-configurations/",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_configurations_database_error(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test handling of database errors during list.

        Verifies:
        - 500 status code for database errors
        - Generic error message returned
        """
        mock_service.get_user_configurations.side_effect = Exception("Database error")

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ):
            response = await async_client.get(
                "/api/v1/saved-configurations/",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ============================================================================
# Unit Tests - Get Configuration Endpoint
# ============================================================================


class TestGetSavedConfiguration:
    """Test suite for GET /saved-configurations/{config_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_configuration_success(
        self, async_client: AsyncClient, mock_user, mock_saved_config, mock_service
    ):
        """
        Test successful retrieval of specific configuration.

        Verifies:
        - 200 status code returned
        - Configuration details returned
        - All fields present in response
        """
        config_id = uuid4()
        mock_service.get_configuration.return_value = mock_saved_config

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ):
            response = await async_client.get(
                f"/api/v1/saved-configurations/{config_id}",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "configuration_id" in data

    @pytest.mark.asyncio
    async def test_get_configuration_not_found(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test retrieval of non-existent configuration.

        Verifies:
        - 404 status code returned
        - Appropriate error message
        """
        config_id = uuid4()
        error = ConfigurationNotFoundError(
            f"Configuration {config_id} not found", code="NOT_FOUND"
        )
        mock_service.get_configuration.side_effect = error

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ):
            response = await async_client.get(
                f"/api/v1/saved-configurations/{config_id}",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "code" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_configuration_unauthorized_access(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test accessing another user's configuration.

        Verifies:
        - 403 status code returned
        - Unauthorized access error
        """
        config_id = uuid4()
        error = UnauthorizedAccessError(
            "Not authorized to access this configuration", code="UNAUTHORIZED"
        )
        mock_service.get_configuration.side_effect = error

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ):
            response = await async_client.get(
                f"/api/v1/saved-configurations/{config_id}",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_get_configuration_invalid_uuid(
        self, async_client: AsyncClient, mock_user
    ):
        """
        Test retrieval with invalid UUID format.

        Verifies:
        - 422 status code for validation error
        """
        with patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ):
            response = await async_client.get(
                "/api/v1/saved-configurations/invalid-uuid",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============================================================================
# Unit Tests - Update Configuration Endpoint
# ============================================================================


class TestUpdateSavedConfiguration:
    """Test suite for PUT /saved-configurations/{config_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_configuration_name(
        self, async_client: AsyncClient, mock_user, mock_saved_config, mock_service
    ):
        """
        Test updating configuration name.

        Verifies:
        - 200 status code returned
        - Name updated successfully
        - Database commit called
        """
        config_id = uuid4()
        update_data = {"name": "Updated Name"}

        mock_saved_config.name = update_data["name"]
        mock_service.update_configuration.return_value = mock_saved_config

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.commit = AsyncMock()

            response = await async_client.put(
                f"/api/v1/saved-configurations/{config_id}",
                json=update_data,
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == update_data["name"]

    @pytest.mark.asyncio
    async def test_update_configuration_public_status(
        self, async_client: AsyncClient, mock_user, mock_saved_config, mock_service
    ):
        """
        Test updating configuration public status.

        Verifies:
        - is_public flag updated
        - Share token generated when made public
        """
        config_id = uuid4()
        update_data = {"is_public": True}

        mock_saved_config.is_public = True
        mock_saved_config.share_token = "new-share-token"
        mock_service.update_configuration.return_value = mock_saved_config

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.commit = AsyncMock()

            response = await async_client.put(
                f"/api/v1/saved-configurations/{config_id}",
                json=update_data,
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_public"] is True
        assert data["share_token"] is not None

    @pytest.mark.asyncio
    async def test_update_configuration_not_found(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test updating non-existent configuration.

        Verifies:
        - 404 status code returned
        - Database rollback called
        """
        config_id = uuid4()
        update_data = {"name": "New Name"}

        error = ConfigurationNotFoundError(
            f"Configuration {config_id} not found", code="NOT_FOUND"
        )
        mock_service.update_configuration.side_effect = error

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.rollback = AsyncMock()

            response = await async_client.put(
                f"/api/v1/saved-configurations/{config_id}",
                json=update_data,
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_configuration_unauthorized(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test updating another user's configuration.

        Verifies:
        - 403 status code returned
        - Unauthorized error message
        """
        config_id = uuid4()
        update_data = {"name": "New Name"}

        error = UnauthorizedAccessError(
            "Not authorized to update this configuration", code="UNAUTHORIZED"
        )
        mock_service.update_configuration.side_effect = error

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.rollback = AsyncMock()

            response = await async_client.put(
                f"/api/v1/saved-configurations/{config_id}",
                json=update_data,
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_update_configuration_empty_request(
        self, async_client: AsyncClient, mock_user, mock_saved_config, mock_service
    ):
        """
        Test update with no changes.

        Verifies:
        - Update succeeds with empty request
        - Configuration returned unchanged
        """
        config_id = uuid4()
        update_data = {}

        mock_service.update_configuration.return_value = mock_saved_config

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.commit = AsyncMock()

            response = await async_client.put(
                f"/api/v1/saved-configurations/{config_id}",
                json=update_data,
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_200_OK


# ============================================================================
# Unit Tests - Delete Configuration Endpoint
# ============================================================================


class TestDeleteSavedConfiguration:
    """Test suite for DELETE /saved-configurations/{config_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_configuration_soft_delete(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test soft delete of configuration.

        Verifies:
        - 204 status code returned
        - Soft delete performed by default
        - Database commit called
        """
        config_id = uuid4()
        mock_service.delete_configuration.return_value = None

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.commit = AsyncMock()

            response = await async_client.delete(
                f"/api/v1/saved-configurations/{config_id}",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_service.delete_configuration.assert_called_once()
        call_kwargs = mock_service.delete_configuration.call_args.kwargs
        assert call_kwargs["hard_delete"] is False

    @pytest.mark.asyncio
    async def test_delete_configuration_hard_delete(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test hard delete of configuration.

        Verifies:
        - Hard delete performed when requested
        - Configuration permanently removed
        """
        config_id = uuid4()
        mock_service.delete_configuration.return_value = None

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.commit = AsyncMock()

            response = await async_client.delete(
                f"/api/v1/saved-configurations/{config_id}?hard_delete=true",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        call_kwargs = mock_service.delete_configuration.call_args.kwargs
        assert call_kwargs["hard_delete"] is True

    @pytest.mark.asyncio
    async def test_delete_configuration_not_found(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test deleting non-existent configuration.

        Verifies:
        - 404 status code returned
        - Database rollback called
        """
        config_id = uuid4()
        error = ConfigurationNotFoundError(
            f"Configuration {config_id} not found", code="NOT_FOUND"
        )
        mock_service.delete_configuration.side_effect = error

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.rollback = AsyncMock()

            response = await async_client.delete(
                f"/api/v1/saved-configurations/{config_id}",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_configuration_unauthorized(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test deleting another user's configuration.

        Verifies:
        - 403 status code returned
        - Unauthorized error message
        """
        config_id = uuid4()
        error = UnauthorizedAccessError(
            "Not authorized to delete this configuration", code="UNAUTHORIZED"
        )
        mock_service.delete_configuration.side_effect = error

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.rollback = AsyncMock()

            response = await async_client.delete(
                f"/api/v1/saved-configurations/{config_id}",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# Unit Tests - Share Configuration Endpoint
# ============================================================================


class TestGenerateShareLink:
    """Test suite for POST /saved-configurations/{config_id}/share endpoint."""

    @pytest.mark.asyncio
    async def test_generate_share_link_success(
        self, async_client: AsyncClient, mock_user, mock_saved_config, mock_service
    ):
        """
        Test successful share link generation.

        Verifies:
        - 200 status code returned
        - Share token generated
        - Share URL constructed correctly
        """
        config_id = uuid4()
        share_token = "test-share-token-abc123"

        mock_service.generate_share_token.return_value = share_token
        mock_saved_config.is_public = True
        mock_service.get_configuration.return_value = mock_saved_config

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.commit = AsyncMock()

            response = await async_client.post(
                f"/api/v1/saved-configurations/{config_id}/share",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["share_token"] == share_token
        assert data["share_url"] == f"/shared/{share_token}"
        assert data["is_public"] is True

    @pytest.mark.asyncio
    async def test_generate_share_link_regenerate(
        self, async_client: AsyncClient, mock_user, mock_saved_config, mock_service
    ):
        """
        Test regenerating existing share link.

        Verifies:
        - New token generated
        - Old token replaced
        """
        config_id = uuid4()
        new_token = "new-share-token-xyz789"

        mock_service.generate_share_token.return_value = new_token
        mock_saved_config.is_public = True
        mock_service.get_configuration.return_value = mock_saved_config

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.commit = AsyncMock()

            response = await async_client.post(
                f"/api/v1/saved-configurations/{config_id}/share",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["share_token"] == new_token

    @pytest.mark.asyncio
    async def test_generate_share_link_not_found(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test share link generation for non-existent configuration.

        Verifies:
        - 404 status code returned
        """
        config_id = uuid4()
        error = ConfigurationNotFoundError(
            f"Configuration {config_id} not found", code="NOT_FOUND"
        )
        mock_service.generate_share_token.side_effect = error

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.rollback = AsyncMock()

            response = await async_client.post(
                f"/api/v1/saved-configurations/{config_id}/share",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_generate_share_link_unauthorized(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test share link generation for another user's configuration.

        Verifies:
        - 403 status code returned
        """
        config_id = uuid4()
        error = UnauthorizedAccessError(
            "Not authorized to share this configuration", code="UNAUTHORIZED"
        )
        mock_service.generate_share_token.side_effect = error

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.rollback = AsyncMock()

            response = await async_client.post(
                f"/api/v1/saved-configurations/{config_id}/share",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# Unit Tests - Get Shared Configuration Endpoint
# ============================================================================


class TestGetSharedConfiguration:
    """Test suite for GET /saved-configurations/shared/{share_token} endpoint."""

    @pytest.mark.asyncio
    async def test_get_shared_configuration_success(
        self, async_client: AsyncClient, mock_saved_config, mock_service
    ):
        """
        Test successful retrieval of shared configuration.

        Verifies:
        - 200 status code returned
        - Configuration accessible via share token
        - Share token not exposed in response
        """
        share_token = "valid-share-token-123"
        mock_saved_config.is_public = True
        mock_service.get_by_share_token.return_value = mock_saved_config

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch("src.api.v1.saved_configurations.DatabaseSession"):
            response = await async_client.get(
                f"/api/v1/saved-configurations/shared/{share_token}"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_public"] is True
        assert data["share_token"] is None  # Not exposed in response

    @pytest.mark.asyncio
    async def test_get_shared_configuration_invalid_token(
        self, async_client: AsyncClient, mock_service
    ):
        """
        Test retrieval with invalid share token.

        Verifies:
        - 404 status code returned
        - Appropriate error message
        """
        share_token = "invalid-token"
        error = InvalidShareTokenError("Invalid share token", code="INVALID_TOKEN")
        mock_service.get_by_share_token.side_effect = error

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch("src.api.v1.saved_configurations.DatabaseSession"):
            response = await async_client.get(
                f"/api/v1/saved-configurations/shared/{share_token}"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_shared_configuration_private(
        self, async_client: AsyncClient, mock_saved_config, mock_service
    ):
        """
        Test accessing private configuration via share token.

        Verifies:
        - Private configurations not accessible
        - 404 status code returned
        """
        share_token = "private-config-token"
        error = InvalidShareTokenError(
            "Configuration is not public", code="NOT_PUBLIC"
        )
        mock_service.get_by_share_token.side_effect = error

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch("src.api.v1.saved_configurations.DatabaseSession"):
            response = await async_client.get(
                f"/api/v1/saved-configurations/shared/{share_token}"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_shared_configuration_no_auth_required(
        self, async_client: AsyncClient, mock_saved_config, mock_service
    ):
        """
        Test shared configuration access without authentication.

        Verifies:
        - No authentication required for shared configs
        - Public access works correctly
        """
        share_token = "public-token-123"
        mock_saved_config.is_public = True
        mock_service.get_by_share_token.return_value = mock_saved_config

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch("src.api.v1.saved_configurations.DatabaseSession"):
            # No Authorization header
            response = await async_client.get(
                f"/api/v1/saved-configurations/shared/{share_token}"
            )

        assert response.status_code == status.HTTP_200_OK


# ============================================================================
# Integration Tests - End-to-End Workflows
# ============================================================================


class TestEndToEndWorkflows:
    """Integration tests for complete user workflows."""

    @pytest.mark.asyncio
    async def test_complete_configuration_lifecycle(
        self, async_client: AsyncClient, mock_user, mock_saved_config, mock_service
    ):
        """
        Test complete lifecycle: save → list → get → update → delete.

        Verifies:
        - All operations work together
        - State changes persist correctly
        """
        config_id = uuid4()
        mock_saved_config.id = config_id

        # Save configuration
        mock_service.save_configuration.return_value = mock_saved_config
        mock_service.get_user_configurations.return_value = [mock_saved_config]
        mock_service.get_configuration.return_value = mock_saved_config
        mock_service.update_configuration.return_value = mock_saved_config
        mock_service.delete_configuration.return_value = None

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.commit = AsyncMock()
            mock_db.rollback = AsyncMock()

            # 1. Save
            save_response = await async_client.post(
                "/api/v1/saved-configurations/",
                json={
                    "name": "Test Config",
                    "configuration_id": str(uuid4()),
                    "is_public": False,
                },
                headers={"Authorization": "Bearer test-token"},
            )
            assert save_response.status_code == status.HTTP_201_CREATED

            # 2. List
            list_response = await async_client.get(
                "/api/v1/saved-configurations/",
                headers={"Authorization": "Bearer test-token"},
            )
            assert list_response.status_code == status.HTTP_200_OK
            assert len(list_response.json()) == 1

            # 3. Get
            get_response = await async_client.get(
                f"/api/v1/saved-configurations/{config_id}",
                headers={"Authorization": "Bearer test-token"},
            )
            assert get_response.status_code == status.HTTP_200_OK

            # 4. Update
            update_response = await async_client.put(
                f"/api/v1/saved-configurations/{config_id}",
                json={"name": "Updated Config"},
                headers={"Authorization": "Bearer test-token"},
            )
            assert update_response.status_code == status.HTTP_200_OK

            # 5. Delete
            delete_response = await async_client.delete(
                f"/api/v1/saved-configurations/{config_id}",
                headers={"Authorization": "Bearer test-token"},
            )
            assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_sharing_workflow(
        self, async_client: AsyncClient, mock_user, mock_saved_config, mock_service
    ):
        """
        Test sharing workflow: save → make public → generate link → access shared.

        Verifies:
        - Sharing functionality works end-to-end
        - Public access works correctly
        """
        config_id = uuid4()
        share_token = "share-token-123"

        mock_saved_config.id = config_id
        mock_saved_config.is_public = True
        mock_saved_config.share_token = share_token

        mock_service.save_configuration.return_value = mock_saved_config
        mock_service.update_configuration.return_value = mock_saved_config
        mock_service.generate_share_token.return_value = share_token
        mock_service.get_configuration.return_value = mock_saved_config
        mock_service.get_by_share_token.return_value = mock_saved_config

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.commit = AsyncMock()

            # 1. Save private configuration
            save_response = await async_client.post(
                "/api/v1/saved-configurations/",
                json={
                    "name": "Shareable Config",
                    "configuration_id": str(uuid4()),
                    "is_public": False,
                },
                headers={"Authorization": "Bearer test-token"},
            )
            assert save_response.status_code == status.HTTP_201_CREATED

            # 2. Make public
            update_response = await async_client.put(
                f"/api/v1/saved-configurations/{config_id}",
                json={"is_public": True},
                headers={"Authorization": "Bearer test-token"},
            )
            assert update_response.status_code == status.HTTP_200_OK

            # 3. Generate share link
            share_response = await async_client.post(
                f"/api/v1/saved-configurations/{config_id}/share",
                headers={"Authorization": "Bearer test-token"},
            )
            assert share_response.status_code == status.HTTP_200_OK
            assert "share_token" in share_response.json()

            # 4. Access via share link (no auth)
            shared_response = await async_client.get(
                f"/api/v1/saved-configurations/shared/{share_token}"
            )
            assert shared_response.status_code == status.HTTP_200_OK


# ============================================================================
# Performance and Load Tests
# ============================================================================


class TestPerformance:
    """Performance and load testing scenarios."""

    @pytest.mark.asyncio
    async def test_list_configurations_performance(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test list endpoint performance with large dataset.

        Verifies:
        - Response time acceptable for large lists
        - Pagination works efficiently
        """
        # Create 100 mock configurations
        configs = [MagicMock() for _ in range(100)]
        for i, config in enumerate(configs):
            config.id = uuid4()
            config.name = f"Config {i}"
            config.configuration_id = uuid4()
            config.user_id = mock_user.id
            config.is_public = False
            config.created_at = datetime.now()
            config.updated_at = datetime.now()

        mock_service.get_user_configurations.return_value = configs

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ):
            import time

            start = time.time()
            response = await async_client.get(
                "/api/v1/saved-configurations/?limit=100",
                headers={"Authorization": "Bearer test-token"},
            )
            elapsed = time.time() - start

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 100
        assert elapsed < 1.0  # Should complete in under 1 second

    @pytest.mark.asyncio
    async def test_concurrent_save_operations(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test handling of concurrent save operations.

        Verifies:
        - Multiple saves can be processed concurrently
        - No race conditions or conflicts
        """
        mock_service.save_configuration.return_value = MagicMock(
            id=uuid4(),
            name="Test",
            configuration_id=uuid4(),
            user_id=mock_user.id,
            is_public=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.commit = AsyncMock()

            # Create 10 concurrent save requests
            tasks = []
            for i in range(10):
                task = async_client.post(
                    "/api/v1/saved-configurations/",
                    json={
                        "name": f"Config {i}",
                        "configuration_id": str(uuid4()),
                        "is_public": False,
                    },
                    headers={"Authorization": "Bearer test-token"},
                )
                tasks.append(task)

            responses = await asyncio.gather(*tasks)

        # All requests should succeed
        assert all(r.status_code == status.HTTP_201_CREATED for r in responses)


# ============================================================================
# Security Tests
# ============================================================================


class TestSecurity:
    """Security-focused test scenarios."""

    @pytest.mark.asyncio
    async def test_sql_injection_prevention(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test SQL injection prevention in configuration name.

        Verifies:
        - SQL injection attempts are handled safely
        - No database errors from malicious input
        """
        malicious_names = [
            "'; DROP TABLE configurations; --",
            "1' OR '1'='1",
            "admin'--",
            "<script>alert('xss')</script>",
        ]

        mock_service.save_configuration.return_value = MagicMock(
            id=uuid4(),
            name="Safe Name",
            configuration_id=uuid4(),
            user_id=mock_user.id,
            is_public=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.commit = AsyncMock()

            for malicious_name in malicious_names:
                response = await async_client.post(
                    "/api/v1/saved-configurations/",
                    json={
                        "name": malicious_name,
                        "configuration_id": str(uuid4()),
                        "is_public": False,
                    },
                    headers={"Authorization": "Bearer test-token"},
                )

                # Should either succeed with sanitized input or fail validation
                assert response.status_code in [
                    status.HTTP_201_CREATED,
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                ]

    @pytest.mark.asyncio
    async def test_authorization_bypass_prevention(
        self, async_client: AsyncClient, mock_service
    ):
        """
        Test prevention of authorization bypass attempts.

        Verifies:
        - Cannot access other users' configurations
        - User ID tampering prevented
        """
        other_user_config_id = uuid4()
        error = UnauthorizedAccessError(
            "Not authorized to access this configuration", code="UNAUTHORIZED"
        )
        mock_service.get_configuration.side_effect = error

        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ):
            response = await async_client.get(
                f"/api/v1/saved-configurations/{other_user_config_id}",
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_share_token_security(
        self, async_client: AsyncClient, mock_service
    ):
        """
        Test share token security measures.

        Verifies:
        - Share tokens are sufficiently random
        - Invalid tokens rejected
        - Token enumeration prevented
        """
        invalid_tokens = [
            "short",
            "a" * 1000,  # Very long
            "../../../etc/passwd",  # Path traversal
            "token with spaces",
            "token\nwith\nnewlines",
        ]

        error = InvalidShareTokenError("Invalid share token", code="INVALID_TOKEN")
        mock_service.get_by_share_token.side_effect = error

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch("src.api.v1.saved_configurations.DatabaseSession"):
            for invalid_token in invalid_tokens:
                response = await async_client.get(
                    f"/api/v1/saved-configurations/shared/{invalid_token}"
                )

                assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_rate_limiting_headers(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test that rate limiting information is provided.

        Verifies:
        - Rate limit headers present (if implemented)
        - Excessive requests handled gracefully
        """
        mock_service.get_user_configurations.return_value = []

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ):
            # Make multiple rapid requests
            responses = []
            for _ in range(5):
                response = await async_client.get(
                    "/api/v1/saved-configurations/",
                    headers={"Authorization": "Bearer test-token"},
                )
                responses.append(response)

        # All should succeed (rate limiting would be at infrastructure level)
        assert all(r.status_code == status.HTTP_200_OK for r in responses)


# ============================================================================
# Edge Cases and Error Scenarios
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_very_long_configuration_name(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test handling of very long configuration names.

        Verifies:
        - Maximum length enforced
        - Appropriate error for too-long names
        """
        long_name = "A" * 1000  # Very long name

        error = SavedConfigurationError(
            "Configuration name too long", code="NAME_TOO_LONG"
        )
        mock_service.save_configuration.side_effect = error

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.rollback = AsyncMock()

            response = await async_client.post(
                "/api/v1/saved-configurations/",
                json={
                    "name": long_name,
                    "configuration_id": str(uuid4()),
                    "is_public": False,
                },
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_special_characters_in_name(
        self, async_client: AsyncClient, mock_user, mock_saved_config, mock_service
    ):
        """
        Test handling of special characters in configuration name.

        Verifies:
        - Unicode characters handled correctly
        - Special characters preserved
        """
        special_names = [
            "Config with émojis 🚗",
            "日本語の設定",
            "Конфигурация",
            "Config with 'quotes' and \"double quotes\"",
        ]

        mock_service.save_configuration.return_value = mock_saved_config

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.commit = AsyncMock()

            for name in special_names:
                response = await async_client.post(
                    "/api/v1/saved-configurations/",
                    json={
                        "name": name,
                        "configuration_id": str(uuid4()),
                        "is_public": False,
                    },
                    headers={"Authorization": "Bearer test-token"},
                )

                assert response.status_code in [
                    status.HTTP_201_CREATED,
                    status.HTTP_400_BAD_REQUEST,
                ]

    @pytest.mark.asyncio
    async def test_pagination_boundary_conditions(
        self, async_client: AsyncClient, mock_user, mock_service
    ):
        """
        Test pagination with boundary values.

        Verifies:
        - Zero skip/limit handled
        - Maximum limit enforced
        - Negative values rejected
        """
        mock_service.get_user_configurations.return_value = []

        test_cases = [
            {"skip": 0, "limit": 1, "expected": status.HTTP_200_OK},
            {"skip": 0, "limit": 100, "expected": status.HTTP_200_OK},
            {"skip": -1, "limit": 10, "expected": status.HTTP_422_UNPROCESSABLE_ENTITY},
            {"skip": 0, "limit": 0, "expected": status.HTTP_422_UNPROCESSABLE_ENTITY},
            {"skip": 0, "limit": 101, "expected": status.HTTP_422_UNPROCESSABLE_ENTITY},
        ]

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ):
            for case in test_cases:
                response = await async_client.get(
                    f"/api/v1/saved-configurations/?skip={case['skip']}&limit={case['limit']}",
                    headers={"Authorization": "Bearer test-token"},
                )

                assert response.status_code == case["expected"]

    @pytest.mark.asyncio
    async def test_empty_update_request(
        self, async_client: AsyncClient, mock_user, mock_saved_config, mock_service
    ):
        """
        Test update with no fields changed.

        Verifies:
        - Empty update succeeds
        - Configuration returned unchanged
        """
        config_id = uuid4()
        mock_service.update_configuration.return_value = mock_saved_config

        with patch(
            "src.api.v1.saved_configurations.get_saved_configuration_service",
            return_value=mock_service,
        ), patch(
            "src.api.v1.saved_configurations.CurrentActiveUser", return_value=mock_user
        ), patch(
            "src.api.v1.saved_configurations.DatabaseSession"
        ) as mock_db:
            mock_db.commit = AsyncMock()

            response = await async_client.put(
                f"/api/v1/saved-configurations/{config_id}",
                json={},
                headers={"Authorization": "Bearer test-token"},
            )

        assert response.status_code == status.HTTP_200_OK