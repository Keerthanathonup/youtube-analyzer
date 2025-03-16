# models/video_summary.py

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from db import Base

class VideoSummary(Base):
    """Model for storing video analysis results."""
    
    __tablename__ = "video_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    short_summary = Column(Text, nullable=True)
    detailed_summary = Column(Text, nullable=True)
    key_points = Column(JSON, nullable=True)
    topics = Column(JSON, nullable=True)
    sentiment = Column(String, nullable=True)
    key_moments = Column(JSON, nullable=True)
    entities = Column(JSON, nullable=True)
    has_transcription = Column(Boolean, nullable=True)
    transcription_source = Column(String, nullable=True)
    last_analyzed = Column(DateTime, nullable=True)
    
    # Relationship to Video model
    video = relationship("Video", back_populates="summary")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "video_id": self.video_id,
            "short_summary": self.short_summary,
            "detailed_summary": self.detailed_summary,
            "key_points": self.key_points,
            "topics": self.topics,
            "sentiment": self.sentiment,
            "key_moments": self.key_moments,
            "entities": self.entities,
            "has_transcription": self.has_transcription,
            "transcription_source": self.transcription_source,
            "last_analyzed": self.last_analyzed.isoformat() if self.last_analyzed else None
        }