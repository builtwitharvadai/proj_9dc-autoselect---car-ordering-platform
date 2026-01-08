"""
Saved configurations API router for vehicle configuration management.

This module provides FastAPI endpoints for managing saved vehicle configurations
including save, list, update, delete, and sharing functionality. Implements proper
authentication, authorization, input validation, and comprehensive error handling.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import CurrentActiveUser, DatabaseSession
from src.core.logging import get_logger
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
    SavedConfigurationService,
    UnauthorizedAccessError,
    get_saved_configuration_service,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/saved-configurations", tags=["saved-configurations"])


@router.post(
    "/",
    response_model=SavedConfigurationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a vehicle configuration",
    description="Save a vehicle configuration for the authenticated user with a custom name",
)
async def save_configuration(
    request: SaveConfigurationRequest,
    current_user: CurrentActiveUser,
    db: DatabaseSession,
) -> SavedConfigurationResponse:
    """
    Save a vehicle configuration for the authenticated user.

    Args:
        request: Configuration save request with name and configuration ID
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        SavedConfigurationResponse: Created saved configuration

    Raises:
        HTTPException: 400 if configuration not found or validation fails
        HTTPException: 500 if database error occurs
    """
    try:
        service = get_saved_configuration_service(db)

        saved_config = await service.save_configuration(
            user_id=current_user.id,
            configuration_id=request.configuration_id,
            name=request.name,
            is_public=request.is_public,
        )

        await db.commit()

        logger.info(
            "Configuration saved successfully",
            saved_config_id=str(saved_config.id),
            user_id=str(current_user.id),
            configuration_id=str(request.configuration_id),
            name=request.name,
        )

        return SavedConfigurationResponse(
            id=saved_config.id,
            name=saved_config.name,
            configuration_id=saved_config.configuration_id,
            user_id=saved_config.user_id,
            notes=saved_config.notes,
            is_public=saved_config.is_public,
            share_token=saved_config.share_token if saved_config.is_public else None,
            created_at=saved_config.created_at,
            updated_at=saved_config.updated_at,
            last_accessed_at=saved_config.last_accessed_at,
        )

    except SavedConfigurationError as e:
        await db.rollback()
        logger.warning(
            "Failed to save configuration",
            error=str(e),
            error_code=e.code,
            user_id=str(current_user.id),
            **e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": e.code, **e.context},
        )
    except Exception as e:
        await db.rollback()
        logger.error(
            "Unexpected error saving configuration",
            error=str(e),
            error_type=type(e).__name__,
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save configuration",
        )


@router.get(
    "/",
    response_model=list[SavedConfigurationResponse],
    summary="List user's saved configurations",
    description="Retrieve all saved configurations for the authenticated user",
)
async def list_user_configurations(
    current_user: CurrentActiveUser,
    db: DatabaseSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    include_deleted: Annotated[bool, Query()] = False,
) -> list[SavedConfigurationResponse]:
    """
    List all saved configurations for the authenticated user.

    Args:
        current_user: Authenticated user from JWT token
        db: Database session
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        include_deleted: Whether to include soft-deleted configurations

    Returns:
        List of saved configurations

    Raises:
        HTTPException: 500 if database error occurs
    """
    try:
        service = get_saved_configuration_service(db)

        configurations = await service.get_user_configurations(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            include_deleted=include_deleted,
        )

        logger.debug(
            "Retrieved user configurations",
            user_id=str(current_user.id),
            count=len(configurations),
            skip=skip,
            limit=limit,
        )

        return [
            SavedConfigurationResponse(
                id=config.id,
                name=config.name,
                configuration_id=config.configuration_id,
                user_id=config.user_id,
                notes=config.notes,
                is_public=config.is_public,
                share_token=config.share_token if config.is_public else None,
                created_at=config.created_at,
                updated_at=config.updated_at,
                last_accessed_at=config.last_accessed_at,
            )
            for config in configurations
        ]

    except Exception as e:
        logger.error(
            "Unexpected error listing configurations",
            error=str(e),
            error_type=type(e).__name__,
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configurations",
        )


@router.get(
    "/{config_id}",
    response_model=SavedConfigurationResponse,
    summary="Get saved configuration by ID",
    description="Retrieve a specific saved configuration by ID",
)
async def get_saved_configuration(
    config_id: UUID,
    current_user: CurrentActiveUser,
    db: DatabaseSession,
) -> SavedConfigurationResponse:
    """
    Get a saved configuration by ID.

    Args:
        config_id: ID of saved configuration
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        SavedConfigurationResponse: Saved configuration details

    Raises:
        HTTPException: 404 if configuration not found
        HTTPException: 403 if user not authorized to access configuration
        HTTPException: 500 if database error occurs
    """
    try:
        service = get_saved_configuration_service(db)

        saved_config = await service.get_configuration(
            config_id=config_id,
            user_id=current_user.id,
        )

        logger.debug(
            "Retrieved saved configuration",
            config_id=str(config_id),
            user_id=str(current_user.id),
        )

        return SavedConfigurationResponse(
            id=saved_config.id,
            name=saved_config.name,
            configuration_id=saved_config.configuration_id,
            user_id=saved_config.user_id,
            notes=saved_config.notes,
            is_public=saved_config.is_public,
            share_token=saved_config.share_token if saved_config.is_public else None,
            created_at=saved_config.created_at,
            updated_at=saved_config.updated_at,
            last_accessed_at=saved_config.last_accessed_at,
        )

    except ConfigurationNotFoundError as e:
        logger.warning(
            "Configuration not found",
            config_id=str(config_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(e), "code": e.code},
        )
    except UnauthorizedAccessError as e:
        logger.warning(
            "Unauthorized access attempt",
            config_id=str(config_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": str(e), "code": e.code},
        )
    except Exception as e:
        logger.error(
            "Unexpected error retrieving configuration",
            error=str(e),
            error_type=type(e).__name__,
            config_id=str(config_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configuration",
        )


@router.put(
    "/{config_id}",
    response_model=SavedConfigurationResponse,
    summary="Update saved configuration",
    description="Update name or public status of a saved configuration",
)
async def update_saved_configuration(
    config_id: UUID,
    request: UpdateSavedConfigurationRequest,
    current_user: CurrentActiveUser,
    db: DatabaseSession,
) -> SavedConfigurationResponse:
    """
    Update a saved configuration.

    Args:
        config_id: ID of saved configuration
        request: Update request with optional name and is_public fields
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        SavedConfigurationResponse: Updated saved configuration

    Raises:
        HTTPException: 404 if configuration not found
        HTTPException: 403 if user not authorized to update configuration
        HTTPException: 400 if validation fails
        HTTPException: 500 if database error occurs
    """
    try:
        service = get_saved_configuration_service(db)

        saved_config = await service.update_configuration(
            config_id=config_id,
            user_id=current_user.id,
            name=request.name,
            is_public=request.is_public,
        )

        await db.commit()

        logger.info(
            "Configuration updated successfully",
            config_id=str(config_id),
            user_id=str(current_user.id),
            name=request.name,
            is_public=request.is_public,
        )

        return SavedConfigurationResponse(
            id=saved_config.id,
            name=saved_config.name,
            configuration_id=saved_config.configuration_id,
            user_id=saved_config.user_id,
            notes=saved_config.notes,
            is_public=saved_config.is_public,
            share_token=saved_config.share_token if saved_config.is_public else None,
            created_at=saved_config.created_at,
            updated_at=saved_config.updated_at,
            last_accessed_at=saved_config.last_accessed_at,
        )

    except ConfigurationNotFoundError as e:
        await db.rollback()
        logger.warning(
            "Configuration not found for update",
            config_id=str(config_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(e), "code": e.code},
        )
    except UnauthorizedAccessError as e:
        await db.rollback()
        logger.warning(
            "Unauthorized update attempt",
            config_id=str(config_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": str(e), "code": e.code},
        )
    except SavedConfigurationError as e:
        await db.rollback()
        logger.warning(
            "Failed to update configuration",
            error=str(e),
            error_code=e.code,
            config_id=str(config_id),
            user_id=str(current_user.id),
            **e.context,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": e.code, **e.context},
        )
    except Exception as e:
        await db.rollback()
        logger.error(
            "Unexpected error updating configuration",
            error=str(e),
            error_type=type(e).__name__,
            config_id=str(config_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration",
        )


@router.delete(
    "/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete saved configuration",
    description="Delete a saved configuration (soft delete by default)",
)
async def delete_saved_configuration(
    config_id: UUID,
    current_user: CurrentActiveUser,
    db: DatabaseSession,
    hard_delete: Annotated[bool, Query()] = False,
) -> None:
    """
    Delete a saved configuration.

    Args:
        config_id: ID of saved configuration
        current_user: Authenticated user from JWT token
        db: Database session
        hard_delete: Whether to permanently delete (vs soft delete)

    Raises:
        HTTPException: 404 if configuration not found
        HTTPException: 403 if user not authorized to delete configuration
        HTTPException: 500 if database error occurs
    """
    try:
        service = get_saved_configuration_service(db)

        await service.delete_configuration(
            config_id=config_id,
            user_id=current_user.id,
            hard_delete=hard_delete,
        )

        await db.commit()

        logger.info(
            "Configuration deleted successfully",
            config_id=str(config_id),
            user_id=str(current_user.id),
            hard_delete=hard_delete,
        )

    except ConfigurationNotFoundError as e:
        await db.rollback()
        logger.warning(
            "Configuration not found for deletion",
            config_id=str(config_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(e), "code": e.code},
        )
    except UnauthorizedAccessError as e:
        await db.rollback()
        logger.warning(
            "Unauthorized deletion attempt",
            config_id=str(config_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": str(e), "code": e.code},
        )
    except Exception as e:
        await db.rollback()
        logger.error(
            "Unexpected error deleting configuration",
            error=str(e),
            error_type=type(e).__name__,
            config_id=str(config_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete configuration",
        )


@router.post(
    "/{config_id}/share",
    response_model=ShareConfigurationResponse,
    summary="Generate share link for configuration",
    description="Generate or regenerate a share token for configuration sharing",
)
async def generate_share_link(
    config_id: UUID,
    current_user: CurrentActiveUser,
    db: DatabaseSession,
) -> ShareConfigurationResponse:
    """
    Generate a share link for a saved configuration.

    Args:
        config_id: ID of saved configuration
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        ShareConfigurationResponse: Share token and URL

    Raises:
        HTTPException: 404 if configuration not found
        HTTPException: 403 if user not authorized to share configuration
        HTTPException: 500 if database error occurs
    """
    try:
        service = get_saved_configuration_service(db)

        share_token = await service.generate_share_token(
            config_id=config_id,
            user_id=current_user.id,
        )

        saved_config = await service.get_configuration(
            config_id=config_id,
            user_id=current_user.id,
        )

        await db.commit()

        share_url = f"/shared/{share_token}"

        logger.info(
            "Share link generated successfully",
            config_id=str(config_id),
            user_id=str(current_user.id),
            token_prefix=share_token[:8],
        )

        return ShareConfigurationResponse(
            share_token=share_token,
            share_url=share_url,
            expires_at=None,
            is_public=saved_config.is_public,
            created_at=saved_config.updated_at,
        )

    except ConfigurationNotFoundError as e:
        await db.rollback()
        logger.warning(
            "Configuration not found for sharing",
            config_id=str(config_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(e), "code": e.code},
        )
    except UnauthorizedAccessError as e:
        await db.rollback()
        logger.warning(
            "Unauthorized share attempt",
            config_id=str(config_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": str(e), "code": e.code},
        )
    except Exception as e:
        await db.rollback()
        logger.error(
            "Unexpected error generating share link",
            error=str(e),
            error_type=type(e).__name__,
            config_id=str(config_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate share link",
        )


@router.get(
    "/shared/{share_token}",
    response_model=SavedConfigurationResponse,
    summary="Get shared configuration",
    description="Retrieve a configuration using its share token",
)
async def get_shared_configuration(
    share_token: str,
    db: DatabaseSession,
) -> SavedConfigurationResponse:
    """
    Get a shared configuration by share token.

    Args:
        share_token: Share token for the configuration
        db: Database session

    Returns:
        SavedConfigurationResponse: Shared configuration details

    Raises:
        HTTPException: 404 if share token invalid or configuration not accessible
        HTTPException: 500 if database error occurs
    """
    try:
        service = get_saved_configuration_service(db)

        saved_config = await service.get_by_share_token(share_token=share_token)

        logger.info(
            "Shared configuration accessed",
            config_id=str(saved_config.id),
            token_prefix=share_token[:8],
        )

        return SavedConfigurationResponse(
            id=saved_config.id,
            name=saved_config.name,
            configuration_id=saved_config.configuration_id,
            user_id=saved_config.user_id,
            notes=saved_config.notes,
            is_public=saved_config.is_public,
            share_token=None,
            created_at=saved_config.created_at,
            updated_at=saved_config.updated_at,
            last_accessed_at=saved_config.last_accessed_at,
        )

    except InvalidShareTokenError as e:
        logger.warning(
            "Invalid share token access attempt",
            token_prefix=share_token[:8],
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(e), "code": e.code},
        )
    except Exception as e:
        logger.error(
            "Unexpected error accessing shared configuration",
            error=str(e),
            error_type=type(e).__name__,
            token_prefix=share_token[:8],
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve shared configuration",
        )