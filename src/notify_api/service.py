from sqlalchemy.orm import Session

from notify_api.models import Notification
from notify_api.repository import (
    create_notification,
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
