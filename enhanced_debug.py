# enhanced_debug.py

import sys
import logging
import traceback
from datetime import datetime

# Configure logging to display more information
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("enhanced_debug")

def run_debug(video_id):
    """Run an enhanced debug process with detailed output."""
    print(f"\n{'='*50}")
    print(f"ENHANCED DEBUG FOR VIDEO: {video_id}")
    print(f"{'='*50}\n")
    
    try:
        # Import required services and repositories
        from db import SessionLocal
        from repositories.video_repository import VideoRepository
        from services.youtube_service import YouTubeService
        from services.transcription_service import TranscriptionService
        from services.analysis_service import AnalysisService
        import config
        
        # Initialize services
        print("Initializing services...")
        youtube_service = YouTubeService()
        transcription_service = TranscriptionService()
        analysis_service = AnalysisService(api_key=config.ANTHROPIC_API_KEY)
        
        # Get database session
        db = SessionLocal()
        repo = VideoRepository(db)
        
        try:
            # STEP 1: Get video details
            print("\nSTEP 1: Getting video details from YouTube API")
            print("-" * 40)
            video_details = youtube_service.get_video_details(video_id)
            
            if not video_details:
                print("❌ Failed to get video details from YouTube API")
                return
            
            print("✅ Successfully retrieved video details:")
            print(f"  Title: {video_details.get('title')}")
            print(f"  Channel: {video_details.get('channel_title')}")
            print(f"  Duration: {video_details.get('duration_seconds')} seconds")
            
            # STEP 2: Get transcript
            print("\nSTEP 2: Getting video transcript")
            print("-" * 40)
            transcript = transcription_service.get_transcript(video_id)
            
            if not transcript:
                print("❌ Failed to retrieve transcript")
                return
            
            print(f"✅ Successfully retrieved transcript ({len(transcript)} characters)")
            print(f"  Transcript preview: {transcript[:100]}...")
            
            # STEP 3: Analyze transcript
            print("\nSTEP 3: Analyzing transcript with Claude API")
            print("-" * 40)
            
            # Prepare metadata
            video_metadata = {
                "title": video_details.get("title", ""),
                "description": video_details.get("description", ""),
                "channel_title": video_details.get("channel_title", "")
            }
            
            # Type check the responses at each step
            print(f"  Metadata types:")
            print(f"    - title: {type(video_metadata['title'])}")
            print(f"    - description: {type(video_metadata['description'])}")
            print(f"    - channel_title: {type(video_metadata['channel_title'])}")
            
            # Call analysis service with additional debugging
            print("  Calling Claude API for analysis...")
            try:
                analysis_results = analysis_service.analyze_video(
                    video_id=video_id,
                    transcript=transcript,
                    video_metadata=video_metadata
                )
                
                print("  Analysis results types:")
                for key, value in analysis_results.items():
                    print(f"    - {key}: {type(value)}")
                
                if "summary" in analysis_results:
                    if isinstance(analysis_results["summary"], dict):
                        print("    ⚠️ WARNING: summary is a dictionary, should be a string")
                        print(f"       Keys: {analysis_results['summary'].keys()}")
                    else:
                        print(f"    Summary preview: {analysis_results['summary'][:100]}...")
                
                if "key_points" in analysis_results:
                    if isinstance(analysis_results["key_points"], list):
                        print(f"    Key points count: {len(analysis_results['key_points'])}")
                        if analysis_results["key_points"] and isinstance(analysis_results["key_points"][0], dict):
                            print(f"    First key point keys: {analysis_results['key_points'][0].keys()}")
                    else:
                        print(f"    ⚠️ WARNING: key_points is not a list, it's a {type(analysis_results['key_points'])}")
                
                # STEP 4: Create or update video in database
                print("\nSTEP 4: Database Operations")
                print("-" * 40)
                
                # Check if video exists
                existing_video = repo.get_video_by_id(video_id)
                if existing_video:
                    print(f"  Video {video_id} already exists in database")
                else:
                    print(f"  Creating video {video_id} in database")
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
                        print("  ✅ Video created successfully")
                    except Exception as e:
                        print(f"  ❌ Error creating video: {str(e)}")
                        traceback.print_exc()
                
                # STEP 5: Save analysis results
                print("\nSTEP 5: Saving analysis results")
                print("-" * 40)
                
                # Convert dictionaries to strings if needed
                if isinstance(analysis_results.get("summary"), dict):
                    print("  Converting summary dictionary to string")
                    if "summary" in analysis_results["summary"]:
                        analysis_results["summary"] = analysis_results["summary"]["summary"]
                    else:
                        analysis_results["summary"] = str(analysis_results["summary"])
                
                if isinstance(analysis_results.get("detailed_summary"), dict):
                    print("  Converting detailed_summary dictionary to string")
                    if "summary" in analysis_results["detailed_summary"]:
                        analysis_results["detailed_summary"] = analysis_results["detailed_summary"]["summary"]
                    else:
                        analysis_results["detailed_summary"] = str(analysis_results["detailed_summary"])
                
                # Ensure we have a string for detailed_summary
                if "detailed_summary" not in analysis_results:
                    analysis_results["detailed_summary"] = analysis_results.get("summary", "")
                
                try:
                    # Extract topics from dictionaries if needed
                    topics = analysis_results.get("topics", [])
                    processed_topics = []
                    
                    if isinstance(topics, list):
                        for topic in topics:
                            if isinstance(topic, dict) and "name" in topic:
                                processed_topics.append(topic["name"])
                            elif isinstance(topic, str):
                                processed_topics.append(topic)
                            else:
                                processed_topics.append(str(topic))
                    elif isinstance(topics, str):
                        processed_topics = [topics]
                    else:
                        processed_topics = ["General"]
                    
                    print(f"  Processed topics: {processed_topics}")
                    
                    # Create summary
                    summary = repo.create_summary(
                        video_id=video_id,
                        short_summary=analysis_results.get("summary", ""),
                        detailed_summary=analysis_results.get("detailed_summary", analysis_results.get("summary", "")),
                        key_points=analysis_results.get("key_points", []),
                        topics=processed_topics,
                        sentiment=analysis_results.get("sentiment", "neutral"),
                        entities=[],  # Default empty entities
                        key_moments=[]  # Default empty key_moments
                    )
                    
                    print("  ✅ Summary created and saved successfully")
                    print(f"  Summary ID: {summary.id if hasattr(summary, 'id') else 'Unknown'}")
                    
                except Exception as e:
                    print(f"  ❌ Error creating summary: {str(e)}")
                    traceback.print_exc()
                
            except Exception as e:
                print(f"  ❌ Error during analysis: {str(e)}")
                traceback.print_exc()
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Top-level error: {str(e)}")
        traceback.print_exc()
    
    print(f"\n{'='*50}")
    print(f"DEBUG PROCESS COMPLETE")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        video_id = sys.argv[1]
        print(f"Running enhanced debug for video ID: {video_id}")
        run_debug(video_id)
    else:
        print("Please provide a video ID as a command-line argument.")
        print("Example: python enhanced_debug.py dQw4w9WgXcQ")
        sys.exit(1)