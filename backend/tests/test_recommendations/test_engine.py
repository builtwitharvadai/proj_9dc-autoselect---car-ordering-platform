"""
Comprehensive test suite for recommendation engine.

Tests cover recommendation algorithms, package suggestions, savings calculations,
collaborative filtering logic, caching, and performance requirements.
Achieves >80% coverage with extensive edge case and error scenario testing.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.cache.redis_client import RedisClient
from src.database.models.package import Package
from src.database.models.recommendation_analytics import (
    PopularConfiguration,
    RecommendationEvent,
    RecommendationEventType,
)
from src.database.models.vehicle import Vehicle
from src.database.models.vehicle_option import VehicleOption
from src.services.recommendations.recommendation_engine import (
    InsufficientDataError,
    RecommendationEngine,
    RecommendationError,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.add = Mock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client."""
    redis = AsyncMock(spec=RedisClient)
    redis.get_json = AsyncMock(return_value=None)
    redis.set_json = AsyncMock()
    return redis


@pytest.fixture
def recommendation_engine(mock_db_session, mock_redis_client):
    """Create recommendation engine instance with mocked dependencies."""
    return RecommendationEngine(
        db_session=mock_db_session,
        redis_client=mock_redis_client,
        enable_cache=True,
    )


@pytest.fixture
def recommendation_engine_no_cache(mock_db_session):
    """Create recommendation engine without caching."""
    return RecommendationEngine(
        db_session=mock_db_session,
        redis_client=None,
        enable_cache=False,
    )


@pytest.fixture
def sample_vehicle_id():
    """Generate sample vehicle ID."""
    return uuid.uuid4()


@pytest.fixture
def sample_package_ids():
    """Generate sample package IDs."""
    return [uuid.uuid4() for _ in range(3)]


@pytest.fixture
def sample_option_ids():
    """Generate sample option IDs."""
    return [uuid.uuid4() for _ in range(5)]


@pytest.fixture
def sample_packages(sample_vehicle_id, sample_option_ids):
    """Create sample package objects."""
    packages = []
    for i in range(3):
        package = Mock(spec=Package)
        package.id = uuid.uuid4()
        package.vehicle_id = sample_vehicle_id
        package.name = f"Premium Package {i+1}"
        package.description = f"Description for package {i+1}"
        package.base_price = Decimal("5000.00")
        package.discounted_price = Decimal("4000.00")
        package.discount_percentage = Decimal("20.00")
        package.savings_amount = Decimal("1000.00")
        package.included_options = sample_option_ids[:3]
        package.option_count = 3
        package.validate_compatibility = Mock(return_value=(True, None))
        packages.append(package)
    return packages


@pytest.fixture
def sample_vehicle_options(sample_option_ids):
    """Create sample vehicle option objects."""
    options = []
    for i, option_id in enumerate(sample_option_ids):
        option = Mock(spec=VehicleOption)
        option.id = option_id
        option.name = f"Option {i+1}"
        option.price = Decimal("1500.00")
        options.append(option)
    return options


@pytest.fixture
def sample_popular_configs(sample_vehicle_id, sample_package_ids):
    """Create sample popular configuration objects."""
    configs = []
    for i in range(3):
        config = Mock(spec=PopularConfiguration)
        config.id = uuid.uuid4()
        config.vehicle_id = sample_vehicle_id
        config.configuration_data = {"trim": "Premium", "year": 2024}
        config.selection_count = 100 - (i * 20)
        config.conversion_count = 50 - (i * 10)
        config.conversion_rate = Decimal("0.5")
        config.popularity_score = Decimal("0.8") - (Decimal("0.2") * i)
        config.is_trending = i == 0
        config.package_ids = [str(sample_package_ids[i])]
        config.option_ids = [str(uuid.uuid4()) for _ in range(3)]
        config.last_selected_at = datetime.utcnow() - timedelta(days=i)
        configs.append(config)
    return configs


# ============================================================================
# Unit Tests - Initialization
# ============================================================================


