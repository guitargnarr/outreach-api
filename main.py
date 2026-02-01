"""
Outreach CRM API
Hidden dashboard backend for projectlavos.com client outreach tracking
"""
import csv
import io
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import bcrypt as _bcrypt
from pydantic import BaseModel
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Session, relationship

from database import Base, engine, get_db

# --- Config ---

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 7


def _hash_pw(pw: str) -> str:
    return _bcrypt.hashpw(pw.encode(), _bcrypt.gensalt()).decode()


def _verify_pw(pw: str, hashed: str) -> bool:
    return _bcrypt.checkpw(pw.encode(), hashed.encode())


PASSPHRASE_HASH = os.getenv(
    "PASSPHRASE_HASH",
    _hash_pw("charioteer"),  # Default for local dev only
)


# --- Database Models ---


class BusinessDB(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False)
    category = Column(String(100), default="")
    demo_url = Column(String(500), default="")
    existing_website = Column(String(500), default="")
    website_quality = Column(Integer, default=0)
    priority = Column(String(20), default="cold")  # hot/warm/cold
    status = Column(String(30), default="prospect")
    contact_name = Column(String(200), default="")
    contact_email = Column(String(200), default="")
    contact_phone = Column(String(50), default="")
    contact_role = Column(String(100), default="")
    demo_value_prop = Column(Text, default="")
    notes = Column(Text, default="")
    portfolio_card_id = Column(String(100), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    events = relationship(
        "OutreachEventDB", back_populates="business", cascade="all, delete-orphan"
    )


class OutreachEventDB(Base):
    __tablename__ = "outreach_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    details = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    business = relationship("BusinessDB", back_populates="events")


# --- Pydantic Models ---


class LoginRequest(BaseModel):
    passphrase: str


class BusinessCreate(BaseModel):
    name: str
    slug: str | None = None
    category: str = ""
    demo_url: str = ""
    existing_website: str = ""
    website_quality: int = 0
    priority: str = "cold"
    status: str = "prospect"
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    contact_role: str = ""
    demo_value_prop: str = ""
    notes: str = ""
    portfolio_card_id: str = ""


class BusinessUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    demo_url: str | None = None
    existing_website: str | None = None
    website_quality: int | None = None
    priority: str | None = None
    status: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    contact_role: str | None = None
    demo_value_prop: str | None = None
    notes: str | None = None
    portfolio_card_id: str | None = None


class BusinessOut(BaseModel):
    id: int
    name: str
    slug: str
    category: str
    demo_url: str
    existing_website: str
    website_quality: int
    priority: str
    status: str
    contact_name: str
    contact_email: str
    contact_phone: str
    contact_role: str
    demo_value_prop: str
    notes: str
    portfolio_card_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EventCreate(BaseModel):
    event_type: str
    details: str = ""


class EventOut(BaseModel):
    id: int
    business_id: int
    event_type: str
    details: str
    created_at: datetime

    class Config:
        from_attributes = True


class BusinessDetail(BusinessOut):
    events: list[EventOut] = []


class SyncItem(BaseModel):
    name: str
    slug: str | None = None
    category: str = ""
    demo_url: str = ""
    existing_website: str = ""
    website_quality: int = 0
    priority: str = "cold"
    status: str = "prospect"
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    contact_role: str = ""
    demo_value_prop: str = ""
    notes: str = ""
    portfolio_card_id: str = ""


# --- Auth Helpers ---


def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_auth(authorization: str = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    token = authorization.replace("Bearer ", "")
    return verify_token(token)


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


# --- App Setup ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Outreach CRM API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Auth Endpoints ---


@app.post("/auth/login")
def login(req: LoginRequest):
    if _verify_pw(req.passphrase, PASSPHRASE_HASH):
        token = create_token({"sub": "charioteer", "role": "admin"})
        return {"token": token, "expires_in": JWT_EXPIRY_DAYS * 86400}
    raise HTTPException(status_code=401, detail="Access denied")


@app.get("/auth/verify")
def verify_auth(user: dict = Depends(require_auth)):
    return {"valid": True, "user": user.get("sub")}


# --- Business CRUD ---


@app.get("/businesses", response_model=list[BusinessOut])
def list_businesses(
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    search: str | None = None,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    query = db.query(BusinessDB)
    if status:
        query = query.filter(BusinessDB.status == status)
    if category:
        query = query.filter(BusinessDB.category.ilike(f"%{category}%"))
    if priority:
        query = query.filter(BusinessDB.priority == priority)
    if search:
        query = query.filter(
            BusinessDB.name.ilike(f"%{search}%")
            | BusinessDB.notes.ilike(f"%{search}%")
        )
    return query.order_by(BusinessDB.updated_at.desc()).all()


@app.get("/businesses/{business_id}", response_model=BusinessDetail)
def get_business(
    business_id: int,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    biz = db.query(BusinessDB).filter(BusinessDB.id == business_id).first()
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")
    events = (
        db.query(OutreachEventDB)
        .filter(OutreachEventDB.business_id == business_id)
        .order_by(OutreachEventDB.created_at.desc())
        .all()
    )
    return BusinessDetail(
        **{c.name: getattr(biz, c.name) for c in biz.__table__.columns},
        events=[EventOut.model_validate(e) for e in events],
    )


@app.post("/businesses", response_model=BusinessOut)
def create_business(
    data: BusinessCreate,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    slug = data.slug or slugify(data.name)
    existing = db.query(BusinessDB).filter(BusinessDB.slug == slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Business with this slug exists")
    biz = BusinessDB(slug=slug, **data.model_dump(exclude={"slug"}))
    db.add(biz)
    db.commit()
    db.refresh(biz)
    return biz


@app.put("/businesses/{business_id}", response_model=BusinessOut)
def update_business(
    business_id: int,
    data: BusinessUpdate,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    biz = db.query(BusinessDB).filter(BusinessDB.id == business_id).first()
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")
    update_data = data.model_dump(exclude_none=True)
    for key, val in update_data.items():
        setattr(biz, key, val)
    biz.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(biz)
    return biz


@app.delete("/businesses/{business_id}")
def delete_business(
    business_id: int,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    biz = db.query(BusinessDB).filter(BusinessDB.id == business_id).first()
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")
    db.delete(biz)
    db.commit()
    return {"status": "deleted", "id": business_id}


# --- Events ---


@app.post("/businesses/{business_id}/events", response_model=EventOut)
def create_event(
    business_id: int,
    data: EventCreate,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    biz = db.query(BusinessDB).filter(BusinessDB.id == business_id).first()
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")
    event = OutreachEventDB(business_id=business_id, **data.model_dump())
    db.add(event)
    biz.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(event)
    return event


# --- Metrics ---


@app.get("/metrics")
def get_metrics(
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    total = db.query(BusinessDB).count()

    # Status breakdown
    status_counts = {}
    for s in ["prospect", "contacted", "responded", "meeting", "closed", "lost"]:
        status_counts[s] = (
            db.query(BusinessDB).filter(BusinessDB.status == s).count()
        )

    # Priority breakdown
    priority_counts = {}
    for p in ["hot", "warm", "cold"]:
        priority_counts[p] = (
            db.query(BusinessDB).filter(BusinessDB.priority == p).count()
        )

    # Category breakdown
    cat_rows = (
        db.query(BusinessDB.category, func.count(BusinessDB.id))
        .group_by(BusinessDB.category)
        .all()
    )
    category_counts = {row[0] or "Uncategorized": row[1] for row in cat_rows}

    # Activity timeline (events per week, last 8 weeks)
    eight_weeks_ago = datetime.now(timezone.utc) - timedelta(weeks=8)
    recent_events = (
        db.query(OutreachEventDB)
        .filter(OutreachEventDB.created_at >= eight_weeks_ago)
        .all()
    )
    weekly_activity = {}
    for event in recent_events:
        week = event.created_at.strftime("%Y-W%W")
        weekly_activity[week] = weekly_activity.get(week, 0) + 1

    # Total events
    total_events = db.query(OutreachEventDB).count()

    # Response rate
    contacted = status_counts.get("contacted", 0)
    responded = status_counts.get("responded", 0)
    meeting = status_counts.get("meeting", 0)
    closed = status_counts.get("closed", 0)
    active_outreach = contacted + responded + meeting
    response_rate = (
        round((responded + meeting + closed) / max(active_outreach + closed, 1) * 100)
    )

    return {
        "total": total,
        "by_status": status_counts,
        "by_priority": priority_counts,
        "by_category": category_counts,
        "weekly_activity": weekly_activity,
        "total_events": total_events,
        "active_outreach": active_outreach,
        "response_rate": response_rate,
        "meetings_set": meeting,
    }


# --- Sync ---


@app.post("/sync")
def sync_businesses(
    items: list[SyncItem],
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    created = 0
    updated = 0
    for item in items:
        slug = item.slug or slugify(item.name)
        existing = db.query(BusinessDB).filter(BusinessDB.slug == slug).first()
        if existing:
            data = item.model_dump(exclude={"slug"}, exclude_unset=True)
            for key, val in data.items():
                if val:  # Only update non-empty fields
                    setattr(existing, key, val)
            existing.updated_at = datetime.now(timezone.utc)
            updated += 1
        else:
            biz = BusinessDB(slug=slug, **item.model_dump(exclude={"slug"}))
            db.add(biz)
            created += 1
    db.commit()
    return {"created": created, "updated": updated, "total": created + updated}


# --- Export ---


@app.get("/export/csv")
def export_csv(
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    businesses = db.query(BusinessDB).order_by(BusinessDB.name).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Name", "Slug", "Category", "Demo URL", "Existing Website",
        "Website Quality", "Priority", "Status", "Contact Name",
        "Contact Email", "Contact Phone", "Contact Role",
        "Demo Value Prop", "Notes", "Created", "Updated",
    ])
    for biz in businesses:
        writer.writerow([
            biz.name, biz.slug, biz.category, biz.demo_url,
            biz.existing_website, biz.website_quality, biz.priority,
            biz.status, biz.contact_name, biz.contact_email,
            biz.contact_phone, biz.contact_role, biz.demo_value_prop,
            biz.notes, biz.created_at, biz.updated_at,
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=outreach_export.csv"},
    )


# --- Health ---


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "service": "outreach-api",
    }


@app.get("/")
def root():
    return {
        "service": "Outreach CRM API",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
