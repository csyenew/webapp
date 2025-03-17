from database import database_connection, SQLALCHEMY_DATABASE_URL
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, CheckConstraint
from datetime import datetime
from sqlalchemy import create_engine
import logging
from logging.config import dictConfig
from log import LogConfig
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
import csv
import uuid
from sqlalchemy.dialects.postgresql import UUID
import os

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

dictConfig(LogConfig().dict())
logger = logging.getLogger("cloud")

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    password = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    account_created = Column(DateTime, default=datetime.utcnow)
    account_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    points = Column(Integer, nullable=False)
    num_of_attemps = Column(Integer, nullable=False)
    deadline = Column(DateTime, nullable=False)
    assignment_created = Column(DateTime, default=datetime.utcnow)
    assignment_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    __table_args__ = (
        CheckConstraint('points >= 1 AND points <= 10', name='check_points_range'),
        CheckConstraint('num_of_attemps >= 1 AND num_of_attemps <= 100', name='check_num_of_attemps_range'),
    )

    user = relationship("User", back_populates="assignments")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "points": self.points,
            "num_of_attemps": self.num_of_attemps,
            "deadline": self.deadline,
            "assignment_created": self.assignment_created,
            "assignment_updated": self.assignment_updated
        }

    

User.assignments = relationship("Assignment",order_by= "Assignment.id" , back_populates="user")

class Submission(Base):
    __tablename__ = 'submissions'

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assignments.id"), nullable=False, index=True)
    submission_url = Column(String)
    submission_date = Column(DateTime, default=datetime.utcnow)
    submission_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignment = relationship("Assignment", back_populates="submissions")

    def to_dict(self):
        return {
            "id": self.id,
            "assignment_id": self.assignment_id,
            "submission_url": self.submission_url,
            "submission_date": self.submission_date,
            "submission_updated": self.submission_updated,
        }

Assignment.submissions = relationship("Submission", back_populates="assignment", order_by= "Submission.id")

if database_connection():
    logger.info("Database is connected")
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(autocommit=False,autoflush=False, bind=engine)
    db = SessionLocal()

    file_path = "/opt/user.csv"
    if os.path.isfile(file_path):
        users_data = []

        with open("/opt/user.csv", mode='r') as csv_file:
            
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                users_data.append({
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "email": row["email"],
                    "password": row["password"]
                })
        
        for user_data in users_data:
            existing_user = db.query(User).filter_by(email=user_data["email"]).first()
            if existing_user:
                continue

            new_user = User(email=user_data["email"],
                            first_name=user_data["first_name"],
                            last_name=user_data["last_name"],
                            password=pwd_context.encrypt(user_data["password"])
                            )

            db.add(new_user)
            db.commit()
    else:
        logger.error("CSV file doesn't exist")
    
    db.close()

