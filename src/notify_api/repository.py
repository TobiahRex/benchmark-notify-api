# Notification repository (CRUD) — to be implemented by data-layer-engineer
#
# Minimal stubs so tests can import. Tests will fail on return values.
# The data-layer-engineer should replace these with real implementations.


def create_notification(session, *, title, message, priority, role):
    """Create a notification record. Stub — replace with real implementation."""
    raise NotImplementedError("create_notification not implemented")


def get_notification_by_id(session, notification_id):
    """Get a notification by id. Stub — replace with real implementation."""
    raise NotImplementedError("get_notification_by_id not implemented")


def list_notifications_by_role(session, *, role):
    """List notifications for a role. Stub — replace with real implementation."""
    raise NotImplementedError("list_notifications_by_role not implemented")


def mark_notification_read(session, notification_id):
    """Mark a notification as read. Stub — replace with real implementation."""
    raise NotImplementedError("mark_notification_read not implemented")
