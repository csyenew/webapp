from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import logging
from logging.config import dictConfig
from passlib.context import CryptContext
from log import LogConfig

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

dictConfig(LogConfig().dict())
logger = logging.getLogger("cloud")


if "DATABASE_URL" in os.environ:
    SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
else:
    raise ValueError("DATABASE_URL must be set")


def database_connection():
    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        connection = engine.connect()
        connection.close()
        return True
    except Exception:
        logger.error("Database is not connected")
        return False
    
    
def get_db():
    
    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False,autoflush=False, bind=engine)
        db = SessionLocal()
        yield db
    finally:
        db.close()
