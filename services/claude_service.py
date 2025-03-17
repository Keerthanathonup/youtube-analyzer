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
        retries = 0
        while retries < max_retries:
            try:
                payload = {
                    "model": model or self.default_model,
                    "max_tokens": max_tokens,
                    "system": system_prompt,
                    "messages": [
                        {"role": "user", "content": user_prompt}
                    ]
                }
                
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload
                )
                
                response.raise_for_status()  # Raise an exception for HTTP errors
                response_json = response.json()
                
                # Extract the content from Claude's response
                return response_json.get("content", [{"text": "No response from Claude"}])[0].get("text", "")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"API call failed (attempt {retries+1}/{max_retries}): {str(e)}")
                retries += 1
                time.sleep(2 * retries)  # Exponential backoff
        
        return "Error: Failed after multiple retries"
        
    def analyze_transcript(self, transcript: str, video_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze video transcript using Claude API.
        
        Args:
            transcript: The full transcript text of the video
            video_metadata: Dictionary containing video title, description, etc.
            
        Returns:
            Dictionary containing analysis results
        """
        # Prepare the prompt with video context
        system_prompt = "You are an expert video content analyzer. Provide clear, concise, and structured analysis of video transcripts."
        
        title = video_metadata.get('title', 'Unknown Title')
        description = video_metadata.get('description', 'No description available')
        
        user_prompt = f"""
        VIDEO ANALYSIS REQUEST
        
        Title: {title}
        Description: {description}
        
        Please analyze the following video transcript and provide:
        1. A concise summary (100-150 words)
        2. 5 key points or takeaways
        3. 3-5 main topics discussed
        4. Overall sentiment and tone analysis (positive, negative, or neutral)
        
        Format your response in JSON with the following structure:
        {{
            "summary": "Your summary here",
            "key_points": ["Point 1", "Point 2", ...],
            "topics": [
                {{"name": "Topic name", "description": "Brief description", "confidence": 85}},
                ...
            ],
            "sentiment": "positive/negative/neutral",
            "sentiment_score": 0.75, // -1 to 1 scale where -1 is very negative, 0 is neutral, 1 is very positive
            "sentiment_analysis": "Brief explanation of sentiment"
        }}
        
        TRANSCRIPT:
        {transcript[:8000]}  # Using more of the transcript than OpenAI since Claude has larger context
        
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
            # First, try to parse the entire response as JSON
            try:
                analysis_results = json.loads(response_text)
            except json.JSONDecodeError:
                # If that fails, try to extract the JSON portion using common markers
                try:
                    # Look for JSON between triple backticks
                    if "```json" in response_text:
                        json_text = response_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in response_text:
                        json_text = response_text.split("```")[1].split("```")[0].strip()
                    else:
                        # Try to find JSON by looking for opening and closing braces
                        start_idx = response_text.find("{")
                        end_idx = response_text.rfind("}") + 1
                        if start_idx >= 0 and end_idx > start_idx:
                            json_text = response_text[start_idx:end_idx]
                        else:
                            raise ValueError("Could not find JSON in response")
                    
                    # Remove any trailing commas which might be causing JSON parse errors
                    json_text = re.sub(r',\s*}', '}', json_text)
                    json_text = re.sub(r',\s*]', ']', json_text)
                    
                    analysis_results = json.loads(json_text)
                except (json.JSONDecodeError, IndexError, ValueError) as e:
                    # If all parsing attempts fail, try to manually extract useful content
                    try:
                        # Last ditch effort - manually extract the summary field
                        summary_match = re.search(r'"summary":\s*"([^"]+)"', response_text)
                        key_points_match = re.search(r'"key_points":\s*\[(.*?)\]', response_text, re.DOTALL)
                        
                        summary = summary_match.group(1) if summary_match else "Could not extract summary"
                        
                        key_points = []
                        if key_points_match:
                            points_text = key_points_match.group(1)
                            # Extract items in quotes
                            points = re.findall(r'"([^"]+)"', points_text)
                            key_points = points if points else ["Could not extract key points"]
                        
                        return {
                            "summary": summary,
                            "key_points": key_points,
                            "topics": [{"name": "Extracted Topic", "description": "Manually extracted from response", "confidence": 50}],
                            "sentiment": "neutral",
                            "sentiment_score": 0.5,
                            "sentiment_analysis": "Analysis constructed from raw response",
                            "raw_response": response_text
                        }
                    except Exception:
                        # If all parsing attempts fail, return a structured error
                        return {
                            "summary": "Error parsing Claude's response",
                            "key_points": ["Unable to parse analysis results"],
                            "topics": [{"name": "Error", "description": "Response parsing failed", "confidence": 0}],
                            "sentiment": "neutral",
                            "sentiment_score": 0,
                            "sentiment_analysis": "Analysis unavailable",
                            "raw_response": response_text  # Include the raw response for debugging
                        }
            
            return analysis_results
            
        except Exception as e:
            # Handle any errors
            print(f"Error in analyze_transcript: {str(e)}")
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