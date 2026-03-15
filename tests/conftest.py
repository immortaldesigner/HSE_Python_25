import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.redis_client import redis_client

redis_client.incr = AsyncMock(return_value=1)
redis_client.get = AsyncMock(return_value=None)
redis_client.set = AsyncMock()
redis_client.expire = AsyncMock()
redis_client.delete = AsyncMock()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base, get_db
from app.services.security import get_current_user, get_current_user_optional
from fastapi.testclient import TestClient

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = 1
    user.username = "test_user"
    return user

@pytest.fixture(scope="function")
def client(db_session, mock_user):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_user_optional] = lambda: mock_user
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()