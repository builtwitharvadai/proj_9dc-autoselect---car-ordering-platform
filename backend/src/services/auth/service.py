"""
Authentication service implementation.

This module provides comprehensive authentication services including user registration,
login, token refresh, and user management. Implements secure password handling with
bcrypt, JWT token generation, and role-based access control.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.security import create_access_token, create_refresh_token
from src.database.models.user import User, UserRole
from src.schemas.auth import (
    UserCreate,
    UserLogin,
    TokenResponse,
    UserResponse,
)

logger = get_logger(__name__)
settings = get_settings()

# Password hashing context with bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticationError(Exception):
    """Base exception for authentication errors."""

    def __init__(self, message: str, code: str = "AUTH_ERROR"):
        super().__init__(message)
        self.code = code


class RegistrationError(AuthenticationError):
    """Exception raised during user registration."""

    def __init__(self, message: str):
        super().__init__(message, code="REGISTRATION_ERROR")


class LoginError(AuthenticationError):
    """Exception raised during login."""

    def __init__(self, message: str):
        super().__init__(message, code="LOGIN_ERROR")


class AuthService:
    """
    Authentication service for user management and authentication.

    Provides secure user registration, login, token generation, and user
    management operations. Implements password hashing with bcrypt, JWT
    token generation, and comprehensive security measures.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize authentication service.

        Args:
            session: Async database session for operations
        """
        self.session = session
        self.logger = logger.bind(service="auth")

    async def register_user(
        self,
        user_data: UserCreate,
        created_by: Optional[uuid.UUID] = None,
    ) -> User:
        """
        Register a new user with email uniqueness validation.

        Args:
            user_data: User registration data
            created_by: UUID of user creating this account (for audit)

        Returns:
            Created user instance

        Raises:
            RegistrationError: If email already exists or validation fails
        """
        self.logger.info(
            "User registration started",
            email=user_data.email,
            role=user_data.role.value if user_data.role else "customer",
        )

        try:
            # Check email uniqueness
            existing_user = await self._get_user_by_email(user_data.email)
            if existing_user:
                self.logger.warning(
                    "Registration failed - email already exists",
                    email=user_data.email,
                )
                raise RegistrationError(
                    f"User with email {user_data.email} already exists"
                )

            # Hash password
            password_hash = self._hash_password(user_data.password)

            # Create user instance
            user = User(
                id=uuid.uuid4(),
                email=user_data.email.lower().strip(),
                password_hash=password_hash,
                first_name=user_data.first_name.strip(),
                last_name=user_data.last_name.strip(),
                role=user_data.role or UserRole.CUSTOMER,
                is_active=True,
                is_verified=False,
                created_by=created_by,
                updated_by=created_by,
            )

            # Persist to database
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)

            self.logger.info(
                "User registered successfully",
                user_id=str(user.id),
                email=user.email,
                role=user.role.value,
            )

            return user

        except RegistrationError:
            await self.session.rollback()
            raise
        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "User registration failed",
                email=user_data.email,
                error=str(e),
                exc_info=True,
            )
            raise RegistrationError(f"Registration failed: {str(e)}") from e

    async def login_user(self, login_data: UserLogin) -> TokenResponse:
        """
        Authenticate user and generate JWT tokens.

        Args:
            login_data: User login credentials

        Returns:
            Token response with access and refresh tokens

        Raises:
            LoginError: If credentials are invalid or account is locked
        """
        self.logger.info("Login attempt", email=login_data.email)

        try:
            # Retrieve user by email
            user = await self._get_user_by_email(login_data.email)
            if not user:
                self.logger.warning(
                    "Login failed - user not found",
                    email=login_data.email,
                )
                raise LoginError("Invalid email or password")

            # Check if account is locked
            if user.is_locked:
                self.logger.warning(
                    "Login failed - account locked",
                    user_id=str(user.id),
                    locked_until=user.locked_until.isoformat()
                    if user.locked_until
                    else None,
                )
                raise LoginError(
                    f"Account is locked until {user.locked_until.isoformat()}"
                )

            # Check if account is active
            if not user.is_active:
                self.logger.warning(
                    "Login failed - account inactive",
                    user_id=str(user.id),
                )
                raise LoginError("Account is inactive")

            # Verify password
            if not self._verify_password(login_data.password, user.password_hash):
                user.increment_failed_login()
                await self.session.commit()

                self.logger.warning(
                    "Login failed - invalid password",
                    user_id=str(user.id),
                    failed_attempts=user.failed_login_attempts,
                )
                raise LoginError("Invalid email or password")

            # Record successful login
            user.record_login()
            await self.session.commit()

            # Generate tokens
            access_token = create_access_token(
                data={"sub": str(user.id), "role": user.role.value}
            )
            refresh_token = create_refresh_token(data={"sub": str(user.id)})

            self.logger.info(
                "Login successful",
                user_id=str(user.id),
                email=user.email,
                role=user.role.value,
            )

            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )

        except LoginError:
            raise
        except Exception as e:
            self.logger.error(
                "Login failed",
                email=login_data.email,
                error=str(e),
                exc_info=True,
            )
            raise LoginError(f"Login failed: {str(e)}") from e

    async def refresh_token(self, user_id: uuid.UUID) -> TokenResponse:
        """
        Generate new access token using refresh token.

        Args:
            user_id: UUID of user requesting token refresh

        Returns:
            Token response with new access token

        Raises:
            AuthenticationError: If user not found or inactive
        """
        self.logger.info("Token refresh requested", user_id=str(user_id))

        try:
            user = await self._get_user_by_id(user_id)
            if not user:
                self.logger.warning(
                    "Token refresh failed - user not found",
                    user_id=str(user_id),
                )
                raise AuthenticationError("User not found")

            if not user.is_active:
                self.logger.warning(
                    "Token refresh failed - account inactive",
                    user_id=str(user_id),
                )
                raise AuthenticationError("Account is inactive")

            # Generate new access token
            access_token = create_access_token(
                data={"sub": str(user.id), "role": user.role.value}
            )

            self.logger.info(
                "Token refreshed successfully",
                user_id=str(user_id),
            )

            return TokenResponse(
                access_token=access_token,
                refresh_token=None,
                token_type="bearer",
                expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )

        except AuthenticationError:
            raise
        except Exception as e:
            self.logger.error(
                "Token refresh failed",
                user_id=str(user_id),
                error=str(e),
                exc_info=True,
            )
            raise AuthenticationError(f"Token refresh failed: {str(e)}") from e

    async def get_user(self, user_id: uuid.UUID) -> Optional[UserResponse]:
        """
        Retrieve user by ID.

        Args:
            user_id: UUID of user to retrieve

        Returns:
            User response or None if not found
        """
        self.logger.debug("Retrieving user", user_id=str(user_id))

        try:
            user = await self._get_user_by_id(user_id)
            if not user:
                return None

            return UserResponse(
                id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.role,
                is_active=user.is_active,
                is_verified=user.is_verified,
                created_at=user.created_at,
                last_login_at=user.last_login_at,
            )

        except Exception as e:
            self.logger.error(
                "Failed to retrieve user",
                user_id=str(user_id),
                error=str(e),
                exc_info=True,
            )
            return None

    async def update_user_role(
        self,
        user_id: uuid.UUID,
        new_role: UserRole,
        updated_by: uuid.UUID,
    ) -> User:
        """
        Update user role.

        Args:
            user_id: UUID of user to update
            new_role: New role to assign
            updated_by: UUID of user performing update

        Returns:
            Updated user instance

        Raises:
            AuthenticationError: If user not found
        """
        self.logger.info(
            "Updating user role",
            user_id=str(user_id),
            new_role=new_role.value,
            updated_by=str(updated_by),
        )

        try:
            user = await self._get_user_by_id(user_id)
            if not user:
                raise AuthenticationError("User not found")

            old_role = user.role
            user.update_role(new_role)
            user.updated_by = updated_by

            await self.session.commit()
            await self.session.refresh(user)

            self.logger.info(
                "User role updated successfully",
                user_id=str(user_id),
                old_role=old_role.value,
                new_role=new_role.value,
            )

            return user

        except AuthenticationError:
            await self.session.rollback()
            raise
        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to update user role",
                user_id=str(user_id),
                error=str(e),
                exc_info=True,
            )
            raise AuthenticationError(f"Role update failed: {str(e)}") from e

    async def verify_user_email(self, user_id: uuid.UUID) -> User:
        """
        Mark user email as verified.

        Args:
            user_id: UUID of user to verify

        Returns:
            Updated user instance

        Raises:
            AuthenticationError: If user not found
        """
        self.logger.info("Verifying user email", user_id=str(user_id))

        try:
            user = await self._get_user_by_id(user_id)
            if not user:
                raise AuthenticationError("User not found")

            user.verify_email()
            await self.session.commit()
            await self.session.refresh(user)

            self.logger.info(
                "User email verified successfully",
                user_id=str(user_id),
            )

            return user

        except AuthenticationError:
            await self.session.rollback()
            raise
        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to verify user email",
                user_id=str(user_id),
                error=str(e),
                exc_info=True,
            )
            raise AuthenticationError(f"Email verification failed: {str(e)}") from e

    async def deactivate_user(
        self,
        user_id: uuid.UUID,
        updated_by: uuid.UUID,
    ) -> User:
        """
        Deactivate user account.

        Args:
            user_id: UUID of user to deactivate
            updated_by: UUID of user performing deactivation

        Returns:
            Updated user instance

        Raises:
            AuthenticationError: If user not found
        """
        self.logger.info(
            "Deactivating user",
            user_id=str(user_id),
            updated_by=str(updated_by),
        )

        try:
            user = await self._get_user_by_id(user_id)
            if not user:
                raise AuthenticationError("User not found")

            user.deactivate()
            user.updated_by = updated_by

            await self.session.commit()
            await self.session.refresh(user)

            self.logger.info(
                "User deactivated successfully",
                user_id=str(user_id),
            )

            return user

        except AuthenticationError:
            await self.session.rollback()
            raise
        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to deactivate user",
                user_id=str(user_id),
                error=str(e),
                exc_info=True,
            )
            raise AuthenticationError(f"Deactivation failed: {str(e)}") from e

    async def _get_user_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve user by email address.

        Args:
            email: Email address to search for

        Returns:
            User instance or None if not found
        """
        normalized_email = email.lower().strip()
        stmt = select(User).where(User.email == normalized_email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """
        Retrieve user by ID.

        Args:
            user_id: UUID of user to retrieve

        Returns:
            User instance or None if not found
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def _hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return pwd_context.hash(password)

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against

        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)