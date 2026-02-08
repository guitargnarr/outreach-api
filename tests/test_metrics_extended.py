"""Extended tests for GET /metrics endpoint.

Covers: auth requirement, category breakdown, weekly activity with events,
response rate calculation, and edge cases.
"""


from helpers import create_test_business as _create_business, create_test_event as _create_event


# --- Auth ---

def test_metrics_requires_auth(client):
    response = client.get("/metrics")
    assert response.status_code == 401


# --- Category breakdown ---

def test_metrics_category_breakdown(client, auth_headers):
    _create_business(client, auth_headers, name="A", category="restaurant")
    _create_business(client, auth_headers, name="B", category="restaurant")
    _create_business(client, auth_headers, name="C", category="retail")
    _create_business(client, auth_headers, name="D")  # empty category

    response = client.get("/metrics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    cats = data["by_category"]
    assert cats["restaurant"] == 2
    assert cats["retail"] == 1
    # Empty category is grouped as "Uncategorized" or ""
    uncategorized = cats.get("Uncategorized", cats.get("", 0))
    assert uncategorized == 1


# --- Status breakdown ---

def test_metrics_status_breakdown(client, auth_headers):
    _create_business(client, auth_headers, name="A", status="prospect")
    _create_business(client, auth_headers, name="B", status="contacted")
    _create_business(client, auth_headers, name="C", status="responded")
    _create_business(client, auth_headers, name="D", status="meeting")
    _create_business(client, auth_headers, name="E", status="closed")
    _create_business(client, auth_headers, name="F", status="lost")

    response = client.get("/metrics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 6
    assert data["by_status"]["prospect"] == 1
    assert data["by_status"]["contacted"] == 1
    assert data["by_status"]["responded"] == 1
    assert data["by_status"]["meeting"] == 1
    assert data["by_status"]["closed"] == 1
    assert data["by_status"]["lost"] == 1


# --- Response rate ---

def test_metrics_response_rate_calculation(client, auth_headers):
    """Response rate = (responded + meeting + closed) / (contacted + responded + meeting + closed)."""
    _create_business(client, auth_headers, name="A", status="contacted")
    _create_business(client, auth_headers, name="B", status="contacted")
    _create_business(client, auth_headers, name="C", status="responded")
    _create_business(client, auth_headers, name="D", status="meeting")

    response = client.get("/metrics", headers=auth_headers)
    data = response.json()

    # active_outreach = contacted(2) + responded(1) + meeting(1) = 4
    # response rate = (responded(1) + meeting(1) + closed(0)) / max(4 + 0, 1) * 100 = 50
    assert data["active_outreach"] == 4
    assert data["response_rate"] == 50
    assert data["meetings_set"] == 1


def test_metrics_response_rate_zero_when_no_outreach(client, auth_headers):
    """All prospects, no one contacted."""
    _create_business(client, auth_headers, name="A", status="prospect")
    _create_business(client, auth_headers, name="B", status="prospect")

    response = client.get("/metrics", headers=auth_headers)
    data = response.json()
    assert data["active_outreach"] == 0
    assert data["response_rate"] == 0


# --- Total events ---

def test_metrics_total_events(client, auth_headers):
    biz = _create_business(client, auth_headers, name="Event Biz")
    _create_event(client, auth_headers, biz["id"], "call", "First call")
    _create_event(client, auth_headers, biz["id"], "email_sent", "Sent pitch")
    _create_event(client, auth_headers, biz["id"], "meeting", "Demo meeting")

    response = client.get("/metrics", headers=auth_headers)
    data = response.json()
    assert data["total_events"] == 3


# --- Weekly activity ---

def test_metrics_weekly_activity(client, auth_headers):
    """Events created within the last 8 weeks should appear in weekly_activity."""
    biz = _create_business(client, auth_headers, name="Active Biz")
    _create_event(client, auth_headers, biz["id"], "call", "Recent call")

    response = client.get("/metrics", headers=auth_headers)
    data = response.json()
    # At least one week should have activity
    assert isinstance(data["weekly_activity"], dict)
    total_weekly = sum(data["weekly_activity"].values())
    assert total_weekly >= 1
