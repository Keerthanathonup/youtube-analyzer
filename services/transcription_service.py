import logging
import time
from typing import Optional, List, Dict, Any
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled, VideoUnavailable

logger = logging.getLogger(__name__)

class TranscriptionService:
    """Service for retrieving and processing video transcripts."""
    
    def __init__(self):
        """Initialize the transcription service."""
        pass
    
    def get_transcript(self, video_id: str, languages: List[str] = ['en']) -> Optional[str]:
        """
        Retrieve transcript for a YouTube video.
        
        Args:
            video_id: YouTube video ID
            languages: List of language codes to try (default is English)
            
        Returns:
            String with full transcript text or None if not available
        """
        logger.info(f"Attempting to retrieve transcript for video ID: {video_id}")
        
        # Simple direct approach first - just try to get the transcript
        try:
            # First attempt - direct approach
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
            if transcript_list:
                logger.info(f"Successfully retrieved transcript for video {video_id} (direct method)")
                return self._process_transcript(transcript_list)
        except Exception as e:
            logger.info(f"Direct transcript retrieval failed: {str(e)}")
            # Continue to more complex approach
        
        # More comprehensive approach
        try:
            # List available transcripts
            available_transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
            logger.info(f"Available transcripts for {video_id}: {[t.language_code for t in available_transcripts]}")
            
            # Try to find a transcript in preferred languages
            for language in languages:
                for transcript in available_transcripts:
                    if transcript.language_code == language:
                        try:
                            logger.info(f"Found transcript in {language}")
                            fetched_transcript = transcript.fetch()
                            return self._process_transcript(fetched_transcript)
                        except Exception as e:
                            logger.warning(f"Error fetching {language} transcript: {str(e)}")
            
            # If no preferred language found, try getting any available transcript
            try:
                default_transcript = next(iter(available_transcripts))
                logger.info(f"Using fallback transcript in {default_transcript.language_code}")
                
                if default_transcript.language_code not in languages:
                    logger.info(f"Translating from {default_transcript.language_code} to {languages[0]}")
                    translated_transcript = default_transcript.translate(languages[0])
                    return self._process_transcript(translated_transcript.fetch())
                else:
                    return self._process_transcript(default_transcript.fetch())
            except Exception as e:
                logger.warning(f"Error using fallback transcript: {str(e)}")
                
        except NoTranscriptFound:
            logger.warning(f"No transcript found for video {video_id}")
        except TranscriptsDisabled:
            logger.warning(f"Transcripts are disabled for video {video_id}")
        except VideoUnavailable:
            logger.warning(f"Video {video_id} is unavailable")
        except Exception as e:
            logger.error(f"Unexpected error retrieving transcript for video {video_id}: {str(e)}")
        
        # Last resort - try the raw API directly
        try:
            logger.info("Attempting direct API call as last resort")
            raw_transcript = YouTubeTranscriptApi.get_transcript(video_id)
            if raw_transcript:
                logger.info("Last resort direct call succeeded")
                return self._process_transcript(raw_transcript)
        except Exception as e:
            logger.warning(f"Last resort failed: {str(e)}")
            
        return None
    
    def _process_transcript(self, transcript_parts: List[Dict[str, Any]]) -> str:
        """
        Process transcript parts into a single readable text.
        
        Args:
            transcript_parts: List of transcript segments from the API
            
        Returns:
            Formatted transcript text
        """
        if not transcript_parts:
            return ""
            
        # Log transcript structure for debugging
        if transcript_parts and len(transcript_parts) > 0:
            logger.debug(f"Sample transcript part: {transcript_parts[0]}")
        
        # Concatenate all text parts with proper spacing
        full_text = ""
        last_end_time = 0
        
        for part in transcript_parts:
            if not isinstance(part, dict) or 'text' not in part:
                logger.warning(f"Unexpected transcript part format: {part}")
                continue
                
            text = part.get('text', '')
            start = part.get('start', 0)
            
            # Add paragraph break for significant time gaps (more than 4 seconds)
            if start - last_end_time > 4:
                full_text += "\n\n"
            # Add space between sequential parts
            elif full_text and not full_text.endswith('\n'):
                full_text += " "
                
            # Add the text and update last end time
            full_text += text
            last_end_time = start + part.get('duration', 0)
        
        logger.info(f"Processed transcript with {len(full_text)} characters")
        return full_text.strip()
    
    def get_transcript_with_timestamps(self, video_id: str, languages: List[str] = ['en']) -> Optional[List[Dict[str, Any]]]:
        """
        Get transcript with timestamp information.
        
        Args:
            video_id: YouTube video ID
            languages: List of language codes to try
            
        Returns:
            List of transcript segments with text and timestamps or None
        """
        try:
            # Simple direct approach first
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
                if transcript:
                    logger.info(f"Retrieved timestamp transcript for {video_id}")
                    return transcript
            except Exception as e:
                logger.debug(f"Direct timestamp transcript retrieval failed: {str(e)}")
            
            # More comprehensive approach
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try preferred languages first
            for language in languages:
                try:
                    transcript = transcript_list.find_transcript([language])
                    return transcript.fetch()
                except:
                    continue
            
            # If preferred languages not found, try any available and translate
            try:
                available_transcript = next(iter(transcript_list))
                if available_transcript.language_code not in languages:
                    available_transcript = available_transcript.translate(languages[0])
                return available_transcript.fetch()
            except:
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving timestamp transcript for video {video_id}: {str(e)}")
            return None

    def mock_transcript_from_metadata(self, title: str, description: str) -> str:
        """
        Generate a mock transcript when actual transcript cannot be retrieved.
        This is a fallback method for analysis when transcripts are unavailable.
        
        Args:
            title: Video title
            description: Video description
            
        Returns:
            Mock transcript text
        """
        logger.info("Generating mock transcript from metadata")
        mock_transcript = f"Video Title: {title}\n\n"
        
        # Add description paragraphs
        if description:
            # Split description into paragraphs and add timestamps
            paragraphs = description.split('\n')
            mock_time = 0
            for para in paragraphs:
                if para.strip():
                    mock_time += 30  # Mock 30-second intervals
                    mock_transcript += f"[{mock_time//60}:{mock_time%60:02d}] {para.strip()}\n\n"
        
        logger.info(f"Generated mock transcript with {len(mock_transcript)} characters")
        return mock_transcript.strip()