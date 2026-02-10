from sqlalchemy.orm import Session

from notify_api.models import DeliveryLog, Notification
from notify_api.repository import (
    create_delivery_log,
    create_notification,
    get_delivery_logs_by_notification,
    get_notification_by_id,
    list_active_channels,
    mark_notification_read,
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
# Delivery
# ---------------------------------------------------------------------------


def deliver_notification(session: Session, notification_id: int) -> list[DeliveryLog]:
    """Route a notification to all active delivery channels.

    Creates a DeliveryLog entry for each active channel. Returns the list of
    created log entries.
    """
    channels = list_active_channels(session)
    logs: list[DeliveryLog] = []
    for channel in channels:
        log = create_delivery_log(
            session,
            notification_id=notification_id,
            channel_id=channel.id,
            status="pending",
        )
        logs.append(log)
    return logs


def get_delivery_status(session: Session, notification_id: int) -> dict | None:
    """Return aggregated delivery status for a notification.

    Returns None if the notification does not exist.
    """
    notif = get_notification_by_id(session, notification_id)
    if notif is None:
        return None

    logs = get_delivery_logs_by_notification(session, notification_id)
    deliveries = []
    for log in logs:
        deliveries.append(
            {
                "log_id": str(log.id),
                "channel_id": str(log.channel_id),
                "channel_name": log.channel.name if log.channel else None,
                "channel_type": log.channel.channel_type if log.channel else None,
                "status": log.status,
                "attempt_count": log.attempt_count,
                "max_attempts": log.max_attempts,
            }
        )
    return {
        "notification_id": notification_id,
        "total_channels": len(deliveries),
        "deliveries": deliveries,
    }
