"""
User model with authentication and role management.

This module defines the User model for authentication, authorization, and user management.
Implements secure password handling, role-based access control, and comprehensive auditing.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Enum as SQLEnum,
    Index,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import AuditedModel


class UserRole(str, enum.Enum):
    """User role enumeration for role-based access control."""

    CUSTOMER = "customer"
    SALES = "sales"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

    @classmethod
    def from_string(cls, value: str) -> "UserRole":
        """
        Convert string to UserRole enum.

        Args:
            value: String representation of role

        Returns:
            UserRole enum value

        Raises:
            ValueError: If value is not a valid role
        """
        try:
            return cls[value.upper()]
        except KeyError:
            raise ValueError(f"Invalid role: {value}")

    def has_permission(self, required_role: "UserRole") -> bool:
        """
        Check if this role has permission for required role.

        Args:
            required_role: The role required for access

        Returns:
            True if this role has sufficient permissions
        """
        role_hierarchy = {
            UserRole.CUSTOMER: 0,
            UserRole.SALES: 1,
            UserRole.ADMIN: 2,
            UserRole.SUPER_ADMIN: 3,
        }
        return role_hierarchy[self] >= role_hierarchy[required_role]


class User(AuditedModel):
    """
    User model for authentication and authorization.

    Implements secure user management with password hashing, role-based access control,
    email verification, and comprehensive audit logging. Supports soft deletion and
    tracks all user modifications.

    Attributes:
        id: Unique user identifier (UUID)
        email: User email address (unique, indexed)
        password_hash: Bcrypt hashed password
        first_name: User's first name
        last_name: User's last name
        role: User role for access control
        is_active: Account active status
        is_verified: Email verification status
        last_login_at: Timestamp of last successful login
        failed_login_attempts: Counter for failed login attempts
        locked_until: Account lock timestamp for security
        created_at: Account creation timestamp (from AuditedModel)
        updated_at: Last modification timestamp (from AuditedModel)
        created_by: User who created this account (from AuditedModel)
        updated_by: User who last modified this account (from AuditedModel)
        deleted_at: Soft deletion timestamp (from AuditedModel)
    """

    __tablename__ = "users"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique user identifier",
    )

    # Authentication fields
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="User email address (unique, case-insensitive)",
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt hashed password",
    )

    # Personal information
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="User's first name",
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="User's last name",
    )

    # Authorization and status
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role", native_enum=False),
        nullable=False,
        default=UserRole.CUSTOMER,
        index=True,
        comment="User role for access control",
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        index=True,
        comment="Account active status",
    )

    is_verified: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
        comment="Email verification status",
    )

    # Security tracking
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="Timestamp of last successful login",
    )

    failed_login_attempts: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Counter for failed login attempts",
    )

    locked_until: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        index=True,
        comment="Account lock timestamp for security",
    )

    # Relationships
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="user",
        foreign_keys="Order.user_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    # Table constraints
    __table_args__ = (
        Index(
            "ix_users_email_lower",
            "email",
            postgresql_ops={"email": "text_pattern_ops"},
        ),
        Index("ix_users_role_active", "role", "is_active"),
        Index("ix_users_active_verified", "is_active", "is_verified"),
        CheckConstraint(
            "length(email) >= 3",
            name="ck_users_email_min_length",
        ),
        CheckConstraint(
            "length(first_name) >= 1",
            name="ck_users_first_name_min_length",
        ),
        CheckConstraint(
            "length(last_name) >= 1",
            name="ck_users_last_name_min_length",
        ),
        CheckConstraint(
            "failed_login_attempts >= 0",
            name="ck_users_failed_attempts_non_negative",
        ),
        CheckConstraint(
            "locked_until IS NULL OR locked_until > created_at",
            name="ck_users_locked_until_after_creation",
        ),
        UniqueConstraint("email", name="uq_users_email"),
        {
            "comment": "User accounts with authentication and authorization",
            "postgresql_partition_by": None,
        },
    )

    def __repr__(self) -> str:
        """
        String representation of User.

        Returns:
            String representation showing key user attributes
        """
        return (
            f"<User(id={self.id}, email='{self.email}', "
            f"role={self.role.value}, is_active={self.is_active})>"
        )

    @property
    def full_name(self) -> str:
        """
        Get user's full name.

        Returns:
            Concatenated first and last name
        """
        return f"{self.first_name} {self.last_name}"

    @property
    def is_locked(self) -> bool:
        """
        Check if account is currently locked.

        Returns:
            True if account is locked and lock period hasn't expired
        """
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until

    @property
    def is_admin(self) -> bool:
        """
        Check if user has admin privileges.

        Returns:
            True if user is admin or super admin
        """
        return self.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN)

    @property
    def can_access_admin_panel(self) -> bool:
        """
        Check if user can access admin panel.

        Returns:
            True if user is active, verified, and has admin role
        """
        return self.is_active and self.is_verified and self.is_admin

    def has_role(self, role: UserRole) -> bool:
        """
        Check if user has specific role.

        Args:
            role: Role to check

        Returns:
            True if user has the specified role
        """
        return self.role == role

    def has_permission(self, required_role: UserRole) -> bool:
        """
        Check if user has permission for required role level.

        Args:
            required_role: Minimum role required

        Returns:
            True if user's role has sufficient permissions
        """
        return self.role.has_permission(required_role)

    def increment_failed_login(self) -> None:
        """
        Increment failed login attempts counter.

        Automatically locks account after 5 failed attempts for 30 minutes.
        """
        self.failed_login_attempts += 1

        if self.failed_login_attempts >= 5:
            from datetime import timedelta

            self.locked_until = datetime.utcnow() + timedelta(minutes=30)

    def reset_failed_login(self) -> None:
        """Reset failed login attempts counter and unlock account."""
        self.failed_login_attempts = 0
        self.locked_until = None

    def record_login(self) -> None:
        """Record successful login and reset security counters."""
        self.last_login_at = datetime.utcnow()
        self.reset_failed_login()

    def activate(self) -> None:
        """Activate user account."""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate user account."""
        self.is_active = False

    def verify_email(self) -> None:
        """Mark email as verified."""
        self.is_verified = True

    def update_role(self, new_role: UserRole) -> None:
        """
        Update user role.

        Args:
            new_role: New role to assign
        """
        self.role = new_role