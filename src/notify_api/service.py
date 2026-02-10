import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from notify_api.models import DeliveryLog, DeliveryStatus, Notification
from notify_api.repository import (
    create_delivery_log,
    create_notification,
    get_delivery_log_by_id,
    get_delivery_logs_by_notification,
    get_notification_by_id,
    get_pending_retries,
    increment_delivery_attempt,
    list_active_channels,
    list_all_channels,
    mark_notification_read,
    update_delivery_log_status,
)


def create_notification_service(
    session: Session, *, title: str, message: str, priority: str, role: str
) -> Notification:
    return create_notification(
        session, title=title, message=message, priority=priority, role=role
    )


def get_unread_notifications(session: Session, *, role: str) -> list[Notification]:
    return (
        session.query(Notification)
        .filter(Notification.role == role, Notification.is_read == False)
        .all()
    )


def mark_notification_read_service(
    session: Session, notification_id: int
) -> Notification | None:
    return mark_notification_read(session, notification_id)


def bulk_mark_read(session: Session, notification_ids: list[int]) -> int:
    count = (
        session.query(Notification)
        .filter(Notification.id.in_(notification_ids))
        .update({Notification.is_read: True}, synchronize_session="fetch")
    )
    session.commit()
    return count


def count_by_priority(session: Session, *, role: str) -> dict[str, int]:
    rows = (
        session.query(Notification.priority, Notification.id)
        .filter(Notification.role == role)
        .all()
    )
    counts: dict[str, int] = {}
    for priority, _ in rows:
        counts[priority] = counts.get(priority, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# DeliveryService
# ---------------------------------------------------------------------------


class DeliveryService:
    """Handles notification delivery with channel routing and retry logic.

    Provides three core capabilities:
      - deliver: Route a notification to all active delivery channels
      - retry_delivery: Retry a failed delivery with exponential backoff
      - get_status: Return aggregated delivery status for a notification

    Retry uses exponential backoff: delay = BASE_DELAY * 2^(attempt - 1)
    Max 3 attempts enforced per delivery log entry.
    """

    MAX_ATTEMPTS: int = 3
    BASE_DELAY_SECONDS: float = 1.0  # Backoff: 1s, 2s, 4s

    @staticmethod
    def deliver(session: Session, notification_id: int) -> list[DeliveryLog]:
        """Route a notification to all active delivery channels.

        Creates a DeliveryLog entry for each active channel with status
        ``pending`` and ``attempt_count=0``.  Returns the list of created
        log entries.
        """
        channels = list_active_channels(session)
        logs: list[DeliveryLog] = []
        for channel in channels:
            log = create_delivery_log(
                session,
                notification_id=notification_id,
                channel_id=channel.id,
                status="pending",
                max_attempts=DeliveryService.MAX_ATTEMPTS,
            )
            logs.append(log)
        return logs

    @staticmethod
    def retry_delivery(
        session: Session, log_id: uuid.UUID | str
    ) -> DeliveryLog | None:
        """Retry a failed delivery with exponential backoff.

        Returns the updated DeliveryLog on success, or ``None`` when:
          - The log does not exist
          - Max attempts have already been reached

        The backoff schedule is ``BASE_DELAY * 2^(attempt - 1)`` seconds.
        Each call increments ``attempt_count``, sets ``last_attempt_at``,
        computes ``next_retry_at``, and marks the status as ``retried``.
        """
        log = get_delivery_log_by_id(session, log_id)
        if log is None:
            return None

        if log.attempt_count >= log.max_attempts:
            return None  # Max attempts exhausted

        # Increment the attempt counter (sets last_attempt_at too)
        log = increment_delivery_attempt(session, log_id)
        if log is None:
            return None

        # Calculate next retry with exponential backoff
        delay = DeliveryService.BASE_DELAY_SECONDS * (
            2 ** (log.attempt_count - 1)
        )
        log.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
        log.status = DeliveryStatus.retried
        session.commit()
        session.refresh(log)
        return log

    @staticmethod
    def get_status(session: Session, notification_id: int) -> dict | None:
        """Return aggregated delivery status for a notification.

        Returns ``None`` if the notification does not exist.
        """
        notif = get_notification_by_id(session, notification_id)
        if notif is None:
            return None

        logs = get_delivery_logs_by_notification(session, notification_id)
        delivered = 0
        failed = 0
        pending = 0
        deliveries = []
        for log in logs:
            status_val = (
                log.status.value
                if isinstance(log.status, DeliveryStatus)
                else log.status
            )
            if status_val == "sent":
                delivered += 1
            elif status_val == "failed":
                failed += 1
            elif status_val in ("pending", "retried"):
                pending += 1
            deliveries.append(
                {
                    "log_id": str(log.id),
                    "channel_id": str(log.channel_id),
                    "channel_name": log.channel.name if log.channel else None,
                    "channel_type": (
                        log.channel.channel_type if log.channel else None
                    ),
                    "status": status_val,
                    "attempt_count": log.attempt_count,
                    "max_attempts": log.max_attempts,
                }
            )
        return {
            "notification_id": notification_id,
            "total_channels": len(deliveries),
            "delivered": delivered,
            "failed": failed,
            "pending": pending,
            "deliveries": deliveries,
        }

    @staticmethod
    def process_pending_retries(session: Session) -> list[DeliveryLog]:
        """Retry all failed deliveries that haven't exhausted their attempts.

        Returns the list of DeliveryLog entries that were retried.
        """
        pending = get_pending_retries(session)
        retried: list[DeliveryLog] = []
        for log in pending:
            result = DeliveryService.retry_delivery(session, log.id)
            if result is not None:
                retried.append(result)
        return retried

    @staticmethod
    def list_channels(session: Session, active_only: bool = False):
        """List delivery channels, optionally filtering to active only."""
        if active_only:
            return list_active_channels(session)
        return list_all_channels(session)


# ---------------------------------------------------------------------------
# Backward-compatible functional API (delegates to DeliveryService)
# ---------------------------------------------------------------------------


def deliver_notification(
    session: Session, notification_id: int
) -> list[DeliveryLog]:
    """Route a notification to all active delivery channels."""
    return DeliveryService.deliver(session, notification_id)


def get_delivery_status(session: Session, notification_id: int) -> dict | None:
    """Return aggregated delivery status for a notification."""
    return DeliveryService.get_status(session, notification_id)
