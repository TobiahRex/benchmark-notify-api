"""Integration tests for delivery channel CRUD and routing via HTTP API.

Owner: test-engineer
Tests: 14
Files: routes.py, service.py, repository.py, schemas.py, models.py

Covers:
  - Channel creation via POST /channels (email, webhook, defaults, validation)
  - Delivery routing via POST /notifications/{id}/deliver (single, multi, deactivated, 404, empty)
  - End-to-end lifecycle (create notification -> create channels -> deliver -> check status)
  - Edge cases (multiple deliveries accumulate, zero deliveries, status response shape)
"""

from notify_api.repository import deactivate_channel


# ---------------------------------------------------------------------------
# Channel CRUD via API
# ---------------------------------------------------------------------------


def test_create_email_channel_via_api(client):
    """POST /channels should create an email channel and return 201 with correct fields."""
    resp = client.post(
        "/channels",
        json={
            "name": "Ops Email",
            "channel_type": "email",
            "config": {"smtp_host": "mail.example.com", "recipient": "ops@example.com"},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Ops Email"
    assert data["channel_type"] == "email"
    assert data["config"]["smtp_host"] == "mail.example.com"
    assert data["is_active"] is True
    assert "id" in data


def test_create_webhook_channel_via_api(client):
    """POST /channels should create a webhook channel with config."""
    resp = client.post(
        "/channels",
        json={
            "name": "PagerDuty",
            "channel_type": "webhook",
            "config": {"url": "https://events.pagerduty.com/v2/enqueue"},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["channel_type"] == "webhook"
    assert data["config"]["url"] == "https://events.pagerduty.com/v2/enqueue"


def test_create_channel_defaults_active(client):
    """Newly created channel should default to is_active=True."""
    resp = client.post(
        "/channels",
        json={"name": "Default Active", "channel_type": "email", "config": {}},
    )
    assert resp.status_code == 201
    assert resp.json()["is_active"] is True


def test_create_channel_missing_required_field(client):
    """POST /channels without required fields should return 422."""
    resp = client.post("/channels", json={"name": "No Type"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Delivery routing via API
# ---------------------------------------------------------------------------


def _create_notification(client, title="Alert", priority="high", role="backend-engineer"):
    """Helper to create a notification via the API."""
    resp = client.post(
        "/notifications",
        json={"title": title, "message": "Test message", "priority": priority, "role": role},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_channel(client, name, channel_type, config=None):
    """Helper to create a channel via the API."""
    resp = client.post(
        "/channels",
        json={"name": name, "channel_type": channel_type, "config": config or {}},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_deliver_single_channel_via_api(client):
    """POST /notifications/{id}/deliver with one channel should return 202 with 1 delivery."""
    notif_id = _create_notification(client)
    _create_channel(client, "Email", "email")

    resp = client.post(f"/notifications/{notif_id}/deliver")
    assert resp.status_code == 202
    data = resp.json()
    assert data["notification_id"] == notif_id
    assert data["deliveries_created"] == 1


def test_deliver_multiple_channels_via_api(client):
    """POST /notifications/{id}/deliver with multiple channels should route to all."""
    notif_id = _create_notification(client)
    _create_channel(client, "Email", "email")
    _create_channel(client, "Slack", "webhook", {"url": "https://hooks.slack.com/x"})

    resp = client.post(f"/notifications/{notif_id}/deliver")
    assert resp.status_code == 202
    assert resp.json()["deliveries_created"] == 2


def test_deliver_skips_deactivated_channels_via_api(client, db_session):
    """Delivery should skip deactivated channels even when created via API."""
    notif_id = _create_notification(client)
    _create_channel(client, "Active Email", "email")
    inactive_id = _create_channel(client, "Inactive Webhook", "webhook")

    # Deactivate via repository (no deactivation API endpoint exists)
    deactivate_channel(db_session, inactive_id)

    resp = client.post(f"/notifications/{notif_id}/deliver")
    assert resp.status_code == 202
    assert resp.json()["deliveries_created"] == 1


def test_deliver_404_missing_notification(client):
    """POST /notifications/99999/deliver should return 404."""
    resp = client.post("/notifications/99999/deliver")
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_deliver_no_channels_returns_zero(client):
    """Delivering with no channels configured should return 202 with 0 deliveries."""
    notif_id = _create_notification(client)
    resp = client.post(f"/notifications/{notif_id}/deliver")
    assert resp.status_code == 202
    assert resp.json()["deliveries_created"] == 0


# ---------------------------------------------------------------------------
# End-to-end lifecycle
# ---------------------------------------------------------------------------


def test_full_delivery_lifecycle(client):
    """Full flow: create notification -> create channels -> deliver -> check status."""
    # 1. Create notification
    notif_id = _create_notification(client, title="Deploy v3.0", priority="critical")

    # 2. Create channels
    _create_channel(client, "Team Email", "email", {"recipient": "team@co.com"})
    _create_channel(client, "Slack Hook", "webhook", {"url": "https://hooks.slack.com/T00"})

    # 3. Trigger delivery
    deliver_resp = client.post(f"/notifications/{notif_id}/deliver")
    assert deliver_resp.status_code == 202
    assert deliver_resp.json()["deliveries_created"] == 2

    # 4. Check delivery status
    status_resp = client.get(f"/notifications/{notif_id}/delivery-status")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["notification_id"] == notif_id
    assert data["total_channels"] == 2
    assert len(data["deliveries"]) == 2

    # 5. Verify each delivery entry has expected fields
    for delivery in data["deliveries"]:
        assert "log_id" in delivery
        assert "channel_id" in delivery
        assert "channel_name" in delivery
        assert "status" in delivery
        assert delivery["attempt_count"] >= 0
        assert delivery["max_attempts"] == 3


def test_multiple_deliveries_accumulate(client):
    """Delivering the same notification twice should accumulate log entries."""
    notif_id = _create_notification(client)
    _create_channel(client, "Email", "email")

    # Deliver twice
    client.post(f"/notifications/{notif_id}/deliver")
    client.post(f"/notifications/{notif_id}/deliver")

    status_resp = client.get(f"/notifications/{notif_id}/delivery-status")
    data = status_resp.json()
    assert data["total_channels"] == 2  # 1 channel x 2 deliveries = 2 logs


def test_delivery_status_zero_deliveries(client):
    """Status for notification with no deliveries should return empty list."""
    notif_id = _create_notification(client)

    status_resp = client.get(f"/notifications/{notif_id}/delivery-status")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["notification_id"] == notif_id
    assert data["total_channels"] == 0
    assert data["deliveries"] == []


def test_delivery_status_includes_channel_metadata(client):
    """Delivery status entries should include channel name and type."""
    notif_id = _create_notification(client)
    _create_channel(client, "Ops Webhook", "webhook", {"url": "https://example.com/hook"})

    client.post(f"/notifications/{notif_id}/deliver")

    status_resp = client.get(f"/notifications/{notif_id}/delivery-status")
    delivery = status_resp.json()["deliveries"][0]
    assert delivery["channel_name"] == "Ops Webhook"
    assert delivery["channel_type"] == "webhook"
