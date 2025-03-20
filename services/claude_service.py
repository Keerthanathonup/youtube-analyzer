# services/claude_service.py

import os
import requests
import json
import time
import re
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class ClaudeService:
    """Service for interacting with Anthropic's Claude API to analyze video transcripts."""
    
    def __init__(self, api_key: str = None):
        """Initialize the Claude service with API key."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key is required")
        
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        # Default to Claude 3 Sonnet for good balance of capabilities and speed
        self.default_model = os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307")
    
    def _call_claude_api(self, system_prompt: str, user_prompt: str, model: str = None, max_tokens: int = 1000, max_retries: int = 3) -> str:
        # Define fallback models in order of preference
        models = [
            model or self.default_model,  # First try the specified/default model
            "claude-3-haiku-20240307",    # Then try haiku if not already the default
            "claude-3-sonnet-20240229",   # Then try sonnet
            "claude-instant-1.2"          # Finally try older model as last resort
        ]
        
        # Remove duplicates while preserving order
        unique_models = []
        for m in models:
            if m not in unique_models:
                unique_models.append(m)
        
        # Try each model in sequence
        last_error = None
        for current_model in unique_models:
            retries = 0
            while retries < max_retries:
                try:
                    payload = {
                        "model": current_model,
                        "max_tokens": max_tokens,
                        "system": system_prompt,
                        "messages": [
                            {"role": "user", "content": user_prompt}
                        ]
                    }
                    
                    response = requests.post(
                        self.base_url,
                        headers=self.headers,
                        json=payload,
                        timeout=15  # Add a timeout
                    )
                    
                    response.raise_for_status()
                    response_json = response.json()
                    
                    # Extract the content from Claude's response
                    logger.info(f"Successfully used model: {current_model}")
                    return response_json.get("content", [{"text": "No response from Claude"}])[0].get("text", "")
                    
                except requests.exceptions.RequestException as e:
                    last_error = e
                    logger.warning(f"API call failed with model {current_model} (attempt {retries+1}/{max_retries}): {str(e)}")
                    retries += 1
                    time.sleep(2 * retries)  # Exponential backoff
            
            logger.warning(f"All retries failed with model {current_model}, trying next model if available")
        
        # If we've tried all models and all failed
        logger.error(f"All models failed after multiple retries. Last error: {str(last_error)}")
        return "Error: Failed with all available models after multiple retries"
        
    def analyze_transcript_with_prompt(self, transcript: str, video_metadata: Dict[str, Any], custom_prompt: str) -> Dict[str, Any]:
        """
        Analyze video transcript using Claude API with a custom prompt.
        """
        # Prepare the system prompt
        system_prompt = "You are an expert video content analyzer. Provide clear, concise, and structured analysis of video transcripts."
        
        # Combine the custom prompt with transcript
        user_prompt = f"""
        {custom_prompt}
        
        TRANSCRIPT:
        {transcript[:8000]}
        
        Respond ONLY with the JSON. No introduction or explanation.
        """
        
        try:
            # Call Claude API with increased max_tokens (changed from 2000 to 4000)
            response_text = self._call_claude_api(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=4000  # Increased from 2000 to 4000
            )
            
            # Extract the JSON from the response
            analysis_results = self._extract_json(response_text)
            
            # Ensure required fields exist with defaults if missing
            required_fields = ["summary", "key_points", "topics", "sentiment", "sentiment_score"]
            for field in required_fields:
                if field not in analysis_results:
                    if field == "summary":
                        analysis_results[field] = "Summary unavailable"
                    elif field == "key_points":
                        analysis_results[field] = ["No key points identified"]
                    elif field == "topics":
                        analysis_results[field] = [{"name": "General", "description": "General content", "confidence": 50}]
                    elif field == "sentiment":
                        analysis_results[field] = "neutral"
                    elif field == "sentiment_score":
                        analysis_results[field] = 0.5
            
            # Process key_points if it's a string
            if isinstance(analysis_results.get("key_points"), str):
                analysis_results["key_points"] = [analysis_results["key_points"]]
            
            # Process topics if it's not in expected format
            if "topics" in analysis_results:
                if isinstance(analysis_results["topics"], str):
                    analysis_results["topics"] = [{"name": analysis_results["topics"], "confidence": 70}]
                elif isinstance(analysis_results["topics"], list) and analysis_results["topics"] and isinstance(analysis_results["topics"][0], str):
                    analysis_results["topics"] = [{"name": topic, "confidence": 70} for topic in analysis_results["topics"]]
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error in analyze_transcript_with_prompt: {str(e)}")
            return {
                "summary": f"Error analyzing transcript: {str(e)}",
                "key_points": ["Error during analysis"],
                "topics": [{"name": "Error", "description": str(e), "confidence": 0}],
                "sentiment": "neutral",
                "sentiment_score": 0,
                "sentiment_analysis": "Analysis failed due to an error"
            }
    def generate_summary(self, transcript: str, max_length: int = 200) -> str:
        """Generate a concise summary of the video transcript."""
        system_prompt = "You are an expert at summarizing video content. Create clear, informative summaries that capture the essence of the video."
        
        user_prompt = f"""
        Please summarize this video transcript in about {max_length} words:
        
        {transcript[:8000]}
        
        Provide ONLY the summary with no additional text.
        """
        
        try:
            return self._call_claude_api(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=400
            ).strip()
        except Exception as e:
            print(f"Error generating summary: {str(e)}")
            return "Summary generation failed."
    
    def extract_key_points(self, transcript: str, max_points: int = 5) -> List[str]:
        """Extract the most important key points from the transcript."""
        system_prompt = "You are an expert at identifying the most important information in video content."
        
        user_prompt = f"""
        Extract exactly {max_points} key points or takeaways from this video transcript:
        
        {transcript[:8000]}
        
        Format your response as a simple list with each point on a new line, preceded by a dash.
        Example:
        - First key point
        - Second key point
        
        Provide ONLY the list with no additional text.
        """
        
        try:
            response = self._call_claude_api(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=500
            )
            
            # Parse the list response
            points = []
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('*'):
                    points.append(line[1:].strip())
                    if len(points) >= max_points:
                        break
            
            # If we couldn't parse properly, just split by newlines
            if not points:
                points = [line.strip() for line in response.split('\n') if line.strip()][:max_points]
            
            return points
        except Exception as e:
            print(f"Error extracting key points: {str(e)}")
            return ["Error extracting key points"]
    
    def analyze_sentiment(self, transcript: str) -> Dict[str, Any]:
        """Analyze the sentiment and tone of the video content."""
        system_prompt = "You are an expert at analyzing sentiment and emotional tone in communication."
        
        user_prompt = f"""
        Analyze the overall sentiment and emotional tone of this video transcript.
        
        {transcript[:8000]}
        
        Provide your analysis in JSON format with the following structure:
        {{
            "score": 0.5, // Use a value from -1 (very negative) to 1 (very positive)
            "label": "positive", // Choose one: "very negative", "negative", "neutral", "positive", or "very positive"
            "analysis": "Brief explanation of your sentiment assessment"
        }}
        
        Respond ONLY with the JSON.
        """
        
        try:
            response = self._call_claude_api(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=300
            )
            
            # Try to parse the JSON response
            try:
                # First try parsing the entire response as JSON
                sentiment_data = json.loads(response)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from the response
                try:
                    if "```json" in response:
                        json_text = response.split("```json")[1].split("```")[0].strip()
                    elif "```" in response:
                        json_text = response.split("```")[1].strip()
                    else:
                        json_text = response[response.find("{"):response.rfind("}")+1]
                    
                    sentiment_data = json.loads(json_text)
                except (json.JSONDecodeError, IndexError):
                    # Default response if parsing fails
                    return {
                        "score": 0,
                        "label": "neutral",
                        "analysis": "Failed to parse sentiment analysis response"
                    }
            
            return sentiment_data
            
        except Exception as e:
            print(f"Error analyzing sentiment: {str(e)}")
            return {"score": 0, "label": "neutral", "analysis": "Error analyzing sentiment"}
    
    def identify_topics(self, transcript: str, max_topics: int = 5) -> List[Dict[str, Any]]:
        """Identify the main topics discussed in the video."""
        system_prompt = "You are an expert at identifying and categorizing the topics discussed in video content."
        
        user_prompt = f"""
        Identify the top {max_topics} topics discussed in this video transcript.
        
        {transcript[:8000]}
        
        Respond in JSON format with the following structure:
        [
            {{
                "name": "Short topic name",
                "description": "Brief description of the topic",
                "confidence": 85 // Confidence score from 0-100
            }},
            // More topics...
        ]
        
        Respond ONLY with the JSON array.
        """
        
        try:
            response = self._call_claude_api(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=800
            )
            
            # Try to parse the JSON response
            try:
                # First try parsing the entire response as JSON
                topics = json.loads(response)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from the response
                try:
                    if "```json" in response:
                        json_text = response.split("```json")[1].split("```")[0].strip()
                    elif "```" in response:
                        json_text = response.split("```")[1].strip()
                    else:
                        json_text = response[response.find("["):response.rfind("]")+1]
                    
                    topics = json.loads(json_text)
                except (json.JSONDecodeError, IndexError):
                    # Default response if parsing fails
                    return [{"name": "Error", "description": "Failed to parse topics response", "confidence": 0}]
            
            # Ensure we return a list
            if isinstance(topics, dict):
                topics = [topics]
            
            return topics[:max_topics]
            
        except Exception as e:
            print(f"Error identifying topics: {str(e)}")
            return [{"name": "Error", "description": "Failed to identify topics", "confidence": 0}]
        

    # Fix the _extract_json method in claude_service.py
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract and parse JSON from text response."""
        try:
            # First try to parse entire response as JSON
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON object or array using regex
            json_pattern = r'({[\s\S]*?}|[[\s\S]*?])'
            json_matches = re.findall(json_pattern, text)
            
            for json_str in json_matches:
                try:
                    # Try to parse each match
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
            
            # If no valid JSON found, try to manually extract key fields
            logger.warning("JSON parsing failed, attempting manual field extraction")
            result = {}
            
            # Extract summary
            try:
                summary_match = re.search(r'"summary"\s*:\s*"([^"]+)"', text)
                if summary_match:
                    result["summary"] = summary_match.group(1)
                else:
                    result["summary"] = "Could not extract summary from response"
            except Exception as e:
                logger.error(f"Error extracting summary: {str(e)}")
                result["summary"] = "Error extracting summary"
            
            # Extract key points
            try:
                key_points = []
                key_points_section = re.search(r'"key_points"\s*:\s*\[(.*?)\]', text, re.DOTALL)
                if key_points_section:
                    key_points_text = key_points_section.group(1)
                    key_points_matches = re.findall(r'"([^"]+)"', key_points_text)
                    if key_points_matches:
                        key_points = key_points_matches
                result["key_points"] = key_points or ["Could not extract key points"]
            except Exception as e:
                logger.error(f"Error extracting key points: {str(e)}")
                result["key_points"] = ["Error extracting key points"]
            
            # Extract topics
            try:
                topics = []
                topics_section = re.search(r'"topics"\s*:\s*\[(.*?)\]', text, re.DOTALL)
                if topics_section:
                    topics_text = topics_section.group(1)
                    topics_matches = re.findall(r'"([^"]+)"', topics_text)
                    if topics_matches:
                        topics = [{"name": topic, "confidence": 70} for topic in topics_matches]
                result["topics"] = topics or [{"name": "General Content", "description": "Extracted from unstructured response", "confidence": 50}]
            except Exception as e:
                logger.error(f"Error extracting topics: {str(e)}")
                result["topics"] = [{"name": "General Content", "description": "Error in extraction", "confidence": 50}]
            
            # Extract sentiment
            try:
                sentiment_match = re.search(r'"sentiment"\s*:\s*"([^"]+)"', text)
                if sentiment_match:
                    result["sentiment"] = sentiment_match.group(1)
                else:
                    result["sentiment"] = "neutral"
            except Exception as e:
                logger.error(f"Error extracting sentiment: {str(e)}")
                result["sentiment"] = "neutral"
            
            result["sentiment_score"] = 0.5
            result["sentiment_analysis"] = "Analysis constructed from raw response"
            
            # Log the raw response for debugging
            logger.warning(f"Used manual extraction fallback for Claude response")
            logger.debug(f"Raw response: {text[:500]}...")
            
            return result




    def analyze_transcript_with_prompt(self, transcript: str, video_metadata: Dict[str, Any], custom_prompt: str) -> Dict[str, Any]:
        """
        Analyze video transcript using Claude API with a custom prompt.
        """
        # Prepare the system prompt
        system_prompt = "You are an expert video content analyzer. Provide clear, concise, and structured analysis of video transcripts."
        
        # Combine the custom prompt with transcript
        user_prompt = f"""
        {custom_prompt}
        
        TRANSCRIPT:
        {transcript[:8000]}
        
        Respond ONLY with the JSON. No introduction or explanation.
        """
        
        try:
            # Call Claude API
            response_text = self._call_claude_api(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=2000
            )
            
            # Extract the JSON from the response
            analysis_results = self._extract_json(response_text)
            
            # Ensure required fields exist with defaults if missing
            required_fields = ["summary", "key_points", "topics", "sentiment", "sentiment_score"]
            for field in required_fields:
                if field not in analysis_results:
                    if field == "summary":
                        analysis_results[field] = "Summary unavailable"
                    elif field == "key_points":
                        analysis_results[field] = ["No key points identified"]
                    elif field == "topics":
                        analysis_results[field] = [{"name": "General", "description": "General content", "confidence": 50}]
                    elif field == "sentiment":
                        analysis_results[field] = "neutral"
                    elif field == "sentiment_score":
                        analysis_results[field] = 0.5
            
            # Process key_points if it's a string
            if isinstance(analysis_results.get("key_points"), str):
                analysis_results["key_points"] = [analysis_results["key_points"]]
            
            # Process topics if it's not in expected format
            if "topics" in analysis_results:
                if isinstance(analysis_results["topics"], str):
                    analysis_results["topics"] = [{"name": analysis_results["topics"], "confidence": 70}]
                elif isinstance(analysis_results["topics"], list) and analysis_results["topics"] and isinstance(analysis_results["topics"][0], str):
                    analysis_results["topics"] = [{"name": topic, "confidence": 70} for topic in analysis_results["topics"]]
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error in analyze_transcript_with_prompt: {str(e)}")
            return {
                "summary": f"Error analyzing transcript: {str(e)}",
                "key_points": ["Error during analysis"],
                "topics": [{"name": "Error", "description": str(e), "confidence": 0}],
                "sentiment": "neutral",
                "sentiment_score": 0,
                "sentiment_analysis": "Analysis failed due to an error"
            }