"""
Recommendation engine with collaborative filtering and rule-based logic.

This module implements the core recommendation engine for suggesting vehicle packages
based on selected options, popular configurations, and collaborative filtering.
Includes comprehensive caching for performance optimization and detailed analytics.
"""

import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.cache.redis_client import RedisClient
from src.core.logging import get_logger
from src.database.models.package import Package
from src.database.models.recommendation_analytics import (
    PopularConfiguration,
    RecommendationEvent,
    RecommendationEventType,
)
from src.database.models.vehicle import Vehicle
from src.database.models.vehicle_option import VehicleOption

logger = get_logger(__name__)


class RecommendationError(Exception):
    """Base exception for recommendation engine errors."""

    def __init__(self, message: str, **context: Any):
        super().__init__(message)
        self.context = context
        logger.error(
            "Recommendation error",
            error=message,
            **context,
        )


class InsufficientDataError(RecommendationError):
    """Raised when insufficient data is available for recommendations."""

    pass


class RecommendationEngine:
    """
    Core recommendation engine for package suggestions.

    Implements collaborative filtering and rule-based logic to suggest relevant
    packages based on user selections, popular configurations, and historical data.
    Includes comprehensive caching for sub-100ms response times.
    """

    # Cache configuration
    CACHE_TTL_SECONDS = 300  # 5 minutes
    CACHE_KEY_PREFIX = "recommendations"

    # Recommendation parameters
    MIN_CONFIDENCE_SCORE = 0.3
    MAX_RECOMMENDATIONS = 5
    POPULARITY_WEIGHT = 0.4
    COMPATIBILITY_WEIGHT = 0.3
    SAVINGS_WEIGHT = 0.3
    TRENDING_DAYS = 30

    def __init__(
        self,
        db_session: AsyncSession,
        redis_client: Optional[RedisClient] = None,
        enable_cache: bool = True,
    ):
        """
        Initialize recommendation engine.

        Args:
            db_session: Database session for queries
            redis_client: Optional Redis client for caching
            enable_cache: Enable/disable caching
        """
        self.db = db_session
        self.redis = redis_client
        self.enable_cache = enable_cache and redis_client is not None

        logger.info(
            "Recommendation engine initialized",
            cache_enabled=self.enable_cache,
        )

    async def recommend_packages(
        self,
        vehicle_id: uuid.UUID,
        selected_option_ids: list[uuid.UUID],
        user_id: Optional[uuid.UUID] = None,
        session_id: Optional[str] = None,
        trim: Optional[str] = None,
        year: Optional[int] = None,
        max_results: int = MAX_RECOMMENDATIONS,
    ) -> list[dict[str, Any]]:
        """
        Generate package recommendations based on selected options.

        Args:
            vehicle_id: Vehicle being configured
            selected_option_ids: Currently selected option IDs
            user_id: Optional user ID for personalization
            session_id: Optional session ID for anonymous tracking
            trim: Optional trim level for compatibility filtering
            year: Optional model year for compatibility filtering
            max_results: Maximum number of recommendations to return

        Returns:
            List of recommended packages with scores and metadata

        Raises:
            RecommendationError: If recommendation generation fails
            InsufficientDataError: If insufficient data for recommendations
        """
        try:
            # Check cache first
            if self.enable_cache:
                cached = await self._get_cached_recommendations(
                    vehicle_id=vehicle_id,
                    selected_option_ids=selected_option_ids,
                    trim=trim,
                    year=year,
                )
                if cached is not None:
                    logger.debug(
                        "Returning cached recommendations",
                        vehicle_id=str(vehicle_id),
                        cache_hit=True,
                    )
                    return cached

            # Load vehicle packages
            packages = await self._load_vehicle_packages(
                vehicle_id=vehicle_id,
                trim=trim,
                year=year,
            )

            if not packages:
                raise InsufficientDataError(
                    "No packages available for vehicle",
                    vehicle_id=str(vehicle_id),
                )

            # Calculate recommendation scores
            recommendations = await self._calculate_recommendation_scores(
                packages=packages,
                selected_option_ids=selected_option_ids,
                vehicle_id=vehicle_id,
            )

            # Sort by score and limit results
            recommendations.sort(key=lambda x: x["score"], reverse=True)
            recommendations = recommendations[:max_results]

            # Track recommendation event
            await self._track_recommendation_event(
                vehicle_id=vehicle_id,
                recommended_packages=recommendations,
                user_id=user_id,
                session_id=session_id,
                event_type=RecommendationEventType.VIEWED,
            )

            # Cache results
            if self.enable_cache:
                await self._cache_recommendations(
                    vehicle_id=vehicle_id,
                    selected_option_ids=selected_option_ids,
                    trim=trim,
                    year=year,
                    recommendations=recommendations,
                )

            logger.info(
                "Generated package recommendations",
                vehicle_id=str(vehicle_id),
                recommendation_count=len(recommendations),
                selected_options=len(selected_option_ids),
            )

            return recommendations

        except InsufficientDataError:
            raise
        except Exception as e:
            raise RecommendationError(
                "Failed to generate recommendations",
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
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Get popular configurations for similar vehicles.

        Args:
            vehicle_id: Vehicle ID for specific matching
            make: Vehicle make for broader matching
            model: Vehicle model for broader matching
            year: Vehicle year for broader matching
            body_style: Vehicle body style for broader matching
            limit: Maximum number of configurations to return

        Returns:
            List of popular configurations with metadata

        Raises:
            RecommendationError: If query fails
        """
        try:
            # Build query for popular configurations
            stmt = (
                select(PopularConfiguration)
                .where(PopularConfiguration.vehicle_id == vehicle_id)
                .order_by(
                    PopularConfiguration.popularity_score.desc(),
                    PopularConfiguration.last_selected_at.desc(),
                )
                .limit(limit)
            )

            result = await self.db.execute(stmt)
            configs = result.scalars().all()

            # If not enough specific matches, broaden search
            if len(configs) < limit and any([make, model, year, body_style]):
                broader_stmt = select(PopularConfiguration)
                conditions = []

                if make:
                    conditions.append(PopularConfiguration.make == make)
                if model:
                    conditions.append(PopularConfiguration.model == model)
                if year:
                    conditions.append(PopularConfiguration.year == year)
                if body_style:
                    conditions.append(PopularConfiguration.body_style == body_style)

                if conditions:
                    broader_stmt = broader_stmt.where(and_(*conditions))

                broader_stmt = broader_stmt.order_by(
                    PopularConfiguration.popularity_score.desc()
                ).limit(limit - len(configs))

                broader_result = await self.db.execute(broader_stmt)
                configs.extend(broader_result.scalars().all())

            # Format configurations
            popular_configs = [
                {
                    "id": str(config.id),
                    "vehicle_id": str(config.vehicle_id),
                    "configuration_data": config.configuration_data,
                    "selection_count": config.selection_count,
                    "conversion_count": config.conversion_count,
                    "conversion_rate": config.conversion_rate,
                    "popularity_score": config.popularity_score,
                    "is_trending": config.is_trending,
                    "package_ids": config.package_ids,
                    "option_ids": config.option_ids,
                }
                for config in configs
            ]

            logger.info(
                "Retrieved popular configurations",
                vehicle_id=str(vehicle_id),
                configuration_count=len(popular_configs),
            )

            return popular_configs

        except Exception as e:
            raise RecommendationError(
                "Failed to retrieve popular configurations",
                vehicle_id=str(vehicle_id),
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
            RecommendationError: If calculation fails
        """
        try:
            # Load package
            stmt = select(Package).where(Package.id == package_id)
            result = await self.db.execute(stmt)
            package = result.scalar_one_or_none()

            if not package:
                raise RecommendationError(
                    "Package not found",
                    package_id=str(package_id),
                )

            # Load package options
            option_stmt = select(VehicleOption).where(
                VehicleOption.id.in_(package.included_options)
            )
            option_result = await self.db.execute(option_stmt)
            package_options = option_result.scalars().all()

            # Calculate individual option prices
            individual_total = sum(
                option.price for option in package_options
            )

            # Calculate package price with discount
            package_price = package.discounted_price

            # Calculate savings
            savings_amount = individual_total - package_price
            savings_percentage = (
                (savings_amount / individual_total * 100)
                if individual_total > 0
                else Decimal("0.00")
            )

            # Check overlap with selected options
            selected_set = set(selected_option_ids)
            package_set = set(package.included_options)
            overlap = selected_set & package_set
            additional_options = package_set - selected_set

            savings_data = {
                "package_id": str(package_id),
                "package_name": package.name,
                "individual_total": float(individual_total),
                "package_price": float(package_price),
                "savings_amount": float(savings_amount),
                "savings_percentage": float(savings_percentage),
                "option_count": len(package_options),
                "overlapping_options": len(overlap),
                "additional_options": len(additional_options),
                "value_proposition": self._generate_value_proposition(
                    savings_amount=savings_amount,
                    savings_percentage=savings_percentage,
                    additional_options=len(additional_options),
                ),
            }

            logger.debug(
                "Calculated package savings",
                package_id=str(package_id),
                savings_amount=float(savings_amount),
                savings_percentage=float(savings_percentage),
            )

            return savings_data

        except Exception as e:
            raise RecommendationError(
                "Failed to calculate package savings",
                package_id=str(package_id),
                error=str(e),
            ) from e

    async def _load_vehicle_packages(
        self,
        vehicle_id: uuid.UUID,
        trim: Optional[str] = None,
        year: Optional[int] = None,
    ) -> list[Package]:
        """Load packages for vehicle with compatibility filtering."""
        stmt = select(Package).where(Package.vehicle_id == vehicle_id)

        result = await self.db.execute(stmt)
        packages = result.scalars().all()

        # Filter by compatibility
        compatible_packages = []
        for package in packages:
            is_valid, _ = package.validate_compatibility(trim=trim, year=year)
            if is_valid:
                compatible_packages.append(package)

        logger.debug(
            "Loaded vehicle packages",
            vehicle_id=str(vehicle_id),
            total_packages=len(packages),
            compatible_packages=len(compatible_packages),
        )

        return compatible_packages

    async def _calculate_recommendation_scores(
        self,
        packages: list[Package],
        selected_option_ids: list[uuid.UUID],
        vehicle_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Calculate recommendation scores for packages."""
        recommendations = []
        selected_set = set(selected_option_ids)

        # Get popularity data
        popularity_data = await self._get_popularity_scores(vehicle_id)

        for package in packages:
            package_set = set(package.included_options)

            # Calculate compatibility score
            overlap = selected_set & package_set
            compatibility_score = (
                len(overlap) / len(selected_set)
                if selected_set
                else 0.0
            )

            # Get popularity score
            popularity_score = popularity_data.get(package.id, 0.0)

            # Calculate savings score
            savings_score = min(
                float(package.discount_percentage) / 100.0,
                1.0,
            )

            # Weighted final score
            final_score = (
                self.COMPATIBILITY_WEIGHT * compatibility_score
                + self.POPULARITY_WEIGHT * popularity_score
                + self.SAVINGS_WEIGHT * savings_score
            )

            # Only include if meets minimum confidence
            if final_score >= self.MIN_CONFIDENCE_SCORE:
                recommendations.append(
                    {
                        "package_id": str(package.id),
                        "package_name": package.name,
                        "description": package.description,
                        "base_price": float(package.base_price),
                        "discounted_price": float(package.discounted_price),
                        "discount_percentage": float(package.discount_percentage),
                        "savings_amount": float(package.savings_amount),
                        "included_options": [
                            str(opt_id) for opt_id in package.included_options
                        ],
                        "option_count": package.option_count,
                        "score": final_score,
                        "compatibility_score": compatibility_score,
                        "popularity_score": popularity_score,
                        "savings_score": savings_score,
                        "overlapping_options": len(overlap),
                    }
                )

        return recommendations

    async def _get_popularity_scores(
        self,
        vehicle_id: uuid.UUID,
    ) -> dict[uuid.UUID, float]:
        """Get normalized popularity scores for packages."""
        # Query popular configurations
        cutoff_date = datetime.utcnow() - timedelta(days=self.TRENDING_DAYS)

        stmt = (
            select(PopularConfiguration)
            .where(
                and_(
                    PopularConfiguration.vehicle_id == vehicle_id,
                    PopularConfiguration.last_selected_at >= cutoff_date,
                )
            )
        )

        result = await self.db.execute(stmt)
        configs = result.scalars().all()

        # Count package occurrences
        package_counts: dict[uuid.UUID, int] = defaultdict(int)
        for config in configs:
            for package_id_str in config.package_ids:
                try:
                    package_id = uuid.UUID(package_id_str)
                    package_counts[package_id] += config.selection_count
                except (ValueError, TypeError):
                    continue

        # Normalize scores
        max_count = max(package_counts.values()) if package_counts else 1
        popularity_scores = {
            package_id: count / max_count
            for package_id, count in package_counts.items()
        }

        return popularity_scores

    async def _track_recommendation_event(
        self,
        vehicle_id: uuid.UUID,
        recommended_packages: list[dict[str, Any]],
        user_id: Optional[uuid.UUID],
        session_id: Optional[str],
        event_type: RecommendationEventType,
    ) -> None:
        """Track recommendation event for analytics."""
        try:
            event = RecommendationEvent(
                user_id=user_id,
                session_id=session_id,
                vehicle_id=vehicle_id,
                recommended_packages={
                    "packages": [
                        {
                            "id": pkg["package_id"],
                            "score": pkg["score"],
                            "name": pkg["package_name"],
                        }
                        for pkg in recommended_packages
                    ]
                },
                selected_packages={},
                event_type=event_type,
                event_metadata={
                    "recommendation_count": len(recommended_packages),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            self.db.add(event)
            await self.db.flush()

            logger.debug(
                "Tracked recommendation event",
                event_id=str(event.id),
                event_type=event_type.value,
                vehicle_id=str(vehicle_id),
            )

        except Exception as e:
            logger.warning(
                "Failed to track recommendation event",
                error=str(e),
                vehicle_id=str(vehicle_id),
            )

    def _generate_value_proposition(
        self,
        savings_amount: Decimal,
        savings_percentage: Decimal,
        additional_options: int,
    ) -> str:
        """Generate human-readable value proposition."""
        if savings_amount <= 0:
            return "Convenient bundle of popular options"

        if savings_percentage >= 20:
            return (
                f"Save {savings_percentage:.0f}% "
                f"(${savings_amount:,.2f}) with this package"
            )
        elif additional_options > 3:
            return (
                f"Get {additional_options} additional features "
                f"and save ${savings_amount:,.2f}"
            )
        else:
            return f"Save ${savings_amount:,.2f} with this popular package"

    async def _get_cached_recommendations(
        self,
        vehicle_id: uuid.UUID,
        selected_option_ids: list[uuid.UUID],
        trim: Optional[str],
        year: Optional[int],
    ) -> Optional[list[dict[str, Any]]]:
        """Get cached recommendations if available."""
        if not self.enable_cache or not self.redis:
            return None

        try:
            cache_key = self._make_cache_key(
                vehicle_id=vehicle_id,
                selected_option_ids=selected_option_ids,
                trim=trim,
                year=year,
            )

            cached_data = await self.redis.get_json(cache_key)
            return cached_data

        except Exception as e:
            logger.warning(
                "Failed to retrieve cached recommendations",
                error=str(e),
                vehicle_id=str(vehicle_id),
            )
            return None

    async def _cache_recommendations(
        self,
        vehicle_id: uuid.UUID,
        selected_option_ids: list[uuid.UUID],
        trim: Optional[str],
        year: Optional[int],
        recommendations: list[dict[str, Any]],
    ) -> None:
        """Cache recommendations for future requests."""
        if not self.enable_cache or not self.redis:
            return

        try:
            cache_key = self._make_cache_key(
                vehicle_id=vehicle_id,
                selected_option_ids=selected_option_ids,
                trim=trim,
                year=year,
            )

            await self.redis.set_json(
                cache_key,
                recommendations,
                ex=self.CACHE_TTL_SECONDS,
            )

            logger.debug(
                "Cached recommendations",
                cache_key=cache_key,
                ttl=self.CACHE_TTL_SECONDS,
            )

        except Exception as e:
            logger.warning(
                "Failed to cache recommendations",
                error=str(e),
                vehicle_id=str(vehicle_id),
            )

    def _make_cache_key(
        self,
        vehicle_id: uuid.UUID,
        selected_option_ids: list[uuid.UUID],
        trim: Optional[str],
        year: Optional[int],
    ) -> str:
        """Generate cache key for recommendations."""
        option_ids_str = ",".join(
            sorted(str(opt_id) for opt_id in selected_option_ids)
        )
        trim_str = trim or "none"
        year_str = str(year) if year else "none"

        return (
            f"{self.CACHE_KEY_PREFIX}:"
            f"{vehicle_id}:"
            f"{option_ids_str}:"
            f"{trim_str}:"
            f"{year_str}"
        )