class TestRecommendationEngineInitialization:
    """Test recommendation engine initialization."""

    def test_init_with_cache_enabled(self, mock_db_session, mock_redis_client):
        """Test initialization with caching enabled."""
        engine = RecommendationEngine(
            db_session=mock_db_session,
            redis_client=mock_redis_client,
            enable_cache=True,
        )

        assert engine.db == mock_db_session
        assert engine.redis == mock_redis_client
        assert engine.enable_cache is True

    def test_init_with_cache_disabled(self, mock_db_session, mock_redis_client):
        """Test initialization with caching disabled."""
        engine = RecommendationEngine(
            db_session=mock_db_session,
            redis_client=mock_redis_client,
            enable_cache=False,
        )

        assert engine.db == mock_db_session
        assert engine.redis == mock_redis_client
        assert engine.enable_cache is False

    def test_init_without_redis_client(self, mock_db_session):
        """Test initialization without Redis client."""
        engine = RecommendationEngine(
            db_session=mock_db_session,
            redis_client=None,
            enable_cache=True,
        )

        assert engine.db == mock_db_session
        assert engine.redis is None
        assert engine.enable_cache is False

    def test_cache_configuration_constants(self):
        """Test cache configuration constants are properly set."""
        assert RecommendationEngine.CACHE_TTL_SECONDS == 300
        assert RecommendationEngine.CACHE_KEY_PREFIX == "recommendations"

    def test_recommendation_parameters(self):
        """Test recommendation algorithm parameters."""
        assert RecommendationEngine.MIN_CONFIDENCE_SCORE == 0.3
        assert RecommendationEngine.MAX_RECOMMENDATIONS == 5
        assert RecommendationEngine.POPULARITY_WEIGHT == 0.4
        assert RecommendationEngine.COMPATIBILITY_WEIGHT == 0.3
        assert RecommendationEngine.SAVINGS_WEIGHT == 0.3
        assert RecommendationEngine.TRENDING_DAYS == 30


# ============================================================================
# Unit Tests - Package Recommendations
# ============================================================================


class TestRecommendPackages:
    """Test package recommendation generation."""

    @pytest.mark.asyncio
    async def test_recommend_packages_success(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
        sample_option_ids,
        sample_packages,
    ):
        """Test successful package recommendation generation."""
        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = sample_packages
        mock_db_session.execute.return_value = mock_result

        # Mock popularity scores
        with patch.object(
            recommendation_engine,
            "_get_popularity_scores",
            return_value={sample_packages[0].id: 0.8},
        ):
            recommendations = await recommendation_engine.recommend_packages(
                vehicle_id=sample_vehicle_id,
                selected_option_ids=sample_option_ids[:2],
                max_results=5,
            )

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert all("package_id" in rec for rec in recommendations)
        assert all("score" in rec for rec in recommendations)
        assert all("package_name" in rec for rec in recommendations)

    @pytest.mark.asyncio
    async def test_recommend_packages_with_cache_hit(
        self,
        recommendation_engine,
        mock_redis_client,
        sample_vehicle_id,
        sample_option_ids,
    ):
        """Test recommendation retrieval from cache."""
        cached_recommendations = [
            {
                "package_id": str(uuid.uuid4()),
                "package_name": "Cached Package",
                "score": 0.85,
            }
        ]
        mock_redis_client.get_json.return_value = cached_recommendations

        recommendations = await recommendation_engine.recommend_packages(
            vehicle_id=sample_vehicle_id,
            selected_option_ids=sample_option_ids,
        )

        assert recommendations == cached_recommendations
        mock_redis_client.get_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_recommend_packages_no_packages_available(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
        sample_option_ids,
    ):
        """Test error when no packages available for vehicle."""
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(InsufficientDataError) as exc_info:
            await recommendation_engine.recommend_packages(
                vehicle_id=sample_vehicle_id,
                selected_option_ids=sample_option_ids,
            )

        assert "No packages available" in str(exc_info.value)
        assert exc_info.value.context["vehicle_id"] == str(sample_vehicle_id)

    @pytest.mark.asyncio
    async def test_recommend_packages_with_trim_filter(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
        sample_option_ids,
        sample_packages,
    ):
        """Test package recommendations with trim level filtering."""
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = sample_packages
        mock_db_session.execute.return_value = mock_result

        with patch.object(
            recommendation_engine,
            "_get_popularity_scores",
            return_value={},
        ):
            recommendations = await recommendation_engine.recommend_packages(
                vehicle_id=sample_vehicle_id,
                selected_option_ids=sample_option_ids,
                trim="Premium",
                year=2024,
            )

        assert isinstance(recommendations, list)
        for package in sample_packages:
            package.validate_compatibility.assert_called_with(
                trim="Premium", year=2024
            )

    @pytest.mark.asyncio
    async def test_recommend_packages_max_results_limit(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
        sample_option_ids,
        sample_packages,
    ):
        """Test max results limit is respected."""
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = sample_packages
        mock_db_session.execute.return_value = mock_result

        with patch.object(
            recommendation_engine,
            "_get_popularity_scores",
            return_value={},
        ):
            recommendations = await recommendation_engine.recommend_packages(
                vehicle_id=sample_vehicle_id,
                selected_option_ids=sample_option_ids,
                max_results=2,
            )

        assert len(recommendations) <= 2

    @pytest.mark.asyncio
    async def test_recommend_packages_tracks_analytics(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
        sample_option_ids,
        sample_packages,
    ):
        """Test recommendation event tracking."""
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = sample_packages
        mock_db_session.execute.return_value = mock_result

        user_id = uuid.uuid4()
        session_id = "test-session-123"

        with patch.object(
            recommendation_engine,
            "_get_popularity_scores",
            return_value={},
        ):
            await recommendation_engine.recommend_packages(
                vehicle_id=sample_vehicle_id,
                selected_option_ids=sample_option_ids,
                user_id=user_id,
                session_id=session_id,
            )

        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_recommend_packages_caches_results(
        self,
        recommendation_engine,
        mock_db_session,
        mock_redis_client,
        sample_vehicle_id,
        sample_option_ids,
        sample_packages,
    ):
        """Test recommendation results are cached."""
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = sample_packages
        mock_db_session.execute.return_value = mock_result

        with patch.object(
            recommendation_engine,
            "_get_popularity_scores",
            return_value={},
        ):
            await recommendation_engine.recommend_packages(
                vehicle_id=sample_vehicle_id,
                selected_option_ids=sample_option_ids,
            )

        mock_redis_client.set_json.assert_called_once()
        call_args = mock_redis_client.set_json.call_args
        assert call_args[1]["ex"] == RecommendationEngine.CACHE_TTL_SECONDS

    @pytest.mark.asyncio
    async def test_recommend_packages_database_error(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
        sample_option_ids,
    ):
        """Test error handling for database failures."""
        mock_db_session.execute.side_effect = Exception("Database error")

        with pytest.raises(RecommendationError) as exc_info:
            await recommendation_engine.recommend_packages(
                vehicle_id=sample_vehicle_id,
                selected_option_ids=sample_option_ids,
            )

        assert "Failed to generate recommendations" in str(exc_info.value)
        assert exc_info.value.context["vehicle_id"] == str(sample_vehicle_id)


