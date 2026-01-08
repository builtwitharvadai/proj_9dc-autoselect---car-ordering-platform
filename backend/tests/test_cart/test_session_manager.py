"""
Comprehensive test suite for cart session management.

Tests cover session creation, expiration handling, cart migration, Redis integration,
and both anonymous and authenticated user scenarios with proper error handling.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from src.cache.redis_client import RedisClient
from src.database.models.cart import Cart
from src.services.cart.session_manager import (
    CartSessionError,
    CartSessionManager,
    SessionCreationError,
    SessionMigrationError,
    get_cart_session_manager,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock = AsyncMock(spec=RedisClient)
    mock.set = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.delete = AsyncMock(return_value=1)
    return mock


@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    mock = AsyncMock(spec=AsyncSession)
    mock.add = MagicMock()
    mock.flush = AsyncMock()
    mock.delete = AsyncMock()
    mock.execute = AsyncMock()
    return mock


@pytest.fixture
def session_manager(mock_redis_client):
    """Create session manager with mocked Redis client."""
    return CartSessionManager(redis_client=mock_redis_client)


@pytest.fixture
def sample_cart_id():
    """Generate sample cart UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_user_id():
    """Generate sample user UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_session_id():
    """Generate sample session ID."""
    return "test_session_id_12345678901234567890"


@pytest.fixture
def anonymous_cart(sample_cart_id, sample_session_id):
    """Create sample anonymous cart."""
    cart = Cart(
        id=sample_cart_id,
        session_id=sample_session_id,
        user_id=None,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    cart.items = []
    return cart


@pytest.fixture
def authenticated_cart(sample_cart_id, sample_user_id):
    """Create sample authenticated cart."""
    cart = Cart(
        id=sample_cart_id,
        session_id=None,
        user_id=sample_user_id,
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    cart.items = []
    return cart


# ============================================================================
# Unit Tests - Session ID Generation
# ============================================================================


class TestSessionIdGeneration:
    """Test session ID generation functionality."""

    def test_generate_session_id_returns_string(self, session_manager):
        """Test that session ID generation returns a string."""
        session_id = session_manager.generate_session_id()

        assert isinstance(session_id, str)
        assert len(session_id) > 0

    def test_generate_session_id_correct_length(self, session_manager):
        """Test that generated session ID has expected length."""
        session_id = session_manager.generate_session_id()

        # URL-safe base64 encoding produces variable length
        # but should be around 43 characters for 32 bytes
        assert len(session_id) >= 32

    def test_generate_session_id_uniqueness(self, session_manager):
        """Test that generated session IDs are unique."""
        session_ids = {session_manager.generate_session_id() for _ in range(100)}

        assert len(session_ids) == 100

    def test_generate_session_id_url_safe(self, session_manager):
        """Test that generated session ID is URL-safe."""
        session_id = session_manager.generate_session_id()

        # URL-safe characters: alphanumeric, -, _
        assert all(c.isalnum() or c in "-_" for c in session_id)


# ============================================================================
# Unit Tests - Expiration Calculation
# ============================================================================


class TestExpirationCalculation:
    """Test cart expiration calculation logic."""

    def test_calculate_expiration_anonymous_default(self, session_manager):
        """Test expiration calculation for anonymous users."""
        now = datetime.utcnow()
        expiration = session_manager.calculate_expiration(
            is_authenticated=False, from_time=now
        )

        expected = now + timedelta(days=7)
        assert abs((expiration - expected).total_seconds()) < 1

    def test_calculate_expiration_authenticated_default(self, session_manager):
        """Test expiration calculation for authenticated users."""
        now = datetime.utcnow()
        expiration = session_manager.calculate_expiration(
            is_authenticated=True, from_time=now
        )

        expected = now + timedelta(days=30)
        assert abs((expiration - expected).total_seconds()) < 1

    def test_calculate_expiration_uses_current_time_when_none(self, session_manager):
        """Test that current time is used when from_time is None."""
        before = datetime.utcnow()
        expiration = session_manager.calculate_expiration(is_authenticated=False)
        after = datetime.utcnow()

        expected_min = before + timedelta(days=7)
        expected_max = after + timedelta(days=7)

        assert expected_min <= expiration <= expected_max

    @pytest.mark.parametrize(
        "is_authenticated,expected_days",
        [
            (False, 7),
            (True, 30),
        ],
    )
    def test_calculate_expiration_correct_days(
        self, session_manager, is_authenticated, expected_days
    ):
        """Test expiration calculation returns correct number of days."""
        now = datetime.utcnow()
        expiration = session_manager.calculate_expiration(
            is_authenticated=is_authenticated, from_time=now
        )

        days_diff = (expiration - now).days
        assert days_diff == expected_days


# ============================================================================
# Unit Tests - Anonymous Cart Creation
# ============================================================================


class TestAnonymousCartCreation:
    """Test anonymous cart creation functionality."""

    @pytest.mark.asyncio
    async def test_create_anonymous_cart_success(
        self, session_manager, mock_db_session, mock_redis_client
    ):
        """Test successful anonymous cart creation."""
        cart = await session_manager.create_anonymous_cart(mock_db_session)

        assert cart is not None
        assert cart.session_id is not None
        assert cart.user_id is None
        assert cart.expires_at > datetime.utcnow()

        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()
        mock_redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_anonymous_cart_with_custom_session_id(
        self, session_manager, mock_db_session, sample_session_id
    ):
        """Test anonymous cart creation with provided session ID."""
        cart = await session_manager.create_anonymous_cart(
            mock_db_session, session_id=sample_session_id
        )

        assert cart.session_id == sample_session_id

    @pytest.mark.asyncio
    async def test_create_anonymous_cart_generates_session_id_when_none(
        self, session_manager, mock_db_session
    ):
        """Test that session ID is generated when not provided."""
        cart = await session_manager.create_anonymous_cart(mock_db_session)

        assert cart.session_id is not None
        assert len(cart.session_id) >= 32

    @pytest.mark.asyncio
    async def test_create_anonymous_cart_sets_correct_expiration(
        self, session_manager, mock_db_session
    ):
        """Test that anonymous cart has 7-day expiration."""
        before = datetime.utcnow() + timedelta(days=7)
        cart = await session_manager.create_anonymous_cart(mock_db_session)
        after = datetime.utcnow() + timedelta(days=7)

        assert before <= cart.expires_at <= after

    @pytest.mark.asyncio
    async def test_create_anonymous_cart_stores_in_redis(
        self, session_manager, mock_db_session, mock_redis_client
    ):
        """Test that cart session is stored in Redis."""
        cart = await session_manager.create_anonymous_cart(mock_db_session)

        mock_redis_client.set.assert_called_once()
        call_args = mock_redis_client.set.call_args

        assert f"cart:session:{cart.session_id}" in call_args[0][0]
        assert str(cart.id) == call_args[0][1]
        assert call_args[1]["ex"] > 0

    @pytest.mark.asyncio
    async def test_create_anonymous_cart_database_error(
        self, session_manager, mock_db_session
    ):
        """Test error handling when database operation fails."""
        mock_db_session.flush.side_effect = Exception("Database error")

        with pytest.raises(SessionCreationError) as exc_info:
            await session_manager.create_anonymous_cart(mock_db_session)

        assert "Failed to create anonymous cart" in str(exc_info.value)
        assert exc_info.value.context["error"] == "Database error"

    @pytest.mark.asyncio
    async def test_create_anonymous_cart_redis_error(
        self, session_manager, mock_db_session, mock_redis_client
    ):
        """Test error handling when Redis operation fails."""
        mock_redis_client.set.side_effect = RedisError("Redis connection failed")

        with pytest.raises(SessionCreationError) as exc_info:
            await session_manager.create_anonymous_cart(mock_db_session)

        assert "Failed to create anonymous cart" in str(exc_info.value)


# ============================================================================
# Unit Tests - Authenticated Cart Creation
# ============================================================================


class TestAuthenticatedCartCreation:
    """Test authenticated cart creation functionality."""

    @pytest.mark.asyncio
    async def test_create_authenticated_cart_success(
        self, session_manager, mock_db_session, sample_user_id
    ):
        """Test successful authenticated cart creation."""
        cart = await session_manager.create_authenticated_cart(
            mock_db_session, sample_user_id
        )

        assert cart is not None
        assert cart.user_id == sample_user_id
        assert cart.session_id is None
        assert cart.expires_at > datetime.utcnow()

        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_authenticated_cart_sets_correct_expiration(
        self, session_manager, mock_db_session, sample_user_id
    ):
        """Test that authenticated cart has 30-day expiration."""
        before = datetime.utcnow() + timedelta(days=30)
        cart = await session_manager.create_authenticated_cart(
            mock_db_session, sample_user_id
        )
        after = datetime.utcnow() + timedelta(days=30)

        assert before <= cart.expires_at <= after

    @pytest.mark.asyncio
    async def test_create_authenticated_cart_no_session_id(
        self, session_manager, mock_db_session, sample_user_id
    ):
        """Test that authenticated cart has no session ID."""
        cart = await session_manager.create_authenticated_cart(
            mock_db_session, sample_user_id
        )

        assert cart.session_id is None

    @pytest.mark.asyncio
    async def test_create_authenticated_cart_database_error(
        self, session_manager, mock_db_session, sample_user_id
    ):
        """Test error handling when database operation fails."""
        mock_db_session.flush.side_effect = Exception("Database error")

        with pytest.raises(SessionCreationError) as exc_info:
            await session_manager.create_authenticated_cart(
                mock_db_session, sample_user_id
            )

        assert "Failed to create authenticated cart" in str(exc_info.value)
        assert str(sample_user_id) in exc_info.value.context["user_id"]


# ============================================================================
# Integration Tests - Cart Retrieval
# ============================================================================


class TestCartRetrieval:
    """Test cart retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_cart_by_session_found_in_redis(
        self,
        session_manager,
        mock_db_session,
        mock_redis_client,
        anonymous_cart,
        sample_session_id,
    ):
        """Test retrieving cart by session ID when found in Redis."""
        mock_redis_client.get.return_value = str(anonymous_cart.id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = anonymous_cart
        mock_db_session.execute.return_value = mock_result

        cart = await session_manager.get_cart_by_session(
            mock_db_session, sample_session_id
        )

        assert cart == anonymous_cart
        mock_redis_client.get.assert_called_once()
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cart_by_session_not_in_redis(
        self,
        session_manager,
        mock_db_session,
        mock_redis_client,
        anonymous_cart,
        sample_session_id,
    ):
        """Test retrieving cart by session ID when not in Redis."""
        mock_redis_client.get.return_value = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = anonymous_cart
        mock_db_session.execute.return_value = mock_result

        cart = await session_manager.get_cart_by_session(
            mock_db_session, sample_session_id
        )

        assert cart == anonymous_cart
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cart_by_session_not_found(
        self, session_manager, mock_db_session, mock_redis_client, sample_session_id
    ):
        """Test retrieving non-existent cart by session ID."""
        mock_redis_client.get.return_value = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        cart = await session_manager.get_cart_by_session(
            mock_db_session, sample_session_id
        )

        assert cart is None

    @pytest.mark.asyncio
    async def test_get_cart_by_session_database_error(
        self, session_manager, mock_db_session, sample_session_id
    ):
        """Test error handling when database query fails."""
        mock_db_session.execute.side_effect = Exception("Database error")

        cart = await session_manager.get_cart_by_session(
            mock_db_session, sample_session_id
        )

        assert cart is None

    @pytest.mark.asyncio
    async def test_get_cart_by_user_found(
        self, session_manager, mock_db_session, authenticated_cart, sample_user_id
    ):
        """Test retrieving cart by user ID."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = authenticated_cart
        mock_db_session.execute.return_value = mock_result

        cart = await session_manager.get_cart_by_user(mock_db_session, sample_user_id)

        assert cart == authenticated_cart
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cart_by_user_not_found(
        self, session_manager, mock_db_session, sample_user_id
    ):
        """Test retrieving non-existent cart by user ID."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        cart = await session_manager.get_cart_by_user(mock_db_session, sample_user_id)

        assert cart is None

    @pytest.mark.asyncio
    async def test_get_cart_by_user_database_error(
        self, session_manager, mock_db_session, sample_user_id
    ):
        """Test error handling when database query fails."""
        mock_db_session.execute.side_effect = Exception("Database error")

        cart = await session_manager.get_cart_by_user(mock_db_session, sample_user_id)

        assert cart is None


# ============================================================================
# Integration Tests - Cart Migration
# ============================================================================


class TestCartMigration:
    """Test cart migration on user login."""

    @pytest.mark.asyncio
    async def test_migrate_cart_no_anonymous_cart(
        self,
        session_manager,
        mock_db_session,
        mock_redis_client,
        sample_session_id,
        sample_user_id,
    ):
        """Test migration when no anonymous cart exists."""
        mock_redis_client.get.return_value = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        cart = await session_manager.migrate_cart_on_login(
            mock_db_session, sample_session_id, sample_user_id
        )

        assert cart is None

    @pytest.mark.asyncio
    async def test_migrate_cart_to_existing_user_cart(
        self,
        session_manager,
        mock_db_session,
        mock_redis_client,
        anonymous_cart,
        authenticated_cart,
        sample_session_id,
        sample_user_id,
    ):
        """Test migrating anonymous cart to existing user cart."""
        # Create mock cart items
        mock_item1 = MagicMock()
        mock_item1.cart_id = anonymous_cart.id
        mock_item2 = MagicMock()
        mock_item2.cart_id = anonymous_cart.id
        anonymous_cart.items = [mock_item1, mock_item2]

        # Mock Redis
        mock_redis_client.get.return_value = str(anonymous_cart.id)

        # Mock database queries
        call_count = 0

        def mock_execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.scalar_one_or_none.return_value = anonymous_cart
            else:
                mock_result.scalar_one_or_none.return_value = authenticated_cart
            return mock_result

        mock_db_session.execute.side_effect = mock_execute_side_effect

        cart = await session_manager.migrate_cart_on_login(
            mock_db_session, sample_session_id, sample_user_id
        )

        assert cart == authenticated_cart
        assert mock_item1.cart_id == authenticated_cart.id
        assert mock_item2.cart_id == authenticated_cart.id
        mock_db_session.delete.assert_called_once_with(anonymous_cart)
        mock_redis_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_migrate_cart_convert_to_user_cart(
        self,
        session_manager,
        mock_db_session,
        mock_redis_client,
        anonymous_cart,
        sample_session_id,
        sample_user_id,
    ):
        """Test converting anonymous cart to user cart when no user cart exists."""
        mock_redis_client.get.return_value = str(anonymous_cart.id)

        call_count = 0

        def mock_execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.scalar_one_or_none.return_value = anonymous_cart
            else:
                mock_result.scalar_one_or_none.return_value = None
            return mock_result

        mock_db_session.execute.side_effect = mock_execute_side_effect

        cart = await session_manager.migrate_cart_on_login(
            mock_db_session, sample_session_id, sample_user_id
        )

        assert cart == anonymous_cart
        assert cart.user_id == sample_user_id
        assert cart.session_id is None
        mock_redis_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_migrate_cart_database_error(
        self,
        session_manager,
        mock_db_session,
        sample_session_id,
        sample_user_id,
    ):
        """Test error handling during cart migration."""
        mock_db_session.execute.side_effect = Exception("Database error")

        with pytest.raises(SessionMigrationError) as exc_info:
            await session_manager.migrate_cart_on_login(
                mock_db_session, sample_session_id, sample_user_id
            )

        assert "Failed to migrate cart on login" in str(exc_info.value)
        assert exc_info.value.context["session_id"] == sample_session_id


# ============================================================================
# Unit Tests - Cart Expiration Extension
# ============================================================================


class TestCartExpirationExtension:
    """Test cart expiration extension functionality."""

    @pytest.mark.asyncio
    async def test_extend_cart_expiration_anonymous_default(
        self, session_manager, mock_db_session, anonymous_cart
    ):
        """Test extending anonymous cart expiration with default days."""
        original_expiration = anonymous_cart.expires_at

        await session_manager.extend_cart_expiration(mock_db_session, anonymous_cart)

        assert anonymous_cart.expires_at > original_expiration
        days_diff = (anonymous_cart.expires_at - datetime.utcnow()).days
        assert days_diff == 7

    @pytest.mark.asyncio
    async def test_extend_cart_expiration_authenticated_default(
        self, session_manager, mock_db_session, authenticated_cart
    ):
        """Test extending authenticated cart expiration with default days."""
        original_expiration = authenticated_cart.expires_at

        await session_manager.extend_cart_expiration(
            mock_db_session, authenticated_cart
        )

        assert authenticated_cart.expires_at > original_expiration
        days_diff = (authenticated_cart.expires_at - datetime.utcnow()).days
        assert days_diff == 30

    @pytest.mark.asyncio
    async def test_extend_cart_expiration_custom_days(
        self, session_manager, mock_db_session, anonymous_cart
    ):
        """Test extending cart expiration with custom days."""
        await session_manager.extend_cart_expiration(
            mock_db_session, anonymous_cart, days=14
        )

        days_diff = (anonymous_cart.expires_at - datetime.utcnow()).days
        assert days_diff == 14

    @pytest.mark.asyncio
    async def test_extend_cart_expiration_updates_redis(
        self, session_manager, mock_db_session, mock_redis_client, anonymous_cart
    ):
        """Test that Redis is updated when extending anonymous cart."""
        await session_manager.extend_cart_expiration(mock_db_session, anonymous_cart)

        mock_redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_extend_cart_expiration_no_redis_for_authenticated(
        self, session_manager, mock_db_session, mock_redis_client, authenticated_cart
    ):
        """Test that Redis is not updated for authenticated cart."""
        await session_manager.extend_cart_expiration(
            mock_db_session, authenticated_cart
        )

        mock_redis_client.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_extend_cart_expiration_redis_error(
        self, session_manager, mock_db_session, mock_redis_client, anonymous_cart
    ):
        """Test error handling when Redis update fails."""
        mock_redis_client.set.side_effect = RedisError("Redis error")

        with pytest.raises(CartSessionError) as exc_info:
            await session_manager.extend_cart_expiration(
                mock_db_session, anonymous_cart
            )

        assert "Failed to extend cart expiration" in str(exc_info.value)


# ============================================================================
# Unit Tests - Redis Operations
# ============================================================================


class TestRedisOperations:
    """Test Redis storage operations."""

    @pytest.mark.asyncio
    async def test_store_session_in_redis_success(
        self, session_manager, mock_redis_client, sample_session_id, sample_cart_id
    ):
        """Test successful session storage in Redis."""
        expires_at = datetime.utcnow() + timedelta(days=7)

        await session_manager._store_session_in_redis(
            sample_session_id, str(sample_cart_id), expires_at
        )

        mock_redis_client.set.assert_called_once()
        call_args = mock_redis_client.set.call_args

        assert f"cart:session:{sample_session_id}" in call_args[0][0]
        assert str(sample_cart_id) == call_args[0][1]
        assert call_args[1]["ex"] > 0

    @pytest.mark.asyncio
    async def test_store_session_in_redis_calculates_ttl(
        self, session_manager, mock_redis_client, sample_session_id, sample_cart_id
    ):
        """Test that TTL is correctly calculated."""
        expires_at = datetime.utcnow() + timedelta(hours=2)

        await session_manager._store_session_in_redis(
            sample_session_id, str(sample_cart_id), expires_at
        )

        call_args = mock_redis_client.set.call_args
        ttl = call_args[1]["ex"]

        assert 7000 < ttl < 7300  # ~2 hours in seconds

    @pytest.mark.asyncio
    async def test_store_session_in_redis_skips_expired(
        self, session_manager, mock_redis_client, sample_session_id, sample_cart_id
    ):
        """Test that expired sessions are not stored."""
        expires_at = datetime.utcnow() - timedelta(hours=1)

        await session_manager._store_session_in_redis(
            sample_session_id, str(sample_cart_id), expires_at
        )

        mock_redis_client.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_session_in_redis_error(
        self, session_manager, mock_redis_client, sample_session_id, sample_cart_id
    ):
        """Test error handling when Redis storage fails."""
        mock_redis_client.set.side_effect = RedisError("Connection failed")
        expires_at = datetime.utcnow() + timedelta(days=7)

        with pytest.raises(SessionCreationError) as exc_info:
            await session_manager._store_session_in_redis(
                sample_session_id, str(sample_cart_id), expires_at
            )

        assert "Failed to store session in Redis" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_session_from_redis_found(
        self, session_manager, mock_redis_client, sample_session_id, sample_cart_id
    ):
        """Test retrieving session from Redis."""
        mock_redis_client.get.return_value = str(sample_cart_id)

        cart_id = await session_manager._get_session_from_redis(sample_session_id)

        assert cart_id == str(sample_cart_id)
        mock_redis_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_from_redis_not_found(
        self, session_manager, mock_redis_client, sample_session_id
    ):
        """Test retrieving non-existent session from Redis."""
        mock_redis_client.get.return_value = None

        cart_id = await session_manager._get_session_from_redis(sample_session_id)

        assert cart_id is None

    @pytest.mark.asyncio
    async def test_get_session_from_redis_error(
        self, session_manager, mock_redis_client, sample_session_id
    ):
        """Test error handling when Redis retrieval fails."""
        mock_redis_client.get.side_effect = RedisError("Connection failed")

        cart_id = await session_manager._get_session_from_redis(sample_session_id)

        assert cart_id is None

    @pytest.mark.asyncio
    async def test_remove_session_from_redis_success(
        self, session_manager, mock_redis_client, sample_session_id
    ):
        """Test removing session from Redis."""
        await session_manager._remove_session_from_redis(sample_session_id)

        mock_redis_client.delete.assert_called_once()
        call_args = mock_redis_client.delete.call_args
        assert f"cart:session:{sample_session_id}" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_remove_session_from_redis_error(
        self, session_manager, mock_redis_client, sample_session_id
    ):
        """Test error handling when Redis deletion fails."""
        mock_redis_client.delete.side_effect = RedisError("Connection failed")

        # Should not raise exception
        await session_manager._remove_session_from_redis(sample_session_id)


# ============================================================================
# Unit Tests - Redis Client Initialization
# ============================================================================


class TestRedisClientInitialization:
    """Test Redis client initialization and error handling."""

    @pytest.mark.asyncio
    async def test_get_redis_client_uses_provided_client(self):
        """Test that provided Redis client is used."""
        mock_redis = AsyncMock(spec=RedisClient)
        manager = CartSessionManager(redis_client=mock_redis)

        client = await manager._get_redis_client()

        assert client == mock_redis

    @pytest.mark.asyncio
    async def test_get_redis_client_initializes_when_none(self):
        """Test Redis client initialization when not provided."""
        manager = CartSessionManager(redis_client=None)

        with patch(
            "src.services.cart.session_manager.get_redis_client"
        ) as mock_get_redis:
            mock_redis = AsyncMock(spec=RedisClient)
            mock_get_redis.return_value = mock_redis

            client = await manager._get_redis_client()

            assert client == mock_redis
            mock_get_redis.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_redis_client_caches_instance(self):
        """Test that Redis client is cached after first initialization."""
        manager = CartSessionManager(redis_client=None)

        with patch(
            "src.services.cart.session_manager.get_redis_client"
        ) as mock_get_redis:
            mock_redis = AsyncMock(spec=RedisClient)
            mock_get_redis.return_value = mock_redis

            client1 = await manager._get_redis_client()
            client2 = await manager._get_redis_client()

            assert client1 == client2
            mock_get_redis.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_redis_client_initialization_error(self):
        """Test error handling when Redis client initialization fails."""
        manager = CartSessionManager(redis_client=None)

        with patch(
            "src.services.cart.session_manager.get_redis_client"
        ) as mock_get_redis:
            mock_get_redis.side_effect = Exception("Redis unavailable")

            with pytest.raises(SessionCreationError) as exc_info:
                await manager._get_redis_client()

            assert "Failed to initialize Redis client" in str(exc_info.value)


# ============================================================================
# Integration Tests - Global Session Manager
# ============================================================================


class TestGlobalSessionManager:
    """Test global session manager singleton."""

    @pytest.mark.asyncio
    async def test_get_cart_session_manager_returns_instance(self):
        """Test that global manager returns instance."""
        manager = await get_cart_session_manager()

        assert isinstance(manager, CartSessionManager)

    @pytest.mark.asyncio
    async def test_get_cart_session_manager_singleton(self):
        """Test that global manager returns same instance."""
        manager1 = await get_cart_session_manager()
        manager2 = await get_cart_session_manager()

        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_get_cart_session_manager_creates_once(self):
        """Test that global manager is created only once."""
        # Reset global state
        import src.services.cart.session_manager as module

        module._session_manager = None

        manager1 = await get_cart_session_manager()
        manager2 = await get_cart_session_manager()

        assert manager1 is manager2


# ============================================================================
# Edge Cases and Error Scenarios
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_create_cart_with_zero_ttl(
        self, session_manager, mock_db_session, mock_redis_client
    ):
        """Test cart creation when expiration is immediate."""
        with patch.object(
            session_manager,
            "calculate_expiration",
            return_value=datetime.utcnow() - timedelta(seconds=1),
        ):
            cart = await session_manager.create_anonymous_cart(mock_db_session)

            # Should still create cart but not store in Redis
            assert cart is not None
            mock_redis_client.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_migrate_cart_with_empty_items(
        self,
        session_manager,
        mock_db_session,
        mock_redis_client,
        anonymous_cart,
        sample_session_id,
        sample_user_id,
    ):
        """Test migrating cart with no items."""
        anonymous_cart.items = []
        mock_redis_client.get.return_value = str(anonymous_cart.id)

        call_count = 0

        def mock_execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.scalar_one_or_none.return_value = anonymous_cart
            else:
                mock_result.scalar_one_or_none.return_value = None
            return mock_result

        mock_db_session.execute.side_effect = mock_execute_side_effect

        cart = await session_manager.migrate_cart_on_login(
            mock_db_session, sample_session_id, sample_user_id
        )

        assert cart == anonymous_cart
        assert len(cart.items) == 0

    def test_session_id_generation_performance(self, session_manager):
        """Test session ID generation performance."""
        import time

        start = time.time()
        for _ in range(1000):
            session_manager.generate_session_id()
        elapsed = time.time() - start

        # Should generate 1000 IDs in less than 1 second
        assert elapsed < 1.0

    @pytest.mark.parametrize(
        "days,is_authenticated",
        [
            (0, False),
            (1, False),
            (7, False),
            (30, True),
            (365, True),
        ],
    )
    def test_expiration_calculation_various_days(
        self, session_manager, days, is_authenticated
    ):
        """Test expiration calculation with various day values."""
        now = datetime.utcnow()

        with patch.object(
            session_manager,
            "ANONYMOUS_EXPIRATION_DAYS" if not is_authenticated else "AUTHENTICATED_EXPIRATION_DAYS",
            days,
        ):
            expiration = session_manager.calculate_expiration(
                is_authenticated=is_authenticated, from_time=now
            )

            expected = now + timedelta(days=days)
            assert abs((expiration - expected).total_seconds()) < 1


# ============================================================================
# Exception Hierarchy Tests
# ============================================================================


class TestExceptionHierarchy:
    """Test custom exception classes."""

    def test_cart_session_error_base_exception(self):
        """Test CartSessionError is base exception."""
        error = CartSessionError("Test error", key="value")

        assert isinstance(error, Exception)
        assert str(error) == "Test error"
        assert error.context == {"key": "value"}

    def test_session_creation_error_inherits_base(self):
        """Test SessionCreationError inherits from CartSessionError."""
        error = SessionCreationError("Creation failed", session_id="123")

        assert isinstance(error, CartSessionError)
        assert isinstance(error, Exception)
        assert error.context == {"session_id": "123"}

    def test_session_migration_error_inherits_base(self):
        """Test SessionMigrationError inherits from CartSessionError."""
        error = SessionMigrationError("Migration failed", user_id="456")

        assert isinstance(error, CartSessionError)
        assert isinstance(error, Exception)
        assert error.context == {"user_id": "456"}

    def test_exception_context_preservation(self):
        """Test that exception context is preserved."""
        context = {
            "session_id": "test_session",
            "user_id": "test_user",
            "error": "Database connection failed",
        }

        error = SessionCreationError("Failed to create cart", **context)

        assert error.context == context
        for key, value in context.items():
            assert error.context[key] == value


# ============================================================================
# Performance and Load Tests
# ============================================================================


class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.asyncio
    async def test_concurrent_cart_creation(self, mock_db_session, mock_redis_client):
        """Test concurrent cart creation performance."""
        import asyncio

        manager = CartSessionManager(redis_client=mock_redis_client)

        async def create_cart():
            return await manager.create_anonymous_cart(mock_db_session)

        # Create 100 carts concurrently
        tasks = [create_cart() for _ in range(100)]
        carts = await asyncio.gather(*tasks)

        assert len(carts) == 100
        assert all(cart is not None for cart in carts)

    @pytest.mark.asyncio
    async def test_session_id_uniqueness_under_load(self):
        """Test session ID uniqueness under concurrent generation."""
        import asyncio

        manager = CartSessionManager()

        def generate_ids():
            return [manager.generate_session_id() for _ in range(100)]

        # Generate IDs concurrently
        loop = asyncio.get_event_loop()
        tasks = [loop.run_in_executor(None, generate_ids) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        all_ids = [id for batch in results for id in batch]
        assert len(all_ids) == 1000
        assert len(set(all_ids)) == 1000  # All unique


# ============================================================================
# Constants and Configuration Tests
# ============================================================================


class TestConstants:
    """Test class constants and configuration."""

    def test_anonymous_expiration_days_constant(self):
        """Test anonymous expiration days constant."""
        assert CartSessionManager.ANONYMOUS_EXPIRATION_DAYS == 7

    def test_authenticated_expiration_days_constant(self):
        """Test authenticated expiration days constant."""
        assert CartSessionManager.AUTHENTICATED_EXPIRATION_DAYS == 30

    def test_session_id_length_constant(self):
        """Test session ID length constant."""
        assert CartSessionManager.SESSION_ID_LENGTH == 32

    def test_redis_session_prefix_constant(self):
        """Test Redis session prefix constant."""
        assert CartSessionManager.REDIS_SESSION_PREFIX == "cart:session"

    def test_redis_key_format(self, session_manager, sample_session_id):
        """Test Redis key format construction."""
        expected_key = f"cart:session:{sample_session_id}"

        key = f"{session_manager.REDIS_SESSION_PREFIX}:{sample_session_id}"

        assert key == expected_key