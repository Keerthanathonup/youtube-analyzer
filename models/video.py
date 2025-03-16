# models/video.py

from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db import Base

class Video(Base):
    """Model for storing video metadata."""
    
    __tablename__ = "videos"
    
    id = Column(String, primary_key=True, index=True)  # YouTube video ID
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    channel_title = Column(String, nullable=True)
    published_at = Column(DateTime, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    transcript = Column(Text, nullable=True)
    transcript_language = Column(String, nullable=True)
    content_type = Column(String, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    is_analyzed = Column(Boolean, nullable=True)
    last_updated = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)
    
    # Relationship to VideoSummary model (one-to-one)
    summary = relationship("VideoSummary", back_populates="video", uselist=False)
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "channel_title": self.channel_title,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "thumbnail_url": self.thumbnail_url,
            "transcript": self.transcript,
            "transcript_language": self.transcript_language,
            "content_type": self.content_type,
            "duration_seconds": self.duration_seconds,
            "is_analyzed": self.is_analyzed,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }