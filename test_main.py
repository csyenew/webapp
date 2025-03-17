from fastapi.testclient import TestClient
from fastapi import status
import pytest
import os
import io
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import app but patch S3 and database before app initializes
with patch("boto3.client"):
    from main import app
    from database import get_db, Base

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

# Override the get_db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Set test environment variables
os.environ["S3_BUCKET"] = "test-bucket"
os.environ["AWS_REGION"] = "us-east-1"

# Mock S3 client
@pytest.fixture(autouse=True)
def mock_s3():
    with patch("main.s3_client") as mock_s3:
        mock_s3.put_object.return_value = {}
        mock_s3.delete_object.return_value = {}
        yield mock_s3

# Create test client
client = TestClient(app)

def test_health_check():
    """Test the health check endpoint"""
    response = client.get('/healthz')
    assert response.status_code == status.HTTP_200_OK
    assert 'status' in response.json()
    assert response.json()['status'] == 'healthy'

def test_upload_file(mock_s3):
    """Test file upload endpoint"""
    # Create a test file
    test_file = io.BytesIO(b"test file content")
    test_file.name = "test.txt"
    
    # Make request
    response = client.post(
        "/v1/user/1/pic",
        files={"file": (test_file.name, test_file, "text/plain")}
    )
    
    # Check S3 client was called
    mock_s3.put_object.assert_called_once()
    
    # Check response
    assert response.status_code == status.HTTP_201_CREATED
    assert "filename" in response.json()
    assert "s3_url" in response.json()
    assert response.json()["filename"] == "test.txt"

def test_get_file():
    """Test get file endpoint"""
    # Add a file record directly to the database
    db = TestingSessionLocal()
    # First ensure user exists
    from models import User, FileRecord
    
    # Check if user exists, add if not
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(id=1, username="testuser", email="test@example.com")
        db.add(user)
    
    # Add file record
    file_record = FileRecord(
        id=1,
        filename="test.txt",
        s3_key="profile_pics/1/test.txt",
        s3_url="https://test-bucket.s3.amazonaws.com/profile_pics/1/test.txt",
        user_id=1
    )
    db.add(file_record)
    db.commit()
    
    # Get the file
    response = client.get("/v1/user/1/pic/1")
    
    # Clean up
    db.query(FileRecord).delete()
    db.commit()
    db.close()
    
    # Check response
    assert response.status_code == status.HTTP_200_OK
    assert "filename" in response.json()
    assert "s3_url" in response.json()

def test_delete_file(mock_s3):
    """Test delete file endpoint"""
    # Add a file record directly to the database
    db = TestingSessionLocal()
    
    # First ensure user exists
    from models import User, FileRecord
    
    # Check if user exists, add if not
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(id=1, username="testuser", email="test@example.com")
        db.add(user)
    
    # Add file record
    file_record = FileRecord(
        id=1,
        filename="test.txt",
        s3_key="profile_pics/1/test.txt",
        s3_url="https://test-bucket.s3.amazonaws.com/profile_pics/1/test.txt",
        user_id=1
    )
    db.add(file_record)
    db.commit()
    
    # Delete the file
    response = client.delete("/v1/user/1/pic/1")
    
    # Clean up
    db.close()
    
    # Check S3 client was called
    mock_s3.delete_object.assert_called_once()
    
    # Check response
    assert response.status_code == status.HTTP_204_NO_CONTENT