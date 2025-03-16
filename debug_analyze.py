# debug_analyze.py - Keep this in the root directory (no import path adjustments needed)

from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import traceback
import sys
import logging

from db import get_db
from models.video import Video
from repositories.video_repository import VideoRepository
from services.youtube_service import YouTubeService
from services.transcription_service import TranscriptionService
from services.analysis_service import AnalysisService
import config

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize debug app
debug_app = FastAPI(title="Debug YouTube Video Analyzer")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Initialize services
youtube_service = YouTubeService()
transcription_service = TranscriptionService()
analysis_service = AnalysisService(api_key=config.ANTHROPIC_API_KEY)

@debug_app.get("/debug/analyze/{video_id}")
async def debug_analyze_video(request: Request, video_id: str, db: Session = Depends(get_db)):
    """Debug version of the analyze_video endpoint with detailed logging."""
    logger.info(f"=== STARTING DEBUG ANALYSIS FOR VIDEO {video_id} ===")
    
    repo = VideoRepository(db)
    
    # STEP 1: Get video from database or YouTube
    logger.info("STEP 1: Getting video details")
    video = repo.get_video_by_id(video_id)
    
    if not video:
        logger.info(f"Video {video_id} not found in database, fetching from YouTube")
        try:
            logger.debug("Calling YouTube API for video details")
            video_details = youtube_service.get_video_details(video_id)
            
            if not video_details:
                logger.error(f"YouTube API returned no details for video {video_id}")
                return {"error": "Could not retrieve video details from YouTube API"}
            
            logger.debug(f"YouTube API response: {video_details}")
            
            # Check if thumbnail_url is present
            if "thumbnail_url" not in video_details or not video_details["thumbnail_url"]:
                logger.warning("No thumbnail URL in video details, setting default")
                video_details["thumbnail_url"] = ""
            
            logger.info("Creating video record in database")
            try:
                video = repo.create_video(
                    video_id=video_id,
                    title=video_details.get("title", "Unknown"),
                    channel_name=video_details.get("channel_title", "Unknown"),
                    published_at=video_details.get("published_at"),
                    thumbnail_url=video_details.get("thumbnail_url", ""),
                    duration=video_details.get("duration_seconds", 0),
                    description=video_details.get("description", "")
                )
                logger.info(f"Video record created: {video.id}")
            except Exception as e:
                logger.error(f"Error creating video in database: {str(e)}")
                logger.error(traceback.format_exc())
                return {"error": f"Database error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error fetching video from YouTube: {str(e)}")
            logger.error(traceback.format_exc())
            return {"error": f"YouTube API error: {str(e)}"}
    else:
        logger.info(f"Found video {video_id} in database")
    
    # STEP 2: Check for existing analysis
    logger.info("STEP 2: Checking for existing analysis")
    existing_summary = repo.get_video_summary(video_id)
    
    if existing_summary:
        logger.info(f"Summary already exists for video {video_id}")
        return {"status": "existing_analysis", "summary": existing_summary.to_dict()}
    
    # STEP 3: Get transcript
    logger.info("STEP 3: Getting transcript")
    try:
        transcript = transcription_service.get_transcript(video_id)
        
        if not transcript:
            logger.error(f"No transcript available for video {video_id}")
            return {"error": "Could not retrieve transcript for this video"}
        
        logger.info(f"Transcript retrieved successfully ({len(transcript)} characters)")
        logger.debug(f"Transcript preview: {transcript[:200]}...")
        
        # Save transcript to database
        try:
            logger.info("Updating transcript in database")
            repo.update_transcript(video_id, transcript)
        except Exception as e:
            logger.error(f"Error saving transcript to database: {str(e)}")
            # Continue anyway, this is not critical
    
    except Exception as e:
        logger.error(f"Error retrieving transcript: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": f"Transcript error: {str(e)}"}
    
    # STEP 4: Analyze transcript with Claude
    logger.info("STEP 4: Analyzing transcript with Claude")
    try:
        # Prepare metadata
        video_metadata = {
            "title": video.title,
            "description": video.description,
            "channel_title": video.channel_title
        }
        
        logger.debug(f"Video metadata: {video_metadata}")
        
        # Call analysis service
        logger.info("Calling Claude API for analysis")
        analysis_results = analysis_service.analyze_video(
            video_id=video_id,
            transcript=transcript,
            video_metadata=video_metadata
        )
        
        logger.info("Analysis completed successfully")
        logger.debug(f"Analysis results: {analysis_results}")
        
    except Exception as e:
        logger.error(f"Error analyzing transcript: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": f"Analysis error: {str(e)}"}
    
    # STEP 5: Save analysis results
    logger.info("STEP 5: Saving analysis results")
    try:
        # Create summary from analysis results
        logger.debug("Creating summary record")
        
        # Check if key_points is a list or needs conversion
        key_points = analysis_results.get("key_points", [])
        if isinstance(key_points, str):
            logger.warning("key_points is a string, converting to list")
            key_points = [key_points]
        
        # Check if topics exists and is properly formatted
        topics = analysis_results.get("topics", [])
        if isinstance(topics, dict):
            logger.warning("topics is a dict, extracting names")
            topics = [topic.get("name", "Unknown") for topic in [topics]]
        elif isinstance(topics, list) and topics and isinstance(topics[0], dict):
            logger.warning("topics contains dicts, extracting names")
            topics = [topic.get("name", "Unknown") for topic in topics]
        
        summary = repo.create_summary(
            video_id=video_id,
            short_summary=analysis_results.get("summary", ""),
            detailed_summary=analysis_results.get("summary", ""),
            key_points=key_points,
            topics=topics,
            sentiment=analysis_results.get("sentiment", "neutral"),
            entities=[], # Default empty entities
            key_moments=[] # Default empty key_moments
        )
        
        # Save to database
        logger.info("Saving summary to database")
        repo.save_video_summary(summary)
        logger.info(f"Summary saved for video {video_id}")
        
        return {
            "status": "success",
            "summary": summary.to_dict() if hasattr(summary, "to_dict") else summary
        }
        
    except Exception as e:
        logger.error(f"Error saving analysis results: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": f"Database error: {str(e)}"}