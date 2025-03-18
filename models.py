from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid

class FileRecord(Base):
    __tablename__ = "files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    file_name = Column(String, nullable=False)
    url = Column(String, nullable=False, unique=True)
    upload_date = Column(Date, server_default=func.now())
    