from sqlalchemy.orm import Session

from notify_api.models import Notification


def create_notification(session: Session, *, title: str, message: str, priority: str, role: str) -> Notification:
    notif = Notification(title=title, message=message, priority=priority, role=role)
    session.add(notif)
    session.commit()
    session.refresh(notif)
    return notif


def get_notification_by_id(session: Session, notification_id: int) -> Notification | None:
    return session.get(Notification, notification_id)


def list_notifications_by_role(session: Session, *, role: str) -> list[Notification]:
    return session.query(Notification).filter(Notification.role == role).all()


def mark_notification_read(session: Session, notification_id: int) -> Notification | None:
    notif = session.get(Notification, notification_id)
    if notif is None:
        return None
    notif.is_read = True
    session.commit()
    session.refresh(notif)
    return notif
