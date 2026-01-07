"""
Database package initialization.

This module serves as the entry point for the database package, providing
a clean namespace for database-related functionality including models,
connections, and utilities.

The package follows a modular structure:
- connection: Database connection management with async support
- models: SQLAlchemy ORM models for all entities
- session: Session management and dependency injection
- redis: Redis client configuration and utilities
"""

# Database package initialization - intentionally minimal
# All exports are handled by submodules to maintain clean separation of concerns
# Import submodules explicitly when needed to avoid circular dependencies

__all__ = []