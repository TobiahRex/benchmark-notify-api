"""Tests for the Notification service (business logic).

Owner: backend-engineer
Tests: 5
Files: service.py
"""

from notify_api.repository import create_notification
from notify_api.service import (
    create_notification_service,
    get_unread_notifications,
    mark_notification_read_service,
    bulk_mark_read,
    count_by_priority,
)


def test_create_notification_service(db_session):
    """Service should create a notification with validated fields."""
    notif = create_notification_service(
        db_session,
        title="New task",
        message="You have a new task assigned",
        priority="high",
        role="backend-engineer",
    )
    assert notif.id is not None
    assert notif.title == "New task"
    assert notif.priority == "high"


def test_get_unread_notifications(db_session):
    """Should return only unread notifications for a role."""
    create_notification(db_session, title="A", message="a", priority="normal", role="architect")
    create_notification(db_session, title="B", message="b", priority="normal", role="architect")
    n3 = create_notification(db_session, title="C", message="c", priority="normal", role="architect")
    # Mark one as read
    n3.is_read = True
    db_session.commit()

    unread = get_unread_notifications(db_session, role="architect")
    assert len(unread) == 2
    assert all(not n.is_read for n in unread)


def test_mark_notification_read_service(db_session):
    """Service should mark a notification as read and return it."""
    notif = create_notification(
        db_session, title="X", message="x", priority="normal", role="architect"
    )
    result = mark_notification_read_service(db_session, notif.id)
    assert result.is_read is True


def test_bulk_mark_read(db_session):
    """Should mark multiple notifications as read at once."""
    n1 = create_notification(db_session, title="A", message="a", priority="normal", role="architect")
    n2 = create_notification(db_session, title="B", message="b", priority="normal", role="architect")
    n3 = create_notification(db_session, title="C", message="c", priority="normal", role="architect")

    count = bulk_mark_read(db_session, [n1.id, n2.id, n3.id])
    assert count == 3

    db_session.expire_all()
    assert n1.is_read is True
    assert n2.is_read is True
    assert n3.is_read is True


def test_count_by_priority(db_session):
    """Should return a dict of priority → count for a role."""
    create_notification(db_session, title="A", message="a", priority="high", role="architect")
    create_notification(db_session, title="B", message="b", priority="high", role="architect")
    create_notification(db_session, title="C", message="c", priority="normal", role="architect")
    create_notification(db_session, title="D", message="d", priority="low", role="architect")

    counts = count_by_priority(db_session, role="architect")
    assert counts["high"] == 2
    assert counts["normal"] == 1
    assert counts["low"] == 1
