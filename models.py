from sqlalchemy import Column, Integer, String, ForeignKey, Date, create_engine
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from database import database_connection, SQLALCHEMY_DATABASE_URL

Base = declarative_base()

class FileRecord(Base):
    __tablename__ = "files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    file_name = Column(String, nullable=False)
    url = Column(String, nullable=True, unique=True)
    upload_date = Column(Date, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "file_name": self.file_name,
            "url": self.url,
            "upload_date": self.upload_date
        }

if database_connection():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
