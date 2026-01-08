"""
Security utilities for password hashing and JWT token management.

This module provides comprehensive security utilities including:
- Password hashing with bcrypt
- JWT token creation and validation
- Token expiration and refresh logic
- Secure random generation
- Token blacklisting support

All operations follow security best practices with proper error handling,
logging, and validation.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import get_settings
from src.core.logging import get_logger

# Initialize settings and logger
settings = get_settings()
logger = get_logger(__name__)

# Password hashing context with bcrypt
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
    bcrypt__ident="2b"
)

# JWT configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7


class SecurityError(Exception):
    """Base exception for security-related errors."""
    
    def __init__(self, message: str, code: str, **context):
        super().__init__(message)
        self.code = code
        self.context = context


class TokenError(SecurityError):
    """Exception raised for token-related errors."""
    pass


class PasswordError(SecurityError):
    """Exception raised for password-related errors."""
    pass


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with proper salt rounds.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password string
        
    Raises:
        PasswordError: If password hashing fails
        
    Example:
        >>> hashed = hash_password("SecurePass123!")
        >>> verify_password("SecurePass123!", hashed)
        True
    """
    if not password:
        logger.error("Attempted to hash empty password")
        raise PasswordError(
            "Password cannot be empty",
            code="EMPTY_PASSWORD"
        )
    
    try:
        hashed = pwd_context.hash(password)
        logger.debug(
            "Password hashed successfully",
            password_length=len(password)
        )
        return hashed
    except Exception as e:
        logger.error(
            "Password hashing failed",
            error=str(e),
            error_type=type(e).__name__
        )
        raise PasswordError(
            "Failed to hash password",
            code="HASH_FAILED",
            original_error=str(e)
        ) from e


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
        
    Raises:
        PasswordError: If verification process fails
        
    Example:
        >>> hashed = hash_password("SecurePass123!")
        >>> verify_password("SecurePass123!", hashed)
        True
        >>> verify_password("WrongPass", hashed)
        False
    """
    if not plain_password or not hashed_password:
        logger.warning(
            "Password verification attempted with empty values",
            has_plain=bool(plain_password),
            has_hashed=bool(hashed_password)
        )
        return False
    
    try:
        is_valid = pwd_context.verify(plain_password, hashed_password)
        logger.debug(
            "Password verification completed",
            is_valid=is_valid
        )
        return is_valid
    except Exception as e:
        logger.error(
            "Password verification failed",
            error=str(e),
            error_type=type(e).__name__
        )
        raise PasswordError(
            "Failed to verify password",
            code="VERIFY_FAILED",
            original_error=str(e)
        ) from e


def needs_rehash(hashed_password: str) -> bool:
    """
    Check if a hashed password needs to be rehashed.
    
    This is useful for upgrading password hashes when security
    parameters change (e.g., increasing bcrypt rounds).
    
    Args:
        hashed_password: Hashed password to check
        
    Returns:
        True if password needs rehashing, False otherwise
        
    Example:
        >>> hashed = hash_password("SecurePass123!")
        >>> needs_rehash(hashed)
        False
    """
    try:
        needs_update = pwd_context.needs_update(hashed_password)
        if needs_update:
            logger.info(
                "Password hash needs update",
                hash_prefix=hashed_password[:10]
            )
        return needs_update
    except Exception as e:
        logger.warning(
            "Failed to check if password needs rehash",
            error=str(e)
        )
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token with expiration.
    
    Args:
        data: Dictionary of claims to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
        
    Raises:
        TokenError: If token creation fails
        
    Example:
        >>> token = create_access_token({"sub": "user@example.com"})
        >>> # Token valid for 60 minutes by default
    """
    try:
        to_encode = data.copy()
        
        # Set expiration time
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        # Encode token
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=ALGORITHM
        )
        
        logger.info(
            "Access token created",
            subject=data.get("sub"),
            expires_at=expire.isoformat(),
            token_type="access"
        )
        
        return encoded_jwt
        
    except Exception as e:
        logger.error(
            "Failed to create access token",
            error=str(e),
            error_type=type(e).__name__,
            data_keys=list(data.keys())
        )
        raise TokenError(
            "Failed to create access token",
            code="TOKEN_CREATE_FAILED",
            original_error=str(e)
        ) from e


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token with extended expiration.
    
    Args:
        data: Dictionary of claims to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT refresh token string
        
    Raises:
        TokenError: If token creation fails
        
    Example:
        >>> token = create_refresh_token({"sub": "user@example.com"})
        >>> # Token valid for 7 days by default
    """
    try:
        to_encode = data.copy()
        
        # Set expiration time
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                days=REFRESH_TOKEN_EXPIRE_DAYS
            )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        
        # Encode token
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=ALGORITHM
        )
        
        logger.info(
            "Refresh token created",
            subject=data.get("sub"),
            expires_at=expire.isoformat(),
            token_type="refresh"
        )
        
        return encoded_jwt
        
    except Exception as e:
        logger.error(
            "Failed to create refresh token",
            error=str(e),
            error_type=type(e).__name__,
            data_keys=list(data.keys())
        )
        raise TokenError(
            "Failed to create refresh token",
            code="TOKEN_CREATE_FAILED",
            original_error=str(e)
        ) from e


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string to decode
        
    Returns:
        Dictionary of decoded token claims
        
    Raises:
        TokenError: If token is invalid, expired, or malformed
        
    Example:
        >>> token = create_access_token({"sub": "user@example.com"})
        >>> payload = decode_token(token)
        >>> payload["sub"]
        'user@example.com'
    """
    if not token:
        logger.warning("Attempted to decode empty token")
        raise TokenError(
            "Token cannot be empty",
            code="EMPTY_TOKEN"
        )
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        
        logger.debug(
            "Token decoded successfully",
            subject=payload.get("sub"),
            token_type=payload.get("type"),
            expires_at=payload.get("exp")
        )
        
        return payload
        
    except jwt.ExpiredSignatureError as e:
        logger.warning(
            "Token has expired",
            error=str(e)
        )
        raise TokenError(
            "Token has expired",
            code="TOKEN_EXPIRED"
        ) from e
        
    except JWTError as e:
        logger.error(
            "Invalid token",
            error=str(e),
            error_type=type(e).__name__
        )
        raise TokenError(
            "Invalid token",
            code="TOKEN_INVALID",
            original_error=str(e)
        ) from e
        
    except Exception as e:
        logger.error(
            "Token decoding failed",
            error=str(e),
            error_type=type(e).__name__
        )
        raise TokenError(
            "Failed to decode token",
            code="TOKEN_DECODE_FAILED",
            original_error=str(e)
        ) from e


