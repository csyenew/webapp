import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment variables before importing app
os.environ["POSTGRES_USER"] = "test"
os.environ["POSTGRES_PASSWORD"] = "test"
os.environ["POSTGRES_HOST"] = "test"
os.environ["POSTGRES_DB"] = "test"
os.environ["S3_BUCKET"] = "test-bucket"
os.environ["AWS_REGION"] = "us-east-1"

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Mock boto3 client
boto3_mock = MagicMock()
s3_client_mock = MagicMock()
boto3_mock.client.return_value = s3_client_mock

# Apply patch to boto3 before importing any app code
with patch.dict('sys.modules', {'boto3': boto3_mock}):
    # Now import the app and database modules
    from database import Base, get_db
    from main import app

# Create test engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    # Create a test user
    from models import User
    user = User(id=1, username="testuser", email="test@example.com")
    session.add(user)
    session.commit()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with the test database."""
    # Override the get_db dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Session is closed in the db_session fixture
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test client
    from fastapi.testclient import TestClient
    test_client = TestClient(app)
    
    yield test_client
    
    # Clean up
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def s3():
    """Fixture for mocked S3 client."""
    s3_client_mock.put_object.reset_mock()
    s3_client_mock.delete_object.reset_mock()
    s3_client_mock.put_object.return_value = {}
    s3_client_mock.delete_object.return_value = {}
    return s3_client_mock