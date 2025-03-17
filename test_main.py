import io
from fastapi import status
from models import FileRecord

# All fixtures are imported from conftest.py

def test_health_check(client):
    """Test the health check endpoint"""
    response = client.get('/healthz')
    assert response.status_code == status.HTTP_200_OK
    assert 'status' in response.json()
    assert response.json()['status'] == 'healthy'

def test_upload_file(client, db_session, s3):
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
    s3.put_object.assert_called_once()
    
    # Check response
    assert response.status_code == status.HTTP_201_CREATED
    assert "filename" in response.json()
    assert "s3_url" in response.json()
    assert response.json()["filename"] == "test.txt"
    
    # Verify file record was created in database
    file_record = db_session.query(FileRecord).first()
    assert file_record is not None
    assert file_record.filename == "test.txt"

def test_get_file(client, db_session):
    """Test get file endpoint"""
    # Add a file record directly to the database
    file_record = FileRecord(
        id=1,
        filename="test.txt",
        s3_key="profile_pics/1/test.txt",
        s3_url="https://test-bucket.s3.amazonaws.com/profile_pics/1/test.txt",
        user_id=1
    )
    db_session.add(file_record)
    db_session.commit()
    
    # Get the file
    response = client.get("/v1/user/1/pic/1")
    
    # Check response
    assert response.status_code == status.HTTP_200_OK
    assert "filename" in response.json()
    assert "s3_url" in response.json()
    assert response.json()["filename"] == "test.txt"

def test_get_file_not_found(client):
    """Test get file that doesn't exist"""
    response = client.get("/v1/user/1/pic/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_delete_file(client, db_session, s3):
    """Test delete file endpoint"""
    # Add a file record directly to the database
    file_record = FileRecord(
        id=1,
        filename="test.txt",
        s3_key="profile_pics/1/test.txt",
        s3_url="https://test-bucket.s3.amazonaws.com/profile_pics/1/test.txt",
        user_id=1
    )
    db_session.add(file_record)
    db_session.commit()
    
    # Delete the file
    response = client.delete("/v1/user/1/pic/1")
    
    # Check S3 client was called
    s3.delete_object.assert_called_once()
    
    # Check response
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify file record was deleted from database
    file_record = db_session.query(FileRecord).filter_by(id=1).first()
    assert file_record is None