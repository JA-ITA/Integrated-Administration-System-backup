"""
Test configuration and fixtures for ITADIAS Identity Microservice
"""
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
import httpx
from fastapi.testclient import TestClient

from database import Base
from app import app
from models import Candidate, OTPVerification
from services.event_service import EventService

# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_db_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()

@pytest.fixture
async def test_db_session(test_db_engine):
    """Create test database session"""
    async_session_maker = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session

@pytest.fixture
def test_client():
    """Create test client"""
    with TestClient(app) as client:
        yield client

@pytest.fixture
async def async_test_client():
    """Create async test client"""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def sample_candidate_data():
    """Sample candidate data for testing"""
    return {
        "email": "test@example.com",
        "phone": "+1234567890",
        "first_name": "John",
        "last_name": "Doe",
        "send_otp": True,
        "otp_channel": "email"
    }

@pytest.fixture
async def created_candidate(test_db_session, sample_candidate_data):
    """Create a test candidate in the database"""
    candidate = Candidate(
        email=sample_candidate_data["email"],
        phone=sample_candidate_data["phone"],
        first_name=sample_candidate_data["first_name"],
        last_name=sample_candidate_data["last_name"]
    )
    
    test_db_session.add(candidate)
    await test_db_session.commit()
    await test_db_session.refresh(candidate)
    
    return candidate

@pytest.fixture
def mock_event_service():
    """Mock event service for testing"""
    class MockEventService:
        def __init__(self):
            self.published_events = []
        
        async def initialize(self):
            pass
        
        async def close(self):
            pass
        
        async def publish_candidate_created(self, candidate):
            self.published_events.append({
                "event_type": "CandidateCreated",
                "candidate_id": str(candidate.id)
            })
            return True
        
        async def publish_candidate_verified(self, candidate):
            self.published_events.append({
                "event_type": "CandidateVerified", 
                "candidate_id": str(candidate.id)
            })
            return True
    
    return MockEventService()

@pytest.fixture
def override_dependencies(test_db_session, mock_event_service):
    """Override app dependencies for testing"""
    from database import get_db
    
    async def override_get_db():
        yield test_db_session
    
    app.dependency_overrides[get_db] = override_get_db
    app.state.event_service = mock_event_service
    
    yield
    
    app.dependency_overrides.clear()