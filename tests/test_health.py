"""Tests for the health and root endpoints (no auth required)."""


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "outreach-api"
    assert "version" in data


def test_root_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Outreach CRM API"
    assert "docs" in data
