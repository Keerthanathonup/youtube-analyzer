from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime

class VideoBase(BaseModel):
    video_id: str
    
class VideoCreate(VideoBase):
    title: str
    description: Optional[str] = None
    channel_name: str
    published_at: datetime
    thumbnail_url: HttpUrl
    duration: int  # Duration in seconds
    
class VideoSearchQuery(BaseModel):
    query: str
    max_results: int = 10
    
class VideoUrlRequest(BaseModel):
    url: HttpUrl
    
class KeyPoint(BaseModel):
    text: str
    timestamp: Optional[int] = None  # Timestamp in seconds
    
class SummaryCreate(BaseModel):
    short_summary: str
    detailed_summary: str
    key_points: List[KeyPoint]
    topics: List[str]
    sentiment: str
    
class SummaryResponse(SummaryCreate):
    id: int
    video_id: str
    created_at: datetime
    
    class Config:
        orm_mode = True
        
class VideoResponse(VideoCreate):
    id: int
    summary: Optional[SummaryResponse] = None
    
    class Config:
        orm_mode = True
        
class VideoListResponse(BaseModel):
    videos: List[VideoResponse]
    total: int