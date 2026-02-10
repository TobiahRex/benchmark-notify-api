"""Tests for delivery channel CRUD, routing, and status endpoint.

Owner: test-engineer
Tests: 10
Files: models.py, repository.py, service.py, routes.py, schemas.py

Covers:
  - Channel CRUD (create email/webhook, list active, deactivate)
  - Delivery routing (single/multi channel, skip deactivated, verify DeliveryLog)
  - Status endpoint (aggregation counts, 404 handling)
"""

from notify_api.models import DeliveryChannel, DeliveryLog, Notification
from notify_api.repository import (
    create_channel,
    get_channel_by_id,
    list_active_channels,
    deactivate_channel,
    create_delivery_log,
    get_delivery_logs_by_notification,
)
from notify_api.service import deliver_notification, get_delivery_status


# ---------------------------------------------------------------------------
# Channel CRUD (repository layer)
# ---------------------------------------------------------------------------


def test_create_email_channel(db_session):
    """Should create an email delivery channel with config."""
    channel = create_channel(
        db_session,
        name="Team Email",
        channel_type="email",
        config={"smtp_host": "smtp.example.com", "smtp_port": 587, "recipient": "team@example.com"},
    )
    assert channel.id is not None
    assert channel.name == "Team Email"
    assert channel.channel_type == "email"
    assert channel.config["smtp_host"] == "smtp.example.com"
    assert channel.is_active is True


def test_create_webhook_channel(db_session):
    """Should create a webhook delivery channel with config."""
    channel = create_channel(
        db_session,
        name="Slack Webhook",
        channel_type="webhook",
        config={"url": "https://hooks.slack.com/services/T00/B00/xxx"},
    )
    assert channel.id is not None
    assert channel.name == "Slack Webhook"
    assert channel.channel_type == "webhook"
    assert channel.config["url"] == "https://hooks.slack.com/services/T00/B00/xxx"
    assert channel.is_active is True


def test_list_active_channels(db_session):
    """Should return only active channels."""
    create_channel(db_session, name="Active", channel_type="email", config={})
    ch2 = create_channel(db_session, name="Inactive", channel_type="webhook", config={})
    create_channel(db_session, name="Also Active", channel_type="webhook", config={})

    # Deactivate one channel
    deactivate_channel(db_session, ch2.id)

    active = list_active_channels(db_session)
    assert len(active) == 2
    assert all(c.is_active for c in active)


def test_deactivate_channel(db_session):
    """Should set is_active to False on a channel."""
    channel = create_channel(db_session, name="To Remove", channel_type="email", config={})
    assert channel.is_active is True

    updated = deactivate_channel(db_session, channel.id)
    assert updated is not None
    assert updated.is_active is False


# ---------------------------------------------------------------------------
# Delivery routing (service layer)
# ---------------------------------------------------------------------------


def _make_notification(db_session, title="Test Alert"):
    """Helper to create a notification for delivery tests."""
    from notify_api.repository import create_notification

    return create_notification(
        db_session,
        title=title,
        message="Something important happened",
        priority="high",
        role="backend-engineer",
    )


def test_deliver_to_single_channel(db_session):
    """Delivering a notification to one active channel creates one DeliveryLog."""
    notif = _make_notification(db_session)
    create_channel(db_session, name="Email", channel_type="email", config={})

    logs = deliver_notification(db_session, notif.id)
    assert len(logs) == 1
    assert logs[0].notification_id == notif.id
    assert logs[0].status in ("pending", "sent")


def test_deliver_to_multiple_channels(db_session):
    """Delivering a notification routes to all active channels."""
    notif = _make_notification(db_session)
    create_channel(db_session, name="Email", channel_type="email", config={})
    create_channel(db_session, name="Webhook", channel_type="webhook", config={"url": "https://example.com/hook"})

    logs = deliver_notification(db_session, notif.id)
    assert len(logs) == 2
    channel_types = {log.channel.channel_type for log in logs}
    assert channel_types == {"email", "webhook"}


def test_skip_deactivated_channels(db_session):
    """Delivery should skip deactivated channels."""
    notif = _make_notification(db_session)
    create_channel(db_session, name="Active Email", channel_type="email", config={})
    inactive = create_channel(db_session, name="Dead Webhook", channel_type="webhook", config={})
    deactivate_channel(db_session, inactive.id)

    logs = deliver_notification(db_session, notif.id)
    assert len(logs) == 1
    assert logs[0].channel.channel_type == "email"


def test_delivery_creates_log_entries(db_session):
    """DeliveryLog entries should have correct fields after delivery."""
    notif = _make_notification(db_session)
    channel = create_channel(db_session, name="Webhook", channel_type="webhook", config={"url": "https://example.com"})

    logs = deliver_notification(db_session, notif.id)
    assert len(logs) == 1

    log = logs[0]
    assert log.notification_id == notif.id
    assert log.channel_id == channel.id
    assert log.attempt_count >= 0
    assert log.max_attempts == 3
    assert log.status in ("pending", "sent")

    # Verify persisted in DB
    db_logs = get_delivery_logs_by_notification(db_session, notif.id)
    assert len(db_logs) == 1


# ---------------------------------------------------------------------------
# Status endpoint (API layer)
# ---------------------------------------------------------------------------


def test_delivery_status_aggregation(client):
    """GET /notifications/{id}/delivery-status should return aggregated counts."""
    # Create notification via API
    resp = client.post(
        "/notifications",
        json={"title": "Deploy", "message": "v2 deployed", "priority": "high", "role": "architect"},
    )
    notif_id = resp.json()["id"]

    # Create channels via API
    client.post("/channels", json={"name": "Email", "channel_type": "email", "config": {}})
    client.post(
        "/channels",
        json={"name": "Webhook", "channel_type": "webhook", "config": {"url": "https://example.com/hook"}},
    )

    # Trigger delivery
    deliver_resp = client.post(f"/notifications/{notif_id}/deliver")
    assert deliver_resp.status_code == 202

    # Check delivery status
    status_resp = client.get(f"/notifications/{notif_id}/delivery-status")
    assert status_resp.status_code == 200

    data = status_resp.json()
    assert data["notification_id"] == notif_id
    assert data["total_channels"] == 2
    assert isinstance(data["deliveries"], list)
    assert len(data["deliveries"]) == 2


def test_delivery_status_404_missing_notification(client):
    """GET /notifications/99999/delivery-status should return 404."""
    response = client.get("/notifications/99999/delivery-status")
    assert response.status_code == 404
    assert "detail" in response.json()