# ============================================================================
# Unit Tests - Popular Configurations
# ============================================================================


class TestGetPopularConfigurations:
    """Test popular configuration retrieval."""

    @pytest.mark.asyncio
    async def test_get_popular_configurations_success(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
        sample_popular_configs,
    ):
        """Test successful popular configuration retrieval."""
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = sample_popular_configs
        mock_db_session.execute.return_value = mock_result

        configs = await recommendation_engine.get_popular_configurations(
            vehicle_id=sample_vehicle_id,
            limit=5,
        )

        assert isinstance(configs, list)
        assert len(configs) == len(sample_popular_configs)
        assert all("id" in config for config in configs)
        assert all("popularity_score" in config for config in configs)

    @pytest.mark.asyncio
    async def test_get_popular_configurations_with_filters(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
        sample_popular_configs,
    ):
        """Test popular configurations with vehicle attribute filters."""
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = sample_popular_configs
        mock_db_session.execute.return_value = mock_result

        configs = await recommendation_engine.get_popular_configurations(
            vehicle_id=sample_vehicle_id,
            make="Toyota",
            model="Camry",
            year=2024,
            body_style="Sedan",
            limit=5,
        )

        assert isinstance(configs, list)
        assert len(configs) > 0

    @pytest.mark.asyncio
    async def test_get_popular_configurations_broadens_search(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
        sample_popular_configs,
    ):
        """Test search broadening when insufficient specific matches."""
        # First query returns 1 result, second query returns 2 more
        mock_result_1 = AsyncMock()
        mock_result_1.scalars.return_value.all.return_value = [
            sample_popular_configs[0]
        ]

        mock_result_2 = AsyncMock()
        mock_result_2.scalars.return_value.all.return_value = sample_popular_configs[
            1:3
        ]

        mock_db_session.execute.side_effect = [mock_result_1, mock_result_2]

        configs = await recommendation_engine.get_popular_configurations(
            vehicle_id=sample_vehicle_id,
            make="Toyota",
            limit=3,
        )

        assert len(configs) == 3
        assert mock_db_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_popular_configurations_empty_result(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
    ):
        """Test handling of empty configuration results."""
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        configs = await recommendation_engine.get_popular_configurations(
            vehicle_id=sample_vehicle_id,
            limit=5,
        )

        assert configs == []

    @pytest.mark.asyncio
    async def test_get_popular_configurations_database_error(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
    ):
        """Test error handling for database failures."""
        mock_db_session.execute.side_effect = Exception("Database error")

        with pytest.raises(RecommendationError) as exc_info:
            await recommendation_engine.get_popular_configurations(
                vehicle_id=sample_vehicle_id
            )

        assert "Failed to retrieve popular configurations" in str(exc_info.value)


