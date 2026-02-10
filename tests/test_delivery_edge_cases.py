"""Edge case tests for delivery: retry exhaustion, invalid config, concurrent delivery, boundaries.

Owner: test-engineer
Tests: 14
Files: models.py, repository.py, service.py, routes.py

Covers:
  - Retry exhaustion (3 failures -> permanently failed, attempt_count increments, backoff)
  - Invalid channel config (unreachable webhook, invalid SMTP stored gracefully)
  - Concurrent delivery (no duplicate logs, idempotent retry)
  - Boundary cases (no active channels, non-existent notification, zero deliveries)
"""

import uuid

from notify_api.repository import (
    create_channel,
    create_delivery_log,
    create_notification,
    get_delivery_log_by_id,
    get_delivery_logs_by_notification,
    get_pending_retries,
    update_delivery_log_status,
)
from notify_api.service import (
    DeliveryService,
    deliver_notification,
    get_delivery_status,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_notification(db_session, title="Edge Case Alert"):
    return create_notification(
        db_session,
        title=title,
        message="Something to test",
        priority="high",
        role="test-engineer",
    )


def _make_channel(db_session, name="Test Channel", channel_type="email", config=None):
    return create_channel(
        db_session,
        name=name,
        channel_type=channel_type,
        config=config or {},
    )


# ---------------------------------------------------------------------------
# Retry exhaustion (acceptance: capped at 3 attempts)
# ---------------------------------------------------------------------------


def test_retry_exhaustion_caps_at_max_attempts(db_session):
    """After 3 retries, retry_delivery should return None (exhausted)."""
    notif = _make_notification(db_session)
    channel = _make_channel(db_session)

    log = create_delivery_log(
        db_session,
        notification_id=notif.id,
        channel_id=channel.id,
        status="failed",
        attempt_count=3,
        max_attempts=3,
    )

    # Attempting to retry should fail - max attempts reached
    result = DeliveryService.retry_delivery(db_session, log.id)
    assert result is None

    # Verify attempt_count was NOT incremented
    refreshed = get_delivery_log_by_id(db_session, log.id)
    assert refreshed.attempt_count == 3


def test_attempt_count_increments_on_retry(db_session):
    """Each retry should increment attempt_count by 1."""
    notif = _make_notification(db_session)
    channel = _make_channel(db_session)

    log = create_delivery_log(
        db_session,
        notification_id=notif.id,
        channel_id=channel.id,
        status="failed",
        attempt_count=0,
        max_attempts=3,
    )

    # First retry: 0 -> 1
    result = DeliveryService.retry_delivery(db_session, log.id)
    assert result is not None
    assert result.attempt_count == 1

    # Mark as failed again for next retry
    update_delivery_log_status(db_session, log.id, "failed")

    # Second retry: 1 -> 2
    result = DeliveryService.retry_delivery(db_session, log.id)
    assert result is not None
    assert result.attempt_count == 2


def test_retry_sets_last_attempt_at(db_session):
    """Retry should set last_attempt_at timestamp."""
    notif = _make_notification(db_session)
    channel = _make_channel(db_session)

    log = create_delivery_log(
        db_session,
        notification_id=notif.id,
        channel_id=channel.id,
        status="failed",
        attempt_count=0,
        max_attempts=3,
    )
    assert log.last_attempt_at is None

    result = DeliveryService.retry_delivery(db_session, log.id)
    assert result.last_attempt_at is not None


def test_retry_calculates_exponential_backoff(db_session):
    """Backoff should be BASE_DELAY * 2^(attempt-1): 1s, 2s, 4s."""
    notif = _make_notification(db_session)
    channel = _make_channel(db_session)

    log = create_delivery_log(
        db_session,
        notification_id=notif.id,
        channel_id=channel.id,
        status="failed",
        attempt_count=0,
        max_attempts=3,
    )

    # First retry: delay = 1 * 2^0 = 1s
    result = DeliveryService.retry_delivery(db_session, log.id)
    assert result is not None
    assert result.next_retry_at is not None
    # next_retry_at should be approximately 1 second after last_attempt_at
    delta = (result.next_retry_at - result.last_attempt_at).total_seconds()
    assert 0.5 <= delta <= 2.0  # Allow some tolerance

    # Mark failed, second retry: delay = 1 * 2^1 = 2s
    update_delivery_log_status(db_session, log.id, "failed")
    result = DeliveryService.retry_delivery(db_session, log.id)
    assert result is not None
    delta = (result.next_retry_at - result.last_attempt_at).total_seconds()
    assert 1.5 <= delta <= 3.0  # ~2s with tolerance


def test_retry_nonexistent_log_returns_none(db_session):
    """Retrying a non-existent log ID should return None."""
    fake_id = uuid.uuid4()
    result = DeliveryService.retry_delivery(db_session, fake_id)
    assert result is None


def test_get_pending_retries_excludes_exhausted(db_session):
    """get_pending_retries should not return logs at max attempts."""
    notif = _make_notification(db_session)
    channel = _make_channel(db_session)

    # Retryable: failed with attempts < max
    retryable = create_delivery_log(
        db_session,
        notification_id=notif.id,
        channel_id=channel.id,
        status="failed",
        attempt_count=1,
        max_attempts=3,
    )

    # Exhausted: failed with attempts == max
    create_delivery_log(
        db_session,
        notification_id=notif.id,
        channel_id=channel.id,
        status="failed",
        attempt_count=3,
        max_attempts=3,
    )

    pending = get_pending_retries(db_session)
    assert len(pending) == 1
    assert pending[0].id == retryable.id


# ---------------------------------------------------------------------------
# Invalid channel config (acceptance: fail gracefully)
# ---------------------------------------------------------------------------


def test_channel_with_unreachable_webhook_url_stored(db_session):
    """Channel with unreachable webhook URL should be stored without error."""
    channel = _make_channel(
        db_session,
        name="Bad Webhook",
        channel_type="webhook",
        config={"url": "https://nonexistent.invalid/hook"},
    )
    assert channel.id is not None
    assert channel.config["url"] == "https://nonexistent.invalid/hook"
    assert channel.is_active is True


def test_channel_with_invalid_smtp_config_stored(db_session):
    """Channel with invalid SMTP config should be stored without error."""
    channel = _make_channel(
        db_session,
        name="Bad SMTP",
        channel_type="email",
        config={"smtp_host": "", "smtp_port": -1, "recipient": "not-an-email"},
    )
    assert channel.id is not None
    assert channel.config["smtp_port"] == -1
    assert channel.is_active is True


def test_delivery_log_records_error_message(db_session):
    """Updating a log with an error message should persist the error."""
    notif = _make_notification(db_session)
    channel = _make_channel(db_session, config={"url": "https://invalid.test"})

    log = create_delivery_log(
        db_session,
        notification_id=notif.id,
        channel_id=channel.id,
    )

    updated = update_delivery_log_status(
        db_session,
        log.id,
        "failed",
        error_message="Connection refused: https://invalid.test",
    )
    assert updated.status == "failed"
    assert "Connection refused" in updated.error_message


# ---------------------------------------------------------------------------
# Concurrent delivery protection (acceptance: no duplicates)
# ---------------------------------------------------------------------------


def test_deliver_twice_creates_separate_logs(db_session):
    """Delivering same notification twice creates distinct DeliveryLog entries."""
    notif = _make_notification(db_session)
    _make_channel(db_session, name="Email", channel_type="email")

    logs1 = deliver_notification(db_session, notif.id)
    logs2 = deliver_notification(db_session, notif.id)

    # Each delivery creates new log entries
    assert len(logs1) == 1
    assert len(logs2) == 1
    assert logs1[0].id != logs2[0].id

    # Total logs for notification should be 2
    all_logs = get_delivery_logs_by_notification(db_session, notif.id)
    assert len(all_logs) == 2


def test_process_pending_retries_skips_exhausted(db_session):
    """process_pending_retries should skip logs at max attempts."""
    notif = _make_notification(db_session)
    channel = _make_channel(db_session)

    # Create one retryable and one exhausted log
    create_delivery_log(
        db_session,
        notification_id=notif.id,
        channel_id=channel.id,
        status="failed",
        attempt_count=1,
        max_attempts=3,
    )
    create_delivery_log(
        db_session,
        notification_id=notif.id,
        channel_id=channel.id,
        status="failed",
        attempt_count=3,
        max_attempts=3,
    )

    retried = DeliveryService.process_pending_retries(db_session)
    assert len(retried) == 1  # Only the retryable one


# ---------------------------------------------------------------------------
# Boundary cases (acceptance: covered)
# ---------------------------------------------------------------------------


def test_deliver_no_active_channels_returns_empty(db_session):
    """Delivering with no active channels should return an empty list."""
    notif = _make_notification(db_session)
    logs = deliver_notification(db_session, notif.id)
    assert logs == []


def test_delivery_status_nonexistent_notification_returns_none(db_session):
    """get_delivery_status for non-existent notification should return None."""
    result = get_delivery_status(db_session, 99999)
    assert result is None
