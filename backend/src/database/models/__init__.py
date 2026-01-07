"""
Database models package initialization.

This module exports all database models for SQLAlchemy and Alembic auto-generation.
Models are imported here to ensure they are registered with the Base metadata
for proper migration generation and relationship resolution.
"""

from src.database.base import (
    Base,
    BaseModel,
    AuditedModel,
    SoftDeleteModel,
    TimestampMixin,
    UUIDMixin,
    SoftDeleteMixin,
    AuditMixin,
    create_table_args,
)
from src.database.models.user import User
from src.database.models.vehicle import Vehicle, VehicleConfiguration
from src.database.models.order import Order
from src.database.models.inventory import InventoryItem

__all__ = [
    "Base",
    "BaseModel",
    "AuditedModel",
    "SoftDeleteModel",
    "TimestampMixin",
    "UUIDMixin",
    "SoftDeleteMixin",
    "AuditMixin",
    "create_table_args",
    "User",
    "Vehicle",
    "VehicleConfiguration",
    "Order",
    "InventoryItem",
]