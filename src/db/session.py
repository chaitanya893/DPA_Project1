from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from config.settings import DATABASE_URL
from src.db.models import Base
from src.utils.logger import setup_logger

logger = setup_logger("db_session")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    # SQLite-specific connect_args if SQLite is used
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


def init_db() -> None:
    """Creates all database tables if they do not exist."""
    logger.info(f"Initializing database schema at {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized successfully.")


def get_db():
    """Generator for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
