from fastapi.testclient import TestClient
from fastapi import status
import pytest
import os
import io
from main import app

client = TestClient(app)

def test_health_check():
    """Test the health check endpoint"""
    response = client.get('/healthz')
    assert response.status_code == status.HTTP_200_OK
    assert 'status' in response.json()
    assert response.json()['status'] == 'healthy'

def test_upload_file():
    """Test file upload endpoint"""
    # Create a test file
    test_file = io.BytesIO(b"test file content")
    test_file.name = "test.txt"
    
    # Make request
    response = client.post(
        "/v1/user/1/pic",
        files={"file": (test_file.name, test_file, "text/plain")}
    )
    
    # Check response
    assert response.status_code == status.HTTP_201_CREATED
    assert "filename" in response.json()
    assert "s3_url" in response.json()
    assert response.json()["filename"] == "test.txt"

def test_get_file():
    """Test get file endpoint"""
    # First upload a file to get its ID
    test_file = io.BytesIO(b"test file content")
    test_file.name = "test.txt"
    upload_response = client.post(
        "/v1/user/1/pic",
        files={"file": (test_file.name, test_file, "text/plain")}
    )
    
    # Get file ID from database or mock it
    file_id = 1  # This would come from the database in a real test
    
    # Get the file
    response = client.get(f"/v1/user/1/pic/{file_id}")
    
    # Check response
    assert response.status_code == status.HTTP_200_OK
    assert "filename" in response.json()
    assert "s3_url" in response.json()

def test_delete_file():
    """Test delete file endpoint"""
    # First upload a file to get its ID
    test_file = io.BytesIO(b"test file content")
    test_file.name = "test.txt"
    upload_response = client.post(
        "/v1/user/1/pic",
        files={"file": (test_file.name, test_file, "text/plain")}
    )
    
    # Get file ID from database or mock it
    file_id = 1  # This would come from the database in a real test
    
    # Delete the file
    response = client.delete(f"/v1/user/1/pic/{file_id}")
    
    # Check response
    assert response.status_code == status.HTTP_204_NO_CONTENT