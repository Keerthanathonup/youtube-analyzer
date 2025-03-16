import os
import logging
import re
from typing import Dict, List, Optional, Any
import googleapiclient.discovery
import googleapiclient.errors
from datetime import datetime

logger = logging.getLogger(__name__)


class YouTubeService:
    """Service for interacting with the YouTube Data API to retrieve video content."""
    
    def __init__(self):
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            logger.warning("YouTube API key not found in environment variables")
            self.api = None
        else:
            api_service_name = "youtube"
            api_version = "v3"
            self.api = googleapiclient.discovery.build(
                api_service_name, api_version, developerKey=api_key)
    
    def extract_video_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract YouTube video ID from various URL formats.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Video ID if found, None otherwise
        """
        # Match standard YouTube URLs
        youtube_regex = (
            r'(?:https?:\/\/)?(?:www\.)?'
            r'(?:youtube\.com\/(?:watch\?v=|embed\/|v\/)|youtu\.be\/)'
            r'([a-zA-Z0-9_-]{11})'
        )
        
        match = re.search(youtube_regex, url)
        if match:
            return match.group(1)
            
        return None
    
    def get_video_details(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve details for a specific video from YouTube.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dictionary with video details or None if not found
        """
        if not self.api:
            logger.error("YouTube API not initialized")
            return None
            
        try:
            request = self.api.videos().list(
                part="snippet,contentDetails",
                id=video_id
            )
            response = request.execute()
            
            if not response.get("items"):
                logger.warning(f"No video found with ID: {video_id}")
                return None
                
            video_data = response["items"][0]
            
            # Extract and format relevant fields
            snippet = video_data.get("snippet", {})
            content_details = video_data.get("contentDetails", {})
            
            # Parse duration from ISO 8601 format
            duration_str = content_details.get("duration", "PT0S")
            duration_seconds = self._parse_duration(duration_str)
            
            # Format published date
            published_at_str = snippet.get("publishedAt")
            if published_at_str:
                published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
            else:
                published_at = None
                
            # Build result dictionary (simplified for content analysis focus)
            result = {
                "id": video_id,
                "title": snippet.get("title"),
                "description": snippet.get("description"),
                "channel_title": snippet.get("channelTitle"),
                "published_at": published_at,
                "duration_seconds": duration_seconds,
                "content_type": self._guess_content_type(snippet.get("title", ""), snippet.get("description", ""))
            }
            
            return result
            
        except googleapiclient.errors.HttpError as e:
            logger.error(f"YouTube API error for video {video_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving video {video_id}: {str(e)}")
            return None
    
    def search_videos(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for videos on YouTube based on a query.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of video data dictionaries
        """
        if not self.api:
            logger.error("YouTube API not initialized")
            return []
            
        try:
            request = self.api.search().list(
                part="snippet",
                q=query,
                type="video",
                maxResults=max_results
            )
            response = request.execute()
            
            videos = []
            for item in response.get("items", []):
                video_id = item.get("id", {}).get("videoId")
                if video_id:
                    # For search results, we get basic data here
                    snippet = item.get("snippet", {})
                    
                    # Format published date
                    published_at_str = snippet.get("publishedAt")
                    if published_at_str:
                        published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                    else:
                        published_at = None
                    
                    videos.append({
                        "id": video_id,
                        "title": snippet.get("title"),
                        "description": snippet.get("description"),
                        "channel_title": snippet.get("channelTitle"),
                        "published_at": published_at
                    })
            
            return videos
            
        except googleapiclient.errors.HttpError as e:
            logger.error(f"YouTube API error for search query '{query}': {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during search for '{query}': {str(e)}")
            return []
    
    def _parse_duration(self, duration_str: str) -> int:
        """
        Parse ISO 8601 duration format to seconds.
        
        Args:
            duration_str: ISO 8601 duration string (e.g., 'PT1H2M3S')
            
        Returns:
            Duration in seconds
        """
        hours = 0
        minutes = 0
        seconds = 0
        
        # Extract hours
        hour_match = re.search(r'(\d+)H', duration_str)
        if hour_match:
            hours = int(hour_match.group(1))
            
        # Extract minutes
        minute_match = re.search(r'(\d+)M', duration_str)
        if minute_match:
            minutes = int(minute_match.group(1))
            
        # Extract seconds
        second_match = re.search(r'(\d+)S', duration_str)
        if second_match:
            seconds = int(second_match.group(1))
            
        return hours * 3600 + minutes * 60 + seconds
    
    def _guess_content_type(self, title: str, description: str) -> str:
        """
        Attempt to guess the content type based on title and description.
        
        Args:
            title: Video title
            description: Video description
            
        Returns:
            Guessed content type
        """
        title_lower = title.lower()
        desc_lower = description.lower()
        combined = title_lower + " " + desc_lower
        
        # Check for common content type indicators
        if any(term in combined for term in ["tutorial", "how to", "guide", "learn", "course"]):
            return "tutorial"
        elif any(term in combined for term in ["review", "rating", "recommend", "worth it"]):
            return "review"
        elif any(term in combined for term in ["vlog", "day in", "my life", "experience"]):
            return "vlog"
        elif any(term in combined for term in ["news", "update", "latest", "breaking"]):
            return "news"
        elif any(term in combined for term in ["explain", "explained", "understanding", "concept"]):
            return "educational"
        elif any(term in combined for term in ["gameplay", "playthrough", "gaming", "let's play"]):
            return "gaming"
        elif any(term in combined for term in ["unboxing", "haul", "new product"]):
            return "unboxing"
        elif any(term in combined for term in ["interview", "conversation", "discussion", "podcast"]):
            return "interview"
            
        # Default type
        return "other"