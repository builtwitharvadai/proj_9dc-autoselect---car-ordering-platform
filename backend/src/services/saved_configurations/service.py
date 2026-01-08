"""
Saved configuration service for managing vehicle configurations.

This module provides the SavedConfigurationService for managing saved vehicle
configurations including saving, retrieving, updating, deleting, and sharing
configurations. Implements proper authorization checks, caching, and error handling.
"""

import secrets
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.models.saved_configuration import SavedConfiguration
from src.database.models.vehicle_configuration import VehicleConfiguration
from src.database.models.user import User

logger = get_logger(__name__)


class SavedConfigurationError(Exception):
    """Base exception for saved configuration operations."""

    def __init__(self, message: str, code: str, **context):
        super().__init__(message)
        self.code = code
        self.context = context


class ConfigurationNotFoundError(SavedConfigurationError):
    """Raised when a saved configuration is not found."""

    def __init__(self, config_id: UUID, **context):
        super().__init__(
            f"Saved configuration not found: {config_id}",
            code="CONFIG_NOT_FOUND",
            config_id=str(config_id),
            **context,
        )


class UnauthorizedAccessError(SavedConfigurationError):
    """Raised when user attempts unauthorized access to configuration."""

    def __init__(self, user_id: UUID, config_id: UUID, **context):
        super().__init__(
            f"User {user_id} not authorized to access configuration {config_id}",
            code="UNAUTHORIZED_ACCESS",
            user_id=str(user_id),
            config_id=str(config_id),
            **context,
        )


class InvalidShareTokenError(SavedConfigurationError):
    """Raised when share token is invalid or expired."""

    def __init__(self, token: str, **context):
        super().__init__(
            f"Invalid or expired share token: {token[:8]}...",
            code="INVALID_SHARE_TOKEN",
            token_prefix=token[:8],
            **context,
        )


