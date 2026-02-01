"""
Database configuration for Outreach API
Neon PostgreSQL + pg8000 driver
"""
import os
import re
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Handle postgres:// vs postgresql:// URL format
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+pg8000" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)

# Remove sslmode from URL (pg8000 handles SSL differently)
if "sslmode=" in DATABASE_URL:
    DATABASE_URL = re.sub(r'[\?&]sslmode=[^&]*', '', DATABASE_URL)
    DATABASE_URL = DATABASE_URL.replace('?&', '?').rstrip('?')

# For local development without database
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./outreach.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    engine = create_engine(DATABASE_URL, connect_args={"ssl_context": ssl_context})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
