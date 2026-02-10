from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from notify_api.database import get_db
from notify_api.schemas import NotificationCreate, NotificationResponse
from notify_api.service import (
    create_notification_service,
    get_unread_notifications,
    mark_notification_read_service,
)
from notify_api.repository import (
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
