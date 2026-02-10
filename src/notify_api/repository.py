import uuid

from sqlalchemy.orm import Session

from notify_api.models import DeliveryChannel, DeliveryLog, Notification


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


# ---------------------------------------------------------------------------
# DeliveryChannel CRUD
# ---------------------------------------------------------------------------


def create_channel(
    session: Session,
    *,
    name: str,
    channel_type: str,
    config: dict | None = None,
) -> DeliveryChannel:
    channel = DeliveryChannel(
        name=name,
        channel_type=channel_type,
        config=config or {},
    )
    session.add(channel)
    session.commit()
    session.refresh(channel)
    return channel


def get_channel_by_id(session: Session, channel_id: uuid.UUID) -> DeliveryChannel | None:
    return session.get(DeliveryChannel, channel_id)


def list_active_channels(session: Session) -> list[DeliveryChannel]:
    return (
        session.query(DeliveryChannel)
        .filter(DeliveryChannel.is_active == True)
        .all()
    )


def deactivate_channel(session: Session, channel_id: uuid.UUID) -> DeliveryChannel | None:
    channel = session.get(DeliveryChannel, channel_id)
    if channel is None:
        return None
    channel.is_active = False
    session.commit()
    session.refresh(channel)
    return channel


# ---------------------------------------------------------------------------
# DeliveryLog CRUD
# ---------------------------------------------------------------------------


def create_delivery_log(
    session: Session,
    *,
    notification_id: int,
    channel_id: uuid.UUID,
    status: str = "pending",
    attempt_count: int = 0,
    max_attempts: int = 3,
) -> DeliveryLog:
    log = DeliveryLog(
        notification_id=notification_id,
        channel_id=channel_id,
        status=status,
        attempt_count=attempt_count,
        max_attempts=max_attempts,
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


def get_delivery_logs_by_notification(
    session: Session, notification_id: int
) -> list[DeliveryLog]:
    return (
        session.query(DeliveryLog)
        .filter(DeliveryLog.notification_id == notification_id)
        .all()
    )
