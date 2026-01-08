"""
Comprehensive test suite for notification service.

Tests notification delivery orchestration, template rendering, preference
handling, retry logic, and integration with AWS services (SES/SNS).
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload, sessionmaker

from src.database.models.notification import (
    NotificationChannel,
    NotificationLog,
    NotificationPreference,
    NotificationStatus,
    NotificationType,
)
from src.database.models.user import User
from src.services.notifications.aws_clients import (
    SESClient,
    SESClientError,
    SNSClient,
    SNSClientError,
)
from src.services.notifications.service import (
    NotificationDeliveryError,
    NotificationService,
    NotificationServiceError,
    NotificationValidationError,
    get_notification_service,
)
from src.services.notifications.templates import (
    TemplateEngine,
    TemplateEngineError,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_ses_client() -> Mock:
    """
    Create mock SES client for email testing.

    Returns:
        Mock SES client with send_email method
    """
    client = Mock(spec=SESClient)
    client.send_email.return_value = {
        "message_id": "test-message-id-123",
        "request_id": "test-request-id-456",
    }
    return client


@pytest.fixture
def mock_sns_client() -> Mock:
    """
    Create mock SNS client for SMS testing.

    Returns:
        Mock SNS client with send_sms method
    """
    client = Mock(spec=SNSClient)
    client.send_sms.return_value = {
        "message_id": "test-sms-id-789",
        "request_id": "test-request-id-012",
    }
    return client


@pytest.fixture
def mock_template_engine() -> Mock:
    """
    Create mock template engine for rendering.

    Returns:
        Mock template engine with render methods
    """
    engine = Mock(spec=TemplateEngine)
    engine.render_email.return_value = {
        "subject": "Test Email Subject",
        "html_body": "<html><body>Test HTML</body></html>",
        "text_body": "Test plain text",
    }
    engine.render_sms.return_value = "Test SMS message"
    return engine


@pytest.fixture
async def mock_db_session() -> AsyncMock:
    """
    Create mock database session for testing.

    Returns:
        Mock async database session
    """
    session = AsyncMock(spec=AsyncSession)
    session.add = Mock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def sample_user() -> User:
    """
    Create sample user for testing.

    Returns:
        User instance with test data
    """
    user = User(
        id=uuid4(),
        email="test@example.com",
        phone="+1234567890",
        name="Test User",
        notification_preferences=[],
    )
    return user


@pytest.fixture
def sample_user_with_preferences() -> User:
    """
    Create sample user with notification preferences.

    Returns:
        User instance with preferences configured
    """
    user_id = uuid4()
    user = User(
        id=user_id,
        email="test@example.com",
        phone="+1234567890",
        name="Test User",
    )

    # Add preferences for different notification types
    preferences = [
        NotificationPreference(
            user_id=user_id,
            notification_type=NotificationType.ORDER_CREATED,
            email_enabled=True,
            sms_enabled=False,
        ),
        NotificationPreference(
            user_id=user_id,
            notification_type=NotificationType.ORDER_CONFIRMED,
            email_enabled=True,
            sms_enabled=True,
        ),
        NotificationPreference(
            user_id=user_id,
            notification_type=NotificationType.PAYMENT_FAILED,
            email_enabled=False,
            sms_enabled=True,
        ),
    ]

    user.notification_preferences = preferences
    return user


@pytest.fixture
def notification_service(
    mock_db_session: AsyncMock,
    mock_ses_client: Mock,
    mock_sns_client: Mock,
    mock_template_engine: Mock,
) -> NotificationService:
    """
    Create notification service with mocked dependencies.

    Args:
        mock_db_session: Mock database session
        mock_ses_client: Mock SES client
        mock_sns_client: Mock SNS client
        mock_template_engine: Mock template engine

    Returns:
        NotificationService instance for testing
    """
    return NotificationService(
        db_session=mock_db_session,
        ses_client=mock_ses_client,
        sns_client=mock_sns_client,
        template_engine=mock_template_engine,
        max_retries=3,
        retry_backoff=1.0,
    )


# ============================================================================
# Unit Tests - Initialization
# ============================================================================


class TestNotificationServiceInitialization:
    """Test notification service initialization and configuration."""

    def test_initialization_with_all_dependencies(
        self,
        mock_db_session: AsyncMock,
        mock_ses_client: Mock,
        mock_sns_client: Mock,
        mock_template_engine: Mock,
    ) -> None:
        """Test service initializes correctly with all dependencies."""
        service = NotificationService(
            db_session=mock_db_session,
            ses_client=mock_ses_client,
            sns_client=mock_sns_client,
            template_engine=mock_template_engine,
            max_retries=5,
            retry_backoff=2.0,
        )

        assert service.db == mock_db_session
        assert service.ses_client == mock_ses_client
        assert service.sns_client == mock_sns_client
        assert service.template_engine == mock_template_engine
        assert service.max_retries == 5

    def test_initialization_with_default_clients(
        self, mock_db_session: AsyncMock
    ) -> None:
        """Test service creates default clients when not provided."""
        with patch(
            "src.services.notifications.service.get_ses_client"
        ) as mock_get_ses, patch(
            "src.services.notifications.service.get_sns_client"
        ) as mock_get_sns, patch(
            "src.services.notifications.service.get_template_engine"
        ) as mock_get_template:

            mock_get_ses.return_value = Mock(spec=SESClient)
            mock_get_sns.return_value = Mock(spec=SNSClient)
            mock_get_template.return_value = Mock(spec=TemplateEngine)

            service = NotificationService(db_session=mock_db_session)

            mock_get_ses.assert_called_once()
            mock_get_sns.assert_called_once()
            mock_get_template.assert_called_once()
            assert service.ses_client is not None
            assert service.sns_client is not None
            assert service.template_engine is not None

    def test_factory_function_creates_service(
        self, mock_db_session: AsyncMock
    ) -> None:
        """Test factory function creates service instance."""
        service = get_notification_service(mock_db_session)

        assert isinstance(service, NotificationService)
        assert service.db == mock_db_session


# ============================================================================
# Unit Tests - Email Notifications
# ============================================================================


class TestEmailNotifications:
    """Test email notification delivery functionality."""

    @pytest.mark.asyncio
    async def test_send_email_notification_success(
        self,
        notification_service: NotificationService,
        sample_user: User,
        mock_db_session: AsyncMock,
        mock_ses_client: Mock,
        mock_template_engine: Mock,
    ) -> None:
        """Test successful email notification delivery."""
        context = {"order_id": "12345", "order_total": "$100.00"}

        result = await notification_service._send_email_notification(
            user=sample_user,
            notification_type=NotificationType.ORDER_CREATED,
            context=context,
        )

        # Verify template rendering
        mock_template_engine.render_email.assert_called_once_with(
            "order_created", context
        )

        # Verify email sending
        mock_ses_client.send_email.assert_called_once()
        call_args = mock_ses_client.send_email.call_args
        assert call_args[1]["to_addresses"] == [sample_user.email]
        assert call_args[1]["subject"] == "Test Email Subject"

        # Verify database operations
        assert mock_db_session.add.called
        assert mock_db_session.flush.called
        assert mock_db_session.commit.called

        # Verify result
        assert result["status"] == "sent"
        assert result["channel"] == "email"
        assert result["message_id"] == "test-message-id-123"

    @pytest.mark.asyncio
    async def test_send_email_notification_no_email_address(
        self,
        notification_service: NotificationService,
        sample_user: User,
    ) -> None:
        """Test email notification fails when user has no email."""
        sample_user.email = None

        with pytest.raises(NotificationValidationError) as exc_info:
            await notification_service._send_email_notification(
                user=sample_user,
                notification_type=NotificationType.ORDER_CREATED,
                context={},
            )

        assert "no email address" in str(exc_info.value).lower()
        assert exc_info.value.context["user_id"] == str(sample_user.id)

    @pytest.mark.asyncio
    async def test_send_email_notification_template_error(
        self,
        notification_service: NotificationService,
        sample_user: User,
        mock_template_engine: Mock,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test email notification handles template rendering errors."""
        mock_template_engine.render_email.side_effect = TemplateEngineError(
            "Template not found"
        )

        with pytest.raises(NotificationDeliveryError) as exc_info:
            await notification_service._send_email_notification(
                user=sample_user,
                notification_type=NotificationType.ORDER_CREATED,
                context={},
            )

        assert "render email template" in str(exc_info.value).lower()
        assert mock_db_session.commit.called  # Log should be saved

    @pytest.mark.asyncio
    async def test_send_email_notification_ses_error(
        self,
        notification_service: NotificationService,
        sample_user: User,
        mock_ses_client: Mock,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test email notification handles SES delivery errors."""
        mock_ses_client.send_email.side_effect = SESClientError(
            "Rate limit exceeded"
        )

        with pytest.raises(NotificationDeliveryError) as exc_info:
            await notification_service._send_email_notification(
                user=sample_user,
                notification_type=NotificationType.ORDER_CREATED,
                context={},
            )

        assert "send email" in str(exc_info.value).lower()
        assert mock_db_session.commit.called  # Failed log should be saved


# ============================================================================
# Unit Tests - SMS Notifications
# ============================================================================


class TestSMSNotifications:
    """Test SMS notification delivery functionality."""

    @pytest.mark.asyncio
    async def test_send_sms_notification_success(
        self,
        notification_service: NotificationService,
        sample_user: User,
        mock_db_session: AsyncMock,
        mock_sns_client: Mock,
        mock_template_engine: Mock,
    ) -> None:
        """Test successful SMS notification delivery."""
        context = {"order_id": "12345", "tracking_number": "TRACK123"}

        result = await notification_service._send_sms_notification(
            user=sample_user,
            notification_type=NotificationType.ORDER_SHIPPED,
            context=context,
        )

        # Verify template rendering
        mock_template_engine.render_sms.assert_called_once_with(
            "order_shipped", context
        )

        # Verify SMS sending
        mock_sns_client.send_sms.assert_called_once()
        call_args = mock_sns_client.send_sms.call_args
        assert call_args[1]["phone_number"] == sample_user.phone
        assert call_args[1]["message"] == "Test SMS message"
        assert call_args[1]["message_type"] == "Transactional"

        # Verify database operations
        assert mock_db_session.add.called
        assert mock_db_session.flush.called
        assert mock_db_session.commit.called

        # Verify result
        assert result["status"] == "sent"
        assert result["channel"] == "sms"
        assert result["message_id"] == "test-sms-id-789"

    @pytest.mark.asyncio
    async def test_send_sms_notification_no_phone_number(
        self,
        notification_service: NotificationService,
        sample_user: User,
    ) -> None:
        """Test SMS notification fails when user has no phone."""
        sample_user.phone = None

        with pytest.raises(NotificationValidationError) as exc_info:
            await notification_service._send_sms_notification(
                user=sample_user,
                notification_type=NotificationType.ORDER_SHIPPED,
                context={},
            )

        assert "no phone number" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_send_sms_notification_template_error(
        self,
        notification_service: NotificationService,
        sample_user: User,
        mock_template_engine: Mock,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test SMS notification handles template rendering errors."""
        mock_template_engine.render_sms.side_effect = TemplateEngineError(
            "Invalid template"
        )

        with pytest.raises(NotificationDeliveryError) as exc_info:
            await notification_service._send_sms_notification(
                user=sample_user,
                notification_type=NotificationType.ORDER_SHIPPED,
                context={},
            )

        assert "render sms template" in str(exc_info.value).lower()
        assert mock_db_session.commit.called

    @pytest.mark.asyncio
    async def test_send_sms_notification_sns_error(
        self,
        notification_service: NotificationService,
        sample_user: User,
        mock_sns_client: Mock,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test SMS notification handles SNS delivery errors."""
        mock_sns_client.send_sms.side_effect = SNSClientError(
            "Invalid phone number"
        )

        with pytest.raises(NotificationDeliveryError) as exc_info:
            await notification_service._send_sms_notification(
                user=sample_user,
                notification_type=NotificationType.ORDER_SHIPPED,
                context={},
            )

        assert "send sms" in str(exc_info.value).lower()
        assert mock_db_session.commit.called


# ============================================================================
# Unit Tests - Notification Preferences
# ============================================================================


class TestNotificationPreferences:
    """Test notification preference handling."""

    @pytest.mark.asyncio
    async def test_get_enabled_channels_with_preferences(
        self,
        notification_service: NotificationService,
        sample_user_with_preferences: User,
    ) -> None:
        """Test getting enabled channels based on user preferences."""
        # Test ORDER_CREATED (email only)
        channels = await notification_service._get_enabled_channels(
            user=sample_user_with_preferences,
            notification_type=NotificationType.ORDER_CREATED,
        )
        assert channels == [NotificationChannel.EMAIL]

        # Test ORDER_CONFIRMED (both email and SMS)
        channels = await notification_service._get_enabled_channels(
            user=sample_user_with_preferences,
            notification_type=NotificationType.ORDER_CONFIRMED,
        )
        assert set(channels) == {
            NotificationChannel.EMAIL,
            NotificationChannel.SMS,
        }

        # Test PAYMENT_FAILED (SMS only)
        channels = await notification_service._get_enabled_channels(
            user=sample_user_with_preferences,
            notification_type=NotificationType.PAYMENT_FAILED,
        )
        assert channels == [NotificationChannel.SMS]

    @pytest.mark.asyncio
    async def test_get_enabled_channels_no_preferences(
        self,
        notification_service: NotificationService,
        sample_user: User,
    ) -> None:
        """Test default to email when no preferences set."""
        channels = await notification_service._get_enabled_channels(
            user=sample_user,
            notification_type=NotificationType.ORDER_CREATED,
        )

        assert channels == [NotificationChannel.EMAIL]

    @pytest.mark.asyncio
    async def test_get_enabled_channels_force_send(
        self,
        notification_service: NotificationService,
        sample_user_with_preferences: User,
    ) -> None:
        """Test force send overrides preferences."""
        channels = await notification_service._get_enabled_channels(
            user=sample_user_with_preferences,
            notification_type=NotificationType.PAYMENT_FAILED,
            force_send=True,
        )

        # Should include both channels despite preferences
        assert set(channels) == {
            NotificationChannel.EMAIL,
            NotificationChannel.SMS,
        }

    @pytest.mark.asyncio
    async def test_get_enabled_channels_missing_contact_info(
        self,
        notification_service: NotificationService,
        sample_user: User,
    ) -> None:
        """Test channels excluded when contact info missing."""
        sample_user.phone = None

        channels = await notification_service._get_enabled_channels(
            user=sample_user,
            notification_type=NotificationType.ORDER_CREATED,
            force_send=True,
        )

        # Should only include email since phone is missing
        assert channels == [NotificationChannel.EMAIL]


# ============================================================================
# Integration Tests - Send Notification
# ============================================================================


class TestSendNotification:
    """Test complete notification sending workflow."""

    @pytest.mark.asyncio
    async def test_send_notification_success_email_only(
        self,
        notification_service: NotificationService,
        sample_user_with_preferences: User,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test sending notification via email only."""
        # Mock user retrieval
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user_with_preferences
        mock_db_session.execute.return_value = mock_result

        context = {"order_id": "12345"}
        result = await notification_service.send_notification(
            user_id=sample_user_with_preferences.id,
            notification_type=NotificationType.ORDER_CREATED,
            context=context,
        )

        assert result["status"] == "completed"
        assert "email" in result["channels"]
        assert result["channels"]["email"]["status"] == "sent"
        assert "sms" not in result["channels"]

    @pytest.mark.asyncio
    async def test_send_notification_success_both_channels(
        self,
        notification_service: NotificationService,
        sample_user_with_preferences: User,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test sending notification via both email and SMS."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user_with_preferences
        mock_db_session.execute.return_value = mock_result

        context = {"order_id": "12345"}
        result = await notification_service.send_notification(
            user_id=sample_user_with_preferences.id,
            notification_type=NotificationType.ORDER_CONFIRMED,
            context=context,
        )

        assert result["status"] == "completed"
        assert "email" in result["channels"]
        assert "sms" in result["channels"]
        assert result["channels"]["email"]["status"] == "sent"
        assert result["channels"]["sms"]["status"] == "sent"

    @pytest.mark.asyncio
    async def test_send_notification_user_not_found(
        self,
        notification_service: NotificationService,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test notification fails when user not found."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(NotificationValidationError) as exc_info:
            await notification_service.send_notification(
                user_id=uuid4(),
                notification_type=NotificationType.ORDER_CREATED,
                context={},
            )

        assert "user not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_send_notification_no_enabled_channels(
        self,
        notification_service: NotificationService,
        sample_user: User,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test notification skipped when no channels enabled."""
        sample_user.email = None
        sample_user.phone = None

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        result = await notification_service.send_notification(
            user_id=sample_user.id,
            notification_type=NotificationType.ORDER_CREATED,
            context={},
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "no_enabled_channels"

    @pytest.mark.asyncio
    async def test_send_notification_partial_failure(
        self,
        notification_service: NotificationService,
        sample_user_with_preferences: User,
        mock_db_session: AsyncMock,
        mock_sns_client: Mock,
    ) -> None:
        """Test notification continues when one channel fails."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user_with_preferences
        mock_db_session.execute.return_value = mock_result

        # Make SMS fail
        mock_sns_client.send_sms.side_effect = SNSClientError("SMS failed")

        result = await notification_service.send_notification(
            user_id=sample_user_with_preferences.id,
            notification_type=NotificationType.ORDER_CONFIRMED,
            context={},
        )

        assert result["status"] == "completed"
        assert result["channels"]["email"]["status"] == "sent"
        assert result["channels"]["sms"]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_send_notification_with_specific_channels(
        self,
        notification_service: NotificationService,
        sample_user_with_preferences: User,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test sending notification to specific channels."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user_with_preferences
        mock_db_session.execute.return_value = mock_result

        result = await notification_service.send_notification(
            user_id=sample_user_with_preferences.id,
            notification_type=NotificationType.ORDER_CREATED,
            context={},
            channels=[NotificationChannel.SMS],  # Override preferences
        )

        assert result["status"] == "completed"
        assert "sms" in result["channels"]
        assert "email" not in result["channels"]

    @pytest.mark.asyncio
    async def test_send_notification_force_send(
        self,
        notification_service: NotificationService,
        sample_user_with_preferences: User,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test force send overrides user preferences."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user_with_preferences
        mock_db_session.execute.return_value = mock_result

        # PAYMENT_FAILED normally only sends SMS
        result = await notification_service.send_notification(
            user_id=sample_user_with_preferences.id,
            notification_type=NotificationType.PAYMENT_FAILED,
            context={},
            force_send=True,
        )

        assert result["status"] == "completed"
        # Should send to both channels despite preferences
        assert "email" in result["channels"]
        assert "sms" in result["channels"]


# ============================================================================
# Unit Tests - Template Mapping
# ============================================================================


class TestTemplateMapping:
    """Test notification type to template name mapping."""

    @pytest.mark.parametrize(
        "notification_type,expected_template",
        [
            (NotificationType.ORDER_CREATED, "order_created"),
            (NotificationType.ORDER_CONFIRMED, "order_confirmed"),
            (NotificationType.ORDER_SHIPPED, "order_shipped"),
            (NotificationType.ORDER_DELIVERED, "order_delivered"),
            (NotificationType.ORDER_CANCELLED, "order_cancelled"),
            (NotificationType.PAYMENT_RECEIVED, "payment_received"),
            (NotificationType.PAYMENT_FAILED, "payment_failed"),
            (NotificationType.DELIVERY_DELAYED, "delivery_delayed"),
            (NotificationType.DELIVERY_REMINDER, "delivery_reminder"),
        ],
    )
    def test_get_template_name_mapping(
        self,
        notification_service: NotificationService,
        notification_type: NotificationType,
        expected_template: str,
    ) -> None:
        """Test correct template name returned for notification type."""
        template_name = notification_service._get_template_name(notification_type)
        assert template_name == expected_template


# ============================================================================
# Integration Tests - Retry Failed Notifications
# ============================================================================


class TestRetryFailedNotifications:
    """Test retry logic for failed notifications."""

    @pytest.mark.asyncio
    async def test_retry_failed_notifications_success(
        self,
        notification_service: NotificationService,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test retrying failed notifications."""
        # Create mock failed notifications
        failed_notification = NotificationLog(
            id=uuid4(),
            user_id=uuid4(),
            notification_type=NotificationType.ORDER_CREATED,
            channel=NotificationChannel.EMAIL,
            recipient="test@example.com",
            status=NotificationStatus.FAILED,
            retry_count=0,
            created_at=datetime.utcnow() - timedelta(hours=1),
        )
        failed_notification.user = User(
            id=failed_notification.user_id,
            email="test@example.com",
        )

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [failed_notification]
        mock_db_session.execute.return_value = mock_result

        result = await notification_service.retry_failed_notifications(hours=24)

        assert result["total_retried"] == 1
        assert mock_db_session.commit.called

    @pytest.mark.asyncio
    async def test_retry_failed_notifications_no_failures(
        self,
        notification_service: NotificationService,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test retry when no failed notifications exist."""
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        result = await notification_service.retry_failed_notifications(hours=24)

        assert result["total_retried"] == 0
        assert result["success_count"] == 0
        assert result["failure_count"] == 0

    @pytest.mark.asyncio
    async def test_retry_failed_notifications_max_retries_exceeded(
        self,
        notification_service: NotificationService,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test notifications with max retries are not retried."""
        # Create notification that has already been retried max times
        failed_notification = NotificationLog(
            id=uuid4(),
            user_id=uuid4(),
            notification_type=NotificationType.ORDER_CREATED,
            channel=NotificationChannel.EMAIL,
            recipient="test@example.com",
            status=NotificationStatus.FAILED,
            retry_count=3,  # Already at max retries
            created_at=datetime.utcnow() - timedelta(hours=1),
        )

        mock_result = AsyncMock()
        # Should not be returned by query due to retry_count filter
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        result = await notification_service.retry_failed_notifications(hours=24)

        assert result["total_retried"] == 0


# ============================================================================
# Unit Tests - User Retrieval
# ============================================================================


class TestUserRetrieval:
    """Test user retrieval with preferences."""

    @pytest.mark.asyncio
    async def test_get_user_with_preferences_found(
        self,
        notification_service: NotificationService,
        sample_user_with_preferences: User,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test retrieving user with preferences."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user_with_preferences
        mock_db_session.execute.return_value = mock_result

        user = await notification_service._get_user_with_preferences(
            sample_user_with_preferences.id
        )

        assert user is not None
        assert user.id == sample_user_with_preferences.id
        assert len(user.notification_preferences) > 0

    @pytest.mark.asyncio
    async def test_get_user_with_preferences_not_found(
        self,
        notification_service: NotificationService,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test retrieving non-existent user."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        user = await notification_service._get_user_with_preferences(uuid4())

        assert user is None


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_send_notification_empty_context(
        self,
        notification_service: NotificationService,
        sample_user: User,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test sending notification with empty context."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        result = await notification_service.send_notification(
            user_id=sample_user.id,
            notification_type=NotificationType.ORDER_CREATED,
            context={},  # Empty context
        )

        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_send_notification_large_context(
        self,
        notification_service: NotificationService,
        sample_user: User,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test sending notification with large context data."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        # Create large context
        large_context = {
            f"field_{i}": f"value_{i}" * 100 for i in range(100)
        }

        result = await notification_service.send_notification(
            user_id=sample_user.id,
            notification_type=NotificationType.ORDER_CREATED,
            context=large_context,
        )

        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_send_notification_special_characters_in_context(
        self,
        notification_service: NotificationService,
        sample_user: User,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test notification with special characters in context."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        context = {
            "message": "Test with special chars: <>&\"'",
            "unicode": "Test with unicode: 你好 🎉",
        }

        result = await notification_service.send_notification(
            user_id=sample_user.id,
            notification_type=NotificationType.ORDER_CREATED,
            context=context,
        )

        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_concurrent_notifications(
        self,
        notification_service: NotificationService,
        sample_user: User,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test sending multiple notifications concurrently."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        # Send multiple notifications concurrently
        tasks = [
            notification_service.send_notification(
                user_id=sample_user.id,
                notification_type=NotificationType.ORDER_CREATED,
                context={"order_id": f"order_{i}"},
            )
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        assert all(
            isinstance(r, dict) and r["status"] == "completed" for r in results
        )


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Test performance characteristics of notification service."""

    @pytest.mark.asyncio
    async def test_notification_delivery_performance(
        self,
        notification_service: NotificationService,
        sample_user: User,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test notification delivery completes within time threshold."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        start_time = datetime.utcnow()

        await notification_service.send_notification(
            user_id=sample_user.id,
            notification_type=NotificationType.ORDER_CREATED,
            context={"order_id": "12345"},
        )

        elapsed = (datetime.utcnow() - start_time).total_seconds()

        # Should complete in under 1 second with mocked dependencies
        assert elapsed < 1.0

    @pytest.mark.asyncio
    async def test_batch_notification_performance(
        self,
        notification_service: NotificationService,
        sample_user: User,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test batch notification processing performance."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        start_time = datetime.utcnow()

        # Send 10 notifications
        tasks = [
            notification_service.send_notification(
                user_id=sample_user.id,
                notification_type=NotificationType.ORDER_CREATED,
                context={"order_id": f"order_{i}"},
            )
            for i in range(10)
        ]

        await asyncio.gather(*tasks)

        elapsed = (datetime.utcnow() - start_time).total_seconds()

        # Should complete in under 2 seconds for 10 notifications
        assert elapsed < 2.0


# ============================================================================
# Exception Context Tests
# ============================================================================


class TestExceptionContext:
    """Test exception context and error information."""

    def test_notification_service_error_context(self) -> None:
        """Test NotificationServiceError stores context."""
        error = NotificationServiceError(
            "Test error",
            user_id="123",
            notification_type="order_created",
        )

        assert str(error) == "Test error"
        assert error.context["user_id"] == "123"
        assert error.context["notification_type"] == "order_created"

    def test_notification_delivery_error_inheritance(self) -> None:
        """Test NotificationDeliveryError inherits from base."""
        error = NotificationDeliveryError("Delivery failed", channel="email")

        assert isinstance(error, NotificationServiceError)
        assert error.context["channel"] == "email"

    def test_notification_validation_error_inheritance(self) -> None:
        """Test NotificationValidationError inherits from base."""
        error = NotificationValidationError("Invalid user", user_id="456")

        assert isinstance(error, NotificationServiceError)
        assert error.context["user_id"] == "456"