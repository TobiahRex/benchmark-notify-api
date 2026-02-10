from datetime import datetime
from typing import Optional

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
