"""
SQLAlchemy declarative base and common model mixins.

This module provides the SQLAlchemy DeclarativeBase, common mixins for timestamps
and UUIDs, and base model utilities with async session support. It implements
production-ready patterns for database models with proper type hints, validation,
and serialization capabilities.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Type, TypeVar

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

from src.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound="Base")


class Base(AsyncAttrs, DeclarativeBase):
    """
    Base class for all SQLAlchemy models with async support.

    Provides common functionality for all database models including
    async attribute loading, type annotations, and utility methods.
    """

    __abstract__ = True

    def to_dict(self, exclude: Optional[set[str]] = None) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.

        Args:
            exclude: Set of attribute names to exclude from output

        Returns:
            Dictionary representation of the model

        Example:
            user = User(name="John", email="john@example.com")
            data = user.to_dict(exclude={"password_hash"})
        """
        exclude = exclude or set()
        result = {}

        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                if isinstance(value, datetime):
                    result[column.name] = value.isoformat()
                elif isinstance(value, uuid.UUID):
                    result[column.name] = str(value)
                else:
                    result[column.name] = value

        logger.debug(
            "Model converted to dictionary",
            model=self.__class__.__name__,
            excluded_fields=list(exclude),
        )

        return result

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """
        Create model instance from dictionary.

        Args:
            data: Dictionary containing model attributes

        Returns:
            New model instance

        Raises:
            ValueError: If required fields are missing or invalid

        Example:
            data = {"name": "John", "email": "john@example.com"}
            user = User.from_dict(data)
        """
        try:
            filtered_data = {
                key: value
                for key, value in data.items()
                if hasattr(cls, key)
            }

            instance = cls(**filtered_data)

            logger.debug(
                "Model created from dictionary",
                model=cls.__name__,
                fields=list(filtered_data.keys()),
            )

            return instance
        except Exception as e:
            logger.error(
                "Failed to create model from dictionary",
                model=cls.__name__,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ValueError(
                f"Failed to create {cls.__name__} from dictionary: {e}"
            ) from e

    def __repr__(self) -> str:
        """
        Generate string representation of model instance.

        Returns:
            String representation with primary key values
        """
        pk_values = []
        for column in self.__table__.primary_key.columns:
            value = getattr(self, column.name, None)
            if value is not None:
                pk_values.append(f"{column.name}={value!r}")

        pk_str = ", ".join(pk_values) if pk_values else "no primary key"
        return f"<{self.__class__.__name__}({pk_str})>"


class TimestampMixin:
    """
    Mixin for automatic timestamp management.

    Adds created_at and updated_at columns that are automatically
    managed by the database. Uses server-side defaults for consistency
    and reliability.
    """

    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        """
        Timestamp when the record was created.

        Automatically set by database on insert.
        """
        return mapped_column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            comment="Timestamp when record was created",
        )

    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        """
        Timestamp when the record was last updated.

        Automatically updated by database on modification.
        """
        return mapped_column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
            comment="Timestamp when record was last updated",
        )


class UUIDMixin:
    """
    Mixin for UUID primary key.

    Provides a UUID primary key column with automatic generation.
    Uses PostgreSQL's native UUID type for optimal performance and storage.
    """

    @declared_attr
    def id(cls) -> Mapped[uuid.UUID]:
        """
        UUID primary key.

        Automatically generated using uuid4 if not provided.
        """
        return mapped_column(
            UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            nullable=False,
            comment="Unique identifier for the record",
        )


class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.

    Adds deleted_at column for marking records as deleted without
    physically removing them from the database. Enables audit trails
    and data recovery.
    """

    @declared_attr
    def deleted_at(cls) -> Mapped[Optional[datetime]]:
        """
        Timestamp when the record was soft deleted.

        NULL indicates the record is active.
        """
        return mapped_column(
            DateTime(timezone=True),
            nullable=True,
            default=None,
            comment="Timestamp when record was soft deleted",
        )

    @property
    def is_deleted(self) -> bool:
        """
        Check if record is soft deleted.

        Returns:
            True if record is deleted, False otherwise
        """
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """
        Mark record as deleted.

        Sets deleted_at to current timestamp.
        """
        if self.deleted_at is None:
            self.deleted_at = datetime.utcnow()
            logger.info(
                "Record soft deleted",
                model=self.__class__.__name__,
                record_id=getattr(self, "id", None),
            )

    def restore(self) -> None:
        """
        Restore soft deleted record.

        Sets deleted_at back to NULL.
        """
        if self.deleted_at is not None:
            self.deleted_at = None
            logger.info(
                "Record restored",
                model=self.__class__.__name__,
                record_id=getattr(self, "id", None),
            )


class AuditMixin(TimestampMixin):
    """
    Mixin for audit trail functionality.

    Extends TimestampMixin with created_by and updated_by columns
    for tracking which user performed the operation.
    """

    @declared_attr
    def created_by(cls) -> Mapped[Optional[str]]:
        """
        User ID who created the record.

        Should be set by application logic.
        """
        return mapped_column(
            String(255),
            nullable=True,
            comment="User ID who created the record",
        )

    @declared_attr
    def updated_by(cls) -> Mapped[Optional[str]]:
        """
        User ID who last updated the record.

        Should be updated by application logic on modifications.
        """
        return mapped_column(
            String(255),
            nullable=True,
            comment="User ID who last updated the record",
        )


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """
    Base model with UUID primary key and timestamps.

    Combines Base, UUIDMixin, and TimestampMixin for a complete
    base model with common functionality. Use this as the base
    for most application models.

    Example:
        class User(BaseModel):
            __tablename__ = "users"

            email: Mapped[str] = mapped_column(String(255), unique=True)
            name: Mapped[str] = mapped_column(String(255))
    """

    __abstract__ = True


class AuditedModel(Base, UUIDMixin, AuditMixin):
    """
    Base model with UUID, timestamps, and audit fields.

    Combines Base, UUIDMixin, and AuditMixin for models that
    require full audit trail capabilities.

    Example:
        class Order(AuditedModel):
            __tablename__ = "orders"

            order_number: Mapped[str] = mapped_column(String(50), unique=True)
            total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    """

    __abstract__ = True


class SoftDeleteModel(BaseModel, SoftDeleteMixin):
    """
    Base model with UUID, timestamps, and soft delete.

    Combines BaseModel and SoftDeleteMixin for models that
    should support soft deletion.

    Example:
        class Vehicle(SoftDeleteModel):
            __tablename__ = "vehicles"

            vin: Mapped[str] = mapped_column(String(17), unique=True)
            make: Mapped[str] = mapped_column(String(100))
    """

    __abstract__ = True


def create_table_args(
    comment: Optional[str] = None,
    schema: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Create __table_args__ dictionary with common settings.

    Args:
        comment: Table comment for documentation
        schema: Database schema name
        **kwargs: Additional table arguments

    Returns:
        Dictionary suitable for __table_args__

    Example:
        class User(BaseModel):
            __tablename__ = "users"
            __table_args__ = create_table_args(
                comment="User accounts",
                schema="public"
            )
    """
    table_args = {}

    if comment:
        table_args["comment"] = comment

    if schema:
        table_args["schema"] = schema

    table_args.update(kwargs)

    logger.debug(
        "Table arguments created",
        comment=comment,
        schema=schema,
        additional_args=list(kwargs.keys()),
    )

    return table_args