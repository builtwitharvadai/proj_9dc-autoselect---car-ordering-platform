"""
Celery tasks for background notification processing.

This module implements Celery tasks for sending notifications asynchronously,
handling retries, and processing notification queues. Includes task monitoring
and comprehensive error handling.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from celery import Task, shared_task
from celery.exceptions import MaxRetriesExceededError, Retry
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.logging import get_logger
from src.database.connection import get_session
from src.database.models.notification import (
    NotificationChannel,
    NotificationLog,
    NotificationStatus,
    NotificationType,
)
from src.services.notifications.service import (
    NotificationService,
    NotificationServiceError,
    get_notification_service,
)

logger = get_logger(__name__)
settings = get_settings()


class NotificationTask(Task):
    """
    Base task class for notification tasks with retry logic.

    Provides common functionality for notification tasks including
    automatic retries, error handling, and task state management.
    """

    autoretry_for = (NotificationServiceError,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True

    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple,
        kwargs: dict,
        einfo: Any,
    ) -> None:
        """
        Handle task failure.

        Args:
            exc: Exception that caused the failure
            task_id: Unique task identifier
            args: Task positional arguments
            kwargs: Task keyword arguments
            einfo: Exception info object
        """
        logger.error(
            "Notification task failed",
            task_id=task_id,
            exception=str(exc),
            args=args,
            kwargs=kwargs,
            exc_info=einfo,
        )

    def on_retry(
        self,
        exc: Exception,
        task_id: str,
        args: tuple,
        kwargs: dict,
        einfo: Any,
    ) -> None:
        """
        Handle task retry.

        Args:
            exc: Exception that triggered the retry
            task_id: Unique task identifier
            args: Task positional arguments
            kwargs: Task keyword arguments
            einfo: Exception info object
        """
        logger.warning(
            "Notification task retrying",
            task_id=task_id,
            exception=str(exc),
            retry_count=self.request.retries,
            max_retries=self.max_retries,
        )

    def on_success(
        self,
        retval: Any,
        task_id: str,
        args: tuple,
        kwargs: dict,
    ) -> None:
        """
        Handle task success.

        Args:
            retval: Task return value
            task_id: Unique task identifier
            args: Task positional arguments
            kwargs: Task keyword arguments
        """
        logger.info(
            "Notification task completed successfully",
            task_id=task_id,
            result=retval,
        )


@shared_task(
    bind=True,
    base=NotificationTask,
    name="notifications.send_notification",
    time_limit=300,
    soft_time_limit=240,
)
def send_notification_task(
    self: Task,
    user_id: str,
    notification_type: str,
    context: dict[str, Any],
    channels: Optional[list[str]] = None,
    force_send: bool = False,
) -> dict[str, Any]:
    """
    Send notification to user asynchronously.

    Args:
        self: Task instance
        user_id: User ID to send notification to
        notification_type: Type of notification
        context: Template context data
        channels: Specific channels to use (optional)
        force_send: Force send regardless of preferences

    Returns:
        Dictionary containing delivery results

    Raises:
        Retry: If notification sending fails and retries remain
        MaxRetriesExceededError: If all retries exhausted
    """
    logger.info(
        "Processing notification task",
        task_id=self.request.id,
        user_id=user_id,
        notification_type=notification_type,
        channels=channels,
    )

    try:
        # Convert string parameters to proper types
        user_uuid = UUID(user_id)
        notification_type_enum = NotificationType(notification_type)
        channel_enums = (
            [NotificationChannel(ch) for ch in channels] if channels else None
        )

        # Get database session
        async def send_notification() -> dict[str, Any]:
            async with get_session() as session:
                service = get_notification_service(session)
                return await service.send_notification(
                    user_id=user_uuid,
                    notification_type=notification_type_enum,
                    context=context,
                    channels=channel_enums,
                    force_send=force_send,
                )

        # Execute async operation
        import asyncio

        result = asyncio.run(send_notification())

        logger.info(
            "Notification sent successfully",
            task_id=self.request.id,
            user_id=user_id,
            result=result,
        )

        return result

    except NotificationServiceError as e:
        logger.error(
            "Notification service error",
            task_id=self.request.id,
            user_id=user_id,
            error=str(e),
            retry_count=self.request.retries,
        )

        # Retry with exponential backoff
        try:
            raise self.retry(exc=e, countdown=2 ** self.request.retries)
        except MaxRetriesExceededError:
            logger.error(
                "Max retries exceeded for notification",
                task_id=self.request.id,
                user_id=user_id,
            )
            raise

    except Exception as e:
        logger.error(
            "Unexpected error in notification task",
            task_id=self.request.id,
            user_id=user_id,
            error=str(e),
            exc_info=True,
        )
        raise


@shared_task(
    bind=True,
    base=NotificationTask,
    name="notifications.send_bulk_notifications",
    time_limit=600,
    soft_time_limit=540,
)
def send_bulk_notifications_task(
    self: Task,
    notifications: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Send multiple notifications in bulk.

    Args:
        self: Task instance
        notifications: List of notification configurations

    Returns:
        Dictionary containing bulk send results
    """
    logger.info(
        "Processing bulk notification task",
        task_id=self.request.id,
        notification_count=len(notifications),
    )

    results = {
        "total": len(notifications),
        "successful": 0,
        "failed": 0,
        "errors": [],
    }

    for notification in notifications:
        try:
            result = send_notification_task.apply_async(
                kwargs=notification,
                retry=True,
            )
            results["successful"] += 1

        except Exception as e:
            results["failed"] += 1
            results["errors"].append(
                {
                    "notification": notification,
                    "error": str(e),
                }
            )
            logger.error(
                "Failed to queue notification",
                notification=notification,
                error=str(e),
            )

    logger.info(
        "Bulk notification task completed",
        task_id=self.request.id,
        results=results,
    )

    return results