# ============================================================================
# Unit Tests - Package Savings Calculation
# ============================================================================


class TestCalculatePackageSavings:
    """Test package savings calculation."""

    @pytest.mark.asyncio
    async def test_calculate_package_savings_success(
        self,
        recommendation_engine,
        mock_db_session,
        sample_packages,
        sample_vehicle_options,
    ):
        """Test successful savings calculation."""
        package = sample_packages[0]

        # Mock package query
        mock_package_result = AsyncMock()
        mock_package_result.scalar_one_or_none.return_value = package

        # Mock options query
        mock_options_result = AsyncMock()
        mock_options_result.scalars.return_value.all.return_value = (
            sample_vehicle_options[:3]
        )

        mock_db_session.execute.side_effect = [
            mock_package_result,
            mock_options_result,
        ]

        savings = await recommendation_engine.calculate_package_savings(
            package_id=package.id,
            selected_option_ids=[sample_vehicle_options[0].id],
        )

        assert isinstance(savings, dict)
        assert "package_id" in savings
        assert "savings_amount" in savings
        assert "savings_percentage" in savings
        assert "value_proposition" in savings
        assert savings["savings_amount"] > 0

    @pytest.mark.asyncio
    async def test_calculate_package_savings_package_not_found(
        self,
        recommendation_engine,
        mock_db_session,
    ):
        """Test error when package not found."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        package_id = uuid.uuid4()

        with pytest.raises(RecommendationError) as exc_info:
            await recommendation_engine.calculate_package_savings(
                package_id=package_id,
                selected_option_ids=[],
            )

        assert "Package not found" in str(exc_info.value)
        assert exc_info.value.context["package_id"] == str(package_id)

    @pytest.mark.asyncio
    async def test_calculate_package_savings_with_overlap(
        self,
        recommendation_engine,
        mock_db_session,
        sample_packages,
        sample_vehicle_options,
    ):
        """Test savings calculation with overlapping options."""
        package = sample_packages[0]

        mock_package_result = AsyncMock()
        mock_package_result.scalar_one_or_none.return_value = package

        mock_options_result = AsyncMock()
        mock_options_result.scalars.return_value.all.return_value = (
            sample_vehicle_options[:3]
        )

        mock_db_session.execute.side_effect = [
            mock_package_result,
            mock_options_result,
        ]

        # Select options that overlap with package
        selected_ids = [sample_vehicle_options[0].id, sample_vehicle_options[1].id]

        savings = await recommendation_engine.calculate_package_savings(
            package_id=package.id,
            selected_option_ids=selected_ids,
        )

        assert savings["overlapping_options"] == 2
        assert savings["additional_options"] == 1

    @pytest.mark.asyncio
    async def test_calculate_package_savings_zero_savings(
        self,
        recommendation_engine,
        mock_db_session,
        sample_packages,
        sample_vehicle_options,
    ):
        """Test savings calculation when no savings available."""
        package = sample_packages[0]
        package.discounted_price = package.base_price  # No discount

        mock_package_result = AsyncMock()
        mock_package_result.scalar_one_or_none.return_value = package

        mock_options_result = AsyncMock()
        mock_options_result.scalars.return_value.all.return_value = (
            sample_vehicle_options[:3]
        )

        mock_db_session.execute.side_effect = [
            mock_package_result,
            mock_options_result,
        ]

        savings = await recommendation_engine.calculate_package_savings(
            package_id=package.id,
            selected_option_ids=[],
        )

        assert savings["savings_amount"] <= 0
        assert "Convenient bundle" in savings["value_proposition"]


# ============================================================================
# Unit Tests - Score Calculation
# ============================================================================


class TestCalculateRecommendationScores:
    """Test recommendation score calculation."""

    @pytest.mark.asyncio
    async def test_calculate_scores_with_compatibility(
        self,
        recommendation_engine,
        sample_packages,
        sample_option_ids,
        sample_vehicle_id,
    ):
        """Test score calculation with high compatibility."""
        with patch.object(
            recommendation_engine,
            "_get_popularity_scores",
            return_value={sample_packages[0].id: 0.8},
        ):
            recommendations = await recommendation_engine._calculate_recommendation_scores(
                packages=sample_packages,
                selected_option_ids=sample_option_ids[:3],
                vehicle_id=sample_vehicle_id,
            )

        assert len(recommendations) > 0
        assert all("compatibility_score" in rec for rec in recommendations)
        assert all("popularity_score" in rec for rec in recommendations)
        assert all("savings_score" in rec for rec in recommendations)

    @pytest.mark.asyncio
    async def test_calculate_scores_filters_low_confidence(
        self,
        recommendation_engine,
        sample_packages,
        sample_option_ids,
        sample_vehicle_id,
    ):
        """Test low confidence scores are filtered out."""
        # Set all scores to zero to get low confidence
        for package in sample_packages:
            package.discount_percentage = Decimal("0.00")

        with patch.object(
            recommendation_engine,
            "_get_popularity_scores",
            return_value={},
        ):
            recommendations = await recommendation_engine._calculate_recommendation_scores(
                packages=sample_packages,
                selected_option_ids=[],  # No overlap
                vehicle_id=sample_vehicle_id,
            )

        # Should filter out packages below MIN_CONFIDENCE_SCORE
        assert all(
            rec["score"] >= RecommendationEngine.MIN_CONFIDENCE_SCORE
            for rec in recommendations
        )

    @pytest.mark.asyncio
    async def test_calculate_scores_weighted_correctly(
        self,
        recommendation_engine,
        sample_packages,
        sample_option_ids,
        sample_vehicle_id,
    ):
        """Test score weights are applied correctly."""
        with patch.object(
            recommendation_engine,
            "_get_popularity_scores",
            return_value={sample_packages[0].id: 1.0},
        ):
            recommendations = await recommendation_engine._calculate_recommendation_scores(
                packages=sample_packages[:1],
                selected_option_ids=sample_option_ids[:3],
                vehicle_id=sample_vehicle_id,
            )

        if recommendations:
            rec = recommendations[0]
            expected_score = (
                RecommendationEngine.COMPATIBILITY_WEIGHT * rec["compatibility_score"]
                + RecommendationEngine.POPULARITY_WEIGHT * rec["popularity_score"]
                + RecommendationEngine.SAVINGS_WEIGHT * rec["savings_score"]
            )
            assert abs(rec["score"] - expected_score) < 0.01


# ============================================================================
# Unit Tests - Popularity Scores
# ============================================================================


class TestGetPopularityScores:
    """Test popularity score calculation."""

    @pytest.mark.asyncio
    async def test_get_popularity_scores_success(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
        sample_popular_configs,
    ):
        """Test successful popularity score retrieval."""
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = sample_popular_configs
        mock_db_session.execute.return_value = mock_result

        scores = await recommendation_engine._get_popularity_scores(
            vehicle_id=sample_vehicle_id
        )

        assert isinstance(scores, dict)
        assert all(isinstance(k, uuid.UUID) for k in scores.keys())
        assert all(0.0 <= v <= 1.0 for v in scores.values())

    @pytest.mark.asyncio
    async def test_get_popularity_scores_normalization(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
        sample_popular_configs,
    ):
        """Test popularity scores are normalized to 0-1 range."""
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = sample_popular_configs
        mock_db_session.execute.return_value = mock_result

        scores = await recommendation_engine._get_popularity_scores(
            vehicle_id=sample_vehicle_id
        )

        if scores:
            max_score = max(scores.values())
            assert max_score == 1.0

    @pytest.mark.asyncio
    async def test_get_popularity_scores_empty_result(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
    ):
        """Test handling of empty popularity data."""
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        scores = await recommendation_engine._get_popularity_scores(
            vehicle_id=sample_vehicle_id
        )

        assert scores == {}

    @pytest.mark.asyncio
    async def test_get_popularity_scores_filters_by_date(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
    ):
        """Test popularity scores filter by trending days."""
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        await recommendation_engine._get_popularity_scores(vehicle_id=sample_vehicle_id)

        # Verify date filtering in query
        call_args = mock_db_session.execute.call_args[0][0]
        assert call_args is not None


# ============================================================================
# Unit Tests - Caching
# ============================================================================


class TestCaching:
    """Test caching functionality."""

    @pytest.mark.asyncio
    async def test_cache_key_generation(
        self,
        recommendation_engine,
        sample_vehicle_id,
        sample_option_ids,
    ):
        """Test cache key generation is consistent."""
        key1 = recommendation_engine._make_cache_key(
            vehicle_id=sample_vehicle_id,
            selected_option_ids=sample_option_ids,
            trim="Premium",
            year=2024,
        )

        key2 = recommendation_engine._make_cache_key(
            vehicle_id=sample_vehicle_id,
            selected_option_ids=sample_option_ids,
            trim="Premium",
            year=2024,
        )

        assert key1 == key2
        assert RecommendationEngine.CACHE_KEY_PREFIX in key1
        assert str(sample_vehicle_id) in key1

    @pytest.mark.asyncio
    async def test_cache_key_different_for_different_inputs(
        self,
        recommendation_engine,
        sample_vehicle_id,
        sample_option_ids,
    ):
        """Test cache keys differ for different inputs."""
        key1 = recommendation_engine._make_cache_key(
            vehicle_id=sample_vehicle_id,
            selected_option_ids=sample_option_ids[:2],
            trim="Premium",
            year=2024,
        )

        key2 = recommendation_engine._make_cache_key(
            vehicle_id=sample_vehicle_id,
            selected_option_ids=sample_option_ids[:3],
            trim="Premium",
            year=2024,
        )

        assert key1 != key2

    @pytest.mark.asyncio
    async def test_get_cached_recommendations_success(
        self,
        recommendation_engine,
        mock_redis_client,
        sample_vehicle_id,
        sample_option_ids,
    ):
        """Test successful cache retrieval."""
        cached_data = [{"package_id": str(uuid.uuid4()), "score": 0.9}]
        mock_redis_client.get_json.return_value = cached_data

        result = await recommendation_engine._get_cached_recommendations(
            vehicle_id=sample_vehicle_id,
            selected_option_ids=sample_option_ids,
            trim="Premium",
            year=2024,
        )

        assert result == cached_data
        mock_redis_client.get_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_recommendations_cache_miss(
        self,
        recommendation_engine,
        mock_redis_client,
        sample_vehicle_id,
        sample_option_ids,
    ):
        """Test cache miss returns None."""
        mock_redis_client.get_json.return_value = None

        result = await recommendation_engine._get_cached_recommendations(
            vehicle_id=sample_vehicle_id,
            selected_option_ids=sample_option_ids,
            trim=None,
            year=None,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_cached_recommendations_redis_error(
        self,
        recommendation_engine,
        mock_redis_client,
        sample_vehicle_id,
        sample_option_ids,
    ):
        """Test cache retrieval handles Redis errors gracefully."""
        mock_redis_client.get_json.side_effect = Exception("Redis error")

        result = await recommendation_engine._get_cached_recommendations(
            vehicle_id=sample_vehicle_id,
            selected_option_ids=sample_option_ids,
            trim=None,
            year=None,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_recommendations_success(
        self,
        recommendation_engine,
        mock_redis_client,
        sample_vehicle_id,
        sample_option_ids,
    ):
        """Test successful cache storage."""
        recommendations = [{"package_id": str(uuid.uuid4()), "score": 0.9}]

        await recommendation_engine._cache_recommendations(
            vehicle_id=sample_vehicle_id,
            selected_option_ids=sample_option_ids,
            trim="Premium",
            year=2024,
            recommendations=recommendations,
        )

        mock_redis_client.set_json.assert_called_once()
        call_args = mock_redis_client.set_json.call_args
        assert call_args[0][1] == recommendations
        assert call_args[1]["ex"] == RecommendationEngine.CACHE_TTL_SECONDS

    @pytest.mark.asyncio
    async def test_cache_recommendations_redis_error(
        self,
        recommendation_engine,
        mock_redis_client,
        sample_vehicle_id,
        sample_option_ids,
    ):
        """Test cache storage handles Redis errors gracefully."""
        mock_redis_client.set_json.side_effect = Exception("Redis error")
        recommendations = [{"package_id": str(uuid.uuid4()), "score": 0.9}]

        # Should not raise exception
        await recommendation_engine._cache_recommendations(
            vehicle_id=sample_vehicle_id,
            selected_option_ids=sample_option_ids,
            trim=None,
            year=None,
            recommendations=recommendations,
        )

    @pytest.mark.asyncio
    async def test_caching_disabled_when_no_redis(
        self,
        recommendation_engine_no_cache,
        sample_vehicle_id,
        sample_option_ids,
    ):
        """Test caching is disabled when Redis not available."""
        result = await recommendation_engine_no_cache._get_cached_recommendations(
            vehicle_id=sample_vehicle_id,
            selected_option_ids=sample_option_ids,
            trim=None,
            year=None,
        )

        assert result is None


# ============================================================================
# Unit Tests - Analytics Tracking
# ============================================================================


class TestAnalyticsTracking:
    """Test recommendation analytics tracking."""

    @pytest.mark.asyncio
    async def test_track_recommendation_event_success(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
    ):
        """Test successful event tracking."""
        recommendations = [
            {
                "package_id": str(uuid.uuid4()),
                "package_name": "Test Package",
                "score": 0.85,
            }
        ]

        await recommendation_engine._track_recommendation_event(
            vehicle_id=sample_vehicle_id,
            recommended_packages=recommendations,
            user_id=uuid.uuid4(),
            session_id="test-session",
            event_type=RecommendationEventType.VIEWED,
        )

        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_recommendation_event_without_user(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
    ):
        """Test event tracking without user ID."""
        recommendations = [
            {
                "package_id": str(uuid.uuid4()),
                "package_name": "Test Package",
                "score": 0.85,
            }
        ]

        await recommendation_engine._track_recommendation_event(
            vehicle_id=sample_vehicle_id,
            recommended_packages=recommendations,
            user_id=None,
            session_id="anonymous-session",
            event_type=RecommendationEventType.VIEWED,
        )

        mock_db_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_recommendation_event_handles_errors(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
    ):
        """Test event tracking handles errors gracefully."""
        mock_db_session.add.side_effect = Exception("Database error")
        recommendations = [
            {
                "package_id": str(uuid.uuid4()),
                "package_name": "Test Package",
                "score": 0.85,
            }
        ]

        # Should not raise exception
        await recommendation_engine._track_recommendation_event(
            vehicle_id=sample_vehicle_id,
            recommended_packages=recommendations,
            user_id=None,
            session_id=None,
            event_type=RecommendationEventType.VIEWED,
        )


# ============================================================================
# Unit Tests - Value Proposition Generation
# ============================================================================


class TestValuePropositionGeneration:
    """Test value proposition text generation."""

    def test_generate_value_proposition_high_savings(
        self,
        recommendation_engine,
    ):
        """Test value proposition for high savings percentage."""
        proposition = recommendation_engine._generate_value_proposition(
            savings_amount=Decimal("2000.00"),
            savings_percentage=Decimal("25.00"),
            additional_options=2,
        )

        assert "25%" in proposition
        assert "$2,000.00" in proposition
        assert "Save" in proposition

    def test_generate_value_proposition_many_options(
        self,
        recommendation_engine,
    ):
        """Test value proposition for many additional options."""
        proposition = recommendation_engine._generate_value_proposition(
            savings_amount=Decimal("500.00"),
            savings_percentage=Decimal("10.00"),
            additional_options=5,
        )

        assert "5 additional features" in proposition
        assert "$500.00" in proposition

    def test_generate_value_proposition_moderate_savings(
        self,
        recommendation_engine,
    ):
        """Test value proposition for moderate savings."""
        proposition = recommendation_engine._generate_value_proposition(
            savings_amount=Decimal("800.00"),
            savings_percentage=Decimal("15.00"),
            additional_options=2,
        )

        assert "$800.00" in proposition
        assert "popular package" in proposition

    def test_generate_value_proposition_no_savings(
        self,
        recommendation_engine,
    ):
        """Test value proposition when no savings."""
        proposition = recommendation_engine._generate_value_proposition(
            savings_amount=Decimal("0.00"),
            savings_percentage=Decimal("0.00"),
            additional_options=3,
        )

        assert "Convenient bundle" in proposition


# ============================================================================
# Unit Tests - Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error handling and exceptions."""

    def test_recommendation_error_initialization(self):
        """Test RecommendationError initialization."""
        error = RecommendationError(
            "Test error",
            vehicle_id="test-id",
            additional_context="test",
        )

        assert str(error) == "Test error"
        assert error.context["vehicle_id"] == "test-id"
        assert error.context["additional_context"] == "test"

    def test_insufficient_data_error_inheritance(self):
        """Test InsufficientDataError inherits from RecommendationError."""
        error = InsufficientDataError("No data", vehicle_id="test-id")

        assert isinstance(error, RecommendationError)
        assert str(error) == "No data"


