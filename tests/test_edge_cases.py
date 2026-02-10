"""Edge case tests added by test-engineer for additional coverage.

Owner: test-engineer
Tests: 3
"""


def test_create_notification_missing_required_field(client):
    """POST /notifications with missing required field should return 422."""
    response = client.post(
        "/notifications",
        json={"title": "Missing message field", "priority": "normal", "role": "architect"},
    )
    assert response.status_code == 422


def test_mark_read_nonexistent_notification(client):
    """PATCH /notifications/99999/read should return 404."""
    response = client.patch("/notifications/99999/read")
    assert response.status_code == 404
    assert "notification" in response.json()["detail"].lower()


def test_list_notifications_empty_role(client):
    """GET /notifications?role=nonexistent should return empty list."""
    response = client.get("/notifications", params={"role": "nonexistent-role"})
    assert response.status_code == 200
    assert response.json() == []
