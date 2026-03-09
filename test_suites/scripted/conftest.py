"""
CSA Step 3 — Assurance Activities: Scripted Test Configuration

Provides shared fixtures for all scripted tests:
- Fresh database per test session
- FastAPI TestClient
- Pre-authenticated helper functions for each role
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from demo_app.app.database import Base, get_db
from demo_app.app.main import app
from demo_app.app.models import User, UserRole
from demo_app.app.routes.auth import get_password_hash

# Use a separate in-memory SQLite DB for tests
SQLALCHEMY_TEST_URL = "sqlite:///./test_qms.db"
test_engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="function", autouse=True)
def setup_test_database():
    """Create all tables before each test and drop them after."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture()
def db_session():
    """Provide a clean DB session for each test, rolling back after."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture()
def client(db_session):
    """Provide a FastAPI TestClient wired to the test database."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

# --- Seed helpers ---

def _create_user(db, username, role, password="Testp@ss123"):
    user = User(
        username=username,
        email=f"{username}@test.local",
        full_name=f"Test {username.title()}",
        hashed_password=get_password_hash(password),
        role=role,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture()
def operator_user(db_session):
    return _create_user(db_session, "test_operator", UserRole.OPERATOR)

@pytest.fixture()
def qa_user(db_session):
    return _create_user(db_session, "test_qa", UserRole.QA)

@pytest.fixture()
def manager_user(db_session):
    return _create_user(db_session, "test_manager", UserRole.MANAGER)

@pytest.fixture()
def admin_user(db_session):
    return _create_user(db_session, "test_admin", UserRole.ADMIN)

# --- Auth helpers ---

def get_auth_token(client: TestClient, username: str, password: str = "Testp@ss123") -> str:
    """Authenticate a user and return a Bearer token string."""
    resp = client.post("/auth/token", data={"username": username, "password": password})
    assert resp.status_code == 200, f"Auth failed for {username}: {resp.text}"
    return resp.json()["access_token"]

def auth_headers(client: TestClient, username: str, password: str = "Testp@ss123") -> dict:
    """Return Authorization headers for a given user."""
    token = get_auth_token(client, username, password)
    return {"Authorization": f"Bearer {token}"}
