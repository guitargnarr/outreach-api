"""Tests for GET /export/csv endpoint."""

import csv
import io


def test_export_csv_empty(client, auth_headers):
    response = client.get("/export/csv", headers=auth_headers)
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "outreach_export.csv" in response.headers["content-disposition"]

    reader = csv.reader(io.StringIO(response.text))
    rows = list(reader)
    assert len(rows) == 1  # Header only
    assert rows[0][0] == "Name"
    assert "Slug" in rows[0]
    assert "Priority" in rows[0]


def test_export_csv_with_data(client, auth_headers):
    # Create some businesses
    client.post("/businesses", json={"name": "Alpha Corp"}, headers=auth_headers)
    client.post(
        "/businesses",
        json={"name": "Beta Inc", "category": "tech", "priority": "hot"},
        headers=auth_headers,
    )

    response = client.get("/export/csv", headers=auth_headers)
    assert response.status_code == 200

    reader = csv.reader(io.StringIO(response.text))
    rows = list(reader)
    assert len(rows) == 3  # Header + 2 data rows

    # Alphabetical order (Alpha before Beta)
    assert rows[1][0] == "Alpha Corp"
    assert rows[2][0] == "Beta Inc"


def test_export_csv_requires_auth(client):
    response = client.get("/export/csv")
    assert response.status_code == 401
