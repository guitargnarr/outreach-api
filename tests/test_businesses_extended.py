"""Extended tests for business CRUD endpoints.

Covers: category filter, search by notes, business detail with events,
slugify edge cases, update partial fields, delete cascades events,
and additional validation scenarios.
"""

from helpers import create_test_business as _create_business


# --- Category Filter ---

def test_filter_by_category(client, auth_headers):
    _create_business(client, auth_headers, name="A", category="restaurant")
    _create_business(client, auth_headers, name="B", category="retail")
    _create_business(client, auth_headers, name="C", category="restaurant")

    response = client.get("/businesses?category=restaurant", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    for biz in data:
        assert "restaurant" in biz["category"].lower()


def test_filter_by_category_partial_match(client, auth_headers):
    """Category filter uses ilike, so partial matches work."""
    _create_business(client, auth_headers, name="A", category="Fine Dining Restaurant")
    _create_business(client, auth_headers, name="B", category="retail")

    response = client.get("/businesses?category=dining", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "A"


# --- Search by Notes ---

def test_search_by_notes(client, auth_headers):
    """Search filter checks both name and notes fields."""
    _create_business(client, auth_headers, name="Alpha Corp", notes="Good prospect for web redesign")
    _create_business(client, auth_headers, name="Beta Inc", notes="Not interested")

    response = client.get("/businesses?search=redesign", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Alpha Corp"


# --- Multiple Filters ---

def test_combined_status_and_priority_filter(client, auth_headers):
    _create_business(client, auth_headers, name="A", status="contacted", priority="hot")
    _create_business(client, auth_headers, name="B", status="contacted", priority="cold")
    _create_business(client, auth_headers, name="C", status="prospect", priority="hot")

    response = client.get(
        "/businesses?status=contacted&priority=hot", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "A"


# --- Slug Generation ---

def test_slugify_special_characters(client, auth_headers):
    """Slug should strip special chars and normalize spaces/hyphens."""
    biz = _create_business(client, auth_headers, name="O'Brien's Pub & Grill!")
    # Apostrophes, ampersand, exclamation stripped; multi-hyphens collapsed
    assert biz["slug"] == "obriens-pub-grill"


def test_slugify_extra_spaces(client, auth_headers):
    biz = _create_business(client, auth_headers, name="  Lots   Of   Spaces  ")
    assert biz["slug"] == "lots-of-spaces"


# --- Business Detail ---

def test_business_detail_includes_events_list(client, auth_headers):
    biz = _create_business(client, auth_headers, name="Detail Biz")
    # Add an event
    client.post(
        f"/businesses/{biz['id']}/events",
        json={"event_type": "intro_call", "details": "Discussed needs"},
        headers=auth_headers,
    )

    detail = client.get(f"/businesses/{biz['id']}", headers=auth_headers).json()
    assert "events" in detail
    assert len(detail["events"]) == 1
    assert detail["events"][0]["event_type"] == "intro_call"


def test_business_detail_requires_auth(client, auth_headers):
    biz = _create_business(client, auth_headers)
    response = client.get(f"/businesses/{biz['id']}")
    assert response.status_code == 401


# --- Update ---

def test_update_preserves_unchanged_fields(client, auth_headers):
    """Updating one field should not reset others."""
    biz = _create_business(
        client, auth_headers, name="Preserve Biz",
        category="tech", priority="hot", notes="Important notes"
    )

    response = client.put(
        f"/businesses/{biz['id']}",
        json={"status": "contacted"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "contacted"
    # Other fields should be preserved
    assert data["category"] == "tech"
    assert data["priority"] == "hot"
    assert data["notes"] == "Important notes"


def test_update_requires_auth(client, auth_headers):
    biz = _create_business(client, auth_headers)
    response = client.put(
        f"/businesses/{biz['id']}",
        json={"priority": "hot"},
    )
    assert response.status_code == 401


# --- Delete ---

def test_delete_requires_auth(client, auth_headers):
    biz = _create_business(client, auth_headers)
    response = client.delete(f"/businesses/{biz['id']}")
    assert response.status_code == 401


def test_delete_cascades_events(client, auth_headers):
    """Deleting a business should also delete its events."""
    biz = _create_business(client, auth_headers, name="Cascade Biz")
    client.post(
        f"/businesses/{biz['id']}/events",
        json={"event_type": "call"},
        headers=auth_headers,
    )

    # Delete the business
    response = client.delete(f"/businesses/{biz['id']}", headers=auth_headers)
    assert response.status_code == 200

    # Business should be gone
    get_resp = client.get(f"/businesses/{biz['id']}", headers=auth_headers)
    assert get_resp.status_code == 404


# --- Ordering ---

def test_list_businesses_ordered_by_updated_at_desc(client, auth_headers):
    """Businesses should be returned most-recently-updated first."""
    biz_a = _create_business(client, auth_headers, name="AAA First")
    _create_business(client, auth_headers, name="BBB Second")

    # Update A so its updated_at is newer
    client.put(
        f"/businesses/{biz_a['id']}",
        json={"notes": "Updated"},
        headers=auth_headers,
    )

    listing = client.get("/businesses", headers=auth_headers).json()
    assert listing[0]["name"] == "AAA First"  # Most recently updated
    assert listing[1]["name"] == "BBB Second"


# --- All Fields ---

def test_create_business_with_all_fields(client, auth_headers):
    """Verify every field in the create payload is stored and returned."""
    payload = {
        "name": "Full Field Biz",
        "slug": "full-field-biz",
        "category": "healthcare",
        "demo_url": "https://demo.example.com",
        "existing_website": "https://existing.example.com",
        "website_quality": 7,
        "priority": "warm",
        "status": "contacted",
        "contact_name": "John Smith",
        "contact_email": "john@example.com",
        "contact_phone": "(502) 555-0100",
        "contact_role": "Owner",
        "contact_linkedin": "https://linkedin.com/in/johnsmith",
        "address": "123 Main St, Louisville, KY",
        "platform": "WordPress",
        "demo_value_prop": "Modern responsive redesign",
        "notes": "Referred by existing client",
        "portfolio_card_id": "full-field",
    }
    response = client.post("/businesses", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    for key, value in payload.items():
        assert data[key] == value, f"Field {key}: expected {value}, got {data[key]}"
