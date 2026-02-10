"""Tests for the Notification SQLAlchemy model.

Owner: data-layer-engineer
Tests: 5
Files: models.py, database.py
"""

from datetime import datetime

from notify_api.models import Notification
from notify_api.database import Base


def test_notification_model_exists():
    """Notification class should be importable and be a SQLAlchemy model."""
    assert hasattr(Notification, "__tablename__")


def test_notification_table_name():
    """Table name should be 'notifications'."""
    assert Notification.__tablename__ == "notifications"


def test_notification_has_required_columns():
    """Model should have all required columns."""
    column_names = [c.name for c in Notification.__table__.columns]
    assert "id" in column_names
    assert "title" in column_names
    assert "message" in column_names
    assert "priority" in column_names
    assert "role" in column_names
    assert "is_read" in column_names
    assert "created_at" in column_names


def test_notification_default_values(db_session):
    """Default values should be set for priority, is_read, and created_at."""
    notif = Notification(title="Test", message="Hello", role="architect")
    db_session.add(notif)
    db_session.commit()
    db_session.refresh(notif)

    assert notif.priority == "normal"
    assert notif.is_read is False
    assert isinstance(notif.created_at, datetime)


def test_notification_inherits_base():
    """Notification should inherit from the declarative Base."""
    assert issubclass(Notification, Base)
