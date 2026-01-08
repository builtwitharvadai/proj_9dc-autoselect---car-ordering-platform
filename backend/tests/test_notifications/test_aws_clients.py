"""
Comprehensive test suite for AWS SES and SNS client wrappers.

This module provides extensive testing for AWS client wrappers including:
- Email sending via SES with retry logic
- SMS sending via SNS with retry logic
- Error handling and exception scenarios
- Retry mechanisms and backoff strategies
- Email identity verification
- SMS opt-out status checking
"""

import time
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectionError as BotoConnectionError,
    EndpointConnectionError,
)

from src.services.notifications.aws_clients import (
    AWSClientError,
    SESClient,
    SESClientError,
    SNSClient,
    SNSClientError,
    get_ses_client,
    get_sns_client,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_boto3_client():
    """Mock boto3 client for testing."""
    with patch("src.services.notifications.aws_clients.boto3.client") as mock:
        yield mock


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    with patch("src.services.notifications.aws_clients.get_settings") as mock:
        settings = Mock()
        settings.aws_access_key_id = "test_access_key"
        settings.aws_secret_access_key = "test_secret_key"
        settings.aws_region = "us-east-1"
        settings.ses_from_email = "noreply@example.com"
        mock.return_value = settings
        yield settings


@pytest.fixture
def ses_client(mock_boto3_client, mock_settings):
    """Create SES client instance for testing."""
    mock_client = MagicMock()
    mock_boto3_client.return_value = mock_client
    client = SESClient(max_retries=3, retry_backoff=0.1)
    client._client = mock_client
    return client


@pytest.fixture
def sns_client(mock_boto3_client, mock_settings):
    """Create SNS client instance for testing."""
    mock_client = MagicMock()
    mock_boto3_client.return_value = mock_client
    client = SNSClient(max_retries=3, retry_backoff=0.1)
    client._client = mock_client
    return client


@pytest.fixture
def sample_email_data():
    """Sample email data for testing."""
    return {
        "to_addresses": ["recipient@example.com"],
        "subject": "Test Email",
        "body_text": "This is a test email",
        "body_html": "<p>This is a test email</p>",
        "from_address": "sender@example.com",
    }


@pytest.fixture
def sample_sms_data():
    """Sample SMS data for testing."""
    return {
        "phone_number": "+12345678901",
        "message": "Test SMS message",
        "sender_id": "TestApp",
        "message_type": "Transactional",
    }


# ============================================================================
# Exception Classes Tests
# ============================================================================


class TestAWSClientError:
    """Test suite for AWSClientError exception."""

    def test_aws_client_error_initialization(self):
        """Test AWSClientError initialization with context."""
        error = AWSClientError(
            "Test error", service="SES", error_code="TestError", retry_count=3
        )

        assert str(error) == "Test error"
        assert error.service == "SES"
        assert error.context["error_code"] == "TestError"
        assert error.context["retry_count"] == 3

    def test_aws_client_error_inheritance(self):
        """Test AWSClientError inherits from Exception."""
        error = AWSClientError("Test error", service="SNS")
        assert isinstance(error, Exception)


class TestSESClientError:
    """Test suite for SESClientError exception."""

    def test_ses_client_error_initialization(self):
        """Test SESClientError initialization."""
        error = SESClientError("SES error", error_code="MessageRejected")

        assert str(error) == "SES error"
        assert error.service == "SES"
        assert error.context["error_code"] == "MessageRejected"

    def test_ses_client_error_inheritance(self):
        """Test SESClientError inherits from AWSClientError."""
        error = SESClientError("Test error")
        assert isinstance(error, AWSClientError)


class TestSNSClientError:
    """Test suite for SNSClientError exception."""

    def test_sns_client_error_initialization(self):
        """Test SNSClientError initialization."""
        error = SNSClientError("SNS error", error_code="InvalidParameter")

        assert str(error) == "SNS error"
        assert error.service == "SNS"
        assert error.context["error_code"] == "InvalidParameter"

    def test_sns_client_error_inheritance(self):
        """Test SNSClientError inherits from AWSClientError."""
        error = SNSClientError("Test error")
        assert isinstance(error, AWSClientError)


# ============================================================================
# SESClient Initialization Tests
# ============================================================================


class TestSESClientInitialization:
    """Test suite for SESClient initialization."""

    def test_ses_client_initialization_with_defaults(
        self, mock_boto3_client, mock_settings
    ):
        """Test SES client initialization with default settings."""
        client = SESClient()

        mock_boto3_client.assert_called_once_with(
            "ses",
            aws_access_key_id="test_access_key",
            aws_secret_access_key="test_secret_key",
            region_name="us-east-1",
        )
        assert client.max_retries == 3
        assert client.retry_backoff == 1.0

    def test_ses_client_initialization_with_custom_credentials(
        self, mock_boto3_client, mock_settings
    ):
        """Test SES client initialization with custom credentials."""
        client = SESClient(
            aws_access_key_id="custom_key",
            aws_secret_access_key="custom_secret",
            region_name="eu-west-1",
        )

        mock_boto3_client.assert_called_once_with(
            "ses",
            aws_access_key_id="custom_key",
            aws_secret_access_key="custom_secret",
            region_name="eu-west-1",
        )

    def test_ses_client_initialization_with_custom_retry_settings(
        self, mock_boto3_client, mock_settings
    ):
        """Test SES client initialization with custom retry settings."""
        client = SESClient(max_retries=5, retry_backoff=2.0)

        assert client.max_retries == 5
        assert client.retry_backoff == 2.0


# ============================================================================
# SESClient Email Sending Tests
# ============================================================================


class TestSESClientSendEmail:
    """Test suite for SES email sending functionality."""

    def test_send_email_success(self, ses_client, sample_email_data):
        """Test successful email sending."""
        ses_client._client.send_email.return_value = {
            "MessageId": "test-message-id-123"
        }

        result = ses_client.send_email(**sample_email_data)

        assert result["message_id"] == "test-message-id-123"
        assert result["status"] == "sent"
        assert result["to_addresses"] == sample_email_data["to_addresses"]
        assert result["from_address"] == sample_email_data["from_address"]
        assert result["subject"] == sample_email_data["subject"]

        ses_client._client.send_email.assert_called_once()

    def test_send_email_with_default_from_address(
        self, ses_client, mock_settings
    ):
        """Test email sending with default from address."""
        ses_client._client.send_email.return_value = {
            "MessageId": "test-message-id"
        }

        result = ses_client.send_email(
            to_addresses=["recipient@example.com"],
            subject="Test",
            body_text="Test body",
        )

        assert result["from_address"] == "noreply@example.com"

    def test_send_email_with_cc_and_bcc(self, ses_client):
        """Test email sending with CC and BCC addresses."""
        ses_client._client.send_email.return_value = {
            "MessageId": "test-message-id"
        }

        result = ses_client.send_email(
            to_addresses=["recipient@example.com"],
            subject="Test",
            body_text="Test body",
            cc_addresses=["cc@example.com"],
            bcc_addresses=["bcc@example.com"],
        )

        call_args = ses_client._client.send_email.call_args[1]
        assert "CcAddresses" in call_args["Destination"]
        assert "BccAddresses" in call_args["Destination"]
        assert result["status"] == "sent"

    def test_send_email_with_reply_to(self, ses_client):
        """Test email sending with reply-to addresses."""
        ses_client._client.send_email.return_value = {
            "MessageId": "test-message-id"
        }

        result = ses_client.send_email(
            to_addresses=["recipient@example.com"],
            subject="Test",
            body_text="Test body",
            reply_to_addresses=["reply@example.com"],
        )

        call_args = ses_client._client.send_email.call_args[1]
        assert "ReplyToAddresses" in call_args
        assert result["status"] == "sent"

    def test_send_email_html_body(self, ses_client, sample_email_data):
        """Test email sending with HTML body."""
        ses_client._client.send_email.return_value = {
            "MessageId": "test-message-id"
        }

        result = ses_client.send_email(**sample_email_data)

        call_args = ses_client._client.send_email.call_args[1]
        assert "Html" in call_args["Message"]["Body"]
        assert result["status"] == "sent"

    def test_send_email_no_recipients_error(self, ses_client):
        """Test email sending fails with no recipients."""
        with pytest.raises(SESClientError) as exc_info:
            ses_client.send_email(
                to_addresses=[], subject="Test", body_text="Test body"
            )

        assert "at least one recipient" in str(exc_info.value).lower()

    def test_send_email_client_error_non_retryable(self, ses_client):
        """Test email sending with non-retryable client error."""
        error_response = {
            "Error": {
                "Code": "MessageRejected",
                "Message": "Email address not verified",
            }
        }
        ses_client._client.send_email.side_effect = ClientError(
            error_response, "SendEmail"
        )

        with pytest.raises(SESClientError) as exc_info:
            ses_client.send_email(
                to_addresses=["test@example.com"],
                subject="Test",
                body_text="Test body",
            )

        assert "MessageRejected" in exc_info.value.context["error_code"]
        assert ses_client._client.send_email.call_count == 1

    def test_send_email_client_error_retryable_success(self, ses_client):
        """Test email sending with retryable error then success."""
        error_response = {
            "Error": {"Code": "Throttling", "Message": "Rate exceeded"}
        }

        ses_client._client.send_email.side_effect = [
            ClientError(error_response, "SendEmail"),
            {"MessageId": "test-message-id"},
        ]

        result = ses_client.send_email(
            to_addresses=["test@example.com"],
            subject="Test",
            body_text="Test body",
        )

        assert result["status"] == "sent"
        assert ses_client._client.send_email.call_count == 2

    def test_send_email_exhausted_retries(self, ses_client):
        """Test email sending fails after exhausting retries."""
        error_response = {
            "Error": {"Code": "ServiceUnavailable", "Message": "Service down"}
        }
        ses_client._client.send_email.side_effect = ClientError(
            error_response, "SendEmail"
        )

        with pytest.raises(SESClientError) as exc_info:
            ses_client.send_email(
                to_addresses=["test@example.com"],
                subject="Test",
                body_text="Test body",
            )

        assert "Failed to send email after 3 attempts" in str(exc_info.value)
        assert ses_client._client.send_email.call_count == 3

    def test_send_email_connection_error_retry(self, ses_client):
        """Test email sending with connection error and retry."""
        ses_client._client.send_email.side_effect = [
            BotoConnectionError(error="Connection failed"),
            {"MessageId": "test-message-id"},
        ]

        result = ses_client.send_email(
            to_addresses=["test@example.com"],
            subject="Test",
            body_text="Test body",
        )

        assert result["status"] == "sent"
        assert ses_client._client.send_email.call_count == 2

    def test_send_email_endpoint_connection_error(self, ses_client):
        """Test email sending with endpoint connection error."""
        ses_client._client.send_email.side_effect = [
            EndpointConnectionError(endpoint_url="https://ses.amazonaws.com"),
            {"MessageId": "test-message-id"},
        ]

        result = ses_client.send_email(
            to_addresses=["test@example.com"],
            subject="Test",
            body_text="Test body",
        )

        assert result["status"] == "sent"
        assert ses_client._client.send_email.call_count == 2

    def test_send_email_botocore_error(self, ses_client):
        """Test email sending with BotoCoreError."""
        ses_client._client.send_email.side_effect = [
            BotoCoreError(),
            {"MessageId": "test-message-id"},
        ]

        result = ses_client.send_email(
            to_addresses=["test@example.com"],
            subject="Test",
            body_text="Test body",
        )

        assert result["status"] == "sent"
        assert ses_client._client.send_email.call_count == 2

    @patch("src.services.notifications.aws_clients.time.sleep")
    def test_send_email_retry_backoff(self, mock_sleep, ses_client):
        """Test email sending retry backoff timing."""
        error_response = {
            "Error": {"Code": "Throttling", "Message": "Rate exceeded"}
        }
        ses_client._client.send_email.side_effect = [
            ClientError(error_response, "SendEmail"),
            ClientError(error_response, "SendEmail"),
            {"MessageId": "test-message-id"},
        ]

        result = ses_client.send_email(
            to_addresses=["test@example.com"],
            subject="Test",
            body_text="Test body",
        )

        assert result["status"] == "sent"
        assert mock_sleep.call_count == 2
        # Verify exponential backoff: 0.1 * 2^0 = 0.1, 0.1 * 2^1 = 0.2
        mock_sleep.assert_any_call(0.1)
        mock_sleep.assert_any_call(0.2)


# ============================================================================
# SESClient Email Verification Tests
# ============================================================================


class TestSESClientVerifyEmail:
    """Test suite for SES email verification functionality."""

    def test_verify_email_identity_success(self, ses_client):
        """Test successful email identity verification."""
        ses_client._client.verify_email_identity.return_value = {}

        result = ses_client.verify_email_identity("test@example.com")

        assert result["email_address"] == "test@example.com"
        assert result["status"] == "verification_sent"
        ses_client._client.verify_email_identity.assert_called_once_with(
            EmailAddress="test@example.com"
        )

    def test_verify_email_identity_client_error(self, ses_client):
        """Test email identity verification with client error."""
        error_response = {
            "Error": {
                "Code": "InvalidParameterValue",
                "Message": "Invalid email address",
            }
        }
        ses_client._client.verify_email_identity.side_effect = ClientError(
            error_response, "VerifyEmailIdentity"
        )

        with pytest.raises(SESClientError) as exc_info:
            ses_client.verify_email_identity("invalid-email")

        assert "Failed to verify email identity" in str(exc_info.value)
        assert exc_info.value.context["error_code"] == "InvalidParameterValue"


# ============================================================================
# SNSClient Initialization Tests
# ============================================================================


class TestSNSClientInitialization:
    """Test suite for SNSClient initialization."""

    def test_sns_client_initialization_with_defaults(
        self, mock_boto3_client, mock_settings
    ):
        """Test SNS client initialization with default settings."""
        client = SNSClient()

        mock_boto3_client.assert_called_with(
            "sns",
            aws_access_key_id="test_access_key",
            aws_secret_access_key="test_secret_key",
            region_name="us-east-1",
        )
        assert client.max_retries == 3
        assert client.retry_backoff == 1.0

    def test_sns_client_initialization_with_custom_credentials(
        self, mock_boto3_client, mock_settings
    ):
        """Test SNS client initialization with custom credentials."""
        client = SNSClient(
            aws_access_key_id="custom_key",
            aws_secret_access_key="custom_secret",
            region_name="ap-southeast-1",
        )

        mock_boto3_client.assert_called_with(
            "sns",
            aws_access_key_id="custom_key",
            aws_secret_access_key="custom_secret",
            region_name="ap-southeast-1",
        )

    def test_sns_client_initialization_with_custom_retry_settings(
        self, mock_boto3_client, mock_settings
    ):
        """Test SNS client initialization with custom retry settings."""
        client = SNSClient(max_retries=5, retry_backoff=2.5)

        assert client.max_retries == 5
        assert client.retry_backoff == 2.5


# ============================================================================
# SNSClient SMS Sending Tests
# ============================================================================


class TestSNSClientSendSMS:
    """Test suite for SNS SMS sending functionality."""

    def test_send_sms_success(self, sns_client, sample_sms_data):
        """Test successful SMS sending."""
        sns_client._client.publish.return_value = {
            "MessageId": "test-sms-id-123"
        }

        result = sns_client.send_sms(**sample_sms_data)

        assert result["message_id"] == "test-sms-id-123"
        assert result["status"] == "sent"
        assert result["phone_number"] == sample_sms_data["phone_number"]
        assert result["message_type"] == sample_sms_data["message_type"]

        sns_client._client.publish.assert_called_once()

    def test_send_sms_with_sender_id(self, sns_client):
        """Test SMS sending with sender ID."""
        sns_client._client.publish.return_value = {"MessageId": "test-sms-id"}

        result = sns_client.send_sms(
            phone_number="+12345678901",
            message="Test message",
            sender_id="MyApp",
        )

        call_args = sns_client._client.publish.call_args[1]
        assert "AWS.SNS.SMS.SenderID" in call_args["MessageAttributes"]
        assert result["status"] == "sent"

    def test_send_sms_promotional_type(self, sns_client):
        """Test SMS sending with promotional message type."""
        sns_client._client.publish.return_value = {"MessageId": "test-sms-id"}

        result = sns_client.send_sms(
            phone_number="+12345678901",
            message="Test message",
            message_type="Promotional",
        )

        call_args = sns_client._client.publish.call_args[1]
        sms_type = call_args["MessageAttributes"]["AWS.SNS.SMS.SMSType"][
            "StringValue"
        ]
        assert sms_type == "Promotional"
        assert result["status"] == "sent"

    def test_send_sms_invalid_phone_format(self, sns_client):
        """Test SMS sending fails with invalid phone format."""
        with pytest.raises(SNSClientError) as exc_info:
            sns_client.send_sms(
                phone_number="1234567890", message="Test message"
            )

        assert "E.164 format" in str(exc_info.value)

    def test_send_sms_invalid_message_type(self, sns_client):
        """Test SMS sending fails with invalid message type."""
        with pytest.raises(SNSClientError) as exc_info:
            sns_client.send_sms(
                phone_number="+12345678901",
                message="Test message",
                message_type="Invalid",
            )

        assert "Message type must be" in str(exc_info.value)

    def test_send_sms_client_error_non_retryable(self, sns_client):
        """Test SMS sending with non-retryable client error."""
        error_response = {
            "Error": {
                "Code": "InvalidParameter",
                "Message": "Invalid phone number",
            }
        }
        sns_client._client.publish.side_effect = ClientError(
            error_response, "Publish"
        )

        with pytest.raises(SNSClientError) as exc_info:
            sns_client.send_sms(
                phone_number="+12345678901", message="Test message"
            )

        assert "InvalidParameter" in exc_info.value.context["error_code"]
        assert sns_client._client.publish.call_count == 1

    def test_send_sms_opted_out_error(self, sns_client):
        """Test SMS sending with opted-out phone number."""
        error_response = {
            "Error": {
                "Code": "OptedOut",
                "Message": "Phone number has opted out",
            }
        }
        sns_client._client.publish.side_effect = ClientError(
            error_response, "Publish"
        )

        with pytest.raises(SNSClientError) as exc_info:
            sns_client.send_sms(
                phone_number="+12345678901", message="Test message"
            )

        assert "OptedOut" in exc_info.value.context["error_code"]

    def test_send_sms_client_error_retryable_success(self, sns_client):
        """Test SMS sending with retryable error then success."""
        error_response = {
            "Error": {"Code": "Throttling", "Message": "Rate exceeded"}
        }

        sns_client._client.publish.side_effect = [
            ClientError(error_response, "Publish"),
            {"MessageId": "test-sms-id"},
        ]

        result = sns_client.send_sms(
            phone_number="+12345678901", message="Test message"
        )

        assert result["status"] == "sent"
        assert sns_client._client.publish.call_count == 2

    def test_send_sms_exhausted_retries(self, sns_client):
        """Test SMS sending fails after exhausting retries."""
        error_response = {
            "Error": {"Code": "ServiceUnavailable", "Message": "Service down"}
        }
        sns_client._client.publish.side_effect = ClientError(
            error_response, "Publish"
        )

        with pytest.raises(SNSClientError) as exc_info:
            sns_client.send_sms(
                phone_number="+12345678901", message="Test message"
            )

        assert "Failed to send SMS after 3 attempts" in str(exc_info.value)
        assert sns_client._client.publish.call_count == 3

    def test_send_sms_connection_error_retry(self, sns_client):
        """Test SMS sending with connection error and retry."""
        sns_client._client.publish.side_effect = [
            BotoConnectionError(error="Connection failed"),
            {"MessageId": "test-sms-id"},
        ]

        result = sns_client.send_sms(
            phone_number="+12345678901", message="Test message"
        )

        assert result["status"] == "sent"
        assert sns_client._client.publish.call_count == 2

    def test_send_sms_endpoint_connection_error(self, sns_client):
        """Test SMS sending with endpoint connection error."""
        sns_client._client.publish.side_effect = [
            EndpointConnectionError(endpoint_url="https://sns.amazonaws.com"),
            {"MessageId": "test-sms-id"},
        ]

        result = sns_client.send_sms(
            phone_number="+12345678901", message="Test message"
        )

        assert result["status"] == "sent"
        assert sns_client._client.publish.call_count == 2

    def test_send_sms_botocore_error(self, sns_client):
        """Test SMS sending with BotoCoreError."""
        sns_client._client.publish.side_effect = [
            BotoCoreError(),
            {"MessageId": "test-sms-id"},
        ]

        result = sns_client.send_sms(
            phone_number="+12345678901", message="Test message"
        )

        assert result["status"] == "sent"
        assert sns_client._client.publish.call_count == 2

    @patch("src.services.notifications.aws_clients.time.sleep")
    def test_send_sms_retry_backoff(self, mock_sleep, sns_client):
        """Test SMS sending retry backoff timing."""
        error_response = {
            "Error": {"Code": "Throttling", "Message": "Rate exceeded"}
        }
        sns_client._client.publish.side_effect = [
            ClientError(error_response, "Publish"),
            ClientError(error_response, "Publish"),
            {"MessageId": "test-sms-id"},
        ]

        result = sns_client.send_sms(
            phone_number="+12345678901", message="Test message"
        )

        assert result["status"] == "sent"
        assert mock_sleep.call_count == 2
        # Verify exponential backoff: 0.1 * 2^0 = 0.1, 0.1 * 2^1 = 0.2
        mock_sleep.assert_any_call(0.1)
        mock_sleep.assert_any_call(0.2)


# ============================================================================
# SNSClient Opt-Out Status Tests
# ============================================================================


class TestSNSClientOptOutStatus:
    """Test suite for SNS opt-out status checking."""

    def test_check_opt_out_status_not_opted_out(self, sns_client):
        """Test checking opt-out status for non-opted-out number."""
        sns_client._client.check_if_phone_number_is_opted_out.return_value = {
            "isOptedOut": False
        }

        result = sns_client.check_opt_out_status("+12345678901")

        assert result["phone_number"] == "+12345678901"
        assert result["is_opted_out"] is False
        sns_client._client.check_if_phone_number_is_opted_out.assert_called_once_with(
            phoneNumber="+12345678901"
        )

    def test_check_opt_out_status_opted_out(self, sns_client):
        """Test checking opt-out status for opted-out number."""
        sns_client._client.check_if_phone_number_is_opted_out.return_value = {
            "isOptedOut": True
        }

        result = sns_client.check_opt_out_status("+12345678901")

        assert result["phone_number"] == "+12345678901"
        assert result["is_opted_out"] is True

    def test_check_opt_out_status_client_error(self, sns_client):
        """Test opt-out status check with client error."""
        error_response = {
            "Error": {
                "Code": "InvalidParameter",
                "Message": "Invalid phone number",
            }
        }
        sns_client._client.check_if_phone_number_is_opted_out.side_effect = (
            ClientError(error_response, "CheckIfPhoneNumberIsOptedOut")
        )

        with pytest.raises(SNSClientError) as exc_info:
            sns_client.check_opt_out_status("+12345678901")

        assert "Failed to check opt-out status" in str(exc_info.value)
        assert exc_info.value.context["error_code"] == "InvalidParameter"


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestFactoryFunctions:
    """Test suite for client factory functions."""

    def test_get_ses_client_default_settings(
        self, mock_boto3_client, mock_settings
    ):
        """Test get_ses_client with default settings."""
        client = get_ses_client()

        assert isinstance(client, SESClient)
        assert client.max_retries == 3
        assert client.retry_backoff == 1.0

    def test_get_ses_client_custom_settings(
        self, mock_boto3_client, mock_settings
    ):
        """Test get_ses_client with custom settings."""
        client = get_ses_client(max_retries=5, retry_backoff=2.0)

        assert isinstance(client, SESClient)
        assert client.max_retries == 5
        assert client.retry_backoff == 2.0

    def test_get_sns_client_default_settings(
        self, mock_boto3_client, mock_settings
    ):
        """Test get_sns_client with default settings."""
        client = get_sns_client()

        assert isinstance(client, SNSClient)
        assert client.max_retries == 3
        assert client.retry_backoff == 1.0

    def test_get_sns_client_custom_settings(
        self, mock_boto3_client, mock_settings
    ):
        """Test get_sns_client with custom settings."""
        client = get_sns_client(max_retries=5, retry_backoff=2.0)

        assert isinstance(client, SNSClient)
        assert client.max_retries == 5
        assert client.retry_backoff == 2.0


# ============================================================================
# Integration Tests
# ============================================================================


class TestSESClientIntegration:
    """Integration tests for SES client."""

    def test_send_email_complete_workflow(
        self, ses_client, sample_email_data
    ):
        """Test complete email sending workflow."""
        ses_client._client.send_email.return_value = {
            "MessageId": "integration-test-id"
        }

        # Send email
        result = ses_client.send_email(**sample_email_data)

        # Verify result structure
        assert "message_id" in result
        assert "status" in result
        assert "to_addresses" in result
        assert "from_address" in result
        assert "subject" in result

        # Verify all fields populated
        assert result["message_id"] == "integration-test-id"
        assert result["status"] == "sent"
        assert len(result["to_addresses"]) > 0

    def test_send_email_with_all_optional_fields(self, ses_client):
        """Test email sending with all optional fields."""
        ses_client._client.send_email.return_value = {
            "MessageId": "test-id"
        }

        result = ses_client.send_email(
            to_addresses=["to@example.com"],
            subject="Test Subject",
            body_text="Plain text body",
            body_html="<p>HTML body</p>",
            from_address="from@example.com",
            reply_to_addresses=["reply@example.com"],
            cc_addresses=["cc@example.com"],
            bcc_addresses=["bcc@example.com"],
        )

        assert result["status"] == "sent"
        call_args = ses_client._client.send_email.call_args[1]

        # Verify all fields in API call
        assert "ToAddresses" in call_args["Destination"]
        assert "CcAddresses" in call_args["Destination"]
        assert "BccAddresses" in call_args["Destination"]
        assert "ReplyToAddresses" in call_args
        assert "Html" in call_args["Message"]["Body"]


class TestSNSClientIntegration:
    """Integration tests for SNS client."""

    def test_send_sms_complete_workflow(self, sns_client, sample_sms_data):
        """Test complete SMS sending workflow."""
        sns_client._client.publish.return_value = {
            "MessageId": "integration-sms-id"
        }

        # Send SMS
        result = sns_client.send_sms(**sample_sms_data)

        # Verify result structure
        assert "message_id" in result
        assert "status" in result
        assert "phone_number" in result
        assert "message_type" in result

        # Verify all fields populated
        assert result["message_id"] == "integration-sms-id"
        assert result["status"] == "sent"
        assert result["phone_number"].startswith("+")

    def test_send_sms_and_check_opt_out(self, sns_client):
        """Test SMS sending and opt-out status check workflow."""
        phone_number = "+12345678901"

        # Check opt-out status first
        sns_client._client.check_if_phone_number_is_opted_out.return_value = {
            "isOptedOut": False
        }
        opt_out_result = sns_client.check_opt_out_status(phone_number)
        assert opt_out_result["is_opted_out"] is False

        # Send SMS
        sns_client._client.publish.return_value = {"MessageId": "test-id"}
        sms_result = sns_client.send_sms(
            phone_number=phone_number, message="Test message"
        )
        assert sms_result["status"] == "sent"


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Performance tests for AWS clients."""

    def test_ses_send_email_performance(self, ses_client, sample_email_data):
        """Test SES email sending performance."""
        ses_client._client.send_email.return_value = {
            "MessageId": "perf-test-id"
        }

        start_time = time.time()
        result = ses_client.send_email(**sample_email_data)
        elapsed_time = time.time() - start_time

        assert result["status"] == "sent"
        assert elapsed_time < 1.0  # Should complete in under 1 second

    def test_sns_send_sms_performance(self, sns_client, sample_sms_data):
        """Test SNS SMS sending performance."""
        sns_client._client.publish.return_value = {"MessageId": "perf-test-id"}

        start_time = time.time()
        result = sns_client.send_sms(**sample_sms_data)
        elapsed_time = time.time() - start_time

        assert result["status"] == "sent"
        assert elapsed_time < 1.0  # Should complete in under 1 second

    @patch("src.services.notifications.aws_clients.time.sleep")
    def test_retry_backoff_timing(self, mock_sleep, ses_client):
        """Test retry backoff timing is efficient."""
        error_response = {
            "Error": {"Code": "Throttling", "Message": "Rate exceeded"}
        }
        ses_client._client.send_email.side_effect = [
            ClientError(error_response, "SendEmail"),
            {"MessageId": "test-id"},
        ]

        start_time = time.time()
        result = ses_client.send_email(
            to_addresses=["test@example.com"],
            subject="Test",
            body_text="Test body",
        )
        elapsed_time = time.time() - start_time

        assert result["status"] == "sent"
        # Should complete quickly with mocked sleep
        assert elapsed_time < 0.5


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Edge case tests for AWS clients."""

    def test_ses_send_email_empty_subject(self, ses_client):
        """Test email sending with empty subject."""
        ses_client._client.send_email.return_value = {
            "MessageId": "test-id"
        }

        result = ses_client.send_email(
            to_addresses=["test@example.com"], subject="", body_text="Test"
        )

        assert result["status"] == "sent"

    def test_ses_send_email_very_long_subject(self, ses_client):
        """Test email sending with very long subject."""
        ses_client._client.send_email.return_value = {
            "MessageId": "test-id"
        }

        long_subject = "A" * 1000
        result = ses_client.send_email(
            to_addresses=["test@example.com"],
            subject=long_subject,
            body_text="Test",
        )

        assert result["status"] == "sent"

    def test_ses_send_email_unicode_content(self, ses_client):
        """Test email sending with unicode content."""
        ses_client._client.send_email.return_value = {
            "MessageId": "test-id"
        }

        result = ses_client.send_email(
            to_addresses=["test@example.com"],
            subject="Test 测试 🎉",
            body_text="Unicode content: 你好世界 🌍",
        )

        assert result["status"] == "sent"

    def test_sns_send_sms_unicode_message(self, sns_client):
        """Test SMS sending with unicode message."""
        sns_client._client.publish.return_value = {"MessageId": "test-id"}

        result = sns_client.send_sms(
            phone_number="+12345678901", message="Unicode: 你好 🎉"
        )

        assert result["status"] == "sent"

    def test_sns_send_sms_very_long_message(self, sns_client):
        """Test SMS sending with very long message."""
        sns_client._client.publish.return_value = {"MessageId": "test-id"}

        long_message = "A" * 1600  # SMS limit is typically 160 chars
        result = sns_client.send_sms(
            phone_number="+12345678901", message=long_message
        )

        assert result["status"] == "sent"

    def test_ses_send_email_multiple_recipients(self, ses_client):
        """Test email sending to multiple recipients."""
        ses_client._client.send_email.return_value = {
            "MessageId": "test-id"
        }

        recipients = [f"user{i}@example.com" for i in range(50)]
        result = ses_client.send_email(
            to_addresses=recipients, subject="Test", body_text="Test body"
        )

        assert result["status"] == "sent"
        assert len(result["to_addresses"]) == 50