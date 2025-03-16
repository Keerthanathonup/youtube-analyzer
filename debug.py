# debug.py
import sys
import logging
from services.youtube_service import YouTubeService
from services.transcription_service import TranscriptionService
from services.analysis_service import AnalysisService
from repositories.video_repository import VideoRepository
from db import SessionLocal
import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_video(video_id):
    """Debug function to analyze a video and print detailed logs."""
    logger.info(f"=== STARTING DEBUG ANALYSIS FOR VIDEO {video_id} ===")
    
    # Initialize services
    youtube_service = YouTubeService()
    transcription_service = TranscriptionService()
    analysis_service = AnalysisService(api_key=config.ANTHROPIC_API_KEY)
    
    # Get database session
    db = SessionLocal()
    repo = VideoRepository(db)
    
    try:
        # STEP 1: Get video from database or YouTube
        logger.info("STEP 1: Getting video details")
        video = repo.get_video_by_id(video_id)
        
        if not video:
            logger.info(f"Video {video_id} not found in database, fetching from YouTube")
            video_details = youtube_service.get_video_details(video_id)
            
            if not video_details:
                logger.error(f"YouTube API returned no details for video {video_id}")
                return
            
            logger.info(f"YouTube API response: {video_details}")
            
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
        else:
            logger.info(f"Found video {video_id} in database")
        
        # STEP 2: Get transcript
        logger.info("STEP 2: Getting transcript")
        transcript = transcription_service.get_transcript(video_id)
        
        if not transcript:
            logger.error(f"No transcript available for video {video_id}")
            return
        
        logger.info(f"Transcript retrieved successfully ({len(transcript)} characters)")
        logger.info(f"Transcript preview: {transcript[:200]}...")
        
        # Save transcript to database
        repo.update_transcript(video_id, transcript)
        
        # STEP 3: Analyze transcript with Claude
        logger.info("STEP 3: Analyzing transcript with Claude")
        
        # Prepare metadata
        video_metadata = {
            "title": video.title,
            "description": video.description,
            "channel_title": video.channel_title
        }
        
        # Call analysis service
        logger.info("Calling Claude API for analysis")
        analysis_results = analysis_service.analyze_video(
            video_id=video_id,
            transcript=transcript,
            video_metadata=video_metadata
        )
        
        logger.info("Analysis completed successfully")
        logger.info(f"Analysis results: {analysis_results}")
        
        # STEP 4: Save analysis results
        logger.info("STEP 4: Saving analysis results")
        
        summary = repo.create_summary(
            video_id=video_id,
            short_summary=analysis_results.get("summary", ""),
            detailed_summary=analysis_results.get("summary", ""),
            key_points=analysis_results.get("key_points", []),
            topics=[topic.get("name", "") for topic in analysis_results.get("topics", [])],
            sentiment=analysis_results.get("sentiment", "neutral")
        )
        
        logger.info(f"Summary saved for video {video_id}")
        logger.info("=== DEBUG ANALYSIS COMPLETE ===")
        
    except Exception as e:
        import traceback
        logger.error(f"Error during analysis: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        video_id = sys.argv[1]
        analyze_video(video_id)
    else:
        # Default to a video that likely has transcripts (TED Talk)
        analyze_video("X4Qm9cGRub0")