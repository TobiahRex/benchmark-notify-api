"""Tests for the Notification REST API endpoints.

Owner: backend-engineer
Tests: 6
Files: routes.py, schemas.py, main.py
"""


def test_create_notification_endpoint(client):
    """POST /notifications should create a notification."""
    response = client.post(
        "/notifications",
        json={
            "title": "Deploy alert",
            "message": "Production deploy started",
            "priority": "high",
            "role": "backend-engineer",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Deploy alert"
    assert data["priority"] == "high"
    assert data["id"] is not None


def test_list_notifications_endpoint(client):
    """GET /notifications?role=X should return notifications for that role."""
    # Create two notifications
    client.post(
        "/notifications",
        json={"title": "A", "message": "a", "priority": "normal", "role": "architect"},
    )
    client.post(
        "/notifications",
        json={"title": "B", "message": "b", "priority": "normal", "role": "architect"},
    )

    response = client.get("/notifications", params={"role": "architect"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_notification_by_id_endpoint(client):
    """GET /notifications/{id} should return a single notification."""
    create_resp = client.post(
        "/notifications",
        json={"title": "Test", "message": "test", "priority": "normal", "role": "architect"},
    )
    notif_id = create_resp.json()["id"]

    response = client.get(f"/notifications/{notif_id}")
    assert response.status_code == 200
    assert response.json()["id"] == notif_id


def test_mark_notification_read_endpoint(client):
    """PATCH /notifications/{id}/read should mark as read."""
    create_resp = client.post(
        "/notifications",
        json={"title": "Unread", "message": "mark me", "priority": "normal", "role": "architect"},
    )
    notif_id = create_resp.json()["id"]

    response = client.patch(f"/notifications/{notif_id}/read")
    assert response.status_code == 200
    assert response.json()["is_read"] is True


def test_get_notification_not_found(client):
    """GET /notifications/99999 should return 404 with specific detail."""
    response = client.get("/notifications/99999")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "notification" in data["detail"].lower()


def test_list_unread_notifications_endpoint(client):
    """GET /notifications?role=X&unread=true should return only unread."""
    client.post(
        "/notifications",
        json={"title": "A", "message": "a", "priority": "normal", "role": "architect"},
    )
    create_resp = client.post(
        "/notifications",
        json={"title": "B", "message": "b", "priority": "normal", "role": "architect"},
    )
    notif_id = create_resp.json()["id"]
    # Mark one as read
    client.patch(f"/notifications/{notif_id}/read")

    response = client.get("/notifications", params={"role": "architect", "unread": "true"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["is_read"] is False
