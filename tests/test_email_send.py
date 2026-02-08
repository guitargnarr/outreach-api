"""Tests for POST /businesses/{id}/send-email endpoint.

Email sending is mocked -- tests verify routing, validation, status
updates, and event logging without touching real SMTP.
"""

from unittest.mock import patch


def _create_business(client, auth_headers, name="Email Biz"):
    return client.post("/businesses", json={"name": name}, headers=auth_headers).json()


def test_send_email_success(client, auth_headers):
    biz = _create_business(client, auth_headers)
    with patch("main._send_smtp_email") as mock_send:
        response = client.post(
            f"/businesses/{biz['id']}/send-email",
            json={
                "to_email": "test@example.com",
                "subject": "Hello",
                "body": "Test body",
            },
            headers=auth_headers,
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "sent"
    assert data["to"] == "test@example.com"
    assert data["business_id"] == biz["id"]
    mock_send.assert_called_once_with("test@example.com", "Hello", "Test body")


def test_send_email_updates_status_from_prospect(client, auth_headers):
    biz = _create_business(client, auth_headers)
    assert biz["status"] == "prospect"

    with patch("main._send_smtp_email"):
        client.post(
            f"/businesses/{biz['id']}/send-email",
            json={"to_email": "a@b.com", "subject": "Hi", "body": "Hey"},
            headers=auth_headers,
        )

    # Status should be auto-updated to contacted
    detail = client.get(f"/businesses/{biz['id']}", headers=auth_headers).json()
    assert detail["status"] == "contacted"


def test_send_email_logs_event(client, auth_headers):
    biz = _create_business(client, auth_headers)
    with patch("main._send_smtp_email"):
        client.post(
            f"/businesses/{biz['id']}/send-email",
            json={"to_email": "a@b.com", "subject": "Pitch", "body": "Hey"},
            headers=auth_headers,
        )

    detail = client.get(f"/businesses/{biz['id']}", headers=auth_headers).json()
    assert len(detail["events"]) == 1
    assert detail["events"][0]["event_type"] == "email_sent"
    assert "a@b.com" in detail["events"][0]["details"]


def test_send_email_business_not_found(client, auth_headers):
    with patch("main._send_smtp_email"):
        response = client.post(
            "/businesses/9999/send-email",
            json={"to_email": "a@b.com", "subject": "Hi", "body": "Hey"},
            headers=auth_headers,
        )
    assert response.status_code == 404


def test_send_email_smtp_failure(client, auth_headers):
    biz = _create_business(client, auth_headers)
    with patch("main._send_smtp_email", side_effect=Exception("SMTP down")):
        response = client.post(
            f"/businesses/{biz['id']}/send-email",
            json={"to_email": "a@b.com", "subject": "Hi", "body": "Hey"},
            headers=auth_headers,
        )
    assert response.status_code == 500
    assert "Failed to send" in response.json()["detail"]


def test_send_email_requires_auth(client):
    response = client.post(
        "/businesses/1/send-email",
        json={"to_email": "a@b.com", "subject": "Hi", "body": "Hey"},
    )
    assert response.status_code == 401
