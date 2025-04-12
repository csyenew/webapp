from pydantic import BaseModel, HttpUrl

class FileUploadSchema(BaseModel):
    file_name: str
    url: str
    

    class Config:
        orm_mode = True

class CustomException(Exception):
    def __init__(self, status_code, msg):
        self.status_code = status_code
        self.msg = msg