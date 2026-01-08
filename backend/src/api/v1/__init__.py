"""
API v1 package initialization.

This module initializes the v1 API package for the AutoSelect platform.
"""

from src.api.v1.auth import router as auth_router

__all__ = ["auth_router"]