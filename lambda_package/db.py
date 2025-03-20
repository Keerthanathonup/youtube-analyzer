# db.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from config import settings

# Create database URL from settings
DATABASE_URL = settings["DATABASE_URL"]

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)

# Create declarative base model
Base = declarative_base()
Base.query = db_session.query_property()

def get_db():
    """
    Generator function to get a database session.
    Yields the session and ensures it is closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initializes the database by creating all defined tables.
    """
    # Import all models here to ensure they are registered with the Base
    # This avoids circular imports
    from models.video import Video
    from models.video_summary import VideoSummary
    
    Base.metadata.create_all(bind=engine)