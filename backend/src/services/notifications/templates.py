"""
Notification template engine with Jinja2 for email and SMS rendering.

This module provides a production-ready template engine for rendering notification
templates with variable substitution, validation, and error handling.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import (
    Environment,
    FileSystemLoader,
    Template,
    TemplateError,
    TemplateNotFound,
    select_autoescape,
)

logger = logging.getLogger(__name__)


class TemplateEngineError(Exception):
    """Base exception for template engine errors."""

    def __init__(self, message: str, template_name: Optional[str] = None):
        super().__init__(message)
        self.template_name = template_name


class TemplateNotFoundError(TemplateEngineError):
    """Raised when a template cannot be found."""

    pass


class TemplateRenderError(TemplateEngineError):
    """Raised when template rendering fails."""

    pass


class TemplateValidationError(TemplateEngineError):
    """Raised when template validation fails."""

    pass


class TemplateEngine:
    """
    Template engine for rendering notification templates.

    Provides methods for loading, rendering, and validating email and SMS
    templates using Jinja2.
    """

    def __init__(
        self,
        template_dir: Optional[str] = None,
        enable_autoescape: bool = True,
        cache_size: int = 400,
    ):
        """
        Initialize the template engine.

        Args:
            template_dir: Directory containing template files. Defaults to
                         'templates/notifications' relative to this file.
            enable_autoescape: Enable autoescaping for HTML templates.
            cache_size: Size of the template cache.
        """
        if template_dir is None:
            template_dir = str(
                Path(__file__).parent.parent.parent.parent
                / "templates"
                / "notifications"
            )

        self.template_dir = Path(template_dir)
        self.cache_size = cache_size

        # Create template directory if it doesn't exist
        self.template_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]) if enable_autoescape else False,
            cache_size=cache_size,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.env.filters["currency"] = self._format_currency
        self.env.filters["date"] = self._format_date

        logger.info(
            "Template engine initialized",
            extra={
                "template_dir": str(self.template_dir),
                "cache_size": cache_size,
                "autoescape": enable_autoescape,
            },
        )

    def render_email(
        self,
        template_name: str,
        context: Dict[str, Any],
        validate: bool = True,
    ) -> Dict[str, str]:
        """
        Render an email template.

        Args:
            template_name: Name of the template file (without extension).
            context: Dictionary of variables to substitute in the template.
            validate: Whether to validate the context before rendering.

        Returns:
            Dictionary containing 'subject', 'html_body', and optionally 'text_body'.

        Raises:
            TemplateNotFoundError: If the template cannot be found.
            TemplateRenderError: If rendering fails.
            TemplateValidationError: If context validation fails.
        """
        if validate:
            self._validate_context(context, template_name)

        try:
            # Render subject
            subject_template = self._load_template(f"{template_name}_subject.txt")
            subject = subject_template.render(**context).strip()

            # Render HTML body
            html_template = self._load_template(f"{template_name}.html")
            html_body = html_template.render(**context)

            # Try to render text body if it exists
            text_body = None
            try:
                text_template = self._load_template(f"{template_name}.txt")
                text_body = text_template.render(**context)
            except TemplateNotFoundError:
                logger.debug(
                    "Text template not found, using HTML only",
                    extra={"template_name": template_name},
                )

            result = {
                "subject": subject,
                "html_body": html_body,
            }

            if text_body:
                result["text_body"] = text_body

            logger.info(
                "Email template rendered successfully",
                extra={
                    "template_name": template_name,
                    "has_text_body": text_body is not None,
                },
            )

            return result

        except TemplateNotFound as e:
            logger.error(
                "Email template not found",
                extra={"template_name": template_name, "error": str(e)},
            )
            raise TemplateNotFoundError(
                f"Email template not found: {template_name}",
                template_name=template_name,
            ) from e
        except TemplateError as e:
            logger.error(
                "Email template rendering failed",
                extra={
                    "template_name": template_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise TemplateRenderError(
                f"Failed to render email template: {str(e)}",
                template_name=template_name,
            ) from e

    def render_sms(
        self,
        template_name: str,
        context: Dict[str, Any],
        validate: bool = True,
    ) -> str:
        """
        Render an SMS template.

        Args:
            template_name: Name of the template file (without extension).
            context: Dictionary of variables to substitute in the template.
            validate: Whether to validate the context before rendering.

        Returns:
            Rendered SMS message text.

        Raises:
            TemplateNotFoundError: If the template cannot be found.
            TemplateRenderError: If rendering fails.
            TemplateValidationError: If context validation fails.
        """
        if validate:
            self._validate_context(context, template_name)

        try:
            template = self._load_template(f"{template_name}_sms.txt")
            message = template.render(**context).strip()

            logger.info(
                "SMS template rendered successfully",
                extra={
                    "template_name": template_name,
                    "message_length": len(message),
                },
            )

            return message

        except TemplateNotFound as e:
            logger.error(
                "SMS template not found",
                extra={"template_name": template_name, "error": str(e)},
            )
            raise TemplateNotFoundError(
                f"SMS template not found: {template_name}",
                template_name=template_name,
            ) from e
        except TemplateError as e:
            logger.error(
                "SMS template rendering failed",
                extra={
                    "template_name": template_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise TemplateRenderError(
                f"Failed to render SMS template: {str(e)}",
                template_name=template_name,
            ) from e

    def validate_template(self, template_name: str, template_type: str = "email") -> bool:
        """
        Validate that a template exists and can be loaded.

        Args:
            template_name: Name of the template file (without extension).
            template_type: Type of template ('email' or 'sms').

        Returns:
            True if the template is valid.

        Raises:
            TemplateNotFoundError: If the template cannot be found.
            TemplateValidationError: If the template is invalid.
        """
        try:
            if template_type == "email":
                # Check for required email templates
                self._load_template(f"{template_name}_subject.txt")
                self._load_template(f"{template_name}.html")
            elif template_type == "sms":
                self._load_template(f"{template_name}_sms.txt")
            else:
                raise TemplateValidationError(
                    f"Invalid template type: {template_type}",
                    template_name=template_name,
                )

            logger.info(
                "Template validation successful",
                extra={
                    "template_name": template_name,
                    "template_type": template_type,
                },
            )

            return True

        except TemplateNotFound as e:
            logger.error(
                "Template validation failed - template not found",
                extra={
                    "template_name": template_name,
                    "template_type": template_type,
                    "error": str(e),
                },
            )
            raise TemplateNotFoundError(
                f"Template not found: {template_name}",
                template_name=template_name,
            ) from e
        except TemplateError as e:
            logger.error(
                "Template validation failed - invalid template",
                extra={
                    "template_name": template_name,
                    "template_type": template_type,
                    "error": str(e),
                },
            )
            raise TemplateValidationError(
                f"Invalid template: {str(e)}",
                template_name=template_name,
            ) from e

    def _load_template(self, template_path: str) -> Template:
        """
        Load a template from the template directory.

        Args:
            template_path: Path to the template file relative to template_dir.

        Returns:
            Loaded Jinja2 template.

        Raises:
            TemplateNotFound: If the template cannot be found.
        """
        try:
            return self.env.get_template(template_path)
        except TemplateNotFound as e:
            logger.debug(
                "Template not found",
                extra={"template_path": template_path},
            )
            raise e

    def _validate_context(self, context: Dict[str, Any], template_name: str) -> None:
        """
        Validate the context dictionary.

        Args:
            context: Context dictionary to validate.
            template_name: Name of the template for error reporting.

        Raises:
            TemplateValidationError: If validation fails.
        """
        if not isinstance(context, dict):
            raise TemplateValidationError(
                "Context must be a dictionary",
                template_name=template_name,
            )

        # Check for None values in required fields
        none_keys = [k for k, v in context.items() if v is None]
        if none_keys:
            logger.warning(
                "Context contains None values",
                extra={
                    "template_name": template_name,
                    "none_keys": none_keys,
                },
            )

    @staticmethod
    def _format_currency(value: float) -> str:
        """Format a number as currency."""
        return f"${value:,.2f}"

    @staticmethod
    def _format_date(value: str) -> str:
        """Format a date string."""
        from datetime import datetime

        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.strftime("%B %d, %Y")
        except (ValueError, AttributeError):
            return value


def get_template_engine(
    template_dir: Optional[str] = None,
    enable_autoescape: bool = True,
    cache_size: int = 400,
) -> TemplateEngine:
    """
    Factory function to create a template engine instance.

    Args:
        template_dir: Directory containing template files.
        enable_autoescape: Enable autoescaping for HTML templates.
        cache_size: Size of the template cache.

    Returns:
        Configured TemplateEngine instance.
    """
    return TemplateEngine(
        template_dir=template_dir,
        enable_autoescape=enable_autoescape,
        cache_size=cache_size,
    )