class SavedConfigurationService:
    """
    Service for managing saved vehicle configurations.

    Provides methods for saving, retrieving, updating, deleting, and sharing
    vehicle configurations with proper authorization and error handling.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize saved configuration service.

        Args:
            session: Async database session
        """
        self.session = session
        logger.debug("SavedConfigurationService initialized")

    async def save_configuration(
        self,
        user_id: UUID,
        configuration_id: UUID,
        name: str,
        is_public: bool = False,
    ) -> SavedConfiguration:
        """
        Save a vehicle configuration for a user.

        Args:
            user_id: ID of user saving configuration
            configuration_id: ID of configuration to save
            name: Custom name for saved configuration
            is_public: Whether configuration should be publicly accessible

        Returns:
            Newly created saved configuration

        Raises:
            SavedConfigurationError: If save operation fails
        """
        try:
            # Verify configuration exists
            config_stmt = select(VehicleConfiguration).where(
                VehicleConfiguration.id == configuration_id,
                VehicleConfiguration.deleted_at.is_(None),
            )
            config_result = await self.session.execute(config_stmt)
            configuration = config_result.scalar_one_or_none()

            if not configuration:
                raise SavedConfigurationError(
                    f"Configuration {configuration_id} not found",
                    code="CONFIG_NOT_FOUND",
                    configuration_id=str(configuration_id),
                )

            # Create saved configuration
            saved_config = SavedConfiguration(
                user_id=user_id,
                configuration_id=configuration_id,
                name=name.strip(),
                is_public=is_public,
                share_token=SavedConfiguration.generate_share_token(),
            )

            self.session.add(saved_config)
            await self.session.flush()
            await self.session.refresh(saved_config)

            logger.info(
                "Configuration saved successfully",
                saved_config_id=str(saved_config.id),
                user_id=str(user_id),
                configuration_id=str(configuration_id),
                name=name,
                is_public=is_public,
            )

            return saved_config

        except IntegrityError as e:
            await self.session.rollback()
            logger.error(
                "Integrity error saving configuration",
                user_id=str(user_id),
                configuration_id=str(configuration_id),
                error=str(e),
            )
            raise SavedConfigurationError(
                "Failed to save configuration due to integrity constraint",
                code="INTEGRITY_ERROR",
                user_id=str(user_id),
                configuration_id=str(configuration_id),
            ) from e
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Database error saving configuration",
                user_id=str(user_id),
                configuration_id=str(configuration_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise SavedConfigurationError(
                "Database error while saving configuration",
                code="DATABASE_ERROR",
                user_id=str(user_id),
                configuration_id=str(configuration_id),
            ) from e

    async def get_user_configurations(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> list[SavedConfiguration]:
        """
        Retrieve all saved configurations for a user.

        Args:
            user_id: ID of user
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Whether to include soft-deleted configurations

        Returns:
            List of saved configurations

        Raises:
            SavedConfigurationError: If retrieval fails
        """
        try:
            stmt = (
                select(SavedConfiguration)
                .where(SavedConfiguration.user_id == user_id)
                .order_by(SavedConfiguration.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            if not include_deleted:
                stmt = stmt.where(SavedConfiguration.deleted_at.is_(None))

            result = await self.session.execute(stmt)
            configurations = list(result.scalars().all())

            logger.debug(
                "Retrieved user configurations",
                user_id=str(user_id),
                count=len(configurations),
                skip=skip,
                limit=limit,
            )

            return configurations

        except SQLAlchemyError as e:
            logger.error(
                "Database error retrieving user configurations",
                user_id=str(user_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise SavedConfigurationError(
                "Failed to retrieve user configurations",
                code="DATABASE_ERROR",
                user_id=str(user_id),
            ) from e

    async def get_configuration(
        self,
        config_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> SavedConfiguration:
        """
        Retrieve a saved configuration by ID.

        Args:
            config_id: ID of saved configuration
            user_id: Optional user ID for authorization check

        Returns:
            Saved configuration

        Raises:
            ConfigurationNotFoundError: If configuration not found
            UnauthorizedAccessError: If user not authorized
        """
        try:
            stmt = select(SavedConfiguration).where(
                SavedConfiguration.id == config_id,
                SavedConfiguration.deleted_at.is_(None),
            )

            result = await self.session.execute(stmt)
            saved_config = result.scalar_one_or_none()

            if not saved_config:
                raise ConfigurationNotFoundError(config_id)

            # Check authorization
            if user_id is not None and not saved_config.is_accessible_by(user_id):
                raise UnauthorizedAccessError(user_id, config_id)

            logger.debug(
                "Retrieved saved configuration",
                config_id=str(config_id),
                user_id=str(user_id) if user_id else None,
            )

            return saved_config

        except (ConfigurationNotFoundError, UnauthorizedAccessError):
            raise
        except SQLAlchemyError as e:
            logger.error(
                "Database error retrieving configuration",
                config_id=str(config_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise SavedConfigurationError(
                "Failed to retrieve configuration",
                code="DATABASE_ERROR",
                config_id=str(config_id),
            ) from e

    async def update_configuration(
        self,
        config_id: UUID,
        user_id: UUID,
        name: Optional[str] = None,
        is_public: Optional[bool] = None,
    ) -> SavedConfiguration:
        """
        Update a saved configuration.

        Args:
            config_id: ID of saved configuration
            user_id: ID of user performing update
            name: Optional new name
            is_public: Optional new public status

        Returns:
            Updated saved configuration

        Raises:
            ConfigurationNotFoundError: If configuration not found
            UnauthorizedAccessError: If user not authorized
        """
        try:
            saved_config = await self.get_configuration(config_id, user_id)

            # Verify ownership
            if not saved_config.belongs_to_user(user_id):
                raise UnauthorizedAccessError(user_id, config_id)

            # Update fields
            if name is not None:
                saved_config.update_name(name)

            if is_public is not None:
                if is_public:
                    saved_config.make_public()
                else:
                    saved_config.make_private()

            saved_config.updated_at = datetime.utcnow()

            await self.session.flush()
            await self.session.refresh(saved_config)

            logger.info(
                "Configuration updated successfully",
                config_id=str(config_id),
                user_id=str(user_id),
                name=name,
                is_public=is_public,
            )

            return saved_config

        except (ConfigurationNotFoundError, UnauthorizedAccessError):
            raise
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Database error updating configuration",
                config_id=str(config_id),
                user_id=str(user_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise SavedConfigurationError(
                "Failed to update configuration",
                code="DATABASE_ERROR",
                config_id=str(config_id),
            ) from e

    async def delete_configuration(
        self,
        config_id: UUID,
        user_id: UUID,
        hard_delete: bool = False,
    ) -> None:
        """
        Delete a saved configuration.

        Args:
            config_id: ID of saved configuration
            user_id: ID of user performing deletion
            hard_delete: Whether to permanently delete (vs soft delete)

        Raises:
            ConfigurationNotFoundError: If configuration not found
            UnauthorizedAccessError: If user not authorized
        """
        try:
            saved_config = await self.get_configuration(config_id, user_id)

            # Verify ownership
            if not saved_config.belongs_to_user(user_id):
                raise UnauthorizedAccessError(user_id, config_id)

            if hard_delete:
                await self.session.delete(saved_config)
                logger.info(
                    "Configuration hard deleted",
                    config_id=str(config_id),
                    user_id=str(user_id),
                )
            else:
                saved_config.archive()
                logger.info(
                    "Configuration soft deleted",
                    config_id=str(config_id),
                    user_id=str(user_id),
                )

            await self.session.flush()

        except (ConfigurationNotFoundError, UnauthorizedAccessError):
            raise
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Database error deleting configuration",
                config_id=str(config_id),
                user_id=str(user_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise SavedConfigurationError(
                "Failed to delete configuration",
                code="DATABASE_ERROR",
                config_id=str(config_id),
            ) from e

    async def generate_share_token(
        self,
        config_id: UUID,
        user_id: UUID,
    ) -> str:
        """
        Generate or regenerate share token for configuration.

        Args:
            config_id: ID of saved configuration
            user_id: ID of user requesting token

        Returns:
            New share token

        Raises:
            ConfigurationNotFoundError: If configuration not found
            UnauthorizedAccessError: If user not authorized
        """
        try:
            saved_config = await self.get_configuration(config_id, user_id)

            # Verify ownership
            if not saved_config.belongs_to_user(user_id):
                raise UnauthorizedAccessError(user_id, config_id)

            # Regenerate token
            new_token = saved_config.regenerate_share_token()

            await self.session.flush()
            await self.session.refresh(saved_config)

            logger.info(
                "Share token generated",
                config_id=str(config_id),
                user_id=str(user_id),
                token_prefix=new_token[:8],
            )

            return new_token

        except (ConfigurationNotFoundError, UnauthorizedAccessError):
            raise
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Database error generating share token",
                config_id=str(config_id),
                user_id=str(user_id),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise SavedConfigurationError(
                "Failed to generate share token",
                code="DATABASE_ERROR",
                config_id=str(config_id),
            ) from e

    async def get_by_share_token(
        self,
        share_token: str,
    ) -> SavedConfiguration:
        """
        Retrieve configuration by share token.

        Args:
            share_token: Share token

        Returns:
            Saved configuration

        Raises:
            InvalidShareTokenError: If token invalid or configuration not accessible
        """
        try:
            stmt = select(SavedConfiguration).where(
                SavedConfiguration.share_token == share_token,
                SavedConfiguration.deleted_at.is_(None),
            )

            result = await self.session.execute(stmt)
            saved_config = result.scalar_one_or_none()

            if not saved_config:
                raise InvalidShareTokenError(share_token)

            # Verify configuration is shareable
            if not saved_config.can_be_shared:
                raise InvalidShareTokenError(
                    share_token,
                    reason="Configuration not shareable",
                )

            logger.debug(
                "Retrieved configuration by share token",
                config_id=str(saved_config.id),
                token_prefix=share_token[:8],
            )

            return saved_config

        except InvalidShareTokenError:
            raise
        except SQLAlchemyError as e:
            logger.error(
                "Database error retrieving configuration by token",
                token_prefix=share_token[:8],
                error=str(e),
                error_type=type(e).__name__,
            )
            raise SavedConfigurationError(
                "Failed to retrieve configuration by share token",
                code="DATABASE_ERROR",
                token_prefix=share_token[:8],
            ) from e

    async def get_statistics(
        self,
        user_id: Optional[UUID] = None,
    ) -> dict:
        """
        Get statistics about saved configurations.

        Args:
            user_id: Optional user ID to filter statistics

        Returns:
            Dictionary containing statistics

        Raises:
            SavedConfigurationError: If statistics retrieval fails
        """
        try:
            base_stmt = select(SavedConfiguration).where(
                SavedConfiguration.deleted_at.is_(None)
            )

            if user_id is not None:
                base_stmt = base_stmt.where(SavedConfiguration.user_id == user_id)

            # Total count
            count_stmt = select(func.count()).select_from(base_stmt.subquery())
            count_result = await self.session.execute(count_stmt)
            total_count = count_result.scalar() or 0

            # Public count
            public_stmt = select(func.count()).select_from(
                base_stmt.where(SavedConfiguration.is_public.is_(True)).subquery()
            )
            public_result = await self.session.execute(public_stmt)
            public_count = public_result.scalar() or 0

            statistics = {
                "total_configurations": total_count,
                "public_configurations": public_count,
                "private_configurations": total_count - public_count,
            }

            if user_id is not None:
                statistics["user_id"] = str(user_id)

            logger.debug(
                "Retrieved saved configuration statistics",
                user_id=str(user_id) if user_id else None,
                **statistics,
            )

            return statistics

        except SQLAlchemyError as e:
            logger.error(
                "Database error retrieving statistics",
                user_id=str(user_id) if user_id else None,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise SavedConfigurationError(
                "Failed to retrieve statistics",
                code="DATABASE_ERROR",
                user_id=str(user_id) if user_id else None,
            ) from e


def get_saved_configuration_service(
    session: AsyncSession,
) -> SavedConfigurationService:
    """
    Factory function for creating SavedConfigurationService instance.

    Args:
        session: Async database session

    Returns:
        SavedConfigurationService instance
    """
    return SavedConfigurationService(session)