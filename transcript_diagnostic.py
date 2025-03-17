#!/usr/bin/env python3
"""
Transcript Diagnostic Tool

This script performs comprehensive diagnostics on the transcript retrieval process 
for a YouTube video and helps identify and fix issues with the analysis pipeline.
"""

import os
import sys
import logging
import time
import argparse
import json
from typing import Dict, Any, List
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("transcript_diagnostic.log")
    ]
)
logger = logging.getLogger("transcript_diagnostic")

# Import local modules
try:
    from services.transcription_service import TranscriptionService
    from services.analysis_service import AnalysisService
    from services.youtube_service import YouTubeService
    from repositories.video_repository import VideoRepository
    from db import SessionLocal
    import config
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.error("Make sure you're running this script from the project root directory.")
    sys.exit(1)

def format_duration(seconds: int) -> str:
    """Format seconds into a readable duration string."""
    if seconds < 60:
        return f"{seconds}s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {seconds}s"

def check_environment() -> Dict[str, Any]:
    """Check environment for required API keys and dependencies."""
    results = {
        "environment": {
            "python_version": sys.version,
            "api_keys": {},
            "dependencies": {}
        },
        "status": "ok"
    }
    
    # Check API keys
    api_keys = {
        "YOUTUBE_API_KEY": os.getenv("YOUTUBE_API_KEY") or config.YOUTUBE_API_KEY,
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY") or config.ANTHROPIC_API_KEY,
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY") or config.OPENAI_API_KEY
    }
    
    for key, value in api_keys.items():
        if value:
            results["environment"]["api_keys"][key] = "✅ Available"
        else:
            results["environment"]["api_keys"][key] = "❌ Missing"
            if key in ["YOUTUBE_API_KEY", "ANTHROPIC_API_KEY"]:
                results["status"] = "warning"
    
    # Check dependencies
    dependencies = ["youtube_transcript_api", "requests", "yt_dlp", "pytube", "openai", "anthropic"]
    
    for dep in dependencies:
        try:
            __import__(dep)
            results["environment"]["dependencies"][dep] = "✅ Installed"
        except ImportError:
            if dep in ["youtube_transcript_api", "requests"]:
                results["status"] = "warning"
                results["environment"]["dependencies"][dep] = "❌ Missing (Required)"
            else:
                results["environment"]["dependencies"][dep] = "⚠️ Missing (Optional)"
    
    return results

def test_youtube_api(video_id: str) -> Dict[str, Any]:
    """Test the YouTube API connectivity and fetch video details."""
    youtube_service = YouTubeService()
    
    start_time = time.time()
    try:
        video_details = youtube_service.get_video_details(video_id)
        duration = time.time() - start_time
        
        if video_details:
            return {
                "status": "success",
                "duration": format_duration(int(duration)),
                "title": video_details.get("title", "Unknown"),
                "channel": video_details.get("channel_title", "Unknown"),
                "description_preview": video_details.get("description", "")[:100] + "..." if video_details.get("description") else "No description"
            }
        else:
            return {
                "status": "error",
                "duration": format_duration(int(duration)),
                "error": "No video details returned"
            }
    except Exception as e:
        duration = time.time() - start_time
        return {
            "status": "error",
            "duration": format_duration(int(duration)),
            "error": str(e)
        }

def test_transcript_retrieval(video_id: str, force_refresh: bool = False) -> Dict[str, Any]:
    """Test transcript retrieval for the video."""
    transcription_service = TranscriptionService()
    
    logger.info(f"Testing transcript retrieval for video {video_id}")
    start_time = time.time()
    
    try:
        transcript = transcription_service.get_transcript(video_id, force_refresh=force_refresh)
        duration = time.time() - start_time
        
        if transcript:
            # Assess quality
            quality_info = transcription_service.assess_transcript_quality(transcript)
            
            return {
                "status": "success",
                "duration": format_duration(int(duration)),
                "transcript_preview": transcript[:150] + "..." if len(transcript) > 150 else transcript,
                "word_count": quality_info["word_count"],
                "quality_score": quality_info["quality"],
                "quality_notes": quality_info["reason"],
                "metrics": transcription_service.get_transcript_metrics()
            }
        else:
            return {
                "status": "error",
                "duration": format_duration(int(duration)),
                "error": "No transcript retrieved",
                "metrics": transcription_service.get_transcript_metrics()
            }
    except Exception as e:
        duration = time.time() - start_time
        return {
            "status": "error",
            "duration": format_duration(int(duration)),
            "error": str(e)
        }

