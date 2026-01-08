"""
FastAPI dependencies for authentication and authorization.

This module provides dependency functions for JWT authentication, role-based
access control, database session management, and user validation.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.logging import get_logger
from src.database.connection import get_db
from src.database.models.user import User, UserRole
from src.schemas.auth import TokenPayload

logger = get_logger(__name__)
settings = get_settings()

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Validate JWT token and retrieve current authenticated user.

    Args:
        credentials: HTTP Bearer token from Authorization header
        db: Database session

    Returns:
        User: Authenticated user object

    Raises:
        HTTPException: 401 if token is invalid, expired, or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        logger.warning("Authentication failed: No credentials provided")
        raise credentials_exception

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id_str: Optional[str] = payload.get("sub")

        if user_id_str is None:
            logger.warning("Authentication failed: Token missing 'sub' claim")
            raise credentials_exception

        try:
            user_id = UUID(user_id_str)
        except ValueError:
            logger.warning(
                "Authentication failed: Invalid user ID format",
                user_id=user_id_str,
            )
            raise credentials_exception

        token_data = TokenPayload(sub=user_id)

    except JWTError as e:
        logger.warning(
            "Authentication failed: JWT validation error",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise credentials_exception

    try:
        user = await db.get(User, token_data.sub)
    except Exception as e:
        logger.error(
            "Database error during user retrieval",
            user_id=str(token_data.sub),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    if user is None:
        logger.warning(
            "Authentication failed: User not found",
            user_id=str(token_data.sub),
        )
        raise credentials_exception

    if not user.is_active:
        logger.warning(
            "Authentication failed: User account is inactive",
            user_id=str(user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    if user.is_locked:
        logger.warning(
            "Authentication failed: User account is locked",
            user_id=str(user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked due to multiple failed login attempts",
        )

    logger.info(
        "User authenticated successfully",
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
    )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Verify that the current user is active.

    Args:
        current_user: User from get_current_user dependency

    Returns:
        User: Active user object

    Raises:
        HTTPException: 403 if user is inactive
    """
    if not current_user.is_active:
        logger.warning(
            "Access denied: User is inactive",
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return current_user


def require_role(*allowed_roles: UserRole):
    """
    Create a dependency that requires specific user roles.

    Args:
        *allowed_roles: Variable number of UserRole values that are allowed

    Returns:
        Callable: Dependency function that validates user role

    Example:
        @router.get("/admin", dependencies=[Depends(require_role(UserRole.ADMIN))])
        async def admin_endpoint():
            return {"message": "Admin access granted"}
    """

    async def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        """
        Validate that current user has one of the required roles.

        Args:
            current_user: Authenticated active user

        Returns:
            User: User with validated role

        Raises:
            HTTPException: 403 if user doesn't have required role
        """
        if current_user.role not in allowed_roles:
            logger.warning(
                "Access denied: Insufficient permissions",
                user_id=str(current_user.id),
                user_role=current_user.role.value,
                required_roles=[role.value for role in allowed_roles],
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        logger.info(
            "Role validation successful",
            user_id=str(current_user.id),
            user_role=current_user.role.value,
        )

        return current_user

    return role_checker


async def get_current_admin(
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))],
) -> User:
    """
    Dependency for endpoints requiring admin access.

    Args:
        current_user: User validated to have admin role

    Returns:
        User: Admin user object
    """
    return current_user


async def get_current_dealer(
    current_user: Annotated[User, Depends(require_role(UserRole.SALES, UserRole.ADMIN, UserRole.SUPER_ADMIN))],
) -> User:
    """
    Dependency for endpoints requiring dealer/sales access.

    Args:
        current_user: User validated to have dealer role or higher

    Returns:
        User: Dealer user object
    """
    return current_user


async def get_optional_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Optional[User]:
    """
    Retrieve current user if authenticated, otherwise return None.

    Useful for endpoints that have different behavior for authenticated
    vs anonymous users without requiring authentication.

    Args:
        credentials: Optional HTTP Bearer token
        db: Database session

    Returns:
        Optional[User]: User object if authenticated, None otherwise
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        logger.debug("Optional authentication failed, proceeding as anonymous")
        return None


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
CurrentDealer = Annotated[User, Depends(get_current_dealer)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_user)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]