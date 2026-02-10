# Notification service (business logic) — to be implemented by backend-engineer
#
# Minimal stubs so tests can import. Tests will fail on return values.
# The backend-engineer should replace these with real implementations.


def create_notification_service(session, *, title, message, priority, role):
    """Create a notification with business logic. Stub — replace with real implementation."""
    raise NotImplementedError("create_notification_service not implemented")


def get_unread_notifications(session, *, role):
    """Get unread notifications for a role. Stub — replace with real implementation."""
    raise NotImplementedError("get_unread_notifications not implemented")


def mark_notification_read_service(session, notification_id):
    """Mark a notification as read via service. Stub — replace with real implementation."""
    raise NotImplementedError("mark_notification_read_service not implemented")


def bulk_mark_read(session, notification_ids):
    """Mark multiple notifications as read. Stub — replace with real implementation."""
    raise NotImplementedError("bulk_mark_read not implemented")


def count_by_priority(session, *, role):
    """Count notifications by priority for a role. Stub — replace with real implementation."""
    raise NotImplementedError("count_by_priority not implemented")
