"""
AWS SES and SNS client wrappers with error handling.

This module provides production-ready client wrappers for AWS SES (email) and
SNS (SMS) services with comprehensive error handling, retry logic, and delivery
status tracking.
"""

import logging
import time
from typing import Any, Optional

import boto3
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectionError as BotoConnectionError,
    EndpointConnectionError,
)

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class AWSClientError(Exception):
    """Base exception for AWS client errors."""

    def __init__(self, message: str, service: str, **context: Any) -> None:
        """
        Initialize AWS client error.

        Args:
            message: Error message
            service: AWS service name (SES or SNS)
            **context: Additional error context
        """
        super().__init__(message)
        self.service = service
        self.context = context


class SESClientError(AWSClientError):
    """Exception for SES-specific errors."""

    def __init__(self, message: str, **context: Any) -> None:
        """
        Initialize SES client error.

        Args:
            message: Error message
            **context: Additional error context
        """
        super().__init__(message, service="SES", **context)


class SNSClientError(AWSClientError):
    """Exception for SNS-specific errors."""

    def __init__(self, message: str, **context: Any) -> None:
        """
        Initialize SNS client error.

        Args:
            message: Error message
            **context: Additional error context
        """
        super().__init__(message, service="SNS", **context)


class SESClient:
    """
    AWS SES client wrapper with error handling and retry logic.

    Provides methods for sending emails with delivery tracking and
    comprehensive error handling.
    """

    def __init__(
        self,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: Optional[str] = None,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
    ) -> None:
        """
        Initialize SES client.

        Args:
            aws_access_key_id: AWS access key ID (defaults to settings)
            aws_secret_access_key: AWS secret access key (defaults to settings)
            region_name: AWS region name (defaults to settings)
            max_retries: Maximum number of retry attempts
            retry_backoff: Initial backoff time in seconds for retries
        """
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        self._client = boto3.client(
            "ses",
            aws_access_key_id=aws_access_key_id or settings.aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
            or settings.aws_secret_access_key,
            region_name=region_name or settings.aws_region,
        )

        logger.info(
            "SES client initialized",
            region=region_name or settings.aws_region,
            max_retries=max_retries,
        )

    def send_email(
        self,
        to_addresses: list[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        from_address: Optional[str] = None,
        reply_to_addresses: Optional[list[str]] = None,
        cc_addresses: Optional[list[str]] = None,
        bcc_addresses: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Send email via AWS SES with retry logic.

        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject
            body_text: Plain text email body
            body_html: HTML email body (optional)
            from_address: Sender email address (defaults to settings)
            reply_to_addresses: Reply-to email addresses (optional)
            cc_addresses: CC email addresses (optional)
            bcc_addresses: BCC email addresses (optional)

        Returns:
            Dictionary containing message ID and delivery status

        Raises:
            SESClientError: If email sending fails after retries
        """
        from_address = from_address or settings.ses_from_email

        # Validate email addresses
        if not to_addresses:
            raise SESClientError(
                "At least one recipient email address is required",
                to_addresses=to_addresses,
            )

        # Build email message
        destination = {"ToAddresses": to_addresses}
        if cc_addresses:
            destination["CcAddresses"] = cc_addresses
        if bcc_addresses:
            destination["BccAddresses"] = bcc_addresses

        message = {
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {"Text": {"Data": body_text, "Charset": "UTF-8"}},
        }

        if body_html:
            message["Body"]["Html"] = {"Data": body_html, "Charset": "UTF-8"}

        # Prepare send parameters
        send_params: dict[str, Any] = {
            "Source": from_address,
            "Destination": destination,
            "Message": message,
        }

        if reply_to_addresses:
            send_params["ReplyToAddresses"] = reply_to_addresses

        # Send email with retry logic
        last_exception: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    "Sending email via SES",
                    attempt=attempt + 1,
                    to_addresses=to_addresses,
                    subject=subject,
                    from_address=from_address,
                )

                response = self._client.send_email(**send_params)

                message_id = response["MessageId"]
                logger.info(
                    "Email sent successfully via SES",
                    message_id=message_id,
                    to_addresses=to_addresses,
                )

                return {
                    "message_id": message_id,
                    "status": "sent",
                    "to_addresses": to_addresses,
                    "from_address": from_address,
                    "subject": subject,
                }

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                error_message = e.response.get("Error", {}).get(
                    "Message", str(e)
                )

                logger.warning(
                    "SES client error",
                    attempt=attempt + 1,
                    error_code=error_code,
                    error_message=error_message,
                    to_addresses=to_addresses,
                )

                last_exception = e

                # Don't retry on certain errors
                if error_code in [
                    "MessageRejected",
                    "MailFromDomainNotVerified",
                    "ConfigurationSetDoesNotExist",
                ]:
                    raise SESClientError(
                        f"SES error: {error_message}",
                        error_code=error_code,
                        to_addresses=to_addresses,
                    ) from e

                # Retry on throttling and temporary errors
                if attempt < self.max_retries - 1:
                    backoff_time = self.retry_backoff * (2**attempt)
                    logger.info(
                        "Retrying SES send after backoff",
                        backoff_seconds=backoff_time,
                        attempt=attempt + 1,
                    )
                    time.sleep(backoff_time)

            except (
                BotoConnectionError,
                EndpointConnectionError,
                BotoCoreError,
            ) as e:
                logger.warning(
                    "SES connection error",
                    attempt=attempt + 1,
                    error=str(e),
                    to_addresses=to_addresses,
                )

                last_exception = e

                if attempt < self.max_retries - 1:
                    backoff_time = self.retry_backoff * (2**attempt)
                    logger.info(
                        "Retrying SES send after connection error",
                        backoff_seconds=backoff_time,
                        attempt=attempt + 1,
                    )
                    time.sleep(backoff_time)

        # All retries exhausted
        raise SESClientError(
            f"Failed to send email after {self.max_retries} attempts",
            to_addresses=to_addresses,
            last_error=str(last_exception),
        ) from last_exception

    def verify_email_identity(self, email_address: str) -> dict[str, Any]:
        """
        Verify email identity for sending.

        Args:
            email_address: Email address to verify

        Returns:
            Dictionary containing verification status

        Raises:
            SESClientError: If verification request fails
        """
        try:
            logger.info("Verifying email identity", email_address=email_address)

            self._client.verify_email_identity(EmailAddress=email_address)

            logger.info(
                "Email identity verification initiated",
                email_address=email_address,
            )

            return {
                "email_address": email_address,
                "status": "verification_sent",
            }

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(
                "Failed to verify email identity",
                email_address=email_address,
                error_code=error_code,
                error_message=error_message,
            )

            raise SESClientError(
                f"Failed to verify email identity: {error_message}",
                error_code=error_code,
                email_address=email_address,
            ) from e


class SNSClient:
    """
    AWS SNS client wrapper with error handling and retry logic.

    Provides methods for sending SMS messages with delivery tracking and
    comprehensive error handling.
    """

    def __init__(
        self,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: Optional[str] = None,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
    ) -> None:
        """
        Initialize SNS client.

        Args:
            aws_access_key_id: AWS access key ID (defaults to settings)
            aws_secret_access_key: AWS secret access key (defaults to settings)
            region_name: AWS region name (defaults to settings)
            max_retries: Maximum number of retry attempts
            retry_backoff: Initial backoff time in seconds for retries
        """
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        self._client = boto3.client(
            "sns",
            aws_access_key_id=aws_access_key_id or settings.aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
            or settings.aws_secret_access_key,
            region_name=region_name or settings.aws_region,
        )

        logger.info(
            "SNS client initialized",
            region=region_name or settings.aws_region,
            max_retries=max_retries,
        )

    def send_sms(
        self,
        phone_number: str,
        message: str,
        sender_id: Optional[str] = None,
        message_type: str = "Transactional",
    ) -> dict[str, Any]:
        """
        Send SMS via AWS SNS with retry logic.

        Args:
            phone_number: Recipient phone number in E.164 format
            message: SMS message text
            sender_id: Sender ID (optional, up to 11 alphanumeric characters)
            message_type: Message type ('Transactional' or 'Promotional')

        Returns:
            Dictionary containing message ID and delivery status

        Raises:
            SNSClientError: If SMS sending fails after retries
        """
        # Validate phone number format
        if not phone_number.startswith("+"):
            raise SNSClientError(
                "Phone number must be in E.164 format (e.g., +1234567890)",
                phone_number=phone_number,
            )

        # Validate message type
        if message_type not in ["Transactional", "Promotional"]:
            raise SNSClientError(
                "Message type must be 'Transactional' or 'Promotional'",
                message_type=message_type,
            )

        # Prepare message attributes
        message_attributes = {
            "AWS.SNS.SMS.SMSType": {
                "DataType": "String",
                "StringValue": message_type,
            }
        }

        if sender_id:
            message_attributes["AWS.SNS.SMS.SenderID"] = {
                "DataType": "String",
                "StringValue": sender_id,
            }

        # Send SMS with retry logic
        last_exception: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    "Sending SMS via SNS",
                    attempt=attempt + 1,
                    phone_number=phone_number,
                    message_type=message_type,
                )

                response = self._client.publish(
                    PhoneNumber=phone_number,
                    Message=message,
                    MessageAttributes=message_attributes,
                )

                message_id = response["MessageId"]
                logger.info(
                    "SMS sent successfully via SNS",
                    message_id=message_id,
                    phone_number=phone_number,
                )

                return {
                    "message_id": message_id,
                    "status": "sent",
                    "phone_number": phone_number,
                    "message_type": message_type,
                }

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                error_message = e.response.get("Error", {}).get(
                    "Message", str(e)
                )

                logger.warning(
                    "SNS client error",
                    attempt=attempt + 1,
                    error_code=error_code,
                    error_message=error_message,
                    phone_number=phone_number,
                )

                last_exception = e

                # Don't retry on certain errors
                if error_code in [
                    "InvalidParameter",
                    "InvalidParameterValue",
                    "OptedOut",
                ]:
                    raise SNSClientError(
                        f"SNS error: {error_message}",
                        error_code=error_code,
                        phone_number=phone_number,
                    ) from e

                # Retry on throttling and temporary errors
                if attempt < self.max_retries - 1:
                    backoff_time = self.retry_backoff * (2**attempt)
                    logger.info(
                        "Retrying SNS send after backoff",
                        backoff_seconds=backoff_time,
                        attempt=attempt + 1,
                    )
                    time.sleep(backoff_time)

            except (
                BotoConnectionError,
                EndpointConnectionError,
                BotoCoreError,
            ) as e:
                logger.warning(
                    "SNS connection error",
                    attempt=attempt + 1,
                    error=str(e),
                    phone_number=phone_number,
                )

                last_exception = e

                if attempt < self.max_retries - 1:
                    backoff_time = self.retry_backoff * (2**attempt)
                    logger.info(
                        "Retrying SNS send after connection error",
                        backoff_seconds=backoff_time,
                        attempt=attempt + 1,
                    )
                    time.sleep(backoff_time)

        # All retries exhausted
        raise SNSClientError(
            f"Failed to send SMS after {self.max_retries} attempts",
            phone_number=phone_number,
            last_error=str(last_exception),
        ) from last_exception

    def check_opt_out_status(self, phone_number: str) -> dict[str, Any]:
        """
        Check if phone number has opted out of SMS.

        Args:
            phone_number: Phone number in E.164 format

        Returns:
            Dictionary containing opt-out status

        Raises:
            SNSClientError: If status check fails
        """
        try:
            logger.info(
                "Checking SMS opt-out status", phone_number=phone_number
            )

            response = self._client.check_if_phone_number_is_opted_out(
                phoneNumber=phone_number
            )

            is_opted_out = response.get("isOptedOut", False)

            logger.info(
                "SMS opt-out status retrieved",
                phone_number=phone_number,
                is_opted_out=is_opted_out,
            )

            return {
                "phone_number": phone_number,
                "is_opted_out": is_opted_out,
            }

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(
                "Failed to check SMS opt-out status",
                phone_number=phone_number,
                error_code=error_code,
                error_message=error_message,
            )

            raise SNSClientError(
                f"Failed to check opt-out status: {error_message}",
                error_code=error_code,
                phone_number=phone_number,
            ) from e


def get_ses_client(
    max_retries: int = 3, retry_backoff: float = 1.0
) -> SESClient:
    """
    Get SES client instance.

    Args:
        max_retries: Maximum number of retry attempts
        retry_backoff: Initial backoff time in seconds for retries

    Returns:
        Configured SES client instance
    """
    return SESClient(max_retries=max_retries, retry_backoff=retry_backoff)


def get_sns_client(
    max_retries: int = 3, retry_backoff: float = 1.0
) -> SNSClient:
    """
    Get SNS client instance.

    Args:
        max_retries: Maximum number of retry attempts
        retry_backoff: Initial backoff time in seconds for retries

    Returns:
        Configured SNS client instance
    """
    return SNSClient(max_retries=max_retries, retry_backoff=retry_backoff)