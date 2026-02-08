"""Extended tests for authentication endpoints.

Covers: expired token, malformed authorization header, token payload contents.
"""

from datetime import datetime, timedelta, timezone

import jwt as pyjwt

from main import JWT_SECRET


def test_expired_token_is_rejected(client):
    """An expired JWT should return 401."""
    expired_payload = {
        "sub": "testuser",
        "role": "admin",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    token = pyjwt.encode(expired_payload, JWT_SECRET, algorithm="HS256")
    response = client.get("/auth/verify", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_malformed_authorization_header(client):
    """A non-Bearer authorization should still be decoded (and fail)."""
    response = client.get("/auth/verify", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert response.status_code == 401


def test_login_returns_valid_token_for_verify(client):
    """The token from /auth/login should work with /auth/verify."""
    login_resp = client.post("/auth/login", json={"passphrase": "charioteer"})
    assert login_resp.status_code == 200
    token = login_resp.json()["token"]

    verify_resp = client.get("/auth/verify", headers={"Authorization": f"Bearer {token}"})
    assert verify_resp.status_code == 200
    assert verify_resp.json()["valid"] is True
    assert verify_resp.json()["user"] == "charioteer"


def test_login_token_has_correct_expiry(client):
    """Token should expire in 7 days (604800 seconds)."""
    login_resp = client.post("/auth/login", json={"passphrase": "charioteer"})
    data = login_resp.json()
    assert data["expires_in"] == 7 * 86400  # 604800 seconds
