"""
Saved configuration schemas for vehicle configuration API.

This module defines Pydantic schemas for saved configuration operations including
save requests, responses, updates, and sharing functionality. Includes comprehensive
validation rules for configuration names, sharing parameters, and access control.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SaveConfigurationRequest(BaseModel):
    """Schema for saving a vehicle configuration."""

    name: str = Field(
        ...,
        description="User-defined name for the saved configuration",
        min_length=1,
        max_length=200,
    )
    configuration_id: UUID = Field(
        ...,
        description="ID of the configuration to save",
    )
    notes: Optional[str] = Field(
        None,
        description="Optional notes about the configuration",
        max_length=2000,
    )
    is_public: bool = Field(
        default=False,
        description="Whether the configuration can be shared publicly",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate configuration name."""
        if not v or not v.strip():
            raise ValueError("Configuration name cannot be empty or whitespace")
        cleaned = v.strip()
        if len(cleaned) < 1:
            raise ValueError("Configuration name must be at least 1 character")
        return cleaned

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        """Validate notes field."""
        if v is None:
            return v
        cleaned = v.strip()
        return cleaned if cleaned else None

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "My Dream Car Configuration",
                "configuration_id": "123e4567-e89b-12d3-a456-426614174000",
                "notes": "Perfect configuration for weekend drives",
                "is_public": False,
            }
        }
    }


class SavedConfigurationResponse(BaseModel):
    """Schema for saved configuration response."""

    id: UUID = Field(
        ...,
        description="Unique identifier for the saved configuration",
    )
    name: str = Field(
        ...,
        description="User-defined name for the configuration",
    )
    configuration_id: UUID = Field(
        ...,
        description="ID of the underlying configuration",
    )
    user_id: UUID = Field(
        ...,
        description="ID of the user who saved the configuration",
    )
    notes: Optional[str] = Field(
        None,
        description="Optional notes about the configuration",
    )
    is_public: bool = Field(
        ...,
        description="Whether the configuration is publicly shareable",
    )
    share_token: Optional[str] = Field(
        None,
        description="Unique token for sharing the configuration",
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when configuration was saved",
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp when configuration was last updated",
    )
    last_accessed_at: Optional[datetime] = Field(
        None,
        description="Timestamp when configuration was last accessed",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174010",
                "name": "My Dream Car Configuration",
                "configuration_id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "notes": "Perfect configuration for weekend drives",
                "is_public": False,
                "share_token": None,
                "created_at": "2026-01-07T22:30:00Z",
                "updated_at": "2026-01-07T22:30:00Z",
                "last_accessed_at": None,
            }
        }
    }


class UpdateSavedConfigurationRequest(BaseModel):
    """Schema for updating a saved configuration."""

    name: Optional[str] = Field(
        None,
        description="Updated name for the configuration",
        min_length=1,
        max_length=200,
    )
    notes: Optional[str] = Field(
        None,
        description="Updated notes about the configuration",
        max_length=2000,
    )
    is_public: Optional[bool] = Field(
        None,
        description="Updated public sharing status",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate configuration name if provided."""
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Configuration name cannot be empty or whitespace")
        cleaned = v.strip()
        if len(cleaned) < 1:
            raise ValueError("Configuration name must be at least 1 character")
        return cleaned

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        """Validate notes field if provided."""
        if v is None:
            return v
        cleaned = v.strip()
        return cleaned if cleaned else None

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Updated Configuration Name",
                "notes": "Updated notes with new preferences",
                "is_public": True,
            }
        }
    }


class ShareConfigurationResponse(BaseModel):
    """Schema for configuration sharing response."""

    share_token: str = Field(
        ...,
        description="Unique token for sharing the configuration",
        min_length=1,
    )
    share_url: str = Field(
        ...,
        description="Complete URL for sharing the configuration",
        min_length=1,
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Timestamp when the share link expires",
    )
    is_public: bool = Field(
        ...,
        description="Whether the configuration is publicly accessible",
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when share link was created",
    )

    @field_validator("share_token")
    @classmethod
    def validate_share_token(cls, v: str) -> str:
        """Validate share token format."""
        if not v or not v.strip():
            raise ValueError("Share token cannot be empty or whitespace")
        return v.strip()

    @field_validator("share_url")
    @classmethod
    def validate_share_url(cls, v: str) -> str:
        """Validate share URL format."""
        if not v or not v.strip():
            raise ValueError("Share URL cannot be empty or whitespace")
        cleaned = v.strip()
        if not cleaned.startswith(("http://", "https://")):
            raise ValueError("Share URL must be a valid HTTP(S) URL")
        return cleaned

    model_config = {
        "json_schema_extra": {
            "example": {
                "share_token": "abc123def456",
                "share_url": "https://example.com/shared/abc123def456",
                "expires_at": None,
                "is_public": True,
                "created_at": "2026-01-07T22:30:00Z",
            }
        }
    }