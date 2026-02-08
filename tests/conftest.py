"""
Shared test fixtures for outreach-api test suite.

Uses an in-memory SQLite database so tests never touch the real DB.
The FastAPI dependency for get_db is overridden to use the test session.
"""
import os
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure the project root and tests dir are on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.pop("DATABASE_URL", None)  # noqa: E402

# Set a known passphrase hash for tests (bcrypt hash of "charioteer")
if "PASSPHRASE_HASH" not in os.environ:
    import bcrypt as _bcrypt
    os.environ["PASSPHRASE_HASH"] = _bcrypt.hashpw(
        b"charioteer", _bcrypt.gensalt()
    ).decode()

from database import Base, get_db  # noqa: E402
from main import app, create_token  # noqa: E402

# In-memory SQLite using StaticPool so all connections share the same DB
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine
)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables before each test, drop them after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(setup_database):
    """FastAPI test client with patched lifespan to use test engine."""
    import database as db_mod
    import main as main_mod
    with patch.object(main_mod, "engine", test_engine),          patch.object(db_mod, "engine", test_engine):
        with TestClient(app) as c:
            yield c


@pytest.fixture
def auth_headers():
    """Return a valid Bearer token header for authenticated requests."""
    token = create_token({"sub": "testuser", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


from helpers import create_test_business, create_test_event  # noqa: E402, F401
