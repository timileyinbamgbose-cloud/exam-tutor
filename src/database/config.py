"""
Database Configuration
Sets up SQLAlchemy connection and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os

# Database URL - will use SQLite for development if PostgreSQL not available
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/examstutor"
)

# For development/testing, fall back to SQLite if PostgreSQL not available
if not os.getenv("DATABASE_URL"):
    # Check if PostgreSQL is available, otherwise use SQLite
    try:
        engine_test = create_engine(DATABASE_URL, echo=False)
        with engine_test.connect() as conn:
            pass
        engine_test.dispose()
    except Exception as e:
        print(f"PostgreSQL not available ({str(e)}), using SQLite for development")
        DATABASE_URL = "sqlite:///./examstutor.db"

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    echo=True if os.getenv("DEBUG", "True") == "True" else False,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=5,
    max_overflow=10
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables"""
    from src.database import models  # Import models
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
