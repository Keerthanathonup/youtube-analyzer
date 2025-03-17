# services/analysis_service.py

from typing import Dict, List, Any, Optional
import logging
import config
import re
from services.claude_service import ClaudeService
from services.transcription_service import TranscriptionService

logger = logging.getLogger(__name__)

class AnalysisService:
    """Service for analyzing video content and generating insights."""
    
    def __init__(self, api_key: str = None):
        """Initialize the analysis service."""
        self.claude_service = ClaudeService(api_key=api_key or config.ANTHROPIC_API_KEY)
        self.transcription_service = TranscriptionService()
        self.use_mock = config.ANTHROPIC_API_KEY is None or config.ANTHROPIC_API_KEY == ""
    
    def analyze_video(self, video_id: str, transcript: Optional[str] = None, video_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze video transcript and generate insights.
        
        Args:
            video_id: YouTube video ID
            transcript: Full transcript text of the video (optional)
            video_metadata: Dictionary with video title, description, etc.
            
        Returns:
            Dictionary with analysis results
        """
        # If transcript wasn't provided, try to get it
        if transcript is None and video_id:
            logger.info(f"No transcript provided, attempting to retrieve for video {video_id}")
            transcript = self.transcription_service.get_transcript(video_id)
        
        # Check if we have enough transcript content to analyze
        if not transcript or len(transcript.split()) < 10:
            logger.warning(f"Insufficient transcript for video {video_id}, using fallback strategy")
            
            # Generate mock transcript from metadata if available
            if video_metadata:
                title = video_metadata.get('title', '')
                description = video_metadata.get('description', '')
                if title or description:
                    logger.info("Generating mock transcript from metadata")
                    transcript = self.transcription_service.mock_transcript_from_metadata(
                        title=title, 
                        description=description
                    )
                    if not transcript or len(transcript.split()) < 10:
                        return self._generate_error_analysis(video_id, "Insufficient content for analysis")
                else:
                    return self._generate_error_analysis(video_id, "Insufficient transcript and metadata")
            else:
                return self._generate_error_analysis(video_id, "Insufficient transcript content for analysis")
        # Add chunking for large transcripts
        if transcript and len(transcript) > 6000:
            logger.info(f"Large transcript detected ({len(transcript)} chars), using chunked analysis")
            return self._analyze_large_transcript(transcript, video_metadata, video_id)
        
        # Use mock data if no API key is available
        if self.use_mock:
            return self._generate_mock_analysis(video_id, video_metadata)
        
        try:
            # Get full analysis from Claude
            logger.info(f"Sending content to Claude for analysis, content length: {len(transcript)}")
            analysis_results = self.claude_service.analyze_transcript(transcript, video_metadata)
            
            # Make sure we have all required fields
            if not all(key in analysis_results for key in ["summary", "key_points", "topics", "sentiment"]):
                logger.warning("Incomplete analysis results from Claude. Filling missing fields.")
                # Fill any missing fields with defaults
                if "summary" not in analysis_results:
                    analysis_results["summary"] = "Summary unavailable"
                if "key_points" not in analysis_results:
                    analysis_results["key_points"] = ["No key points identified"]
                if "topics" not in analysis_results:
                    analysis_results["topics"] = [{"name": "General", "description": "General content", "confidence": 50}]
                if "sentiment" not in analysis_results:
                    analysis_results["sentiment"] = "neutral"
                if "sentiment_score" not in analysis_results:
                    analysis_results["sentiment_score"] = 0
                if "sentiment_analysis" not in analysis_results:
                    analysis_results["sentiment_analysis"] = "Sentiment analysis unavailable"
            
            # Add video_id to the results
            analysis_results["video_id"] = video_id
            
            # Add source information to indicate if this was based on actual transcript or metadata
            if transcript and video_metadata and transcript.startswith(f"Video Title: {video_metadata.get('title', '')}"):
                analysis_results["analysis_source"] = "metadata"
            else:
                analysis_results["analysis_source"] = "transcript"
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error during analysis: {str(e)}", exc_info=True)
            return self._generate_error_analysis(video_id, f"Error during analysis: {str(e)}")
    
    def analyze_sentiment(self, transcript: str) -> Dict[str, Any]:
        """
        Analyze the sentiment of the video transcript.
        
        Args:
            transcript: Full transcript text
            
        Returns:
            Dictionary with sentiment analysis
        """
        if self.use_mock:
            return {
                "score": 0.2,
                "label": "positive",
                "analysis": "The content appears generally positive with an informative tone."
            }
        
        try:
            return self.claude_service.analyze_sentiment(transcript)
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}", exc_info=True)
            return {"score": 0, "label": "neutral", "analysis": "Error analyzing sentiment"}
    
    def extract_topics(self, transcript: str, max_topics: int = 5) -> List[Dict[str, Any]]:
        """
        Extract main topics from the transcript.
        
        Args:
            transcript: Full transcript text
            max_topics: Maximum number of topics to return
            
        Returns:
            List of topic dictionaries
        """
        if self.use_mock:
            return [
                {"name": "Technology", "description": "Discussion of technological concepts", "confidence": 85},
                {"name": "Education", "description": "Educational content and learning", "confidence": 70}
            ]
        
        try:
            return self.claude_service.identify_topics(transcript, max_topics)
        except Exception as e:
            logger.error(f"Error extracting topics: {str(e)}", exc_info=True)
            return [{"name": "Error", "description": "Failed to extract topics", "confidence": 0}]
    
    def generate_summary(self, transcript: str, max_length: int = 200) -> str:
        """
        Generate a concise summary of the transcript.
        
        Args:
            transcript: Full transcript text
            max_length: Maximum length of summary in words
            
        Returns:
            Summary text
        """
        if self.use_mock:
            return "This is a mock summary of the video content. In a real implementation, this would be generated based on the transcript."
        
        try:
            return self.claude_service.generate_summary(transcript, max_length)
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}", exc_info=True)
            return "Error generating summary"
    
    def extract_key_points(self, transcript: str, max_points: int = 5) -> List[str]:
        """
        Extract key points from the transcript.
        
        Args:
            transcript: Full transcript text
            max_points: Maximum number of key points to return
            
        Returns:
            List of key point strings
        """
        if self.use_mock:
            return [
                "This is the first mock key point",
                "This is the second mock key point",
                "This is the third mock key point"
            ]
        
        try:
            return self.claude_service.extract_key_points(transcript, max_points)
        except Exception as e:
            logger.error(f"Error extracting key points: {str(e)}", exc_info=True)
            return ["Error extracting key points"]
    
    def _generate_mock_analysis(self, video_id: str, video_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock analysis results for development/testing."""
        title = video_metadata.get('title', '')
        
        return {
            "video_id": video_id,
            "summary": f"This is a mock summary of the video titled '{title}'. In a real implementation, this would be generated through AI analysis of the transcript.",
            "key_points": [
                f"First key point about {title}",
                "Second key point with general information",
                "Third key point about the content",
                "Fourth key point with additional details",
                "Fifth key point summarizing the video"
            ],
            "topics": [
                {"name": "Main Topic", "description": "The primary subject of the video", "confidence": 90},
                {"name": "Secondary Topic", "description": "Another important subject covered", "confidence": 75},
                {"name": "Minor Topic", "description": "A briefly mentioned subject", "confidence": 60}
            ],
            "sentiment": "positive",
            "sentiment_score": 0.65,
            "sentiment_analysis": "The video has a generally positive tone with informative content.",
            "analysis_source": "mock"
        }
    
    def _generate_error_analysis(self, video_id: str, error_message: str) -> Dict[str, Any]:
        """Generate analysis results for error cases."""
        return {
            "video_id": video_id,
            "summary": f"Analysis error: {error_message}",
            "key_points": ["Unable to analyze video content"],
            "topics": [{"name": "Error", "description": error_message, "confidence": 0}],
            "sentiment": "neutral",
            "sentiment_score": 0,
            "sentiment_analysis": "Unable to analyze sentiment",
            "analysis_source": "error"
        }
    def _analyze_large_transcript(self, transcript, video_metadata, video_id):
        """
        Break down large transcripts into chunks for analysis.
        
        Args:
            transcript: Full transcript text
            video_metadata: Dictionary with video metadata
            video_id: YouTube video ID
            
        Returns:
            Dictionary with combined analysis results
        """
        logger.info(f"Chunking large transcript ({len(transcript)} chars) for {video_id}")
        
        # Split transcript into chunks of ~4000 characters (preserving whole sentences)
        chunks = []
        current_chunk = ""
        sentences = re.split(r'([.!?])', transcript)
        
        for i in range(0, len(sentences), 2):
            if i+1 < len(sentences):
                sentence = sentences[i] + sentences[i+1]
            else:
                sentence = sentences[i]
                
            if len(current_chunk) + len(sentence) < 4000:
                current_chunk += sentence
            else:
                chunks.append(current_chunk)
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
            
        logger.info(f"Split transcript into {len(chunks)} chunks")
        
        # Analyze each chunk
        results = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Analyzing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
            
            chunk_title = f"{video_metadata.get('title', '')} - Part {i+1}"
            chunk_metadata = {
                "title": chunk_title,
                "description": video_metadata.get("description", ""),
                "channel_title": video_metadata.get("channel_title", "")
            }
            
            try:
                # Use mock data if no API key is available
                if self.use_mock:
                    chunk_result = self._generate_mock_analysis(video_id, chunk_metadata)
                else:
                    chunk_result = self.claude_service.analyze_transcript(chunk, chunk_metadata)
                    
                results.append(chunk_result)
            except Exception as e:
                logger.error(f"Error analyzing chunk {i+1}: {str(e)}")
        
        # Combine results
        if not results:
            return self._generate_error_analysis(video_id, "Failed to analyze transcript chunks")
        
        combined_result = {
            "video_id": video_id,
            "summary": "",
            "detailed_summary": "",
            "key_points": [],
            "topics": [],
            "sentiment": self._combine_sentiments([r.get("sentiment", "neutral") for r in results]),
            "sentiment_score": sum([r.get("sentiment_score", 0) for r in results]) / len(results),
            "sentiment_analysis": ""
        }
        
        # Combine summaries
        summaries = [r.get("summary", "") for r in results]
        combined_result["summary"] = self._combine_summaries(summaries)
        combined_result["detailed_summary"] = combined_result["summary"]
        
        # Combine key points (take top 3 from each chunk, up to 10 total)
        all_key_points = []
        for result in results:
            points = result.get("key_points", [])
            if points:
                all_key_points.extend(points[:3])
        combined_result["key_points"] = all_key_points[:10]
        
        # Combine topics (take most common across all chunks)
        all_topics = []
        for result in results:
            topics = result.get("topics", [])
            if isinstance(topics, list):
                for topic in topics:
                    if isinstance(topic, dict) and "name" in topic:
                        all_topics.append(topic["name"])
                    elif isinstance(topic, str):
                        all_topics.append(topic)
        
        # Count topic occurrences
        topic_counts = {}
        for topic in all_topics:
            if topic in topic_counts:
                topic_counts[topic] += 1
            else:
                topic_counts[topic] = 1
        
        # Take the most common topics
        top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        combined_result["topics"] = [{"name": topic, "description": "", "confidence": count * 20} 
                                    for topic, count in top_topics]
        
        # Combine sentiment analysis texts
        sentiment_analyses = [r.get("sentiment_analysis", "") for r in results if r.get("sentiment_analysis")]
        if sentiment_analyses:
            combined_result["sentiment_analysis"] = sentiment_analyses[0]
        
        return combined_result

    def _combine_summaries(self, summaries):
        """Combine multiple summaries into a single coherent summary."""
        if not summaries:
            return ""
        
        if len(summaries) == 1:
            return summaries[0]
        
        combined = ""
        total_length = sum(len(s) for s in summaries)
        
        if total_length <= 150:
            # If total is short, just join them
            combined = " ".join(summaries)
        else:
            # Otherwise, take the first one and add key sentences from others
            combined = summaries[0]
            
            for summary in summaries[1:]:
                sentences = re.split(r'([.!?])', summary)
                
                # Join sentences back together
                sentences_joined = []
                for i in range(0, len(sentences), 2):
                    if i+1 < len(sentences):
                        sentences_joined.append(sentences[i] + sentences[i+1])
                    else:
                        sentences_joined.append(sentences[i])
                
                # Take the first sentence from each additional summary
                if sentences_joined:
                    combined += " " + sentences_joined[0]
        
        return combined

    def _combine_sentiments(self, sentiments):
        """Determine the overall sentiment from multiple chunk sentiments."""
        if not sentiments:
            return "neutral"
        
        # Count occurrences
        sentiment_counts = {}
        for sentiment in sentiments:
            lower_sentiment = sentiment.lower()
            if lower_sentiment in sentiment_counts:
                sentiment_counts[lower_sentiment] += 1
            else:
                sentiment_counts[lower_sentiment] = 1
        
        # Find the most common sentiment
        max_count = 0
        most_common = "neutral"
        
        for sentiment, count in sentiment_counts.items():
            if count > max_count:
                max_count = count
                most_common = sentiment
        
        return most_common