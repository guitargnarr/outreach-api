"""Extended tests for POST /sync endpoint.

Covers: slug generation with special characters, update only non-empty fields,
sync preserves existing data, and validation.
"""


def _list_businesses(client, auth_headers):
    return client.get("/businesses", headers=auth_headers).json()


# --- Slug Generation ---

def test_sync_generates_slug_from_name(client, auth_headers):
    items = [{"name": "Bob's Auto Shop"}]
    response = client.post("/sync", json=items, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["created"] == 1

    listing = _list_businesses(client, auth_headers)
    assert listing[0]["slug"] == "bobs-auto-shop"


def test_sync_preserves_existing_data_on_update(client, auth_headers):
    """Sync update should only overwrite non-empty fields, keeping existing data."""
    # Create business with some data
    client.post(
        "/businesses",
        json={"name": "Existing Co", "category": "tech", "notes": "Important notes"},
        headers=auth_headers,
    )

    # Sync with only priority set (name matches slug)
    items = [{"name": "Existing Co", "priority": "hot"}]
    response = client.post("/sync", json=items, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["updated"] == 1

    # Verify existing data is preserved
    listing = _list_businesses(client, auth_headers)
    biz = listing[0]
    assert biz["priority"] == "hot"
    assert biz["category"] == "tech"  # Preserved
    assert biz["notes"] == "Important notes"  # Preserved


def test_sync_multiple_items_at_once(client, auth_headers):
    """Sync with a larger batch of items."""
    items = [
        {"name": f"Business {i}", "category": "batch", "priority": "cold"}
        for i in range(10)
    ]
    response = client.post("/sync", json=items, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 10
    assert data["total"] == 10


def test_sync_with_all_fields(client, auth_headers):
    """Sync item with every possible field populated."""
    items = [{
        "name": "Full Sync Biz",
        "slug": "full-sync-biz",
        "category": "healthcare",
        "demo_url": "https://demo.example.com",
        "existing_website": "https://old.example.com",
        "website_quality": 5,
        "priority": "warm",
        "status": "contacted",
        "contact_name": "Dr. Smith",
        "contact_email": "smith@clinic.com",
        "contact_phone": "(502) 555-9999",
        "contact_role": "Practice Manager",
        "contact_linkedin": "https://linkedin.com/in/drsmith",
        "address": "456 Medical Row, Louisville, KY",
        "platform": "Custom PHP",
        "demo_value_prop": "Modern HIPAA-compliant redesign",
        "notes": "Referral from Dr. Jones",
        "portfolio_card_id": "full-sync",
    }]
    response = client.post("/sync", json=items, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["created"] == 1

    listing = _list_businesses(client, auth_headers)
    biz = listing[0]
    assert biz["name"] == "Full Sync Biz"
    assert biz["contact_name"] == "Dr. Smith"
    assert biz["platform"] == "Custom PHP"


def test_sync_idempotent_on_repeated_calls(client, auth_headers):
    """Syncing the same items twice should not create duplicates."""
    items = [{"name": "Idempotent Biz", "category": "test"}]

    # First sync
    resp1 = client.post("/sync", json=items, headers=auth_headers)
    assert resp1.json()["created"] == 1
    assert resp1.json()["updated"] == 0

    # Second sync - same item
    resp2 = client.post("/sync", json=items, headers=auth_headers)
    assert resp2.json()["created"] == 0
    assert resp2.json()["updated"] == 1

    # Should still be only 1 business
    listing = _list_businesses(client, auth_headers)
    assert len(listing) == 1
