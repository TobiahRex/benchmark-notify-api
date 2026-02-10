from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from notify_api.database import get_db
from notify_api.schemas import (
    ChannelCreate,
    ChannelResponse,
    DeliveryStatusResponse,
    NotificationCreate,
    NotificationResponse,
)
from notify_api.service import (
    DeliveryService,
    create_notification_service,
    deliver_notification,
    get_delivery_status,
    get_unread_notifications,
    mark_notification_read_service,
)
from notify_api.repository import (
    create_channel,
    get_notification_by_id,
    list_notifications_by_role,
)

router = APIRouter()


@router.post("/notifications", response_model=NotificationResponse, status_code=201)
def create_notification(payload: NotificationCreate, db: Session = Depends(get_db)):
    notif = create_notification_service(
        db,
        title=payload.title,
        message=payload.message,
        priority=payload.priority,
        role=payload.role,
    )
    return notif


@router.get("/notifications", response_model=list[NotificationResponse])
def list_notifications(
    role: str = Query(...),
    unread: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    if unread and unread.lower() == "true":
        return get_unread_notifications(db, role=role)
    return list_notifications_by_role(db, role=role)


@router.get("/notifications/{notification_id}", response_model=NotificationResponse)
def get_notification(notification_id: int, db: Session = Depends(get_db)):
    notif = get_notification_by_id(db, notification_id)
    if notif is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif


@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_read(notification_id: int, db: Session = Depends(get_db)):
    notif = mark_notification_read_service(db, notification_id)
    if notif is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif


# ---------------------------------------------------------------------------
# DeliveryChannel endpoints
# ---------------------------------------------------------------------------


@router.post("/channels", response_model=ChannelResponse, status_code=201)
def create_delivery_channel(payload: ChannelCreate, db: Session = Depends(get_db)):
    channel = create_channel(
        db,
        name=payload.name,
        channel_type=payload.channel_type,
        config=payload.config,
    )
    return channel


@router.get("/channels", response_model=list[ChannelResponse])
def list_channels(
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    return DeliveryService.list_channels(db, active_only=active_only)


# ---------------------------------------------------------------------------
# Delivery endpoints
# ---------------------------------------------------------------------------


@router.post("/notifications/{notification_id}/deliver", status_code=202)
def trigger_delivery(notification_id: int, db: Session = Depends(get_db)):
    notif = get_notification_by_id(db, notification_id)
    if notif is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    logs = deliver_notification(db, notification_id)
    return {"notification_id": notification_id, "deliveries_created": len(logs)}


@router.get(
    "/notifications/{notification_id}/delivery-status",
    response_model=DeliveryStatusResponse,
)
def delivery_status(notification_id: int, db: Session = Depends(get_db)):
    result = get_delivery_status(db, notification_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return result
