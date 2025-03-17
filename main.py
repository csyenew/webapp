# python imports
import base64
from typing import Any
import json
import statsd
from datetime import datetime
import boto3
import os
from botocore.exceptions import NoCredentialsError
# Framework Imports
from fastapi import FastAPI, status, Request, HTTPException, Depends, Header, Body
from sqlalchemy.orm import Session

# Project Imports
from utils import response
from passlib.context import CryptContext
from logging.config import dictConfig
from fastapi.exceptions import RequestValidationError
import logging
from log import LogConfig
from database import database_connection, get_db
from schema import LoginSerializer
import models
from schema import Assignment, CustomException, Submission
from fastapi.responses import JSONResponse

c = statsd.StatsClient()



dictConfig(LogConfig().dict())
logger = logging.getLogger("cloud")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):

    try:
        dct = {}
        for error in exc.errors():
            dct[error["loc"][1]] = error["msg"]

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=dct,
        )
    except Exception as e:
        return response("Paremeters are required", status.HTTP_400_BAD_REQUEST)

@app.exception_handler(CustomException)
async def handle_custom_exception(request, exc: CustomException):
    return JSONResponse(
        status_code=exc.status_code, content=exc.msg
    )


@app.exception_handler(exc_class_or_status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
async def handle_method_not_allowed(request: Request, exc: HTTPException):
    return response("Method Not Allowed", status.HTTP_405_METHOD_NOT_ALLOWED, no_content=True)
    

# Health endpoint
@app.get("/healthz")
async def health_check(payload: Any = Body(None)):

    c.incr("Health")

    if payload:
        return response("Request cannot contain payload", status.HTTP_405_METHOD_NOT_ALLOWED, no_content=True)
    if not database_connection():
        return response("Database is not connected", status.HTTP_503_SERVICE_UNAVAILABLE, no_content=True)
    return response("Database is connected", status.HTTP_200_OK, log_level="info", no_content=True)


def authenticate_user(user: LoginSerializer, db: Session = Depends(get_db)):
    try:
        if not database_connection():
            return response("Database is not connected", status.HTTP_503_SERVICE_UNAVAILABLE, no_content=True)
        if not user.email or not user.password:
            return response("Email and password are required", status.HTTP_400_BAD_REQUEST)

        stored_user = db.query(models.User).filter_by(email=user.email).first()
        if not stored_user:
            return response("Incorrect email or password", status.HTTP_401_UNAUTHORIZED)

        if not pwd_context.verify(user.password, stored_user.password):
            return response("Incorrect email or password", status.HTTP_401_UNAUTHORIZED)

        # generate token
        token = base64.b64encode(
            f'{user.email}:{user.password}'.encode()).decode()

        # return response with token and user data
        return response( "Login Successful", status.HTTP_200_OK, data={
            "first_name": stored_user.first_name,
            "last_name": stored_user.last_name,
            "email": stored_user.email
        }, headers={
            "access-token": token
        })
    except Exception as e:
        return response( str(e), status.HTTP_408_REQUEST_TIMEOUT)


@app.post("/v3/user/login")
def login(user: LoginSerializer, auth: str = Depends(authenticate_user)):
    return auth



############################################################################################

@app.post("/v3/assignments")
def create_assignment(assignment: Assignment, authorization: str = Header(None),  db: Session = Depends(get_db)):
    c.incr("Create_Assignment")
    try:
        if not database_connection():
            return response("Database is not connected", status.HTTP_503_SERVICE_UNAVAILABLE, no_content=True)
        
        assignment_data = assignment.dict()
        
        if any(item not in ["name", "points", "num_of_attemps", "deadline"] for item in assignment_data.keys()):
            return response( "Please provide correct parameters", status.HTTP_400_BAD_REQUEST)

        if authorization is None:
            return response( "Authorization header missing", status.HTTP_400_BAD_REQUEST)

        auth_type, encoded_code = authorization.split(" ")
        if auth_type != "Basic":
            return response( "Authorization type not supported", status.HTTP_400_BAD_REQUEST)

        code = base64.b64decode(encoded_code).decode("utf-8")

        email, password = code.split(":")

        user = db.query(models.User).filter_by(email=email).first()
        if not user:
            return response( "User not found", status.HTTP_404_NOT_FOUND)
        
        if not pwd_context.verify(password, user.password):
            return response( "Invalid authorization", status.HTTP_401_UNAUTHORIZED)

        new_assignment = models.Assignment(
            name=assignment.name,
            points=assignment.points,
            num_of_attemps=assignment.num_of_attemps,
            deadline=assignment.deadline,
            owner_user_id=user.id
        )

        db.add(new_assignment)
        db.commit()
        return_data = json.loads(
            json.dumps(db.query(models.Assignment).filter_by(id=new_assignment.id).first().to_dict(),
                       indent=4, sort_keys=True, default=str))
        return response( "Assignment Created Successfully", status.HTTP_201_CREATED, return_data, log_level="info")
    except Exception as e:
        return response( str(e), status.HTTP_408_REQUEST_TIMEOUT)



@app.put("/v3/assignments/{id}")
async def update_assignment(id: str, data: Assignment, authorization: str = Header(None), db: Session = Depends(get_db)):
    c.incr("Update_Assignment")
    try:
        if not database_connection():
            return response("Database is not connected", status.HTTP_503_SERVICE_UNAVAILABLE, no_content=True)
        assignment = db.query(models.Assignment).filter_by(id=id).first()
        if not assignment:
            return response( "Assignment not found", status.HTTP_404_NOT_FOUND)

        if authorization is None:
            return response( "Authorization header missing", status.HTTP_400_BAD_REQUEST)
        try:
            auth_type, encoded_code = authorization.split(" ")
            if auth_type != "Basic":
                return response( "Authorization type not supported", status.HTTP_400_BAD_REQUEST)

            code = base64.b64decode(encoded_code).decode("utf-8")
            email, password = code.split(":")

            user = db.query(models.User).filter_by(email=email).first()
            if not user:
                return response( "User not found", status.HTTP_404_NOT_FOUND)
            
             # Check if user is authorized to access this data
            if assignment.owner_user_id != user.id:
                return response( "Not authorized to access other user's data", status.HTTP_403_FORBIDDEN)

            if not pwd_context.verify(password, user.password):
                return response( "Invalid authorization", status.HTTP_401_UNAUTHORIZED)

           

            # Update assignment data
            assignment.name = data.name
            assignment.points = data.points
            assignment.num_of_attemps = data.num_of_attemps
            assignment.deadline = data.deadline

            db.add(assignment)
            db.commit()
            db.refresh(assignment)

            return response("Assignment Updated successfully", status.HTTP_204_NO_CONTENT, log_level="info")

            
        except Exception as e:
            return response("Invalid authorization header : {}".format(str(e)), status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return response( str(e), status.HTTP_408_REQUEST_TIMEOUT)


@app.delete("/v3/assignments/{id}")
async def delete_assignment(id: str, authorization: str = Header(None), db: Session = Depends(get_db)):
    c.incr("delete_Assignment")
    try:
        if not database_connection():
            return response("Database is not connected", status.HTTP_503_SERVICE_UNAVAILABLE, no_content=True)
        # Check if assignment exists
        assignment = db.query(models.Assignment).filter_by(id=id).first()
        if not assignment:
            return response( "Assignment not found", status.HTTP_404_NOT_FOUND)

        if authorization is None:
            return response( "Authorization header missing", status.HTTP_400_BAD_REQUEST)
        try:
            auth_type, encoded_code = authorization.split(" ")
            if auth_type != "Basic":
                return response( "Authorization type not supported", status.HTTP_400_BAD_REQUEST)

            code = base64.b64decode(encoded_code).decode("utf-8")
            email, password = code.split(":")

            user = db.query(models.User).filter_by(email=email).first()
            if not user:
                return response( "User not found", status.HTTP_404_NOT_FOUND)
            
            # Check if user is authorized to access this data
            if assignment.owner_user_id != user.id:
                return response( "Not authorized to access other user's data", status.HTTP_403_FORBIDDEN)


            if not pwd_context.verify(password, user.password):
                return response( "Invalid authorization", status.HTTP_401_UNAUTHORIZED)
            
            db.delete(assignment)
            db.commit()

            return response( "Assignment deleted successfully", status.HTTP_204_NO_CONTENT, log_level="info")

        except Exception as e:
            return response( "Invalid authorization header : {}".format(str(e)), status.HTTP_400_BAD_REQUEST)

    except Exception as e:
            return response( str(e), status.HTTP_408_REQUEST_TIMEOUT)


@app.get("/v3/assignments/{id}")
async def get_assignment(id: str, db: Session = Depends(get_db), authorization: str = Header(None)):
    c.incr("Get_Assignment")
    try:
        if not database_connection():
            return response("Database is not connected", status.HTTP_503_SERVICE_UNAVAILABLE, no_content=True)
        # Check if assignment exists
        assignment = db.query(models.Assignment).filter_by(id=id).first()
        if not assignment:
            return response( "Assignment not found", status.HTTP_404_NOT_FOUND)

        if authorization is None:
            return response( "Authorization header missing", status.HTTP_400_BAD_REQUEST)
        try:
            auth_type, encoded_code = authorization.split(" ")
            if auth_type != "Basic":
                return response( "Authorization type not supported", status.HTTP_400_BAD_REQUEST)

            code = base64.b64decode(encoded_code).decode("utf-8")
            email, password = code.split(":")

            user = db.query(models.User).filter_by(email=email).first()
            if not user:
                return response( "User not found", status.HTTP_404_NOT_FOUND)
            
            # Check if user is authorized to access this data
            if assignment.owner_user_id != user.id:
                return response( "Not authorized to access other user's data", status.HTTP_403_FORBIDDEN)


            if not pwd_context.verify(password, user.password):
                return response( "Invalid authorization", status.HTTP_401_UNAUTHORIZED)
            
            return response("Assignemnt data retrieved successfully", status.HTTP_200_OK,
                        data=json.loads(json.dumps(assignment.to_dict(), indent=4, sort_keys=True, default=str)), log_level="info")

        except Exception as e:
            return response( "Invalid authorization header : {}".format(str(e)), status.HTTP_400_BAD_REQUEST)

    except Exception as e:
            return response( str(e), status.HTTP_408_REQUEST_TIMEOUT)
    

@app.get("/v3/assignments")
async def get_assignments(db: Session = Depends(get_db)):
    c.incr("Get_Assignment_List")
    try:
        if not database_connection():
            return response("Database is not connected", status.HTTP_503_SERVICE_UNAVAILABLE, no_content=True)
        assignments = db.query(models.Assignment).all()

        
        assignments_data = [assignment.to_dict() for assignment in assignments]
        logger.info("Images fetched successfully 200")
        return assignments_data

    except Exception as e:
        return response( "Invalid authorization header : {}".format(str(e)), status.HTTP_400_BAD_REQUEST)
    

@app.post("/v3/assignments/{id}/submission")
async def create_submission(submission: Submission, id: str, db: Session = Depends(get_db), authorization: str = Header(None)):
    try:
        if not database_connection():
            return response("Database is not connected", status.HTTP_503_SERVICE_UNAVAILABLE, no_content=True)
        
        if authorization is None:
            return response( "Authorization header missing", status.HTTP_400_BAD_REQUEST)
        
        try:
            auth_type, encoded_code = authorization.split(" ")
            if auth_type != "Basic":
                return response( "Authorization type not supported", status.HTTP_400_BAD_REQUEST)

            code = base64.b64decode(encoded_code).decode("utf-8")
            email, password = code.split(":")

            user = db.query(models.User).filter_by(email=email).first()
            if not user:
                return response( "User not found", status.HTTP_404_NOT_FOUND)

            if not pwd_context.verify(password, user.password):
                return response( "Invalid authorization", status.HTTP_401_UNAUTHORIZED)
            
            # Check if assignment exists
            assignment = db.query(models.Assignment).filter_by(id=id).first()
            if not assignment:
                return response( "Assignment not found", status.HTTP_400_BAD_REQUEST)
            
            # Check if user is authorized to access this data
            if assignment.owner_user_id != user.id:
                return response( "Not authorized to access other user's data", status.HTTP_403_FORBIDDEN)

    
            # Check if the submission deadline has passed
            if assignment.deadline < datetime.now():
                return response( "Submission deadline has passed", status.HTTP_400_BAD_REQUEST)
    
            # Get the count of submissions for the assignment
            submissions_count = db.query(models.Submission).filter(models.Submission.assignment_id == id).count()

            if submissions_count >= assignment.num_of_attemps:
                return response(f"Submission limit exceeded for assignment {assignment.name}", status.HTTP_400_BAD_REQUEST)
            
            new_submission = models.Submission(
                assignment_id=assignment.id,
                submission_url=submission.submission_url
            )

            db.add(new_submission)
            db.commit()
            send_to_sns_topic(new_submission.submission_url, str(user.id), str(assignment.id), str(new_submission.id), user.email)

            return_data = json.loads(
                json.dumps(db.query(models.Submission).filter_by(id=new_submission.id).first().to_dict(),
                        indent=4, sort_keys=True, default=str))
            return response( "Submission Created Successfully", status.HTTP_201_CREATED, return_data, log_level="info")
        
        except Exception as e:
            return response( "Invalid authorization header : {}".format(str(e)), status.HTTP_400_BAD_REQUEST)

    except Exception as e:
            return response( str(e), status.HTTP_408_REQUEST_TIMEOUT)
    
    
def send_to_sns_topic(url, user_id, assigmment_id, submission_id, user_email):
    # Replace 'your-aws-region' and 'your-sns-topic-arn' with your AWS region and SNS topic ARN
    aws_region = os.getenv("AWS_REGION")
    sns_topic_arn = os.getenv("SNS_TOPIC_ARN")

    # Create an SNS client
    sns_client = boto3.client('sns', region_name=aws_region)

    # Message to be sent to the SNS topic
    message = json.dumps({
        "repo_url": url,
        "user_id": user_id,
        "assigmment_id": assigmment_id,
        "submission_id": submission_id,
        "user_email": user_email
    })

    # Publish the message to the SNS topic
    sns_client.publish(
        TopicArn=sns_topic_arn,
        Message=message,
        Subject='New Submission',
    )