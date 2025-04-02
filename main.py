from fastapi import FastAPI, File, UploadFile, Depends, Request, HTTPException, status, Body
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import boto3
import json
import os
from sqlalchemy.orm import Session
import logging
from typing import Any
from uuid import UUID

from database import get_db, database_connection
from models import FileRecord
from schema import FileUploadSchema, CustomException
from utils import response
from io import BytesIO
import time
import statsd
from statsd import StatsClient


# Configure logger
# logging.basicConfig(
#     level=logging.INFO,
#     format="[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s",
#     datefmt="%b/%d/%Y %H:%M:%S"
# )
# logger = logging.getLogger("cloud")
import logging.config


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s",
            "datefmt": "%b/%d/%Y %H:%M:%S"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": "ext://sys.stderr"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "filename": "cloudwatch.log",
            "maxBytes": 1024 * 1025 * 50,
            "backupCount": 10,
            "level": "INFO"
        }
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO"
    },
    "loggers": {
        "cloud": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False
        }
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("cloud")

statsd_client = StatsClient('localhost', 8125)

app = FastAPI()

S3_BUCKET_NAME = os.getenv('S3_BUCKET')
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


# Middleware to capture metrics for each API request
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response_obj = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000  # convert to milliseconds

    # Emit custom metrics
    statsd_client.incr('api.request.count')
    statsd_client.timing('api.request.response_time', duration_ms)
    logger.info(f"Request {request.method} {request.url.path} took {duration_ms:.2f}ms")
    return response_obj


@app.exception_handler(CustomException)
async def handle_custom_exception(request, exc: CustomException):
    return JSONResponse(
        status_code=exc.status_code, content=exc.msg
    )

@app.get("/healthz")
async def health_check():

    if not database_connection():
        return response("Database is not connected", status.HTTP_503_SERVICE_UNAVAILABLE, no_content=True)
    return response("Database is connected", status.HTTP_200_OK, log_level="info", no_content=True)

@app.post("/v1/file")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a profile picture for a user"""
    try:
        # Generate a unique filename
        new_image = FileRecord(
            file_name=file.filename,
            url=None,
        )

        db.add(new_image)
        db.commit()

        s3_key = f"{S3_BUCKET_NAME}/{new_image.id}/{file.filename}"

        # file_content = await file.read()
        
        # Upload to S3 with metadata
        s3_client = boto3.Session(profile_name='dev').client("s3") if USE_PROFILE else boto3.client("s3")
        s3_client.put_object(Body=await file.read(), Bucket=S3_BUCKET_NAME, Key=f"{new_image.id}/{file.filename}")

        new_image.url = s3_key

        db.add(new_image)
        db.commit()
        
        logger.info(f"File uploaded: {file.filename} → {s3_key}")
        
        return_data = json.loads(
        json.dumps(db.query(FileRecord).filter_by(id=new_image.id).first().to_dict(),
               indent=4, sort_keys=True, default=str))

        return response("Image uploaded Successfully", status.HTTP_201_CREATED, return_data, log_level="info")
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=f"Error uploading file: {str(e)}"
        )

@app.get("/v1/file/{id}")
def get_file(id: str, db: Session = Depends(get_db)):
    """Get file information by file ID"""
    try:
        file_record = db.query(FileRecord).filter_by(id=id).first()
    except:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    if not file_record:
        logger.warning(f"File not found: ID {id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return_data = json.loads(
        json.dumps(file_record.to_dict(), indent=4, sort_keys=True, default=str))

    return response("Image retrived Successfully", status.HTTP_200_OK, return_data, log_level="info")

@app.delete("/v1/file/{id}")
def delete_file(id: str, db: Session = Depends(get_db)):
    """Delete a file by ID"""
    try:
        file_record = db.query(FileRecord).filter_by(id=id).first()
    except:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    if not file_record:
        logger.warning(f"File not found: ID {id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    try:
        # Delete from S3
        s3_client = boto3.Session(profile_name='dev').client("s3") if USE_PROFILE else boto3.client("s3")
        s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=f"{file_record.id}/{file_record.file_name}")
        
        # Delete from database
        db.delete(file_record)
        db.commit()
        
        logger.info(f"File deleted: {file_record.file_name}")
        return response("Image deleted successfully", status.HTTP_204_NO_CONTENT, log_level="info", no_content=True)
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=f"Error deleting file: {str(e)}"
        )
    
# Edge cases for unsupported methods
@app.head("/v1/file", status_code=405)
@app.options("/v1/file", status_code=405)
@app.patch("/v1/file", status_code=405)
@app.put("/v1/file", status_code=405)
@app.head("/v1/file/{id}", status_code=405)
@app.options("/v1/file/{id}", status_code=405)
@app.patch("/v1/file/{id}", status_code=405)
@app.put("/v1/file/{id}", status_code=405)
@app.post("/v1/file/{id}", status_code=405)
async def method_not_allowed():
    return {"detail": "Method Not Allowed"}

# Handle missing parameters for GET and DELETE
@app.get("/v1/file")
async def get_files():
    """Reject GET requests to /v1/file without an ID"""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Bad Request: ID is required"
    )

@app.delete("/v1/file")
async def delete_files():
    """Reject DELETE requests to /v1/file without an ID"""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Bad Request: ID is required"
    )