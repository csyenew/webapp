import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Patch the engine creation BEFORE importing the app
# This prevents the database connection attempt during import

# 1. Create a test SQLite engine
test_engine = create_engine('sqlite:///:memory:')
TestSessionLocal = sessionmaker(bind=test_engine)
TestBase = declarative_base()

# 2. Create patchers for the critical functions
database_module = patch.dict('sys.modules', {
    # Haven't imported these modules yet, so we can patch sys.modules
})

# 3. Apply the patchers
with patch('sqlalchemy.create_engine', return_value=test_engine), \
     patch('sqlalchemy.ext.declarative.declarative_base', return_value=TestBase), \
     patch('sqlalchemy.orm.sessionmaker', return_value=TestSessionLocal), \
     patch('boto3.client'):
    
    # 4. Set environment variables
    os.environ["POSTGRES_USER"] = "test_user"
    os.environ["POSTGRES_PASSWORD"] = "test_password"
    os.environ["POSTGRES_HOST"] = "test_host"
    os.environ["POSTGRES_DB"] = "test_db"
    os.environ["S3_BUCKET"] = "test-bucket"
    os.environ["AWS_REGION"] = "us-east-1"
    
    # 5. Now import the application code
    from database import get_db, Base
    from main import app

# 6. Create test tables in the SQLite database
Base.metadata.create_all(bind=test_engine)

@pytest.fixture
def db():
    # Create a fresh session for each test
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)
    
    # Create a test user if needed
    from models import User
    user = User(id=1, username="testuser", email="test@example.com")
    session.add(user)
    session.commit()
    
    yield session
    
    # Rollback the transaction
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db):
    # Override the get_db dependency
    def override_get_db():
        try:
            yield db
        finally:
            pass  # We're managing the session in the db fixture
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Create and return a test client
    from fastapi.testclient import TestClient
    test_client = TestClient(app)
    
    yield test_client
    
    # Clear the override after the test
    app.dependency_overrides.clear()

@pytest.fixture
def s3_client():
    with patch("main.s3_client") as mock_s3:
        mock_s3.put_object.return_value = {}
        mock_s3.delete_object.return_value = {}
        yield mock_s3