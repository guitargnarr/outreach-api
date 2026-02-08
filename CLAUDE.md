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

**Endpoints (18):**

| Group | Method | Path | Auth |
|-------|--------|------|------|
| Auth | POST | /auth/login | No |
| Auth | GET | /auth/verify | Yes |
| Business | GET | /businesses | Yes |
| Business | POST | /businesses | Yes |
| Business | GET | /businesses/{id} | Yes |
| Business | PUT | /businesses/{id} | Yes |
| Business | DELETE | /businesses/{id} | Yes |
| Events | POST | /businesses/{id}/events | Yes |
| Email | POST | /businesses/{id}/send-email | Yes |
| Metrics | GET | /metrics | Yes |
| Sync | POST | /sync | Yes |
| Export | GET | /export/csv | Yes |
| Health | GET | /health | No |
| Health | GET | / | No |

---

## Test Coverage (Updated 2026-02-08)

**Status: 43/43 passing (100%)**
**Endpoint coverage: 18/18 (100%)**
**Runtime: 0.59s**

| File | Tests | Endpoints Covered |
|------|-------|-------------------|
| test_auth.py | 6 | /auth/login (3), /auth/verify (3) |
| test_businesses.py | 20 | /businesses CRUD (13), events (2), metrics (2), filters (3) |
| test_email_send.py | 6 | /businesses/{id}/send-email (6, SMTP mocked) |
| test_export.py | 3 | /export/csv (3) |
| test_sync.py | 6 | /sync (6) |
| test_health.py | 2 | /health (1), / (1) |

**Test infrastructure:** In-memory SQLite via StaticPool, FastAPI TestClient, JWT auth fixture.

**Run tests:**
```bash
cd ~/Projects/outreach-api
python3 -m pytest tests/ -v
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
