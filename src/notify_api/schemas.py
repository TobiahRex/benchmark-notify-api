import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class NotificationCreate(BaseModel):
    title: str
    message: str
    priority: str = "normal"
    role: str


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    message: str
    priority: str
    role: str
    is_read: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# DeliveryChannel
# ---------------------------------------------------------------------------


class ChannelCreate(BaseModel):
    name: str
    channel_type: str
    config: dict[str, Any] = {}


class ChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    channel_type: str
    config: dict[str, Any] | None
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------


class DeliveryLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_id: str
    channel_id: str
    channel_name: str | None
    channel_type: str | None
    status: str
    attempt_count: int
    max_attempts: int
    last_attempt_at: datetime | None = None
    error_message: str | None = None


class DeliveryStatusResponse(BaseModel):
    notification_id: int
    total_channels: int
    delivered: int = 0
    failed: int = 0
    pending: int = 0
    deliveries: list[DeliveryLogResponse]
