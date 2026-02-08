"""Tests for authentication endpoints."""

def test_login_with_correct_passphrase(client):
    response = client.post("/auth/login", json={"passphrase": "charioteer"})
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "expires_in" in data
    assert data["expires_in"] > 0


def test_login_with_wrong_passphrase(client):
    response = client.post("/auth/login", json={"passphrase": "wrong-password"})
    assert response.status_code == 401
    assert "Access denied" in response.json()["detail"]


def test_login_missing_passphrase(client):
    response = client.post("/auth/login", json={})
    assert response.status_code == 422  # Validation error


def test_verify_auth_with_valid_token(client, auth_headers):
    response = client.get("/auth/verify", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["user"] == "testuser"


def test_verify_auth_without_token(client):
    response = client.get("/auth/verify")
    assert response.status_code == 401
    assert "Missing authorization" in response.json()["detail"]


def test_verify_auth_with_invalid_token(client):
    response = client.get("/auth/verify", headers={"Authorization": "Bearer invalid.token.here"})
    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]
