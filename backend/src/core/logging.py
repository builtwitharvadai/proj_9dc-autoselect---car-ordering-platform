"""
Structured logging configuration with JSON formatting and request correlation.

This module provides centralized logging configuration with structured JSON
output, request ID correlation, performance logging, and FastAPI integration.
Supports multiple log levels, custom formatters, and context propagation.
"""

import logging
import sys
import time
from contextvars import ContextVar
from typing import Any, Optional
from uuid import uuid4

import structlog
from structlog.types import EventDict, Processor

from src.core.config import get_settings

# Context variables for request correlation
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
user_id_ctx: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


def add_request_id(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Add request ID from context to log event.

    Args:
        logger: Logger instance
        method_name: Log method name
        event_dict: Event dictionary to modify

    Returns:
        Modified event dictionary with request_id
    """
    request_id = request_id_ctx.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def add_user_id(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Add user ID from context to log event.

    Args:
        logger: Logger instance
        method_name: Log method name
        event_dict: Event dictionary to modify

    Returns:
        Modified event dictionary with user_id
    """
    user_id = user_id_ctx.get()
    if user_id:
        event_dict["user_id"] = user_id
    return event_dict


def add_timestamp(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Add ISO format timestamp to log event.

    Args:
        logger: Logger instance
        method_name: Log method name
        event_dict: Event dictionary to modify

    Returns:
        Modified event dictionary with timestamp
    """
    from datetime import datetime, timezone

    event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    return event_dict


def add_log_level(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Add log level to event dictionary.

    Args:
        logger: Logger instance
        method_name: Log method name
        event_dict: Event dictionary to modify

    Returns:
        Modified event dictionary with level
    """
    if method_name == "warn":
        method_name = "warning"
    event_dict["level"] = method_name.upper()
    return event_dict


def add_logger_name(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Add logger name to event dictionary.

    Args:
        logger: Logger instance
        method_name: Log method name
        event_dict: Event dictionary to modify

    Returns:
        Modified event dictionary with logger name
    """
    event_dict["logger"] = logger.name
    return event_dict


def configure_logging() -> None:
    """
    Configure structured logging with JSON formatting.

    Sets up structlog with appropriate processors for development and
    production environments. Configures log levels, formatters, and
    output handlers based on application settings.
    """
    settings = get_settings()

    # Determine processors based on environment
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_timestamp,
        add_log_level,
        add_logger_name,
        add_request_id,
        add_user_id,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Use console renderer for development, JSON for production
    if settings.is_development:
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            )
        )
    else:
        processors.append(structlog.processors.JSONRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )

    # Set log levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger instance
    """
    return structlog.get_logger(name)


def set_request_id(request_id: Optional[str] = None) -> str:
    """
    Set request ID in context for correlation.

    Args:
        request_id: Optional request ID, generates UUID if not provided

    Returns:
        Request ID that was set
    """
    if request_id is None:
        request_id = str(uuid4())
    request_id_ctx.set(request_id)
    return request_id


def get_request_id() -> str:
    """
    Get current request ID from context.

    Returns:
        Current request ID or empty string if not set
    """
    return request_id_ctx.get()


def set_user_id(user_id: Optional[str]) -> None:
    """
    Set user ID in context for correlation.

    Args:
        user_id: User ID to set in context
    """
    user_id_ctx.set(user_id)


def get_user_id() -> Optional[str]:
    """
    Get current user ID from context.

    Returns:
        Current user ID or None if not set
    """
    return user_id_ctx.get()


def clear_context() -> None:
    """
    Clear all context variables.

    Should be called at the end of request processing to prevent
    context leakage between requests.
    """
    request_id_ctx.set("")
    user_id_ctx.set(None)


class PerformanceLogger:
    """
    Context manager for performance logging.

    Logs execution time of code blocks with structured context.
    """

    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        operation: str,
        **context: Any,
    ):
        """
        Initialize performance logger.

        Args:
            logger: Logger instance to use
            operation: Operation name for logging
            **context: Additional context to include in logs
        """
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time: Optional[float] = None

    def __enter__(self) -> "PerformanceLogger":
        """
        Start performance timing.

        Returns:
            Self for context manager protocol
        """
        self.start_time = time.perf_counter()
        self.logger.debug(
            "Operation started",
            operation=self.operation,
            **self.context,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Log performance metrics on exit.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        if self.start_time is None:
            return

        duration_ms = (time.perf_counter() - self.start_time) * 1000

        if exc_type is not None:
            self.logger.error(
                "Operation failed",
                operation=self.operation,
                duration_ms=round(duration_ms, 2),
                error_type=exc_type.__name__,
                **self.context,
            )
        else:
            log_method = self.logger.warning if duration_ms > 500 else self.logger.info
            log_method(
                "Operation completed",
                operation=self.operation,
                duration_ms=round(duration_ms, 2),
                **self.context,
            )


def log_performance(
    logger: structlog.stdlib.BoundLogger,
    operation: str,
    **context: Any,
) -> PerformanceLogger:
    """
    Create performance logger context manager.

    Args:
        logger: Logger instance to use
        operation: Operation name for logging
        **context: Additional context to include in logs

    Returns:
        PerformanceLogger context manager

    Example:
        >>> logger = get_logger(__name__)
        >>> with log_performance(logger, "database_query", table="users"):
        ...     result = db.query(User).all()
    """
    return PerformanceLogger(logger, operation, **context)