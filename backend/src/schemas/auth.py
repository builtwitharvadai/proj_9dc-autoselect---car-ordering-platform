"""
Authentication schemas for request/response validation.

This module defines Pydantic schemas for authentication-related operations
including user registration, login, token management, and user responses.
All schemas include comprehensive validation for security and data integrity.
"""

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """
    Schema for user registration requests.
    
    Validates email format and password strength requirements.
    """
    
    email: EmailStr = Field(
        ...,
        description="User email address",
        examples=["user@example.com"]
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User password (8-128 characters)",
        examples=["SecurePass123!"]
    )
    first_name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="User first name",
        examples=["John"]
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="User last name",
        examples=["Doe"]
    )
    phone: Optional[str] = Field(
        None,
        min_length=10,
        max_length=20,
        description="User phone number",
        examples=["+1234567890"]
    )
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """
        Validate password meets security requirements.
        
        Requirements:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        
        Args:
            value: Password to validate
            
        Returns:
            Validated password
            
        Raises:
            ValueError: If password doesn't meet requirements
        """
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one digit")
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise ValueError("Password must contain at least one special character")
        
        return value
    
    @field_validator("phone")
    @classmethod
    def validate_phone_format(cls, value: Optional[str]) -> Optional[str]:
        """
        Validate phone number format.
        
        Args:
            value: Phone number to validate
            
        Returns:
            Validated phone number
            
        Raises:
            ValueError: If phone format is invalid
        """
        if value is None:
            return value
        
        # Remove common separators
        cleaned = re.sub(r"[\s\-\(\)]", "", value)
        
        # Check if it contains only digits and optional leading +
        if not re.match(r"^\+?\d{10,15}$", cleaned):
            raise ValueError(
                "Phone number must contain 10-15 digits and may start with +"
            )
        
        return value
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "john.doe@example.com",
                    "password": "SecurePass123!",
                    "first_name": "John",
                    "last_name": "Doe",
                    "phone": "+1234567890"
                }
            ]
        }
    }


class UserLogin(BaseModel):
    """
    Schema for user login requests.
    
    Validates email format and password presence.
    """
    
    email: EmailStr = Field(
        ...,
        description="User email address",
        examples=["user@example.com"]
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="User password",
        examples=["SecurePass123!"]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "john.doe@example.com",
                    "password": "SecurePass123!"
                }
            ]
        }
    }


class TokenResponse(BaseModel):
    """
    Schema for authentication token responses.
    
    Contains access token, refresh token, and metadata.
    """
    
    access_token: str = Field(
        ...,
        description="JWT access token for API authentication",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token for obtaining new access tokens",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')",
        examples=["bearer"]
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds",
        examples=[3600]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 3600
                }
            ]
        }
    }


class TokenRefresh(BaseModel):
    """
    Schema for token refresh requests.
    
    Contains refresh token for obtaining new access token.
    """
    
    refresh_token: str = Field(
        ...,
        description="JWT refresh token",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                }
            ]
        }
    }


class UserResponse(BaseModel):
    """
    Schema for user data responses.
    
    Contains user information without sensitive data like passwords.
    """
    
    id: UUID = Field(
        ...,
        description="User unique identifier",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )
    email: EmailStr = Field(
        ...,
        description="User email address",
        examples=["user@example.com"]
    )
    first_name: str = Field(
        ...,
        description="User first name",
        examples=["John"]
    )
    last_name: str = Field(
        ...,
        description="User last name",
        examples=["Doe"]
    )
    phone: Optional[str] = Field(
        None,
        description="User phone number",
        examples=["+1234567890"]
    )
    role: str = Field(
        ...,
        description="User role (customer, dealer, admin, super_admin)",
        examples=["customer"]
    )
    is_active: bool = Field(
        ...,
        description="Whether user account is active",
        examples=[True]
    )
    is_email_verified: bool = Field(
        ...,
        description="Whether user email is verified",
        examples=[True]
    )
    created_at: datetime = Field(
        ...,
        description="Account creation timestamp",
        examples=["2024-01-01T00:00:00Z"]
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
        examples=["2024-01-01T00:00:00Z"]
    )
    last_login_at: Optional[datetime] = Field(
        None,
        description="Last login timestamp",
        examples=["2024-01-01T00:00:00Z"]
    )
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "john.doe@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                    "phone": "+1234567890",
                    "role": "customer",
                    "is_active": True,
                    "is_email_verified": True,
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                    "last_login_at": "2024-01-01T12:00:00Z"
                }
            ]
        }
    }


class PasswordChange(BaseModel):
    """
    Schema for password change requests.
    
    Validates current and new password requirements.
    """
    
    current_password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Current password",
        examples=["OldPass123!"]
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (8-128 characters)",
        examples=["NewSecurePass123!"]
    )
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, value: str) -> str:
        """
        Validate new password meets security requirements.
        
        Args:
            value: New password to validate
            
        Returns:
            Validated password
            
        Raises:
            ValueError: If password doesn't meet requirements
        """
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one digit")
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise ValueError("Password must contain at least one special character")
        
        return value
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "current_password": "OldPass123!",
                    "new_password": "NewSecurePass123!"
                }
            ]
        }
    }


class PasswordReset(BaseModel):
    """
    Schema for password reset requests.
    
    Contains email for password reset link.
    """
    
    email: EmailStr = Field(
        ...,
        description="User email address for password reset",
        examples=["user@example.com"]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "john.doe@example.com"
                }
            ]
        }
    }


class PasswordResetConfirm(BaseModel):
    """
    Schema for password reset confirmation.
    
    Contains reset token and new password.
    """
    
    token: str = Field(
        ...,
        description="Password reset token from email",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (8-128 characters)",
        examples=["NewSecurePass123!"]
    )
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, value: str) -> str:
        """
        Validate new password meets security requirements.
        
        Args:
            value: New password to validate
            
        Returns:
            Validated password
            
        Raises:
            ValueError: If password doesn't meet requirements
        """
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one digit")
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise ValueError("Password must contain at least one special character")
        
        return value
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "new_password": "NewSecurePass123!"
                }
            ]
        }
    }