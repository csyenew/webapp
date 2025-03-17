from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import logging
from logging.config import dictConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cloud")

# Get database connection info from environment variables
DB_USERNAME = os.getenv("POSTGRES_USER", "csye6225")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "csye6225")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_NAME = os.getenv("POSTGRES_DB", "csye6225")

try:
    SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    logger.info(f"Connecting to database at {DB_HOST}")
except Exception as e:
    logger.error(f"Error creating database URL: {str(e)}")
    raise ValueError("DATABASE_URL configuration error")

# Create engine with improved connection settings
try:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,  # Recycle connections after 30 minutes
        connect_args={"connect_timeout": 10}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {str(e)}")
    raise

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)