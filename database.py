from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

if "DATABASE_URL" in os.environ:
    SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
else:
    raise ValueError("DATABASE_URL must be set")
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False,autoflush=False, bind=engine)

Base = declarative_base()
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()