def test_analysis(video_id: str, transcript: str = None) -> Dict[str, Any]:
    """Test content analysis with Claude API."""
    analysis_service = AnalysisService(api_key=config.ANTHROPIC_API_KEY)
    youtube_service = YouTubeService()
    
    if not transcript:
        transcription_service = TranscriptionService()
        transcript = transcription_service.get_transcript(video_id)
        
        if not transcript:
            return {
                "status": "error",
                "error": "No transcript available for analysis"
            }
    
    # Get video metadata
    video_metadata = {}
    try:
        video_details = youtube_service.get_video_details(video_id)
        if video_details:
            video_metadata = {
                "title": video_details.get("title", ""),
                "description": video_details.get("description", ""),
                "channel_title": video_details.get("channel_title", "")
            }
    except Exception as e:
        logger.warning(f"Could not get video metadata: {e}")
    
    # Test analysis
    logger.info(f"Testing content analysis for video {video_id}")
    start_time = time.time()
    
    try:
        analysis_results = analysis_service.analyze_video(
            video_id=video_id,
            transcript=transcript,
            video_metadata=video_metadata
        )
        duration = time.time() - start_time
        
        if analysis_results:
            return {
                "status": "success",
                "duration": format_duration(int(duration)),
                "summary_preview": analysis_results.get("summary", "")[:150] + "..." if analysis_results.get("summary", "") else "No summary",
                "key_points_count": len(analysis_results.get("key_points", [])),
                "topics_count": len(analysis_results.get("topics", [])),
                "sentiment": analysis_results.get("sentiment", "unknown")
            }
        else:
            return {
                "status": "error",
                "duration": format_duration(int(duration)),
                "error": "No analysis results returned"
            }
    except Exception as e:
        duration = time.time() - start_time
        return {
            "status": "error",
            "duration": format_duration(int(duration)),
            "error": str(e)
        }

def test_database_integration(video_id: str) -> Dict[str, Any]:
    """Test database integration by saving and retrieving video and summary data."""
    db = SessionLocal()
    try:
        repo = VideoRepository(db)
        
        # Check if video exists
        video = repo.get_video_by_id(video_id)
        
        if video:
            logger.info(f"Video {video_id} already exists in database")
            video_status = "existing"
        else:
            # Try to create video from YouTube data
            youtube_service = YouTubeService()
            video_details = youtube_service.get_video_details(video_id)
            
            if not video_details:
                return {"status": "error", "error": "Could not get video details from YouTube"}
            
            try:
                logger.info(f"Creating video {video_id} in database")
                video = repo.create_video(
                    video_id=video_id,
                    title=video_details.get("title", "Unknown"),
                    channel_name=video_details.get("channel_title", "Unknown"),
                    published_at=video_details.get("published_at"),
                    thumbnail_url=video_details.get("thumbnail_url", ""),
                    duration=video_details.get("duration_seconds", 0),
                    description=video_details.get("description", "")
                )
                video_status = "created"
            except Exception as e:
                logger.error(f"Error creating video in database: {e}")
                return {"status": "error", "error": f"Database error: {str(e)}"}
        
        # Check if summary exists
        summary = repo.get_video_summary(video_id)
        
        if summary:
            logger.info(f"Summary for video {video_id} already exists in database")
            summary_status = "existing"
        else:
            # Get transcript and analyze
            transcription_service = TranscriptionService()
            transcript = transcription_service.get_transcript(video_id)
            
            if not transcript:
                return {
                    "status": "partial",
                    "video_status": video_status,
                    "summary_status": "error",
                    "error": "Could not retrieve transcript for analysis"
                }
            
            try:
                # Analyze with Claude
                analysis_service = AnalysisService(api_key=config.ANTHROPIC_API_KEY)
                video_metadata = {
                    "title": video.title,
                    "description": video.description,
                    "channel_title": video.channel_title
                }
                
                analysis_results = analysis_service.analyze_video(
                    video_id=video_id,
                    transcript=transcript,
                    video_metadata=video_metadata
                )
                
                if not analysis_results:
                    return {
                        "status": "partial",
                        "video_status": video_status,
                        "summary_status": "error",
                        "error": "Analysis service returned no results"
                    }
                
                # Create summary
                logger.info(f"Creating summary for video {video_id}")
                summary = repo.create_summary(
                    video_id=video_id,
                    short_summary=analysis_results.get("summary", ""),
                    detailed_summary=analysis_results.get("summary", ""),
                    key_points=analysis_results.get("key_points", []),
                    topics=[topic.get("name", "") for topic in analysis_results.get("topics", [])],
                    sentiment=analysis_results.get("sentiment", "neutral")
                )
                summary_status = "created"
            except Exception as e:
                logger.error(f"Error creating summary in database: {e}")
                return {
                    "status": "partial",
                    "video_status": video_status,
                    "summary_status": "error",
                    "error": f"Database error: {str(e)}"
                }
        
        return {
            "status": "success",
            "video_status": video_status,
            "summary_status": summary_status,
            "video_id": video_id,
            "title": video.title if video else "Unknown",
            "has_transcript": bool(video.transcript) if video else False,
            "summary_id": summary.id if summary else None
        }
    
    finally:
        db.close()

