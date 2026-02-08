# Outreach CRM API

**Live:** https://outreach-api-miha.onrender.com
**Frontend:** https://outreach-tracker-one.vercel.app
**GitHub:** guitargnarr/outreach-api

---

## Architecture

**Framework:** FastAPI (sync), SQLAlchemy ORM, Pydantic v2
**Auth:** JWT passphrase-based (ADMIN_PASSPHRASE env var)
**Database:** SQLite (dev), PostgreSQL (prod via DATABASE_URL)
**Email:** Gmail SMTP (SMTP_EMAIL + SMTP_APP_PASSWORD env vars)

**Endpoints (14):**

| # | Group | Method | Path | Auth |
|---|-------|--------|------|------|
| 1 | Auth | POST | /auth/login | No |
| 2 | Auth | GET | /auth/verify | Yes |
| 3 | Business | GET | /businesses | Yes |
| 4 | Business | POST | /businesses | Yes |
| 5 | Business | GET | /businesses/{id} | Yes |
| 6 | Business | PUT | /businesses/{id} | Yes |
| 7 | Business | DELETE | /businesses/{id} | Yes |
| 8 | Events | POST | /businesses/{id}/events | Yes |
| 9 | Email | POST | /businesses/{id}/send-email | Yes |
| 10 | Metrics | GET | /metrics | Yes |
| 11 | Sync | POST | /sync | Yes |
| 12 | Export | GET | /export/csv | Yes |
| 13 | Health | GET | /health | No |
| 14 | Health | GET | / | No |

---

## Test Coverage (Updated 2026-02-08)

**Status: 89/89 passing (100%)**
**Endpoint coverage: 14/14 (100%)**
**Runtime: ~1.3s**

### Test File Inventory (14 files)

| File | Tests | What It Covers |
|------|-------|----------------|
| conftest.py | -- | Shared fixtures: in-memory SQLite (StaticPool), TestClient, JWT auth_headers |
| test_auth.py | 6 | Login success/fail/missing, verify valid/missing/invalid token |
| test_auth_extended.py | 4 | Expired token, malformed header, login-to-verify flow, expiry value |
| test_businesses.py | 20 | CRUD (create/read/update/delete), events, metrics basic, status/priority/search filters |
| test_businesses_extended.py | 14 | Category filter, notes search, combined filters, slugify edge cases, detail with events, update preserves fields, delete cascades, ordering, all-fields create, auth checks |
| test_events_extended.py | 5 | Auth requirement, events in detail, empty details, timestamp update, missing event_type |
| test_email_send.py | 6 | Success, status auto-update, event logging, not found, SMTP failure, auth |
| test_email_send_extended.py | 7 | Missing fields (subject/body/to_email), status not downgraded, multiple emails, SMTP not configured |
| test_export.py | 3 | Empty CSV, CSV with data, auth requirement |
| test_export_extended.py | 4 | All columns present, field content, special characters, alphabetical sort |
| test_metrics_extended.py | 7 | Auth requirement, category/status breakdown, response rate math, zero outreach, total events, weekly activity |
| test_sync.py | 6 | Create new, update by slug, mixed create/update, custom slug, auth, empty list |
| test_sync_extended.py | 5 | Slug generation, preserve existing data, batch (10 items), all fields, idempotency |
| test_health.py | 2 | /health returns 200, / returns 200 |

### Coverage by Endpoint

| Endpoint | Tests | Scenarios |
|----------|-------|-----------|
| POST /auth/login | 5 | Correct/wrong passphrase, missing field, token validity, expiry |
| GET /auth/verify | 6 | Valid/invalid/expired/missing/malformed token, login-verify flow |
| GET /businesses | 8 | Empty list, auth, status/priority/category/search/combined filters, ordering |
| POST /businesses | 7 | Basic create, custom slug, duplicate slug, all fields, special chars, extra spaces, auth |
| GET /businesses/{id} | 4 | Found, not found, includes events, auth |
| PUT /businesses/{id} | 4 | Update fields, not found, preserves unchanged, auth |
| DELETE /businesses/{id} | 4 | Delete, not found, cascades events, auth |
| POST /businesses/{id}/events | 5 | Create, nonexistent biz, empty details, timestamp update, missing type |
| POST /businesses/{id}/send-email | 13 | Success, status update, event log, not found, SMTP fail, auth, missing fields (3), status not downgraded (2), multiple emails, SMTP not configured |
| GET /metrics | 9 | Empty DB, with data, auth, category/status breakdown, response rate (2), total events, weekly activity |
| POST /sync | 11 | Create new, update by slug, mixed, custom slug, auth, empty list, slug gen, preserve data, batch, all fields, idempotent |
| GET /export/csv | 7 | Empty, with data, auth, all columns, field content, special chars, sorted |
| GET /health | 1 | Returns 200 with status/service/version |
| GET / | 1 | Returns 200 with service/version/docs |

### Test Infrastructure

- **Database:** In-memory SQLite via `StaticPool` (all connections share same DB, reset per test)
- **Client:** FastAPI `TestClient` (sync, no httpx needed)
- **Auth:** JWT fixture generates valid Bearer token headers
- **Mocking:** `unittest.mock.patch` for SMTP email (no real emails sent in tests)
- **Isolation:** `setup_database` autouse fixture creates/drops all tables per test

### Run Tests

```bash
cd ~/Projects/outreach-api
python3 -m pytest tests/ -v          # Full suite (89 tests)
python3 -m pytest tests/ -v -x       # Stop on first failure
python3 -m pytest tests/test_auth.py  # Single file
```

---

## Development

```bash
pip install -r requirements.txt
cp .env.example .env  # Edit with your values
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Deploy

Backend auto-deploys from main via Render. Push to main triggers redeploy.
