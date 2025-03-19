from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

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
        return False
    
    
def get_db():
    
    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False,autoflush=False, bind=engine)
        db = SessionLocal()
        yield db
    finally:
        db.close()