def run_full_diagnostic(video_id: str, force_refresh: bool = False) -> Dict[str, Any]:
    """Run a full diagnostic on the entire pipeline for a specific video."""
    results = {
        "video_id": video_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "environment": {},
        "youtube_api": {},
        "transcript_retrieval": {},
        "analysis": {},
        "database": {},
        "overall_status": "pending"
    }
    
    # Check environment
    logger.info("Checking environment...")
    env_check = check_environment()
    results["environment"] = env_check
    
    # Test YouTube API
    logger.info("Testing YouTube API...")
    youtube_test = test_youtube_api(video_id)
    results["youtube_api"] = youtube_test
    
    if youtube_test["status"] != "success":
        results["overall_status"] = "failed"
        return results
    
    # Test transcript retrieval
    logger.info("Testing transcript retrieval...")
    transcript_test = test_transcript_retrieval(video_id, force_refresh)
    results["transcript_retrieval"] = transcript_test
    
    if transcript_test["status"] != "success":
        results["overall_status"] = "failed"
        return results
    
    # Get the transcript for analysis test
    transcription_service = TranscriptionService()
    transcript = transcription_service.get_transcript(video_id)
    
    # Test analysis
    logger.info("Testing content analysis...")
    analysis_test = test_analysis(video_id, transcript)
    results["analysis"] = analysis_test
    
    if analysis_test["status"] != "success":
        results["overall_status"] = "failed"
        return results
    
    # Test database integration
    logger.info("Testing database integration...")
    db_test = test_database_integration(video_id)
    results["database"] = db_test
    
    if db_test["status"] != "success":
        results["overall_status"] = "partial"
    else:
        results["overall_status"] = "success"
    
    return results

def main():
    parser = argparse.ArgumentParser(description="YouTube Transcript Diagnostic Tool")
    parser.add_argument("video_id", help="YouTube video ID to analyze")
    parser.add_argument("--force-refresh", action="store_true", help="Force refresh cached transcripts")
    parser.add_argument("--output", help="Output file for diagnostics results (JSON)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
    
    print(f"\n🔍 Running diagnostics for video ID: {args.video_id}\n")
    
    try:
        results = run_full_diagnostic(args.video_id, args.force_refresh)
        
        # Save results to file if specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to {args.output}")
        
        # Print summary
        print("\n=== Diagnostic Summary ===")
        print(f"Video ID: {args.video_id}")
        print(f"Title: {results['youtube_api'].get('title', 'Unknown')}")
        print(f"Channel: {results['youtube_api'].get('channel', 'Unknown')}")
        print(f"Overall Status: {results['overall_status'].upper()}")
        
        # Print component status
        print("\nComponent Status:")
        print(f"- Environment: {results['environment']['status']}")
        print(f"- YouTube API: {results['youtube_api']['status']}")
        print(f"- Transcript Retrieval: {results['transcript_retrieval']['status']}")
        print(f"- Content Analysis: {results['analysis']['status']}")
        print(f"- Database Integration: {results['database']['status']}")
        
        # Print transcript info if available
        if results['transcript_retrieval']['status'] == 'success':
            print("\nTranscript Details:")
            print(f"- Word Count: {results['transcript_retrieval'].get('word_count', 'Unknown')}")
            print(f"- Quality Score: {results['transcript_retrieval'].get('quality_score', 'Unknown')}/100")
            print(f"- Notes: {results['transcript_retrieval'].get('quality_notes', 'None')}")
        
        # Print recommendations based on results
        print("\nRecommendations:")
        if results['overall_status'] == 'success':
            print("✅ All components are working correctly!")
        else:
            if results['environment']['status'] == 'warning':
                missing_keys = [k for k, v in results['environment'].get('api_keys', {}).items() 
                              if '❌' in v]
                if missing_keys:
                    print(f"⚠️  Missing API keys: {', '.join(missing_keys)}")
                    print("   Add these to your .env file or environment variables")
                
                missing_deps = [k for k, v in results['environment'].get('dependencies', {}).items() 
                              if '❌' in v]
                if missing_deps:
                    print(f"⚠️  Missing required dependencies: {', '.join(missing_deps)}")
                    print("   Install with: pip install " + " ".join(missing_deps))
            
            if results['transcript_retrieval']['status'] == 'error':
                print("❌ Transcript retrieval failed:")
                print(f"   Error: {results['transcript_retrieval'].get('error', 'Unknown error')}")
                print("   Try installing optional dependencies like yt-dlp or pytube for better success rates")
            
            if results['analysis']['status'] == 'error':
                print("❌ Content analysis failed:")
                print(f"   Error: {results['analysis'].get('error', 'Unknown error')}")
                print("   Check your Claude API key and connection")
            
            if results['database']['status'] == 'error':
                print("❌ Database integration failed:")
                print(f"   Error: {results['database'].get('error', 'Unknown error')}")
                print("   Check database configuration and run migrations")
        
        print("\nSee transcript_diagnostic.log for more details")
        
    except Exception as e:
        logger.error(f"Diagnostic failed: {e}", exc_info=True)
        print(f"\n❌ Diagnostic failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())