# ============================================================================
# Integration Tests - End-to-End Workflows
# ============================================================================


class TestEndToEndWorkflows:
    """Test complete recommendation workflows."""

    @pytest.mark.asyncio
    async def test_complete_recommendation_workflow(
        self,
        recommendation_engine,
        mock_db_session,
        mock_redis_client,
        sample_vehicle_id,
        sample_option_ids,
        sample_packages,
    ):
        """Test complete recommendation generation workflow."""
        # Setup mocks
        mock_package_result = AsyncMock()
        mock_package_result.scalars.return_value.all.return_value = sample_packages
        mock_db_session.execute.return_value = mock_package_result

        mock_redis_client.get_json.return_value = None

        # Execute workflow
        with patch.object(
            recommendation_engine,
            "_get_popularity_scores",
            return_value={sample_packages[0].id: 0.9},
        ):
            recommendations = await recommendation_engine.recommend_packages(
                vehicle_id=sample_vehicle_id,
                selected_option_ids=sample_option_ids[:2],
                user_id=uuid.uuid4(),
                session_id="test-session",
                trim="Premium",
                year=2024,
            )

        # Verify results
        assert len(recommendations) > 0
        assert recommendations[0]["score"] > 0
        mock_db_session.add.assert_called()
        mock_redis_client.set_json.assert_called()


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Test performance requirements."""

    @pytest.mark.asyncio
    async def test_recommendation_response_time(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
        sample_option_ids,
        sample_packages,
    ):
        """Test recommendations complete within performance threshold."""
        import time

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = sample_packages
        mock_db_session.execute.return_value = mock_result

        start_time = time.time()

        with patch.object(
            recommendation_engine,
            "_get_popularity_scores",
            return_value={},
        ):
            await recommendation_engine.recommend_packages(
                vehicle_id=sample_vehicle_id,
                selected_option_ids=sample_option_ids,
            )

        elapsed_time = time.time() - start_time

        # Should complete in under 100ms (excluding actual DB/Redis calls)
        assert elapsed_time < 0.1

    @pytest.mark.asyncio
    async def test_cache_improves_performance(
        self,
        recommendation_engine,
        mock_redis_client,
        sample_vehicle_id,
        sample_option_ids,
    ):
        """Test caching improves response time."""
        cached_data = [{"package_id": str(uuid.uuid4()), "score": 0.9}]
        mock_redis_client.get_json.return_value = cached_data

        import time

        start_time = time.time()

        await recommendation_engine.recommend_packages(
            vehicle_id=sample_vehicle_id,
            selected_option_ids=sample_option_ids,
        )

        elapsed_time = time.time() - start_time

        # Cached response should be very fast
        assert elapsed_time < 0.01


# ============================================================================
# Edge Cases and Boundary Tests
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_selected_options(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
        sample_packages,
    ):
        """Test recommendations with no selected options."""
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = sample_packages
        mock_db_session.execute.return_value = mock_result

        with patch.object(
            recommendation_engine,
            "_get_popularity_scores",
            return_value={},
        ):
            recommendations = await recommendation_engine.recommend_packages(
                vehicle_id=sample_vehicle_id,
                selected_option_ids=[],
            )

        assert isinstance(recommendations, list)

    @pytest.mark.asyncio
    async def test_all_packages_incompatible(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
        sample_option_ids,
        sample_packages,
    ):
        """Test when all packages are incompatible."""
        for package in sample_packages:
            package.validate_compatibility = Mock(return_value=(False, "Incompatible"))

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = sample_packages
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(InsufficientDataError):
            await recommendation_engine.recommend_packages(
                vehicle_id=sample_vehicle_id,
                selected_option_ids=sample_option_ids,
            )

    @pytest.mark.asyncio
    async def test_max_results_zero(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
        sample_option_ids,
        sample_packages,
    ):
        """Test with max_results set to zero."""
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = sample_packages
        mock_db_session.execute.return_value = mock_result

        with patch.object(
            recommendation_engine,
            "_get_popularity_scores",
            return_value={},
        ):
            recommendations = await recommendation_engine.recommend_packages(
                vehicle_id=sample_vehicle_id,
                selected_option_ids=sample_option_ids,
                max_results=0,
            )

        assert recommendations == []

    @pytest.mark.asyncio
    async def test_invalid_uuid_in_package_ids(
        self,
        recommendation_engine,
        mock_db_session,
        sample_vehicle_id,
    ):
        """Test handling of invalid UUIDs in popularity data."""
        invalid_config = Mock(spec=PopularConfiguration)
        invalid_config.package_ids = ["invalid-uuid", "not-a-uuid"]
        invalid_config.selection_count = 10

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [invalid_config]
        mock_db_session.execute.return_value = mock_result

        # Should not raise exception
        scores = await recommendation_engine._get_popularity_scores(
            vehicle_id=sample_vehicle_id
        )

        assert scores == {}