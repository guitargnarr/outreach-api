"""Tests for POST /sync endpoint -- bulk business import/update."""


def test_sync_creates_new_businesses(client, auth_headers):
    items = [
        {"name": "Sync Biz A"},
        {"name": "Sync Biz B", "category": "restaurant"},
    ]
    response = client.post("/sync", json=items, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 2
    assert data["updated"] == 0
    assert data["total"] == 2

    # Verify they exist
    listing = client.get("/businesses", headers=auth_headers).json()
    assert len(listing) == 2


def test_sync_updates_existing_by_slug(client, auth_headers):
    # Create initial business
    client.post("/businesses", json={"name": "Existing Biz"}, headers=auth_headers)

    # Sync with same slug should update
    items = [{"name": "Existing Biz", "priority": "hot", "category": "tech"}]
    response = client.post("/sync", json=items, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 0
    assert data["updated"] == 1


def test_sync_mixed_create_and_update(client, auth_headers):
    client.post("/businesses", json={"name": "Old Biz"}, headers=auth_headers)

    items = [
        {"name": "Old Biz", "status": "contacted"},
        {"name": "New Biz", "priority": "warm"},
    ]
    response = client.post("/sync", json=items, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 1
    assert data["updated"] == 1
    assert data["total"] == 2


def test_sync_custom_slug(client, auth_headers):
    items = [{"name": "My Business", "slug": "custom-slug-here"}]
    response = client.post("/sync", json=items, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["created"] == 1

    listing = client.get("/businesses", headers=auth_headers).json()
    assert listing[0]["slug"] == "custom-slug-here"


def test_sync_requires_auth(client):
    response = client.post("/sync", json=[{"name": "No Auth"}])
    assert response.status_code == 401


def test_sync_empty_list(client, auth_headers):
    response = client.post("/sync", json=[], headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 0
    assert data["updated"] == 0
    assert data["total"] == 0
