# tests/test_transcript.py
import sys
import os

# Add the parent directory to the Python path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from services.transcription_service import TranscriptionService

# Load environment variables
load_dotenv()

def test_transcript_retrieval():
    """Test retrieving a transcript from a known YouTube video."""
    # Initialize the transcription service
    service = TranscriptionService()
    
    # Try multiple videos that should have English captions
    test_videos = [
        "9bZkp7q19f0",  # Gangnam Style - very popular
        "hVvEISFw9w0",  # A TED Talk - should have good captions
        "8jPQjjsBbIc",  # A tutorial video that likely has captions
        "TuMbYBSYAn0",  # A news segment that should have captions
        "dQw4w9WgXcQ"   # Original test video
    ]
    
    found_transcript = False
    
    for video_id in test_videos:
        print(f"\nAttempting to retrieve transcript for video ID: {video_id}")
        
        try:
            transcript = service.get_transcript(video_id)
            
            if transcript:
                print(f"SUCCESS! Retrieved transcript with {len(transcript)} characters.")
                print("\nFirst 200 characters of transcript:")
                print(transcript[:200] + "...")
                found_transcript = True
                break
            else:
                print(f"No transcript available for video {video_id}")
                
        except Exception as e:
            print(f"ERROR retrieving transcript for {video_id}: {str(e)}")
    
    if not found_transcript:
        print("\nFAILED to retrieve transcripts for all test videos.")
        print("This could indicate an issue with:")
        print("1. The YouTube Transcript API library")
        print("2. Your network connection")
        print("3. YouTube's API restrictions in your region")
    
    return found_transcript

if __name__ == "__main__":
    print("Testing YouTube Transcript API...")
    success = test_transcript_retrieval()
    
    if not success:
        print("\nAdditional debugging information:")
        # Try to import the library directly to check if it's installed
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            print("✓ youtube_transcript_api is installed")
            
            # Test the library directly
            try:
                print("Testing direct API call...")
                transcript_list = YouTubeTranscriptApi.list_transcripts("9bZkp7q19f0")  # Gangnam Style
                print(f"Available transcripts: {[t.language_code for t in transcript_list]}")
            except Exception as e:
                print(f"Direct API call failed: {str(e)}")
        except ImportError:
            print("✗ youtube_transcript_api is not installed")
            print("Run: pip install youtube-transcript-api")