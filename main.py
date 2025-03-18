from fastapi import FastAPI, File, UploadFile, Depends, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import boto3
import uuid
import os
from sqlalchemy.orm import Session
import logging

from database import get_db
from models import FileRecord
from schema import FileUploadSchema
from utils import response

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s",
    datefmt="%b/%d/%Y %H:%M:%S"
)
logger = logging.getLogger("cloud")

app = FastAPI()

S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
USE_PROFILE = os.getenv('USE_PROFILE', False)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    dct = {}
    for error in exc.errors():
        dct[error["loc"][1]] = error["msg"]

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=dct,
    )

@app.exception_handler(CustomException)
async def handle_custom_exception(request, exc: CustomException):
    return JSONResponse(
        status_code=exc.status_code, content=exc.msg
    )

@app.get("/healthz")
async def health_check():
    return response(True, "Health check successful", status.HTTP_200_OK, log_level="info")

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