from pydantic import BaseModel, HttpUrl

class FileUploadSchema(BaseModel):
    filename: str
    s3_url: str

    class Config:
        orm_mode = True