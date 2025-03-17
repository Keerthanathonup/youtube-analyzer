# models/video_relationship.py

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db import Base

class VideoRelationship(Base):
    """Model for storing relationships between videos."""
    
    __tablename__ = "video_relationships"
    
    source_video_id = Column(String, ForeignKey("videos.id"), primary_key=True)
    target_video_id = Column(String, ForeignKey("videos.id"), primary_key=True)
    similarity_score = Column(Float, nullable=True)
    relationship_type = Column(String, nullable=True)  # e.g., "content_similarity", "same_channel", "recommended"
    relation_details = Column(Text, nullable=True)  # JSON field for additional details
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships to Video model
    source_video = relationship("Video", foreign_keys=[source_video_id])
    target_video = relationship("Video", foreign_keys=[target_video_id])
    
    # Add indexes for better query performance
    __table_args__ = (
        Index('idx_video_relationship_source', source_video_id),
        Index('idx_video_relationship_target', target_video_id),
        Index('idx_video_relationship_type', relationship_type),
    )
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "source_video_id": self.source_video_id,
            "target_video_id": self.target_video_id,
            "similarity_score": self.similarity_score,
            "relationship_type": self.relationship_type,
            "relation_details": self.relation_details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }