"""Extended tests for POST /businesses/{id}/send-email endpoint.

Covers: validation errors, status not updated when already beyond prospect,
multiple emails to same business, and SMTP not configured scenario.
"""

from unittest.mock import patch

from helpers import create_test_business as _create_business


# --- Validation ---

def test_send_email_missing_subject(client, auth_headers):
    biz = _create_business(client, auth_headers)
    response = client.post(
        f"/businesses/{biz['id']}/send-email",
        json={"to_email": "test@example.com", "body": "Hello"},
        headers=auth_headers,
    )
    assert response.status_code == 422  # Missing required field


def test_send_email_missing_body(client, auth_headers):
    biz = _create_business(client, auth_headers)
    response = client.post(
        f"/businesses/{biz['id']}/send-email",
        json={"to_email": "test@example.com", "subject": "Hello"},
        headers=auth_headers,
    )
    assert response.status_code == 422  # Missing required field


def test_send_email_missing_to_email(client, auth_headers):
    biz = _create_business(client, auth_headers)
    response = client.post(
        f"/businesses/{biz['id']}/send-email",
        json={"subject": "Hello", "body": "Test"},
        headers=auth_headers,
    )
    assert response.status_code == 422  # Missing required field


# --- Status Behavior ---

def test_send_email_does_not_downgrade_status(client, auth_headers):
    """If business is already beyond 'prospect', status should not change."""
    biz = _create_business(client, auth_headers, status="responded")

    with patch("main._send_smtp_email"):
        client.post(
            f"/businesses/{biz['id']}/send-email",
            json={"to_email": "a@b.com", "subject": "Follow up", "body": "Checking in"},
            headers=auth_headers,
        )

    detail = client.get(f"/businesses/{biz['id']}", headers=auth_headers).json()
    assert detail["status"] == "responded"  # Not changed to "contacted"


def test_send_email_does_not_change_contacted_status(client, auth_headers):
    """If already 'contacted', sending another email should not change status."""
    biz = _create_business(client, auth_headers, status="contacted")

    with patch("main._send_smtp_email"):
        client.post(
            f"/businesses/{biz['id']}/send-email",
            json={"to_email": "a@b.com", "subject": "Follow up", "body": "Hey"},
            headers=auth_headers,
        )

    detail = client.get(f"/businesses/{biz['id']}", headers=auth_headers).json()
    assert detail["status"] == "contacted"  # Unchanged


# --- Multiple Emails ---

def test_send_multiple_emails_logs_multiple_events(client, auth_headers):
    biz = _create_business(client, auth_headers)

    with patch("main._send_smtp_email"):
        for i in range(3):
            client.post(
                f"/businesses/{biz['id']}/send-email",
                json={"to_email": f"user{i}@example.com", "subject": f"Email {i}", "body": "Hi"},
                headers=auth_headers,
            )

    detail = client.get(f"/businesses/{biz['id']}", headers=auth_headers).json()
    assert len(detail["events"]) == 3
    for event in detail["events"]:
        assert event["event_type"] == "email_sent"


# --- SMTP Not Configured ---

def test_send_email_smtp_not_configured(client, auth_headers):
    """When SMTP env vars are not set, _send_smtp_email raises HTTPException(500)."""
    biz = _create_business(client, auth_headers)

    # Patch the SMTP credentials to be empty
    with patch("main.SMTP_EMAIL", ""), patch("main.SMTP_APP_PASSWORD", ""):
        response = client.post(
            f"/businesses/{biz['id']}/send-email",
            json={"to_email": "a@b.com", "subject": "Hi", "body": "Test"},
            headers=auth_headers,
        )

    assert response.status_code == 500
    assert "SMTP not configured" in response.json()["detail"]
