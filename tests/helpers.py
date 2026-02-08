"""Shared test helpers for outreach-api test suite.

Importable from test files via: from helpers import create_test_business, create_test_event
"""


def create_test_business(client, auth_headers, name="Test Biz", **overrides):
    """Create a business via the API. Not a fixture -- call directly."""
    return client.post("/businesses", json={"name": name, **overrides}, headers=auth_headers).json()


def create_test_event(client, auth_headers, business_id, event_type="call", details=""):
    """Create an event via the API."""
    return client.post(
        f"/businesses/{business_id}/events",
        json={"event_type": event_type, "details": details},
        headers=auth_headers,
    ).json()
