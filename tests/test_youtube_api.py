# tests/test_youtube_api.py
import sys
import os

# Add the parent directory to the Python path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from services.youtube_service import YouTubeService

# Load environment variables
load_dotenv()

def test_youtube_api():
    """Test retrieving video details from the YouTube API."""
    # Initialize the YouTube service
    service = YouTubeService()
    
    # Test video ID (Gangnam Style - very popular)
    video_id = "9bZkp7q19f0"
    
    print(f"Attempting to retrieve details for video ID: {video_id}")
    
    try:
        # Test get_video_details method
        video_details = service.get_video_details(video_id)
        
        if video_details:
            print(f"SUCCESS! Retrieved video details:")
            print(f"Title: {video_details.get('title')}")
            print(f"Channel: {video_details.get('channel_title')}")
            print(f"Duration: {video_details.get('duration_seconds')} seconds")
            print(f"Thumbnail URL: {video_details.get('thumbnail_url')}")
            
            # Also test search functionality
            print("\nTesting search functionality...")
            search_query = "python tutorial"
            search_results = service.search_videos(search_query, max_results=2)
            
            if search_results:
                print(f"SUCCESS! Found {len(search_results)} videos for query '{search_query}':")
                for i, result in enumerate(search_results, 1):
                    print(f"{i}. {result.get('title')} (ID: {result.get('id')})")
            else:
                print(f"No videos found for query '{search_query}'")
        else:
            print(f"ERROR: Could not retrieve details for video {video_id}")
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    print("Testing YouTube API...")
    test_youtube_api()