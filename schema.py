from pydantic import BaseModel, EmailStr, Field, HttpUrl
from fastapi import status
from datetime import datetime

class LoginSerializer(BaseModel):
    email: str
    password: str

class CustomException(Exception):
    def __init__(self, status_code, msg):
        self.status_code = status_code
        self.msg = msg

class User(BaseModel):
    first_name: str
    last_name: str
    password: str
    email: EmailStr

    class Config:
        orm_mode = True


class Assignment(BaseModel):
    def __init__(self, **data):
        if any(item not in ["name", "points", "num_of_attemps", "deadline"] for item in data.keys()):
            raise CustomException(status.HTTP_400_BAD_REQUEST, {"keys":"Please provide correct parameters"})
        for key, value in data.items():
            if isinstance(value, int) and key not in ["points", "num_of_attemps"]:
                raise CustomException(status.HTTP_400_BAD_REQUEST, {key: "The value should be string"})
            if key in ["points", "num_of_attemps"] and (isinstance(value, str) or isinstance(value, float)):
                raise CustomException(status.HTTP_400_BAD_REQUEST, {key: "The value should be Integer"})
        super().__init__(**data)

    name: str
    points: int = Field(ge=1, le=10)
    num_of_attemps: int = Field(ge=1, le=100)
    deadline: datetime

    class Config:
        orm_mode = True

class Submission(BaseModel):

    def __init__(self, **data):
        if any(item not in ["submission_url"] for item in data.keys()):
            raise CustomException(status.HTTP_400_BAD_REQUEST, {"keys":"Please provide correct parameters"})
        super().__init__(**data)

    submission_url: HttpUrl

    class Config:
        orm_mode = True