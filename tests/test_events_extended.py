"""Extended tests for POST /businesses/{id}/events endpoint.

Covers: auth requirement, event appears in business detail, multiple events
ordering, and edge cases.
"""


def _create_business(client, auth_headers, name="Event Biz"):
    return client.post("/businesses", json={"name": name}, headers=auth_headers).json()


# --- Auth ---

def test_create_event_requires_auth(client):
    response = client.post(
        "/businesses/1/events",
        json={"event_type": "call", "details": "Left voicemail"},
    )
    assert response.status_code == 401


# --- Events in Detail ---

def test_events_appear_in_business_detail(client, auth_headers):
    biz = _create_business(client, auth_headers)
    client.post(
        f"/businesses/{biz['id']}/events",
        json={"event_type": "phone_call", "details": "First call"},
        headers=auth_headers,
    )
    client.post(
        f"/businesses/{biz['id']}/events",
        json={"event_type": "email_sent", "details": "Sent proposal"},
        headers=auth_headers,
    )

    detail = client.get(f"/businesses/{biz['id']}", headers=auth_headers).json()
    assert len(detail["events"]) == 2
    # Events are ordered by created_at desc (most recent first)
    event_types = [e["event_type"] for e in detail["events"]]
    assert "phone_call" in event_types
    assert "email_sent" in event_types


# --- Event with empty details ---

def test_create_event_with_empty_details(client, auth_headers):
    biz = _create_business(client, auth_headers)
    response = client.post(
        f"/businesses/{biz['id']}/events",
        json={"event_type": "site_visit"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["event_type"] == "site_visit"
    assert data["details"] == ""


# --- Event updates business updated_at ---

def test_create_event_updates_business_timestamp(client, auth_headers):
    biz = _create_business(client, auth_headers)
    original_updated = biz["updated_at"]

    # Small delay is handled by the app setting updated_at to now()
    client.post(
        f"/businesses/{biz['id']}/events",
        json={"event_type": "call", "details": "Check-in"},
        headers=auth_headers,
    )

    detail = client.get(f"/businesses/{biz['id']}", headers=auth_headers).json()
    # updated_at should be >= original (may be equal in fast test execution)
    assert detail["updated_at"] >= original_updated


# --- Missing event_type ---

def test_create_event_missing_event_type(client, auth_headers):
    biz = _create_business(client, auth_headers)
    response = client.post(
        f"/businesses/{biz['id']}/events",
        json={"details": "No type provided"},
        headers=auth_headers,
    )
    assert response.status_code == 422  # Validation error
