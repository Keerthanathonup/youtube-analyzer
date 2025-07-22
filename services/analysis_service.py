from services.claude_service import ClaudeService
from services.transcription_service import TranscriptionService
from services.category_detection import CategoryDetectionService
import logging
import config
import re
import json
import time
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class AnalysisService:
    """Service for analyzing video content and generating insights."""
    
    def __init__(self, api_key: str = None):
        """Initialize the analysis service."""
        self.claude_service = ClaudeService(api_key=api_key or config.ANTHROPIC_API_KEY)
        self.transcription_service = TranscriptionService()
        # Initialize the category detection service
        self.category_detection = CategoryDetectionService(claude_service=self.claude_service)
        self.use_mock = config.ANTHROPIC_API_KEY is None or config.ANTHROPIC_API_KEY == ""
        
        # Add caching for better performance
        self.analysis_cache = {}
    
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
        start_time = time.time()
        
        # Check cache first
        cache_key = f"{video_id}_{hash(transcript) if transcript else 'no_transcript'}"
        if cache_key in self.analysis_cache:
            logger.info(f"Returning cached analysis for {video_id}")
            return self.analysis_cache[cache_key]
        
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
            # Detect video category before analysis
            logger.info("Detecting video category before analysis")
            title = video_metadata.get('title', '') if video_metadata else ''
            description = video_metadata.get('description', '') if video_metadata else ''
            channel = video_metadata.get('channel_title', '') if video_metadata else ''
            
            # Get the category, confidence, and any secondary categories
            category, confidence, secondary_categories = self.category_detection.detect_category(
                transcript=transcript, 
                title=title, 
                description=description, 
                channel_title=channel
            )
            
            logger.info(f"Detected category: {category} (confidence: {confidence:.2f})")
            if secondary_categories:
                secondary_cats = ", ".join([f"{cat} ({conf:.2f})" for cat, conf in secondary_categories])
                logger.info(f"Secondary categories: {secondary_cats}")
            
            # Use enhanced analysis with better prompting
            analysis_results = self._perform_enhanced_analysis(
                transcript, video_metadata, category, video_id
            )
            
            # Post-process and validate results
            final_results = self._post_process_analysis(analysis_results, video_id, category)
            
            # Cache the results
            self.analysis_cache[cache_key] = final_results
            
            processing_time = time.time() - start_time
            logger.info(f"Analysis completed in {processing_time:.2f} seconds for {video_id}")
            
            return final_results
            
        except Exception as e:
            logger.error(f"Error during analysis: {str(e)}", exc_info=True)
            return self._generate_error_analysis(video_id, f"Error during analysis: {str(e)}")
    
    def _perform_enhanced_analysis(self, transcript: str, video_metadata: Dict[str, Any], 
                                 category: str, video_id: str) -> Dict[str, Any]:
        """Perform enhanced analysis with better prompting strategies."""
        
        title = video_metadata.get('title', '') if video_metadata else ''
        description = video_metadata.get('description', '') if video_metadata else ''
        
        # Create enhanced prompt based on content type
        enhanced_prompt = self._create_enhanced_prompt(category, title, description)
        
        # Prepare transcript with better chunking if needed
        processed_transcript = self._prepare_transcript_for_analysis(transcript)
        
        # Use enhanced Claude prompting
        system_prompt = """You are an expert content analyst specializing in extracting structured, actionable insights from video transcripts. Your analysis should be:

1. COMPREHENSIVE: Cover all major points thoroughly
2. ORGANIZED: Present information in clear, logical sections  
3. ACTIONABLE: Focus on practical takeaways
4. DETAILED: Provide specific examples and explanations
5. STRUCTURED: Use consistent formatting and categorization

Always respond with valid JSON in the exact format specified."""

        user_prompt = f"""
        {enhanced_prompt}
        
        VIDEO DETAILS:
        Title: {title}
        Description: {description[:500]}
        
        TRANSCRIPT:
        {processed_transcript}
        
        RESPOND WITH EXACTLY THIS JSON STRUCTURE (no additional text):
        {{
            "summary": "Comprehensive 150-200 word summary covering all main points",
            "detailed_summary": "Detailed 300-400 word analysis with specific examples",
            "key_points": [
                {{
                    "point": "Specific, actionable takeaway",
                    "explanation": "Detailed explanation with context",
                    "timestamp": null,
                    "importance": "high|medium|low"
                }}
            ],
            "topics": [
                {{
                    "name": "Topic name",
                    "description": "What this topic covers",
                    "confidence": 85,
                    "subtopics": ["related", "concepts"]
                }}
            ],
            "sentiment": "positive|negative|neutral",
            "sentiment_score": 0.7,
            "sentiment_analysis": "Explanation of tone and presentation style",
            "actionable_insights": [
                "Specific action or recommendation based on content"
            ],
            "target_audience": "Who would benefit most from this content",
            "difficulty_level": "beginner|intermediate|advanced",
            "time_investment": "Estimated time to implement/learn concepts",
            "related_concepts": ["concept1", "concept2"]
        }}
        """
        
        # Call Claude with enhanced parameters
        response = self.claude_service._call_claude_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=3000,  # Increased for more detailed responses
            model="claude-3-haiku-20240307"  # Use consistent model
        )
        
        return self._parse_claude_response_enhanced(response)
    
    def _create_enhanced_prompt(self, category: str, title: str, description: str) -> str:
        """Create category-specific enhanced prompts for better analysis."""
        
        base_instructions = {
            "Educational/Tutorial": """
            For this EDUCATIONAL/TUTORIAL content, provide:
            
            KEY POINTS (8-12 points):
            - Step-by-step instructions with clear explanations
            - Prerequisites and requirements
            - Common mistakes to avoid
            - Pro tips and best practices
            - Troubleshooting guidance
            - Real-world applications
            
            TOPICS should include:
            - Main subject areas covered
            - Technical concepts explained  
            - Tools and technologies mentioned
            - Skills being taught
            
            ACTIONABLE INSIGHTS should focus on:
            - What the viewer can immediately implement
            - Follow-up learning recommendations
            - Practice exercises or projects
            """,
            
            "Cooking/Recipe": """
            For this COOKING/RECIPE content, provide:
            
            KEY POINTS (8-12 points):
            - Ingredient preparation techniques
            - Cooking methods and temperatures
            - Timing and sequencing
            - Texture and flavor notes
            - Serving suggestions
            - Storage and leftover tips
            
            TOPICS should include:
            - Cuisine type and dish category
            - Cooking techniques demonstrated
            - Dietary considerations
            - Equipment needed
            
            ACTIONABLE INSIGHTS should focus on:
            - Make-ahead tips
            - Ingredient substitutions
            - Scaling the recipe
            """,
            
            "Product Review/Unboxing": """
            For this PRODUCT REVIEW content, provide:
            
            KEY POINTS (8-12 points):
            - Product specifications and features
            - Performance in real-world scenarios
            - Pros and cons with specific examples
            - Value for money assessment
            - Comparison with alternatives
            - Purchase recommendations
            
            TOPICS should include:
            - Product category and type
            - Key features evaluated
            - Use cases and scenarios
            - Target user groups
            
            ACTIONABLE INSIGHTS should focus on:
            - Whether to buy or not and why
            - Best use cases for this product
            - Alternatives to consider
            """,
            
            "default": """
            For this content, provide:
            
            KEY POINTS (8-12 points):
            - Main arguments or information presented
            - Supporting evidence and examples
            - Conclusions and implications
            - Practical applications
            - Important details and context
            
            TOPICS should include:
            - Primary subject matter
            - Secondary themes
            - Concepts discussed
            - Relevant fields or industries
            
            ACTIONABLE INSIGHTS should focus on:
            - What the viewer can learn or apply
            - Follow-up actions or research
            - Key takeaways for implementation
            """
        }
        
        return base_instructions.get(category, base_instructions["default"])
    
    def _prepare_transcript_for_analysis(self, transcript: str) -> str:
        """Prepare transcript for analysis with better formatting."""
        
        # Clean up transcript
        cleaned = re.sub(r'\s+', ' ', transcript)  # Normalize whitespace
        cleaned = re.sub(r'[^\w\s\.,!?;:\-\(\)]', '', cleaned)  # Remove special chars
        
        # If transcript is very long, intelligently chunk it
        if len(cleaned) > 8000:
            # Take first and last portions, plus middle sample
            start_portion = cleaned[:3000]
            end_portion = cleaned[-2000:]
            
            # Find a good middle portion
            middle_start = len(cleaned) // 2 - 1500
            middle_end = len(cleaned) // 2 + 1500
            middle_portion = cleaned[middle_start:middle_end]
            
            cleaned = f"{start_portion}\n\n[... content continues ...]\n\n{middle_portion}\n\n[... content continues ...]\n\n{end_portion}"
        
        return cleaned
    
    def _parse_claude_response_enhanced(self, response_text: str) -> Dict[str, Any]:
        """Enhanced parsing with better error handling and validation."""
        
        if isinstance(response_text, dict):
            return self._validate_and_enhance_response(response_text)
        
        try:
            # Try to extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                parsed = json.loads(json_str)
                return self._validate_and_enhance_response(parsed)
        except Exception as e:
            logger.warning(f"JSON parsing failed: {e}")
        
        # Fallback: manually extract sections
        return self._manual_content_extraction(response_text)
    
    def _validate_and_enhance_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and enhance the parsed response."""
        
        # Ensure required fields exist
        required_fields = {
            "summary": "Comprehensive analysis not available",
            "detailed_summary": "",
            "key_points": [],
            "topics": [],
            "sentiment": "neutral",
            "sentiment_score": 0.5,
            "sentiment_analysis": "No sentiment analysis available",
            "actionable_insights": [],
            "target_audience": "General audience",
            "difficulty_level": "intermediate",
            "time_investment": "Variable",
            "related_concepts": []
        }
        
        for field, default in required_fields.items():
            if field not in response:
                response[field] = default
        
        # Validate and fix key_points structure
        if response["key_points"]:
            enhanced_points = []
            for point in response["key_points"]:
                if isinstance(point, str):
                    enhanced_points.append({
                        "point": point,
                        "explanation": "",
                        "timestamp": None,
                        "importance": "medium"
                    })
                elif isinstance(point, dict):
                    enhanced_points.append({
                        "point": point.get("point", point.get("text", str(point))),
                        "explanation": point.get("explanation", ""),
                        "timestamp": point.get("timestamp"),
                        "importance": point.get("importance", "medium")
                    })
            response["key_points"] = enhanced_points
        
        # Validate topics structure
        if response["topics"]:
            enhanced_topics = []
            for topic in response["topics"]:
                if isinstance(topic, str):
                    enhanced_topics.append({
                        "name": topic,
                        "description": "",
                        "confidence": 70,
                        "subtopics": []
                    })
                elif isinstance(topic, dict):
                    enhanced_topics.append({
                        "name": topic.get("name", str(topic)),
                        "description": topic.get("description", ""),
                        "confidence": topic.get("confidence", 70),
                        "subtopics": topic.get("subtopics", [])
                    })
            response["topics"] = enhanced_topics
        
        # Ensure detailed_summary exists
        if not response["detailed_summary"]:
            response["detailed_summary"] = response["summary"]
        
        # Ensure actionable_insights is a list
        if isinstance(response["actionable_insights"], str):
            response["actionable_insights"] = [response["actionable_insights"]]
        
        return response
    
    def _manual_content_extraction(self, text: str) -> Dict[str, Any]:
        """Manual extraction when JSON parsing fails."""
        
        result = {
            "summary": self._extract_section(text, "summary", "A summary of the video content."),
            "detailed_summary": "",
            "key_points": self._extract_key_points_manual(text),
            "topics": self._extract_topics_manual(text),
            "sentiment": "neutral",
            "sentiment_score": 0.5,
            "sentiment_analysis": "Unable to determine sentiment from response",
            "actionable_insights": self._extract_actionable_insights(text),
            "target_audience": "General audience",
            "difficulty_level": "intermediate",
            "time_investment": "Variable",
            "related_concepts": []
        }
        
        result["detailed_summary"] = result["summary"]
        return result
    
    def _extract_section(self, text: str, section_name: str, default: str) -> str:
        """Extract a specific section from text."""
        pattern = rf"{section_name}[:\s]*([^]+?)(?=\n\n|\n[A-Z]|$)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else default
    
    def _extract_key_points_manual(self, text: str) -> List[Dict[str, Any]]:
        """Manually extract key points from text."""
        points = []
        
        # Look for bullet points or numbered lists
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if (line.startswith('-') or line.startswith('*') or 
                line.startswith('•') or re.match(r'^\d+\.', line)):
                
                clean_point = re.sub(r'^[-*•\d\.]+\s*', '', line).strip()
                if clean_point and len(clean_point) > 10:
                    points.append({
                        "point": clean_point,
                        "explanation": "",
                        "timestamp": None,
                        "importance": "medium"
                    })
        
        # If no points found, create from sentences
        if not points:
            sentences = re.split(r'[.!?]+', text)
            for sentence in sentences[:8]:
                sentence = sentence.strip()
                if len(sentence) > 20:
                    points.append({
                        "point": sentence,
                        "explanation": "",
                        "timestamp": None,
                        "importance": "medium"
                    })
        
        return points[:10]  # Limit to 10 points
    
    def _extract_topics_manual(self, text: str) -> List[Dict[str, Any]]:
        """Manually extract topics from text."""
        # Simple topic extraction
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 
                       'to', 'for', 'of', 'with', 'by', 'this', 'that', 'is', 'are'}
        
        words = re.findall(r'\b[A-Z][a-z]+\b', text)  # Capitalized words
        word_freq = {}
        
        for word in words:
            if word.lower() not in common_words and len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top topics
        sorted_topics = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        topics = []
        for topic, freq in sorted_topics[:5]:
            topics.append({
                "name": topic,
                "description": f"Topic mentioned {freq} times",
                "confidence": min(freq * 20, 90),
                "subtopics": []
            })
        
        return topics
    
    def _extract_actionable_insights(self, text: str) -> List[str]:
        """Extract actionable insights from text."""
        insights = []
        
        # Look for action-oriented sentences
        action_patterns = [
            r'should\s+([^.]+)',
            r'can\s+([^.]+)',
            r'try\s+([^.]+)',
            r'use\s+([^.]+)',
            r'implement\s+([^.]+)',
            r'consider\s+([^.]+)'
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 10:
                    insights.append(f"Consider to {match.strip()}")
        
        return insights[:5]  # Limit to 5 insights
    
    def _post_process_analysis(self, analysis: Dict[str, Any], video_id: str, category: str) -> Dict[str, Any]:
        """Post-process analysis results for consistency and quality."""
        
        # Add metadata
        analysis["video_id"] = video_id
        analysis["content_category"] = {
            "primary": category,
            "analysis_version": "enhanced_v1.0"
        }
        analysis["analysis_quality"] = self._assess_analysis_quality(analysis)
        
        # Ensure minimum quality standards
        if len(analysis["key_points"]) < 5:
            logger.warning(f"Low key points count for {video_id}, analysis may be incomplete")
        
        if len(analysis["summary"]) < 100:
            logger.warning(f"Short summary for {video_id}, analysis may be incomplete")
        
        return analysis
    
    def _assess_analysis_quality(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality of the analysis."""
        
        quality_score = 0
        factors = []
        
        # Check summary quality
        if len(analysis.get("summary", "")) > 100:
            quality_score += 20
            factors.append("Good summary length")
        
        # Check key points
        key_points = analysis.get("key_points", [])
        if len(key_points) >= 5:
            quality_score += 20
            factors.append("Sufficient key points")
        
        # Check if key points have explanations
        explained_points = sum(1 for kp in key_points if kp.get("explanation"))
        if explained_points > len(key_points) * 0.5:
            quality_score += 15
            factors.append("Detailed key points")
        
        # Check topics
        topics = analysis.get("topics", [])
        if len(topics) >= 3:
            quality_score += 15
            factors.append("Good topic coverage")
        
        # Check actionable insights
        insights = analysis.get("actionable_insights", [])
        if len(insights) >= 2:
            quality_score += 15
            factors.append("Actionable insights provided")
        
        # Check detailed summary
        if analysis.get("detailed_summary") and len(analysis["detailed_summary"]) > 200:
            quality_score += 15
            factors.append("Comprehensive detailed summary")
        
        return {
            "score": quality_score,
            "factors": factors,
            "assessment": "high" if quality_score > 80 else "medium" if quality_score > 60 else "low"
        }
    
    def _generate_error_analysis(self, video_id: str, error_message: str) -> Dict[str, Any]:
        """Generate error response when analysis fails."""
        return {
            "video_id": video_id,
            "summary": f"Analysis failed: {error_message}",
            "detailed_summary": f"Unable to analyze video {video_id}. {error_message}",
            "key_points": [{"point": "Analysis not available", "explanation": error_message, "timestamp": None, "importance": "low"}],
            "topics": [{"name": "Error", "description": error_message, "confidence": 0, "subtopics": []}],
            "sentiment": "neutral",
            "sentiment_score": 0,
            "sentiment_analysis": "No analysis available due to error",
            "actionable_insights": ["Retry analysis or check video accessibility"],
            "target_audience": "Unknown",
            "difficulty_level": "unknown",
            "time_investment": "Unknown",
            "related_concepts": [],
            "content_category": {"primary": "error"},
            "analysis_quality": {"score": 0, "factors": [], "assessment": "failed"},
            "error": True
        }
    
    def _generate_mock_analysis(self, video_id: str, video_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock analysis for testing when no API key is available."""
        title = video_metadata.get('title', 'Unknown Video') if video_metadata else 'Unknown Video'
        
        return {
            "video_id": video_id,
            "summary": f"This is a mock analysis for '{title}'. The video covers important topics and provides valuable insights for viewers interested in the subject matter.",
            "detailed_summary": f"This comprehensive mock analysis of '{title}' demonstrates the structure and quality of insights that would be provided by the AI analysis system. The video content is processed to extract key information, identify main themes, and provide actionable takeaways for the audience.",
            "key_points": [
                {"point": "Main concept introduction and overview", "explanation": "The video begins with foundational concepts", "timestamp": None, "importance": "high"},
                {"point": "Detailed explanation of key processes", "explanation": "Core methodology is explained step by step", "timestamp": None, "importance": "high"},
                {"point": "Practical examples and demonstrations", "explanation": "Real-world applications are shown", "timestamp": None, "importance": "medium"},
                {"point": "Best practices and recommendations", "explanation": "Expert tips for optimal results", "timestamp": None, "importance": "medium"},
                {"point": "Common pitfalls and how to avoid them", "explanation": "Preventive measures are discussed", "timestamp": None, "importance": "medium"}
            ],
            "topics": [
                {"name": "Core Concepts", "description": "Fundamental principles covered in the content", "confidence": 85, "subtopics": ["basics", "principles"]},
                {"name": "Practical Applications", "description": "Real-world use cases and examples", "confidence": 80, "subtopics": ["examples", "case studies"]},
                {"name": "Best Practices", "description": "Recommended approaches and methodologies", "confidence": 75, "subtopics": ["recommendations", "optimization"]}
            ],
            "sentiment": "positive",
            "sentiment_score": 0.7,
            "sentiment_analysis": "The content has a positive and informative tone, designed to educate and help viewers",
            "actionable_insights": [
                "Follow the step-by-step process outlined in the video",
                "Implement the recommended best practices",
                "Avoid the common mistakes mentioned",
                "Practice with the provided examples"
            ],
            "target_audience": "Intermediate learners and professionals",
            "difficulty_level": "intermediate",
            "time_investment": "30-60 minutes to implement concepts",
            "related_concepts": ["related topic 1", "related topic 2", "advanced concepts"],
            "content_category": {"primary": "Educational/Tutorial", "analysis_version": "mock_v1.0"},
            "analysis_quality": {"score": 85, "factors": ["Structured content", "Clear examples"], "assessment": "high"},
            "mock": True
        }
    
    # Legacy methods for backward compatibility
    def _parse_claude_response(self, response_text: str) -> Dict[str, Any]:
        """Legacy method - redirects to enhanced version."""
        return self._parse_claude_response_enhanced(response_text)
    
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
        
        # Use the first 5000 characters for analysis
        short_transcript = transcript[:5000]
        
        title = video_metadata.get('title', '')
        description = video_metadata.get('description', '')
        channel = video_metadata.get('channel_title', '')
        
        # Detect category
        category, confidence, secondary_categories = self.category_detection.detect_category(
            transcript=short_transcript, 
            title=title, 
            description=description, 
            channel_title=channel
        )
        
        # Use enhanced analysis
        analysis_results = self._perform_enhanced_analysis(
            short_transcript, video_metadata, category, video_id
        )
        
        # Post-process
        final_results = self._post_process_analysis(analysis_results, video_id, category)
        
        return final_results
