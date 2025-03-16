# api/routes/video_routes.py
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from db import get_db
from models.video import Video
from repositories.video_repository import VideoRepository
from services.analysis_service import AnalysisService  # Changed from VideoAnalysisService to match actual class name

router = APIRouter()

# Initialize the analysis service
analysis_service = AnalysisService()

@router.get("/videos/recent", response_model=List[Dict[str, Any]])
async def get_recent_videos(db: Session = Depends(get_db)):
    """Get recently analyzed videos."""
    repo = VideoRepository(db)
    videos = repo.get_recent_videos(limit=10)
    
    # Convert to dict format for API response
    return [
        {
            "id": video.id,
            "title": video.title,
            "channel_title": video.channel_title,
            "thumbnail_url": video.thumbnail_url,
            "is_analyzed": video.is_analyzed
        }
        for video in videos
    ]

@router.get("/videos/{video_id}", response_model=Dict[str, Any])
async def get_video_details(
    video_id: str = Path(..., description="YouTube video ID"),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific video."""
    repo = VideoRepository(db)
    video = repo.get_video_by_id(video_id)
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    # Convert to dict format for API response
    result = {
        "id": video.id,
        "title": video.title,
        "description": video.description,
        "channel_title": video.channel_title,
        "thumbnail_url": video.thumbnail_url,
        "published_at": video.published_at.isoformat() if video.published_at else None,
        "duration_seconds": video.duration_seconds,
        "is_analyzed": video.is_analyzed
    }
    
    # Add summary data if available
    if video.summary:
        result["summary"] = {
            "short_summary": video.summary.short_summary,
            "detailed_summary": video.summary.detailed_summary,
            "key_points": video.summary.key_points,
            "topics": video.summary.topics,
            "sentiment": video.summary.sentiment,
            "entities": video.summary.entities,
            "key_moments": video.summary.key_moments
        }
    
    return result

@router.get("/search", response_model=Dict[str, Any])
async def search_videos(
    q: str,
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Search for videos by query."""
    repo = VideoRepository(db)
    videos = repo.search_videos(q, limit=limit, offset=offset)
    total = repo.count_search_results(q)
    
    # Convert to dict format for API response
    return {
        "results": [
            {
                "id": video.id,
                "title": video.title,
                "channel_title": video.channel_title,
                "thumbnail_url": video.thumbnail_url,
                "is_analyzed": video.is_analyzed
            }
            for video in videos
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }