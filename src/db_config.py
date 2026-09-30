import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .database import Base

# By default, use SQLite for isolated tests or local verification.
# For production (Phase 25 boundary), set DATABASE_URL (e.g. postgresql://...)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./returns_manager.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
