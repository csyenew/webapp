from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status
from fastapi.responses import JSONResponse
import boto3
import uuid
import os
from sqlalchemy.orm import Session
import logging

from database import get_db, engine, init_db
from models import Base, FileRecord
from schema import FileUploadSchema

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s",
    datefmt="%b/%d/%Y %H:%M:%S"
)
logger = logging.getLogger("cloud")

# Initialize database tables
init_db()

app = FastAPI(title="File Upload API")

# Get S3 bucket name from environment variable
S3_BUCKET = os.getenv("S3_BUCKET", "")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Create S3 client using IAM role (no credentials needed)
s3_client = boto3.client('s3', region_name=AWS_REGION)

@app.get("/healthz", status_code=200)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint to verify database connection"""
    try:
        # Check database connection
        db.execute("SELECT 1")
        logger.info("Database is connected 200")
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Database is not connected: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error"
        )

@app.post("/v1/user/{user_id}/pic", response_model=FileUploadSchema, status_code=201)
async def upload_file(
    user_id: int, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    """Upload a profile picture for a user"""
    try:
        # Generate a unique filename
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        s3_key = f"profile_pics/{user_id}/{unique_filename}"
        
        # Read file content
        file_content = await file.read()
        
        # Upload to S3 with metadata
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=file_content,
            ContentType=file.content_type,
            Metadata={
                "user_id": str(user_id),
                "original_filename": file.filename
            }
        )
        
        # Create S3 URL
        s3_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{s3_key}"
        
        # Save file metadata to database
        file_record = FileRecord(
            filename=file.filename,
            s3_key=s3_key,
            s3_url=s3_url,
            user_id=user_id
        )
        db.add(file_record)
        db.commit()
        db.refresh(file_record)
        
        logger.info(f"File uploaded: {file.filename} → {s3_url}")
        
        return {
            "filename": file_record.filename,
            "s3_url": file_record.s3_url
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )

@app.get("/v1/user/{user_id}/pic/{file_id}", response_model=FileUploadSchema)
def get_file(user_id: int, file_id: int, db: Session = Depends(get_db)):
    """Get file information by file ID"""
    file_record = db.query(FileRecord).filter(
        FileRecord.id == file_id, 
        FileRecord.user_id == user_id
    ).first()
    
    if not file_record:
        logger.warning(f"File not found: ID {file_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or access denied"
        )
    
    return {
        "filename": file_record.filename,
        "s3_url": file_record.s3_url
    }

@app.delete("/v1/user/{user_id}/pic/{file_id}", status_code=204)
def delete_file(user_id: int, file_id: int, db: Session = Depends(get_db)):
    """Delete a file by ID"""
    file_record = db.query(FileRecord).filter(
        FileRecord.id == file_id, 
        FileRecord.user_id == user_id
    ).first()
    
    if not file_record:
        logger.warning(f"Attempted to delete non-existent file: ID {file_id} for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or access denied"
        )
    
    try:
        # Delete from S3
        s3_client.delete_object(
            Bucket=S3_BUCKET,
            Key=file_record.s3_key
        )
        
        # Delete from database
        db.delete(file_record)
        db.commit()
        
        logger.info(f"File deleted: {file_record.filename}")
        return None
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting file: {str(e)}"
        )