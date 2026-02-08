"""Tests for business CRUD endpoints."""

# --- Helper ---


def create_business(client, auth_headers, name="Test Biz", **overrides):
    payload = {"name": name, **overrides}
    return client.post("/businesses", json=payload, headers=auth_headers)


# --- List ---

def test_list_businesses_empty(client, auth_headers):
    response = client.get("/businesses", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_businesses_requires_auth(client):
    response = client.get("/businesses")
    assert response.status_code == 401


# --- Create ---

def test_create_business(client, auth_headers):
    response = create_business(client, auth_headers, name="Acme Corp")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Acme Corp"
    assert data["slug"] == "acme-corp"
    assert data["priority"] == "cold"
    assert data["status"] == "prospect"
    assert "id" in data


def test_create_business_custom_slug(client, auth_headers):
    response = create_business(client, auth_headers, name="Test", slug="custom-slug")
    assert response.status_code == 200
    assert response.json()["slug"] == "custom-slug"


def test_create_business_duplicate_slug(client, auth_headers):
    create_business(client, auth_headers, name="Acme Corp")
    response = create_business(client, auth_headers, name="Acme Corp")
    assert response.status_code == 400
    assert "slug exists" in response.json()["detail"]


def test_create_business_with_fields(client, auth_headers):
    response = create_business(
        client,
        auth_headers,
        name="Full Biz",
        category="restaurant",
        priority="hot",
        status="contacted",
        contact_name="Jane Doe",
        contact_email="jane@example.com",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "restaurant"
    assert data["priority"] == "hot"
    assert data["status"] == "contacted"
    assert data["contact_name"] == "Jane Doe"
    assert data["contact_email"] == "jane@example.com"


def test_create_business_requires_auth(client):
    response = client.post("/businesses", json={"name": "No Auth Biz"})
    assert response.status_code == 401


# --- Get by ID ---

def test_get_business_by_id(client, auth_headers):
    created = create_business(client, auth_headers, name="Get Me").json()
    response = client.get(f"/businesses/{created["id"]}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Get Me"
    assert "events" in data  # BusinessDetail includes events


def test_get_business_not_found(client, auth_headers):
    response = client.get("/businesses/9999", headers=auth_headers)
    assert response.status_code == 404


# --- Update ---

def test_update_business(client, auth_headers):
    created = create_business(client, auth_headers, name="Update Me").json()
    response = client.put(
        f"/businesses/{created["id"]}",
        json={"priority": "hot", "notes": "Updated"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["priority"] == "hot"
    assert data["notes"] == "Updated"


def test_update_business_not_found(client, auth_headers):
    response = client.put(
        "/businesses/9999",
        json={"priority": "hot"},
        headers=auth_headers,
    )
    assert response.status_code == 404


# --- Delete ---

def test_delete_business(client, auth_headers):
    created = create_business(client, auth_headers, name="Delete Me").json()
    response = client.delete(f"/businesses/{created["id"]}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    # Verify it is gone
    get_resp = client.get(f"/businesses/{created["id"]}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_delete_business_not_found(client, auth_headers):
    response = client.delete("/businesses/9999", headers=auth_headers)
    assert response.status_code == 404


# --- Events ---

def test_create_event_for_business(client, auth_headers):
    biz = create_business(client, auth_headers, name="Event Biz").json()
    response = client.post(
        f"/businesses/{biz["id"]}/events",
        json={"event_type": "phone_call", "details": "Left voicemail"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["event_type"] == "phone_call"
    assert data["details"] == "Left voicemail"
    assert data["business_id"] == biz["id"]


def test_create_event_for_nonexistent_business(client, auth_headers):
    response = client.post(
        "/businesses/9999/events",
        json={"event_type": "call"},
        headers=auth_headers,
    )
    assert response.status_code == 404


# --- Metrics ---

def test_metrics_empty_db(client, auth_headers):
    response = client.get("/metrics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert "by_status" in data
    assert "by_priority" in data
    assert "response_rate" in data


def test_metrics_with_data(client, auth_headers):
    create_business(client, auth_headers, name="Biz A", priority="hot", status="contacted")
    create_business(client, auth_headers, name="Biz B", priority="cold")
    response = client.get("/metrics", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["by_priority"]["hot"] == 1
    assert data["by_priority"]["cold"] == 1


# --- Filters ---

def test_filter_by_status(client, auth_headers):
    create_business(client, auth_headers, name="A", status="contacted")
    create_business(client, auth_headers, name="B", status="prospect")
    response = client.get("/businesses?status=contacted", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "A"


def test_filter_by_priority(client, auth_headers):
    create_business(client, auth_headers, name="Hot", priority="hot")
    create_business(client, auth_headers, name="Cold", priority="cold")
    response = client.get("/businesses?priority=hot", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Hot"


def test_search_by_name(client, auth_headers):
    create_business(client, auth_headers, name="Alpha Industries")
    create_business(client, auth_headers, name="Beta Corp")
    response = client.get("/businesses?search=Alpha", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Alpha Industries"
