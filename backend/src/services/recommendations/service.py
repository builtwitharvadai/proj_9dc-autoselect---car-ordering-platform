"""
Recommendation service orchestrating engine and analytics.

This module provides the high-level service layer for package recommendations,
coordinating between the recommendation engine, analytics tracking, and caching.
Implements comprehensive error handling, performance monitoring, and structured
logging for production-grade recommendation delivery.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.cache.redis_client import RedisClient
from src.core.logging import get_logger
from src.database.models.recommendation_analytics import (
    RecommendationEvent,
    RecommendationEventType,
)
from src.services.recommendations.recommendation_engine import (
    InsufficientDataError,
    RecommendationEngine,
    RecommendationError,
)

logger = get_logger(__name__)


class RecommendationServiceError(Exception):
    """Base exception for recommendation service errors."""

    def __init__(self, message: str, **context: Any):
        super().__init__(message)
        self.context = context
        logger.error(
            "Recommendation service error",
            error=message,
            **context,
        )


class RecommendationService:
    """
    High-level service for package recommendations and analytics.

    Orchestrates the recommendation engine, analytics tracking, and caching
    to provide fast, accurate package recommendations with comprehensive
    monitoring and error handling.
    """

    # Service configuration
    DEFAULT_MAX_RECOMMENDATIONS = 5
    DEFAULT_POPULAR_LIMIT = 5
    PERFORMANCE_THRESHOLD_MS = 100

    def __init__(
        self,
        db_session: AsyncSession,
        redis_client: Optional[RedisClient] = None,
        enable_cache: bool = True,
        enable_analytics: bool = True,
    ):
        """
        Initialize recommendation service.

        Args:
            db_session: Database session for queries
            redis_client: Optional Redis client for caching
            enable_cache: Enable/disable caching
            enable_analytics: Enable/disable analytics tracking
        """
        self.db = db_session
        self.redis = redis_client
        self.enable_cache = enable_cache
        self.enable_analytics = enable_analytics

        # Initialize recommendation engine
        self.engine = RecommendationEngine(
            db_session=db_session,
            redis_client=redis_client,
            enable_cache=enable_cache,
        )

        logger.info(
            "Recommendation service initialized",
            cache_enabled=enable_cache,
            analytics_enabled=enable_analytics,
        )

    async def get_package_recommendations(
        self,
        vehicle_id: uuid.UUID,
        selected_option_ids: list[uuid.UUID],
        user_id: Optional[uuid.UUID] = None,
        session_id: Optional[str] = None,
        trim: Optional[str] = None,
        year: Optional[int] = None,
        max_results: int = DEFAULT_MAX_RECOMMENDATIONS,
        include_popular: bool = True,
    ) -> dict[str, Any]:
        """
        Get package recommendations with analytics tracking.

        Args:
            vehicle_id: Vehicle being configured
            selected_option_ids: Currently selected option IDs
            user_id: Optional user ID for personalization
            session_id: Optional session ID for anonymous tracking
            trim: Optional trim level for compatibility
            year: Optional model year for compatibility
            max_results: Maximum number of recommendations
            include_popular: Include popular configurations

        Returns:
            Dictionary containing recommendations and metadata

        Raises:
            RecommendationServiceError: If recommendation generation fails
        """
        start_time = datetime.utcnow()

        try:
            # Generate recommendations
            recommendations = await self.engine.recommend_packages(
                vehicle_id=vehicle_id,
                selected_option_ids=selected_option_ids,
                user_id=user_id,
                session_id=session_id,
                trim=trim,
                year=year,
                max_results=max_results,
            )

            # Get popular configurations if requested
            popular_configs = []
            if include_popular:
                try:
                    popular_configs = await self.engine.get_popular_configurations(
                        vehicle_id=vehicle_id,
                        limit=self.DEFAULT_POPULAR_LIMIT,
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to retrieve popular configurations",
                        error=str(e),
                        vehicle_id=str(vehicle_id),
                    )

            # Calculate processing time
            processing_time_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )

            # Track performance
            if processing_time_ms > self.PERFORMANCE_THRESHOLD_MS:
                logger.warning(
                    "Recommendation generation exceeded performance threshold",
                    processing_time_ms=processing_time_ms,
                    threshold_ms=self.PERFORMANCE_THRESHOLD_MS,
                    vehicle_id=str(vehicle_id),
                )

            # Track analytics event
            if self.enable_analytics:
                await self._track_recommendation_viewed(
                    vehicle_id=vehicle_id,
                    recommendations=recommendations,
                    user_id=user_id,
                    session_id=session_id,
                )

            # Build response
            response = {
                "vehicle_id": str(vehicle_id),
                "recommendations": recommendations,
                "popular_configurations": popular_configs,
                "metadata": {
                    "recommendation_count": len(recommendations),
                    "popular_count": len(popular_configs),
                    "processing_time_ms": processing_time_ms,
                    "generated_at": datetime.utcnow().isoformat(),
                    "cache_enabled": self.enable_cache,
                },
            }

            logger.info(
                "Package recommendations generated successfully",
                vehicle_id=str(vehicle_id),
                recommendation_count=len(recommendations),
                popular_count=len(popular_configs),
                processing_time_ms=processing_time_ms,
            )

            return response

        except InsufficientDataError as e:
            logger.warning(
                "Insufficient data for recommendations",
                vehicle_id=str(vehicle_id),
                error=str(e),
            )
            return {
                "vehicle_id": str(vehicle_id),
                "recommendations": [],
                "popular_configurations": [],
                "metadata": {
                    "recommendation_count": 0,
                    "popular_count": 0,
                    "processing_time_ms": 0,
                    "generated_at": datetime.utcnow().isoformat(),
                    "error": "insufficient_data",
                    "error_message": str(e),
                },
            }
        except RecommendationError as e:
            raise RecommendationServiceError(
                "Failed to generate recommendations",
                vehicle_id=str(vehicle_id),
                error=str(e),
                **e.context,
            ) from e
        except Exception as e:
            raise RecommendationServiceError(
                "Unexpected error generating recommendations",
                vehicle_id=str(vehicle_id),
                error=str(e),
            ) from e

    async def get_popular_configurations(
        self,
        vehicle_id: uuid.UUID,
        make: Optional[str] = None,
        model: Optional[str] = None,
        year: Optional[int] = None,
        body_style: Optional[str] = None,
        limit: int = DEFAULT_POPULAR_LIMIT,
    ) -> dict[str, Any]:
        """
        Get popular configurations for similar vehicles.

        Args:
            vehicle_id: Vehicle ID for specific matching
            make: Vehicle make for broader matching
            model: Vehicle model for broader matching
            year: Vehicle year for broader matching
            body_style: Vehicle body style for broader matching
            limit: Maximum number of configurations

        Returns:
            Dictionary containing popular configurations and metadata

        Raises:
            RecommendationServiceError: If query fails
        """
        start_time = datetime.utcnow()

        try:
            configurations = await self.engine.get_popular_configurations(
                vehicle_id=vehicle_id,
                make=make,
                model=model,
                year=year,
                body_style=body_style,
                limit=limit,
            )

            processing_time_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )

            response = {
                "vehicle_id": str(vehicle_id),
                "configurations": configurations,
                "metadata": {
                    "configuration_count": len(configurations),
                    "processing_time_ms": processing_time_ms,
                    "generated_at": datetime.utcnow().isoformat(),
                },
            }

            logger.info(
                "Popular configurations retrieved successfully",
                vehicle_id=str(vehicle_id),
                configuration_count=len(configurations),
                processing_time_ms=processing_time_ms,
            )

            return response

        except Exception as e:
            raise RecommendationServiceError(
                "Failed to retrieve popular configurations",
                vehicle_id=str(vehicle_id),
                error=str(e),
            ) from e

    async def track_recommendation_events(
        self,
        vehicle_id: uuid.UUID,
        event_type: RecommendationEventType,
        package_ids: list[uuid.UUID],
        user_id: Optional[uuid.UUID] = None,
        session_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Track recommendation interaction events.

        Args:
            vehicle_id: Vehicle ID
            event_type: Type of event (viewed, clicked, selected, etc.)
            package_ids: Package IDs involved in the event
            user_id: Optional user ID
            session_id: Optional session ID
            metadata: Optional additional event metadata

        Raises:
            RecommendationServiceError: If tracking fails
        """
        if not self.enable_analytics:
            logger.debug(
                "Analytics tracking disabled, skipping event",
                event_type=event_type.value,
            )
            return

        try:
            event = RecommendationEvent(
                user_id=user_id,
                session_id=session_id,
                vehicle_id=vehicle_id,
                recommended_packages={},
                selected_packages={
                    "package_ids": [str(pkg_id) for pkg_id in package_ids],
                    "timestamp": datetime.utcnow().isoformat(),
                },
                event_type=event_type,
                event_metadata=metadata or {},
            )

            self.db.add(event)
            await self.db.flush()

            logger.info(
                "Recommendation event tracked",
                event_id=str(event.id),
                event_type=event_type.value,
                vehicle_id=str(vehicle_id),
                package_count=len(package_ids),
            )

        except Exception as e:
            logger.error(
                "Failed to track recommendation event",
                error=str(e),
                event_type=event_type.value,
                vehicle_id=str(vehicle_id),
            )
            raise RecommendationServiceError(
                "Failed to track recommendation event",
                vehicle_id=str(vehicle_id),
                event_type=event_type.value,
                error=str(e),
            ) from e

    async def calculate_package_savings(
        self,
        package_id: uuid.UUID,
        selected_option_ids: list[uuid.UUID],
    ) -> dict[str, Any]:
        """
        Calculate potential savings from selecting a package.

        Args:
            package_id: Package to evaluate
            selected_option_ids: Currently selected options

        Returns:
            Dictionary with savings calculations and metadata

        Raises:
            RecommendationServiceError: If calculation fails
        """
        try:
            savings_data = await self.engine.calculate_package_savings(
                package_id=package_id,
                selected_option_ids=selected_option_ids,
            )

            logger.debug(
                "Package savings calculated",
                package_id=str(package_id),
                savings_amount=savings_data["savings_amount"],
            )

            return savings_data

        except Exception as e:
            raise RecommendationServiceError(
                "Failed to calculate package savings",
                package_id=str(package_id),
                error=str(e),
            ) from e

    async def _track_recommendation_viewed(
        self,
        vehicle_id: uuid.UUID,
        recommendations: list[dict[str, Any]],
        user_id: Optional[uuid.UUID],
        session_id: Optional[str],
    ) -> None:
        """Track recommendation viewed event."""
        try:
            await self.track_recommendation_events(
                vehicle_id=vehicle_id,
                event_type=RecommendationEventType.VIEWED,
                package_ids=[
                    uuid.UUID(rec["package_id"]) for rec in recommendations
                ],
                user_id=user_id,
                session_id=session_id,
                metadata={
                    "recommendation_count": len(recommendations),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        except Exception as e:
            logger.warning(
                "Failed to track recommendation viewed event",
                error=str(e),
                vehicle_id=str(vehicle_id),
            )