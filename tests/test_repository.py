"""Tests for the Notification repository (CRUD operations).

Owner: data-layer-engineer
Tests: 4
Files: repository.py
"""

from notify_api.models import Notification
from notify_api.repository import (
    create_notification,
    get_notification_by_id,
    list_notifications_by_role,
    mark_notification_read,
)


def test_create_notification(db_session):
    """Should create a notification and return it with an id."""
    notif = create_notification(
        db_session,
        title="Deploy complete",
        message="v1.2.3 deployed to prod",
        priority="high",
        role="backend-engineer",
    )
    assert notif.id is not None
    assert notif.title == "Deploy complete"
    assert notif.priority == "high"
    assert notif.role == "backend-engineer"


def test_get_notification_by_id(db_session):
    """Should retrieve a notification by its id."""
    notif = create_notification(
        db_session,
        title="Test alert",
        message="Something happened",
        priority="normal",
        role="architect",
    )
    found = get_notification_by_id(db_session, notif.id)
    assert found is not None
    assert found.id == notif.id
    assert found.title == "Test alert"


def test_list_notifications_by_role(db_session):
    """Should return only notifications for the specified role."""
    create_notification(db_session, title="A", message="a", priority="normal", role="architect")
    create_notification(db_session, title="B", message="b", priority="normal", role="backend-engineer")
    create_notification(db_session, title="C", message="c", priority="normal", role="architect")

    results = list_notifications_by_role(db_session, role="architect")
    assert len(results) == 2
    assert all(n.role == "architect" for n in results)


def test_mark_notification_read(db_session):
    """Should mark a notification as read."""
    notif = create_notification(
        db_session,
        title="Unread",
        message="Mark me",
        priority="normal",
        role="architect",
    )
    assert notif.is_read is False

    updated = mark_notification_read(db_session, notif.id)
    assert updated is not None
    assert updated.is_read is True
