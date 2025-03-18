import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# Add the project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Mock boto3 client
mock_s3 = MagicMock()
mock_s3.put_object.return_value = {}
mock_s3.delete_object.return_value = {}

@pytest.fixture
def client():
    """Test client fixture that connects to the test database"""
    # Import here to avoid circular imports
    from fastapi.testclient import TestClient
    from main import app
    
    return TestClient(app)

@pytest.fixture
def db():
    """Database session fixture for testing"""
    # Import here to avoid circular imports
    from database import SessionLocal
    
    # Create a fresh session for each test
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def s3_client():
    """Mock S3 client fixture"""
    with patch("main.s3_client", mock_s3):
        yield mock_s3