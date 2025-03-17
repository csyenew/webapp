from fastapi.testclient import TestClient
from fastapi import status
import pytest
import os
import io
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import app and database components
from main import app
from database import get_db, Base
from models import User, FileRecord

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test tables
Base.metadata.create_all(bind=engine)

# Override the dependency to use test database
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)

# Mock environment variables
os.environ["S3_BUCKET"] = "test-bucket"
os.environ["AWS_REGION"] = "us-east-1"

@pytest.fixture
def test_db():
    # Create fresh tables for each test
    Base.metadata.create_all(bind=engine)
    
    # Add test user
    db = TestingSessionLocal()
    test_user = User(id=1, username="testuser", email="test@example.com")
    db.add(test_user)
    db.commit()
    
    yield db
    
    # Clean up
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def mock_s3():
    with patch("main.s3_client") as mock_s3:
        # Mock the S3 client responses
        mock_s3.put_object.return_value = {}
        mock_s3.delete_object.return_value = {}
        yield mock_s3

@pytest.fixture
def test_file():
    # Create a test file for upload
    content = b"test file content"
    file = io.BytesIO(content)
    file.name = "test.txt"
    return file

def test_health_check(test_db):
    """Test the health check endpoint"""
    response = client.get('/healthz')
    assert response.status_code == status.HTTP_200_OK
    assert 'status' in response.json()
    assert response.json()['status'] == 'healthy'

def test_upload_file(test_db, mock_s3, test_file):
    """Test file upload endpoint"""
    # Prepare test file
    files = {"file": (test_file.name, test_file, "text/plain")}
    
    # Make request
    response = client.post(
        "/v1/user/1/pic",
        files=files
    )
    
    # Verify S3 was called correctly
    mock_s3.put_object.assert_called_once()
    call_kwargs = mock_s3.put_object.call_args.kwargs
    assert call_kwargs["Bucket"] == "test-bucket"
    assert "profile_pics/1/" in call_kwargs["Key"]
    
    # Check response
    assert response.status_code == status.HTTP_201_CREATED
    assert "filename" in response.json()
    assert response.json()["filename"] == "test.txt"
    assert "s3_url" in response.json()
    
    # Verify database entry was created
    db = test_db
    file_record = db.query(FileRecord).first()
    assert file_record is not None
    assert file_record.filename == "test.txt"
    assert file_record.user_id == 1

def test_get_file(test_db):
    """Test get file endpoint"""
    # Add a test file record to the database
    db = test_db
    file_record = FileRecord(
        id=1,
        filename="test.txt",
        s3_key="profile_pics/1/test.txt",
        s3_url=f"https://test-bucket.s3.amazonaws.com/profile_pics/1/test.txt",
        user_id=1
    )
    db.add(file_record)
    db.commit()
    
    # Get the file
    response = client.get("/v1/user/1/pic/1")
    
    # Check response
    assert response.status_code == status.HTTP_200_OK
    assert "filename" in response.json()
    assert "s3_url" in response.json()
    assert response.json()["filename"] == "test.txt"

def test_get_file_not_found(test_db):
    """Test getting a non-existent file"""
    response = client.get("/v1/user/1/pic/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_get_file_wrong_user(test_db):
    """Test getting a file with wrong user ID"""
    # Add a test file record to the database
    db = test_db
    file_record = FileRecord(
        id=1,
        filename="test.txt",
        s3_key="profile_pics/1/test.txt",
        s3_url=f"https://test-bucket.s3.amazonaws.com/profile_pics/1/test.txt",
        user_id=1
    )
    db.add(file_record)
    db.commit()
    
    # Try to get file with wrong user ID
    response = client.get("/v1/user/2/pic/1")
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_delete_file(test_db, mock_s3):
    """Test delete file endpoint"""
    # Add a test file record to the database
    db = test_db
    file_record = FileRecord(
        id=1,
        filename="test.txt",
        s3_key="profile_pics/1/test.txt",
        s3_url=f"https://test-bucket.s3.amazonaws.com/profile_pics/1/test.txt",
        user_id=1
    )
    db.add(file_record)
    db.commit()
    
    # Delete the file
    response = client.delete("/v1/user/1/pic/1")
    
    # Check response
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify S3 delete was called
    mock_s3.delete_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="profile_pics/1/test.txt"
    )
    
    # Verify database record was deleted
    file_record = db.query(FileRecord).get(1)
    assert file_record is None

def test_delete_file_not_found(test_db, mock_s3):
    """Test deleting a non-existent file"""
    response = client.delete("/v1/user/1/pic/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    mock_s3.delete_object.assert_not_called()