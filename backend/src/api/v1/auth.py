"""
Authentication API endpoints for the AutoSelect platform.

This module implements FastAPI routes for user authentication including:
- User registration with email verification
- Login with JWT token generation
- Token refresh for session extension
- Logout with token invalidation
- User profile retrieval

All endpoints include comprehensive error handling, input validation,
and structured logging for observability.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.core.logging import get_logger
from src.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    TokenRefreshRequest,
    UserProfileResponse,
    MessageResponse,
)
from src.services.auth.service import AuthService
from src.api.deps import get_auth_service, get_current_user
from src.database.models.user import User

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user account",
    description="Create a new user account with email and password. "
    "Returns JWT tokens for immediate authentication.",
)
async def register(
    request: UserRegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """
    Register a new user account.

    Args:
        request: User registration data including email, password, and profile
        auth_service: Authentication service dependency

    Returns:
        TokenResponse with access and refresh tokens

    Raises:
        HTTPException: 400 if email already exists or validation fails
        HTTPException: 500 for internal server errors
    """
    logger.info(
        "User registration attempt",
        email=request.email,
        role=request.role,
    )

    try:
        tokens = await auth_service.register_user(
            email=request.email,
            password=request.password,
            first_name=request.first_name,
            last_name=request.last_name,
            phone=request.phone,
            role=request.role,
        )

        logger.info(
            "User registration successful",
            email=request.email,
            role=request.role,
        )

        return tokens

    except ValueError as e:
        logger.warning(
            "User registration failed - validation error",
            email=request.email,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "User registration failed - internal error",
            email=request.email,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user. Please try again later.",
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticate user with email and password. "
    "Returns JWT tokens for API access.",
)
async def login(
    request: UserLoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """
    Authenticate user and generate JWT tokens.

    Args:
        request: Login credentials (email and password)
        auth_service: Authentication service dependency

    Returns:
        TokenResponse with access and refresh tokens

    Raises:
        HTTPException: 401 for invalid credentials
        HTTPException: 403 for locked or inactive accounts
        HTTPException: 500 for internal server errors
    """
    logger.info("User login attempt", email=request.email)

    try:
        tokens = await auth_service.authenticate_user(
            email=request.email,
            password=request.password,
        )

        logger.info("User login successful", email=request.email)

        return tokens

    except ValueError as e:
        error_message = str(e).lower()

        if "locked" in error_message:
            logger.warning(
                "Login failed - account locked",
                email=request.email,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is locked due to too many failed login attempts. "
                "Please contact support.",
            )
        elif "inactive" in error_message or "not active" in error_message:
            logger.warning(
                "Login failed - account inactive",
                email=request.email,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not active. Please verify your email.",
            )
        else:
            logger.warning(
                "Login failed - invalid credentials",
                email=request.email,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
    except Exception as e:
        logger.error(
            "Login failed - internal error",
            email=request.email,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed. Please try again later.",
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Generate new access token using refresh token. "
    "Extends user session without re-authentication.",
)
async def refresh_token(
    request: TokenRefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """
    Refresh access token using refresh token.

    Args:
        request: Token refresh request with refresh token
        auth_service: Authentication service dependency

    Returns:
        TokenResponse with new access and refresh tokens

    Raises:
        HTTPException: 401 for invalid or expired refresh token
        HTTPException: 500 for internal server errors
    """
    logger.info("Token refresh attempt")

    try:
        tokens = await auth_service.refresh_access_token(
            refresh_token=request.refresh_token
        )

        logger.info("Token refresh successful")

        return tokens

    except ValueError as e:
        logger.warning(
            "Token refresh failed - invalid token",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    except Exception as e:
        logger.error(
            "Token refresh failed - internal error",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed. Please try again later.",
        )


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="User logout",
    description="Invalidate current access token and refresh token. "
    "Requires valid authentication.",
)
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    """
    Logout user and invalidate tokens.

    Args:
        credentials: HTTP Bearer token credentials
        current_user: Currently authenticated user
        auth_service: Authentication service dependency

    Returns:
        MessageResponse confirming logout

    Raises:
        HTTPException: 401 for invalid authentication
        HTTPException: 500 for internal server errors
    """
    logger.info(
        "User logout attempt",
        user_id=str(current_user.id),
        email=current_user.email,
    )

    try:
        access_token = credentials.credentials

        await auth_service.logout_user(
            user_id=current_user.id,
            access_token=access_token,
        )

        logger.info(
            "User logout successful",
            user_id=str(current_user.id),
            email=current_user.email,
        )

        return MessageResponse(message="Successfully logged out")

    except ValueError as e:
        logger.warning(
            "Logout failed - invalid token",
            user_id=str(current_user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )
    except Exception as e:
        logger.error(
            "Logout failed - internal error",
            user_id=str(current_user.id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed. Please try again later.",
        )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Retrieve profile information for the authenticated user. "
    "Requires valid authentication.",
)
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserProfileResponse:
    """
    Get current user profile information.

    Args:
        current_user: Currently authenticated user

    Returns:
        UserProfileResponse with user profile data

    Raises:
        HTTPException: 401 for invalid authentication
    """
    logger.info(
        "User profile retrieval",
        user_id=str(current_user.id),
        email=current_user.email,
    )

    try:
        return UserProfileResponse(
            id=current_user.id,
            email=current_user.email,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            phone=current_user.phone,
            role=current_user.role,
            is_active=current_user.is_active,
            is_email_verified=current_user.is_email_verified,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at,
        )

    except Exception as e:
        logger.error(
            "Profile retrieval failed",
            user_id=str(current_user.id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile. Please try again later.",
        )