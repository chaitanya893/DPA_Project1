import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Boolean,
    Text,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class CompanyUniverse(Base):
    """Company Master Universe (25 companies)."""
    __tablename__ = "company_universe"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(255), nullable=False)
    ticker = Column(String(20), nullable=False, unique=True)
    exchange = Column(String(50), nullable=False)
    country = Column(String(10), nullable=False)
    cik_or_sedar_id = Column(String(30), nullable=False)
    ir_page_url = Column(String(500), nullable=False)
    market_cap_bucket = Column(String(50), nullable=False)
    expected_call_language = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    # Relationships
    events = relationship("EventRegistry", back_populates="company", cascade="all, delete-orphan")


class EventRegistry(Base):
    """Phase 1 Deliverable: Event Registry for discovered earnings calls."""
    __tablename__ = "event_registry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("company_universe.id"), nullable=False)
    ticker = Column(String(20), nullable=False)
    fiscal_period = Column(String(50), nullable=True)  # e.g., 'Q3 FY2024' or NULL if unannounced
    call_datetime_utc = Column(DateTime, nullable=True)
    timezone_as_published = Column(String(50), nullable=True)
    webcast_url = Column(Text, nullable=True)
    dial_in_available = Column(Boolean, nullable=True, default=None)
    replay_url = Column(Text, nullable=True)
    replay_expiry_date = Column(DateTime, nullable=True)
    registration_required = Column(Boolean, nullable=True, default=None)
    vendor = Column(String(100), nullable=True)  # Q4 Inc, Notified, Nasdaq IR, Investis, Kaltura, Zoom Events, Custom
    discovery_source = Column(String(100), nullable=False)  # SEC_EDGAR_8K, IR_PAGE, NEWSWIRE, VENDOR_PLATFORM
    announced_at_utc = Column(DateTime, nullable=True)
    lead_time_hours = Column(Float, nullable=True)
    discovered_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    confidence = Column(Float, nullable=False, default=1.0)  # 0.0 to 1.0

    company = relationship("CompanyUniverse", back_populates="events")


class CrawlLog(Base):
    """Immutable crawl and attempt logs."""
    __tablename__ = "crawl_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(255), nullable=False)
    target_url = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    http_status = Column(Integer, nullable=True)
    outcome = Column(String(50), nullable=False)  # SUCCESS, BLOCKED, FAILED, PARSE_ERROR
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    correlation_id = Column(String(50), nullable=True)
