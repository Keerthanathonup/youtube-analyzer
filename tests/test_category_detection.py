# tests/test_category_detection.py

import sys
import os
import json

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.category_detection import CategoryDetectionService
from services.claude_service import ClaudeService
from services.youtube_service import YouTubeService
from services.transcription_service import TranscriptionService
from services.analysis_service import AnalysisService
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_category_detection():
    """Test the category detection functionality with a real YouTube video."""
    # Initialize services
    claude_service = ClaudeService()
    category_detection = CategoryDetectionService(claude_service=claude_service)
    youtube_service = YouTubeService()
    transcription_service = TranscriptionService()
    
    # Test videos of different types
    test_videos = {
        # Educational/Tutorial
        "educational": "8jPQjjsBbIc",  # A Python tutorial video
        
        # Cooking/Recipe
        "cooking": "RCD71WkBFrk",      # A cooking video
        
        # Product Review/Unboxing
        "review": "eUjhf4lxStY",        # A smartphone review
        
        # Entertainment/Vlog
        "vlog": "8dh3K3O9VsE",         # A travel vlog
        
        # Gaming
        "gaming": "YUnT4vt5-8A"         # A gaming video
    }
    
    # Choose a video to test (you can change this to test different categories)
    test_type = "educational"
    video_id = test_videos[test_type]
    
    print(f"\nTesting category detection with {test_type} video (ID: {video_id})")
    
    # Get video details
    try:
        video_details = youtube_service.get_video_details(video_id)
        if not video_details:
            print("❌ Could not get video details from YouTube API")
            return
            
        print(f"Video Title: {video_details.get('title')}")
        print(f"Channel: {video_details.get('channel_title')}")
        
        # Get transcript
        transcript = transcription_service.get_transcript(video_id)
        if not transcript:
            print("❌ Could not retrieve transcript for this video")
            return
            
        print(f"Transcript retrieved: {len(transcript)} characters")
        
        # Test category detection
        print("\nDetecting video category...")
        category, confidence, secondary_categories = category_detection.detect_category(
            transcript=transcript, 
            title=video_details.get('title', ''),
            description=video_details.get('description', ''),
            channel_title=video_details.get('channel_title', '')
        )
        
        print(f"✓ Primary Category: {category} (confidence: {confidence:.2f})")
        if secondary_categories:
            print("Secondary Categories:")
            for cat, conf in secondary_categories:
                print(f"  - {cat} (confidence: {conf:.2f})")
        
        # Get category-specific prompt
        print("\nGetting category-specific prompt...")
        prompt = category_detection.get_analysis_prompt(
            category=category,
            title=video_details.get('title', ''),
            description=video_details.get('description', ''),
            video_id=video_id
        )
        
        print(f"✓ Got prompt for {category} category ({len(prompt)} characters)")
        
        # Test a full analysis with the new AnalysisService
        print("\nTesting full analysis with category-specific prompt...")
        analysis_service = AnalysisService()
        
        analysis_results = analysis_service.analyze_video(
            video_id=video_id,
            transcript=transcript,
            video_metadata=video_details
        )
        
        if analysis_results:
            print("\n=== Analysis Results ===")
            print(f"Detected Category: {analysis_results.get('content_category', {}).get('primary', 'Unknown')}")
            print(f"Summary: {analysis_results.get('summary', '')[:150]}...")
            print(f"Key Points: {len(analysis_results.get('key_points', []))} items")
            topics = analysis_results.get('topics', [])
            if isinstance(topics, list) and topics and isinstance(topics[0], str):
                # If topics are simple strings
                print(f"Topics: {topics}")
            else:
                # If topics are dictionaries with a 'name' field
                print(f"Topics: {[t.get('name', '') for t in topics]}")
            print(f"Sentiment: {analysis_results.get('sentiment', 'Unknown')}")
            
            # Save the results to a file for inspection
            with open(f"test_analysis_{test_type}.json", "w") as f:
                json.dump(analysis_results, f, indent=2)
                
            print(f"\nComplete results saved to test_analysis_{test_type}.json")
        else:
            print("❌ Analysis failed to return results")
    
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
if __name__ == "__main__":
    test_category_detection()