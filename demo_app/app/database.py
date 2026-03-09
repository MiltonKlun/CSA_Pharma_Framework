import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base

# Use environment variable or default to local sqlite for dev convenience if not using docker
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pharma_qms.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

from .audit_trail import track_changes
event.listen(Session, "before_flush", track_changes)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
