# app.py

from fastapi import FastAPI, Request, Depends, Form, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional

from db import get_db
import config
from models.video import Video
from models.video_summary import VideoSummary
from repositories.video_repository import VideoRepository
from services.youtube_service import YouTubeService
from services.transcription_service import TranscriptionService
from services.analysis_service import AnalysisService

# Helper function for formatting video duration
def format_duration(seconds):
    """
    Format duration in seconds to a readable string (HH:MM:SS or MM:SS format).
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if not seconds:
        return "00:00"
        
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

# Helper function for formatting timestamps        
def format_timestamp(seconds):
    """Format seconds into MM:SS format for video timestamps."""
    if not seconds:
        return "00:00"
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes:02d}:{seconds:02d}"

# Initialize FastAPI app
app = FastAPI(title="YouTube Video Content Analyzer")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")
templates.env.globals["format_duration"] = format_duration  # Make function available in templates
templates.env.globals["format_timestamp"] = format_timestamp  # Make timestamp formatter available in templates

# Initialize services
youtube_service = YouTubeService()
transcription_service = TranscriptionService()
analysis_service = AnalysisService(api_key=config.ANTHROPIC_API_KEY)

# Routes
@app.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    """Home page with search form and recent videos."""
    repo = VideoRepository(db)
    recent_videos = repo.get_recent_videos(limit=5)
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "recent_videos": recent_videos}
    )

@app.get("/search")
async def search_form(
    request: Request,
    q: str = Query(None),  # This allows handling /search?q=query
    page: int = Query(1), 
    db: Session = Depends(get_db)

):
    """Search form page that also handles query parameters."""
    # If no query parameter, just show the form
    if not q:
        return templates.TemplateResponse("search.html", {"request": request})
    
    # Otherwise, search for videos with the query
    try:
        # Make sure the YouTube service is initialized
        if youtube_service.api is None:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "error": "YouTube API is not configured. Please check your API key."}
            )
        
        per_page = 5
        videos = youtube_service.search_videos(q, max_results=per_page)

        # Create a simple pagination object
        pagination = {
            "page": page,
            "per_page": per_page,
            "total_items": len(videos),
            "total_pages": 1  # For now, just one page since we're not implementing full pagination
        }
        
        # Debug print the videos to see what's returned
        print(f"Found {len(videos)} videos for query: {q}")
        for video in videos:
            print(f"Video ID: {video.get('id')}, Title: {video.get('title')}")
        
        return templates.TemplateResponse(
            "search.html", 
            {"request": request, "videos": videos, "query": q}
        )
    except Exception as e:
        import traceback
        print(f"Error in search: {str(e)}")
        print(traceback.format_exc())
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": str(e)}
        )

@app.post("/search")
async def search_results(
    request: Request, 
    query: str = Form(...),
    db: Session = Depends(get_db)

):
    """Search for videos and display results."""
    try:
        # Make sure the YouTube service is initialized
        if youtube_service.api is None:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "error": "YouTube API is not configured. Please check your API key."}
            )
        per_page=5   
        videos = youtube_service.search_videos(query, max_results=per_page)

        # Create a simple pagination object
        pagination = {
            "page": 1,
            "per_page": per_page,
            "total_items": len(videos),
            "total_pages": 1  # For now, just one page since we're not implementing full pagination
        }

        return templates.TemplateResponse(
            "search.html", 
            {"request": request, "videos": videos, "query": query}
        )
    except Exception as e:
        import traceback
        print(f"Error in search: {str(e)}")
        print(traceback.format_exc())
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": str(e)}
        )

@app.get("/video/{video_id}")
async def video_details(request: Request, video_id: str, db: Session = Depends(get_db)):
    """Display video details and analysis if available."""
    repo = VideoRepository(db)
    video = repo.get_video_by_id(video_id)
    
    if not video:
        # Get video details from YouTube
        try:
            video_details = youtube_service.get_video_details(video_id)
    
            # Use the repository method to create the video
            video = repo.create_video(
                video_id=video_id,
                title=video_details.get("title", "Unknown"),
                channel_name=video_details.get("channel_title", "Unknown"),
                published_at=video_details.get("published_at"),
                thumbnail_url=video_details.get("thumbnail_url", ""),
                duration=video_details.get("duration_seconds", 0),
                description=video_details.get("description", "")
            )
        except Exception as e:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "error": f"Error retrieving video: {str(e)}"}
            )
    
    # Check if we have analysis
    summary = repo.get_video_summary(video_id)
    
    # Calculate sentiment percentage (for UI meter)
    sentiment_percentage = 50  # Default to neutral
    sentiment_description = "This content has a neutral tone."
    
    if summary and summary.sentiment:
        if summary.sentiment.lower() == "positive":
            sentiment_percentage = 75
            sentiment_description = "This content has a generally positive tone."
        elif summary.sentiment.lower() == "very positive":
            sentiment_percentage = 90
            sentiment_description = "This content has a very positive and enthusiastic tone."
        elif summary.sentiment.lower() == "negative":
            sentiment_percentage = 25
            sentiment_description = "This content has a generally negative tone."
        elif summary.sentiment.lower() == "very negative":
            sentiment_percentage = 10
            sentiment_description = "This content has a very negative or critical tone."
    
    return templates.TemplateResponse(
        "video.html",
        {
            "request": request, 
            "video": video, 
            "summary": summary,
            "sentiment_percentage": sentiment_percentage,
            "sentiment_description": sentiment_description,
            "debug": False  # Set to True for debugging information
        }
    )

@app.get("/analyze/{video_id}")
async def analyze_video(request: Request, video_id: str, db: Session = Depends(get_db)):
    """Analyze a video and display results."""
    repo = VideoRepository(db)
    
    # Get video from database
    video = repo.get_video_by_id(video_id)
    if not video:
        # Get video details from YouTube
        try:
            video_details = youtube_service.get_video_details(video_id)
            video = repo.create_video(
                video_id=video_id,
                title=video_details.get("title", "Unknown"),
                channel_name=video_details.get("channel_title", "Unknown"),
                published_at=video_details.get("published_at"),
                thumbnail_url=video_details.get("thumbnail_url", ""),
                duration=video_details.get("duration_seconds", 0),
                description=video_details.get("description", "")
            )
        except Exception as e:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "error": f"Error retrieving video: {str(e)}"}
            )
    
    # Check if we already have analysis
    existing_summary = repo.get_video_summary(video_id)
    if existing_summary:
        return templates.TemplateResponse(
            "analysis.html",
            {"request": request, "video": video, "summary": existing_summary, "is_new": False}
        )
    
    # Get transcript
    try:
        transcript = transcription_service.get_transcript(video_id)
        if not transcript:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "error": "Could not retrieve transcript for this video"}
            )
    except Exception as e:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": f"Error retrieving transcript: {str(e)}"}
        )
    
    # Prepare metadata for analysis
    video_metadata = {
        "title": video.title,
        "description": video.description,
        "channel_title": video.channel_title
    }
    
    # Analyze transcript
    try:
        analysis_results = analysis_service.analyze_video(
            video_id=video_id,
            transcript=transcript,
            video_metadata=video_metadata
        )
        
        # Create VideoSummary from analysis results
        summary = repo.create_summary(
            video_id=video_id,
            short_summary=analysis_results.get("summary", ""),
            detailed_summary=analysis_results.get("detailed_summary", analysis_results.get("summary", "")),
            key_points=analysis_results.get("key_points", []),
            topics=[topic.get("name", "") for topic in analysis_results.get("topics", [])],
            sentiment=analysis_results.get("sentiment", "neutral"),
            entities=[], # Default empty entities
            key_moments=[] # Default empty key_moments
        )
        # Save to database
        repo.save_video_summary(summary)
        
        return templates.TemplateResponse(
            "analysis.html",
            {"request": request, "video": video, "summary": summary, "is_new": True}
        )
    except Exception as e:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": f"Error analyzing video: {str(e)}"}
        )

@app.get("/api/videos")
async def api_get_videos(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """API endpoint to get videos."""
    repo = VideoRepository(db)
    videos = repo.get_videos(limit=limit, skip=skip)
    return [video.to_dict() for video in videos]

@app.get("/api/videos/{video_id}")
async def api_get_video(
    video_id: str,
    db: Session = Depends(get_db)
):
    """API endpoint to get a specific video."""
    repo = VideoRepository(db)
    video = repo.get_video_by_id(video_id)
    if not video:
        return {"error": "Video not found"}
    return video.to_dict()

@app.get("/api/videos/{video_id}/summary")
async def api_get_video_summary(
    video_id: str,
    db: Session = Depends(get_db)
):
    """API endpoint to get a video summary."""
    repo = VideoRepository(db)
    summary = repo.get_video_summary(video_id)
    if not summary:
        return {"error": "Summary not found"}
    return summary.to_dict()

# At the end of app.py
if __name__ == "__main__":
    print("Starting YouTube Analyzer application...")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)