@shared_task(
    bind=True,
    name="notifications.retry_failed_notifications",
    time_limit=1800,
    soft_time_limit=1740,
)
def retry_failed_notifications_task(
    self: Task,
    hours: int = 24,
) -> dict[str, Any]:
    """
    Retry failed notifications from the last N hours.

    Args:
        self: Task instance
        hours: Number of hours to look back

    Returns:
        Dictionary containing retry statistics
    """
    logger.info(
        "Starting failed notification retry task",
        task_id=self.request.id,
        hours=hours,
    )

    async def retry_notifications() -> dict[str, Any]:
        async with get_session() as session:
            service = get_notification_service(session)
            return await service.retry_failed_notifications(hours=hours)

    import asyncio

    result = asyncio.run(retry_notifications())

    logger.info(
        "Failed notification retry completed",
        task_id=self.request.id,
        result=result,
    )

    return result


@shared_task(
    bind=True,
    name="notifications.cleanup_old_logs",
    time_limit=3600,
    soft_time_limit=3540,
)
def cleanup_old_notification_logs_task(
    self: Task,
    days: int = 90,
) -> dict[str, Any]:
    """
    Clean up old notification logs.

    Args:
        self: Task instance
        days: Number of days to retain logs

    Returns:
        Dictionary containing cleanup statistics
    """
    logger.info(
        "Starting notification log cleanup task",
        task_id=self.request.id,
        retention_days=days,
    )

    async def cleanup_logs() -> dict[str, Any]:
        async with get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Delete old logs
            from sqlalchemy import delete, select

            stmt = delete(NotificationLog).where(
                NotificationLog.created_at < cutoff_date
            )

            result = await session.execute(stmt)
            await session.commit()

            deleted_count = result.rowcount

            logger.info(
                "Notification logs cleaned up",
                deleted_count=deleted_count,
                cutoff_date=cutoff_date.isoformat(),
            )

            return {
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
            }

    import asyncio

    result = asyncio.run(cleanup_logs())

    logger.info(
        "Notification log cleanup completed",
        task_id=self.request.id,
        result=result,
    )

    return result


@shared_task(
    bind=True,
    name="notifications.generate_notification_report",
    time_limit=1800,
    soft_time_limit=1740,
)
def generate_notification_report_task(
    self: Task,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """
    Generate notification delivery report.

    Args:
        self: Task instance
        start_date: Report start date (ISO format)
        end_date: Report end date (ISO format)

    Returns:
        Dictionary containing report data
    """
    logger.info(
        "Generating notification report",
        task_id=self.request.id,
        start_date=start_date,
        end_date=end_date,
    )

    async def generate_report() -> dict[str, Any]:
        async with get_session() as session:
            from sqlalchemy import func, select

            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)

            # Query notification statistics
            stmt = (
                select(
                    NotificationLog.notification_type,
                    NotificationLog.channel,
                    NotificationLog.status,
                    func.count(NotificationLog.id).label("count"),
                )
                .where(
                    NotificationLog.created_at >= start,
                    NotificationLog.created_at <= end,
                )
                .group_by(
                    NotificationLog.notification_type,
                    NotificationLog.channel,
                    NotificationLog.status,
                )
            )

            result = await session.execute(stmt)
            rows = result.all()

            # Organize statistics
            report = {
                "period": {
                    "start": start_date,
                    "end": end_date,
                },
                "statistics": {},
            }

            for row in rows:
                notification_type = row.notification_type.value
                channel = row.channel.value
                status = row.status.value
                count = row.count

                if notification_type not in report["statistics"]:
                    report["statistics"][notification_type] = {}

                if channel not in report["statistics"][notification_type]:
                    report["statistics"][notification_type][channel] = {}

                report["statistics"][notification_type][channel][status] = count

            return report

    import asyncio

    result = asyncio.run(generate_report())

    logger.info(
        "Notification report generated",
        task_id=self.request.id,
        report_summary=result,
    )

    return result


@shared_task(
    bind=True,
    name="notifications.monitor_notification_health",
    time_limit=300,
    soft_time_limit=240,
)
def monitor_notification_health_task(
    self: Task,
) -> dict[str, Any]:
    """
    Monitor notification system health.

    Args:
        self: Task instance

    Returns:
        Dictionary containing health metrics
    """
    logger.info(
        "Monitoring notification health",
        task_id=self.request.id,
    )

    async def check_health() -> dict[str, Any]:
        async with get_session() as session:
            from sqlalchemy import func, select

            now = datetime.utcnow()
            last_hour = now - timedelta(hours=1)

            # Check recent notification statistics
            stmt = (
                select(
                    NotificationLog.status,
                    func.count(NotificationLog.id).label("count"),
                )
                .where(NotificationLog.created_at >= last_hour)
                .group_by(NotificationLog.status)
            )

            result = await session.execute(stmt)
            rows = result.all()

            stats = {row.status.value: row.count for row in rows}

            total = sum(stats.values())
            failed = stats.get(NotificationStatus.FAILED.value, 0)
            success_rate = (
                ((total - failed) / total * 100) if total > 0 else 100.0
            )

            health = {
                "timestamp": now.isoformat(),
                "period": "last_hour",
                "total_notifications": total,
                "success_rate": round(success_rate, 2),
                "status_breakdown": stats,
                "healthy": success_rate >= 95.0,
            }

            return health

    import asyncio

    result = asyncio.run(check_health())

    logger.info(
        "Notification health check completed",
        task_id=self.request.id,
        health=result,
    )

    return result