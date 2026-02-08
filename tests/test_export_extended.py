"""Extended tests for GET /export/csv endpoint.

Covers: all CSV columns present, field content verification, and special characters.
"""

import csv
import io


def _create_business(client, auth_headers, name="Export Biz", **overrides):
    return client.post("/businesses", json={"name": name, **overrides}, headers=auth_headers).json()


def test_export_csv_contains_all_columns(client, auth_headers):
    """Header row should have all 19 expected columns."""
    response = client.get("/export/csv", headers=auth_headers)
    assert response.status_code == 200

    reader = csv.reader(io.StringIO(response.text))
    header = next(reader)
    expected_columns = [
        "Name", "Slug", "Category", "Demo URL", "Existing Website",
        "Website Quality", "Platform", "Priority", "Status", "Contact Name",
        "Contact Email", "Contact Phone", "Contact Role", "LinkedIn",
        "Address", "Demo Value Prop", "Notes", "Created", "Updated",
    ]
    assert header == expected_columns


def test_export_csv_field_content(client, auth_headers):
    """Data rows should contain the exact values from the business record."""
    _create_business(
        client, auth_headers,
        name="Precise Biz",
        category="tech",
        priority="hot",
        status="contacted",
        contact_name="Jane Doe",
        contact_email="jane@example.com",
        contact_phone="(502) 555-1234",
        platform="Squarespace",
    )

    response = client.get("/export/csv", headers=auth_headers)
    reader = csv.reader(io.StringIO(response.text))
    rows = list(reader)
    assert len(rows) == 2  # Header + 1 data row

    data_row = rows[1]
    assert data_row[0] == "Precise Biz"       # Name
    assert data_row[1] == "precise-biz"        # Slug
    assert data_row[2] == "tech"               # Category
    assert data_row[7] == "hot"                # Priority
    assert data_row[8] == "contacted"          # Status
    assert data_row[9] == "Jane Doe"           # Contact Name
    assert data_row[10] == "jane@example.com"  # Contact Email
    assert data_row[11] == "(502) 555-1234"    # Contact Phone


def test_export_csv_special_characters(client, auth_headers):
    """Business names with commas and quotes should be properly escaped in CSV."""
    _create_business(
        client, auth_headers,
        name='O\'Brien, Inc.',
        notes='Has a "special" offer',
    )

    response = client.get("/export/csv", headers=auth_headers)
    reader = csv.reader(io.StringIO(response.text))
    rows = list(reader)
    assert len(rows) == 2
    assert rows[1][0] == "O'Brien, Inc."
    # Notes column (index 16)
    assert rows[1][16] == 'Has a "special" offer'


def test_export_csv_multiple_businesses_sorted(client, auth_headers):
    """Businesses should be sorted alphabetically by name in CSV export."""
    _create_business(client, auth_headers, name="Zeta Corp")
    _create_business(client, auth_headers, name="Alpha Corp")
    _create_business(client, auth_headers, name="Mu Corp")

    response = client.get("/export/csv", headers=auth_headers)
    reader = csv.reader(io.StringIO(response.text))
    rows = list(reader)
    assert len(rows) == 4  # Header + 3 data rows
    assert rows[1][0] == "Alpha Corp"
    assert rows[2][0] == "Mu Corp"
    assert rows[3][0] == "Zeta Corp"