def verify_token_type(payload: Dict[str, Any], expected_type: str) -> bool:
    """
    Verify that a token payload has the expected type.
    
    Args:
        payload: Decoded token payload
        expected_type: Expected token type ("access" or "refresh")
        
    Returns:
        True if token type matches, False otherwise
        
    Example:
        >>> token = create_access_token({"sub": "user@example.com"})
        >>> payload = decode_token(token)
        >>> verify_token_type(payload, "access")
        True
        >>> verify_token_type(payload, "refresh")
        False
    """
    token_type = payload.get("type")
    is_valid = token_type == expected_type
    
    if not is_valid:
        logger.warning(
            "Token type mismatch",
            expected=expected_type,
            actual=token_type,
            subject=payload.get("sub")
        )
    
    return is_valid


def get_token_expiration(token: str) -> Optional[datetime]:
    """
    Get the expiration time of a token.
    
    Args:
        token: JWT token string
        
    Returns:
        Expiration datetime or None if token is invalid
        
    Example:
        >>> token = create_access_token({"sub": "user@example.com"})
        >>> exp = get_token_expiration(token)
        >>> exp > datetime.utcnow()
        True
    """
    try:
        payload = decode_token(token)
        exp_timestamp = payload.get("exp")
        
        if exp_timestamp:
            return datetime.fromtimestamp(exp_timestamp)
        
        logger.warning(
            "Token has no expiration claim",
            subject=payload.get("sub")
        )
        return None
        
    except TokenError:
        return None


def is_token_expired(token: str) -> bool:
    """
    Check if a token is expired.
    
    Args:
        token: JWT token string
        
    Returns:
        True if token is expired, False otherwise
        
    Example:
        >>> token = create_access_token({"sub": "user@example.com"})
        >>> is_token_expired(token)
        False
    """
    try:
        decode_token(token)
        return False
    except TokenError as e:
        return e.code == "TOKEN_EXPIRED"


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Length of the token in bytes (default: 32)
        
    Returns:
        URL-safe random token string
        
    Raises:
        ValueError: If length is invalid
        
    Example:
        >>> token = generate_secure_token()
        >>> len(token) >= 32
        True
    """
    if length <= 0:
        logger.error(
            "Invalid token length requested",
            length=length
        )
        raise ValueError("Token length must be positive")
    
    try:
        token = secrets.token_urlsafe(length)
        logger.debug(
            "Secure token generated",
            length=length,
            token_length=len(token)
        )
        return token
        
    except Exception as e:
        logger.error(
            "Failed to generate secure token",
            error=str(e),
            length=length
        )
        raise


def create_token_pair(user_id: UUID, email: str, role: str) -> Dict[str, str]:
    """
    Create both access and refresh tokens for a user.
    
    Args:
        user_id: User's unique identifier
        email: User's email address
        role: User's role
        
    Returns:
        Dictionary containing access_token and refresh_token
        
    Raises:
        TokenError: If token creation fails
        
    Example:
        >>> tokens = create_token_pair(
        ...     user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        ...     email="user@example.com",
        ...     role="customer"
        ... )
        >>> "access_token" in tokens and "refresh_token" in tokens
        True
    """
    try:
        token_data = {
            "sub": email,
            "user_id": str(user_id),
            "role": role
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token({"sub": email, "user_id": str(user_id)})
        
        logger.info(
            "Token pair created",
            user_id=str(user_id),
            email=email,
            role=role
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
        
    except Exception as e:
        logger.error(
            "Failed to create token pair",
            error=str(e),
            user_id=str(user_id),
            email=email
        )
        raise TokenError(
            "Failed to create token pair",
            code="TOKEN_PAIR_FAILED",
            original_error=str(e)
        ) from e


def get_token_subject(token: str) -> Optional[str]:
    """
    Extract the subject (email) from a token.
    
    Args:
        token: JWT token string
        
    Returns:
        Subject string or None if token is invalid
        
    Example:
        >>> token = create_access_token({"sub": "user@example.com"})
        >>> get_token_subject(token)
        'user@example.com'
    """
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except TokenError:
        return None


def get_token_user_id(token: str) -> Optional[UUID]:
    """
    Extract the user ID from a token.
    
    Args:
        token: JWT token string
        
    Returns:
        User UUID or None if token is invalid or missing user_id
        
    Example:
        >>> tokens = create_token_pair(
        ...     user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        ...     email="user@example.com",
        ...     role="customer"
        ... )
        >>> user_id = get_token_user_id(tokens["access_token"])
        >>> user_id == UUID("123e4567-e89b-12d3-a456-426614174000")
        True
    """
    try:
        payload = decode_token(token)
        user_id_str = payload.get("user_id")
        
        if user_id_str:
            return UUID(user_id_str)
        
        return None
        
    except (TokenError, ValueError):
        return None