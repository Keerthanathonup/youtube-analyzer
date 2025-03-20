# services/category_detection.py

import logging
from typing import Dict, List, Any, Tuple, Optional
import re
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class CategoryDetectionService:
    """Service for detecting YouTube video categories and providing appropriate analysis prompts."""
    
    def __init__(self, claude_service=None):
        """Initialize the category detection service."""
        self.claude_service = claude_service
        self.categories = [
            "Educational/Tutorial",
            "Entertainment/Vlog",
            "Cooking/Recipe",
            "Product Review/Unboxing",
            "Travel/Destination",
            "Gaming",
            "News/Commentary",
            "Health & Fitness",
            "Business/Finance",
            "DIY/Crafts/Home Improvement"
        ]
        
        # Load category prompts
        self.category_prompts = self._load_category_prompts()
        
    def _load_category_prompts(self) -> Dict[str, str]:
        """Load category-specific prompts from configuration file."""
        try:
            # Try to load from JSON file
            prompts_file = Path(__file__).parent.parent / "config" / "category_prompts.json"
            
            if prompts_file.exists():
                with open(prompts_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                # If file doesn't exist, use default prompts
                return self._get_default_prompts()
        except Exception as e:
            logger.error(f"Error loading category prompts: {str(e)}")
            return self._get_default_prompts()
    
    def _get_default_prompts(self) -> Dict[str, str]:
        """Return default category prompts if config file is not available."""
        return {
            "Educational/Tutorial": self._get_educational_prompt(),
            "Entertainment/Vlog": self._get_entertainment_prompt(),
            "Cooking/Recipe": self._get_cooking_prompt(),
            "Product Review/Unboxing": self._get_review_prompt(),
            "Travel/Destination": self._get_travel_prompt(),
            "Gaming": self._get_gaming_prompt(),
            "News/Commentary": self._get_news_prompt(),
            "Health & Fitness": self._get_fitness_prompt(),
            "Business/Finance": self._get_business_prompt(),
            "DIY/Crafts/Home Improvement": self._get_diy_prompt(),
            # Fallback prompt for unknown categories
            "default": self._get_default_analysis_prompt()
        }
    
    def detect_category(self, transcript: str, title: str, description: str, channel_title: str = None) -> Tuple[str, float, List[Tuple[str, float]]]:
        """
        Detect the primary and secondary categories of a video.
        
        Args:
            transcript: Video transcript text
            title: Video title
            description: Video description
            channel_title: Channel name (optional)
            
        Returns:
            Tuple containing (primary_category, confidence, [(secondary_category, confidence), ...])
        """
        # If Claude service is not available, try rule-based detection
        if not self.claude_service:
            category, confidence = self._rule_based_category_detection(title, description, transcript)
            return category, confidence, []
        
        # Prepare transcript excerpt (first 1500 chars)
        transcript_excerpt = transcript[:1500] + "..." if len(transcript) > 1500 else transcript
        
        # Format the prompt for category detection
        system_prompt = "You are an expert at categorizing YouTube video content based on transcripts, titles, and descriptions."
        
        user_prompt = f"""
        Based on the following YouTube video information, classify this video into its most appropriate category.
        
        Title: {title}
        
        Channel: {channel_title or 'Unknown'}
        
        Description: {description[:500]}
        
        Transcript excerpt:
        {transcript_excerpt}
        
        Available categories:
        {', '.join(self.categories)}
        
        Return your analysis in this JSON format:
        {{
            "primary_category": "Category name from the list",
            "primary_confidence": 0.XX, // confidence between 0 and 1
            "secondary_categories": [
                ["Category name", 0.XX], // confidence between 0 and 1
                ["Category name", 0.XX]  // include up to 2 secondary categories if relevant
            ],
            "reasoning": "Brief explanation of your classification decision"
        }}
        
        Only include secondary categories if they're notably present in the content with confidence > 0.3.
        """
        
        try:
            # Get response from Claude
            response = self.claude_service._call_claude_api(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=500
            )
            
            # Parse the JSON response
            result = self._extract_json(response)
            
            primary_category = result.get("primary_category", self.categories[0])
            primary_confidence = result.get("primary_confidence", 0.5)
            secondary_categories = result.get("secondary_categories", [])
            
            # Log the detection result
            logger.info(f"Detected category for video: {primary_category} (confidence: {primary_confidence:.2f})")
            if secondary_categories:
                logger.info(f"Secondary categories: {secondary_categories}")
            
            return primary_category, primary_confidence, secondary_categories
            
        except Exception as e:
            logger.error(f"Error detecting video category: {str(e)}")
            # Fallback to rule-based detection
            category, confidence = self._rule_based_category_detection(title, description, transcript)
            return category, confidence, []
    
    def _rule_based_category_detection(self, title: str, description: str, transcript: str) -> Tuple[str, float]:
        """
        Use rule-based heuristics to detect video category when AI detection is unavailable.
        
        Args:
            title: Video title
            description: Video description
            transcript: Video transcript
            
        Returns:
            Tuple of (category, confidence)
        """
        # Combine all text for analysis
        title_lower = title.lower()
        desc_lower = description.lower()
        transcript_sample = transcript[:500].lower() if transcript else ""
        combined = f"{title_lower} {desc_lower} {transcript_sample}"
        
        # Category patterns (keywords and phrases)
        patterns = {
            "Educational/Tutorial": [
                r"how to", r"learn", r"tutorial", r"guide", r"course", r"class", 
                r"lesson", r"explain", r"explained", r"teaching", r"education"
            ],
            "Entertainment/Vlog": [
                r"vlog", r"day in my life", r"my day", r"follow me", r"lifestyle", 
                r"funny", r"comedy", r"prank", r"challenge", r"reaction"
            ],
            "Cooking/Recipe": [
                r"recipe", r"cook", r"cooking", r"bake", r"baking", r"food", r"meal",
                r"ingredient", r"kitchen", r"dish", r"delicious", r"tasty"
            ],
            "Product Review/Unboxing": [
                r"review", r"unboxing", r"worth it", r"should you buy", r"hands on", 
                r"first look", r"testing", r"comparison", r"versus", r"pros and cons"
            ],
            "Travel/Destination": [
                r"travel", r"tour", r"visiting", r"destination", r"vacation", r"trip",
                r"hotel", r"resort", r"things to do in", r"guide to", r"explore"
            ],
            "Gaming": [
                r"gameplay", r"gaming", r"playthrough", r"walkthrough", r"let's play",
                r"game", r"mission", r"strategy", r"stream", r"level"
            ],
            "News/Commentary": [
                r"news", r"politics", r"latest", r"update", r"report", r"analysis",
                r"opinion", r"current events", r"breaking", r"headline"
            ],
            "Health & Fitness": [
                r"workout", r"exercise", r"fitness", r"diet", r"nutrition", r"health",
                r"weight loss", r"training", r"cardio", r"strength", r"yoga"
            ],
            "Business/Finance": [
                r"invest", r"finance", r"money", r"business", r"entrepreneur", 
                r"stock market", r"passive income", r"crypto", r"trading", r"startup"
            ],
            "DIY/Crafts/Home Improvement": [
                r"diy", r"craft", r"make", r"build", r"project", r"handmade", 
                r"renovation", r"fix", r"repair", r"home improvement", r"decor"
            ]
        }
        
        # Count matches for each category
        category_scores = {}
        for category, keywords in patterns.items():
            score = 0
            for keyword in keywords:
                matches = len(re.findall(r'\b' + keyword + r'\b', combined))
                score += matches
            
            # Normalize score (0-1)
            matches_needed_for_max_confidence = 5  # Adjust as needed
            confidence = min(score / matches_needed_for_max_confidence, 1.0)
            category_scores[category] = confidence
        
        # Get category with highest score
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])
            if best_category[1] > 0.1:  # Minimum confidence threshold
                return best_category
        
        # Default to Educational if no clear matches
        return "Educational/Tutorial", 0.5
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract and parse JSON from text response."""
        try:
            # First try to parse entire response as JSON
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON object or array
            json_pattern = r'({[\s\S]*?}|[[\s\S]*?])'
            json_matches = re.findall(json_pattern, text)
            
            for json_str in json_matches:
                try:
                    # Try to parse each match
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
            
            # If no valid JSON found, create default response
            logger.warning("Could not parse JSON from Claude response, using default")
            return {
                "primary_category": "Educational/Tutorial",
                "primary_confidence": 0.5,
                "secondary_categories": []
            }
    
    def get_analysis_prompt(self, category: str, title: str, description: str, video_id: str) -> str:
        """
        Get the appropriate analysis prompt for the detected category.
        
        Args:
            category: Detected video category
            title: Video title
            description: Video description
            video_id: YouTube video ID
            
        Returns:
            Complete analysis prompt for Claude
        """
        # Get category-specific prompt template
        prompt_template = self.category_prompts.get(category)
        
        # If category not in prompts, use default
        if not prompt_template:
            prompt_template = self.category_prompts.get("default", self._get_default_analysis_prompt())
        
        # Construct the full prompt
        full_prompt = f"""
        Video Analysis Request for {category} content
        
        {prompt_template}
        
        Title: {title}
        URL: https://youtube.com/watch?v={video_id}
        Description: {description[:500]} {'...' if len(description) > 500 else ''}
        
        Please analyze the transcript of this video and provide the requested insights.
        """
        
        return full_prompt
        
    # Default prompt templates for each category
    def _get_educational_prompt(self) -> str:
        return """
        Analyze this educational video with special focus on:
        - Learning objectives and key concepts introduced
        - Step-by-step breakdown of any processes or methods taught
        - Prerequisites and assumed knowledge
        - Supporting examples and their effectiveness
        - Practical applications mentioned
        - Key terminology defined
        - Quality of explanations (clarity, depth, accuracy)
        - Suggested follow-up resources or next steps
        - Areas where additional explanation might be helpful
        - Questions this content answers and questions it raises

        Format the analysis with clear headings for each section, including "Key Concepts," "Step-by-Step Process," "Terminology," and "Practical Applications."
        
        Provide your analysis in JSON format including:
        - summary: A concise summary (100-150 words)
        - key_points: 5-7 key takeaways, including any step-by-step processes
        - topics: 3-5 main topics/concepts covered
        - sentiment: Overall tone (positive, negative, neutral)
        - sentiment_score: Number between -1 and 1
        - sentiment_analysis: Brief explanation of tone and effectiveness as educational content
        """
    
    def _get_entertainment_prompt(self) -> str:
        return """
        Analyze this entertainment/vlog content with special focus on:
        - Narrative structure and storytelling elements
        - Key moments and highlights with timestamps
        - Character/personality dynamics (if multiple people)
        - Production quality observations (editing, music, visual style)
        - Emotional tone throughout the video
        - Cultural references or trending topics mentioned
        - Audience engagement strategies used
        - Memorable quotes or moments
        - Recurring themes or motifs in the creator's content
        - Content uniqueness compared to similar creators

        Format the analysis in an engaging style with sections for "Story Arc," "Highlight Moments," "Creator Style," and "Audience Takeaways."
        
        Provide your analysis in JSON format including:
        - summary: A concise summary (100-150 words)
        - key_points: 5-7 key moments or highlights from the content
        - topics: 3-5 main themes or topics
        - sentiment: Overall tone (positive, negative, neutral)
        - sentiment_score: Number between -1 and 1
        - sentiment_analysis: Brief explanation of emotional tone and engagement factors
        """
        
    def _get_cooking_prompt(self) -> str:
        return """
        Analyze this cooking/recipe video with special focus on:
        - Complete ingredient list with measurements
        - Equipment and tools required
        - Preparation steps in chronological order
        - Cooking techniques demonstrated
        - Timing guidelines for each major step
        - Visual cues for determining doneness
        - Substitution options mentioned
        - Chef's tips and special insights
        - Serving suggestions and presentation ideas
        - Nutrition information (if provided)
        - Difficulty level assessment
        - Time-saving opportunities

        Format the analysis with clear sections for "Ingredients," "Preparation Method," "Chef's Tips," and "Final Presentation," making it easy to follow as a cooking guide.
        
        Provide your analysis in JSON format including:
        - summary: A concise summary of the recipe and result (100-150 words)
        - key_points: 5-7 key steps or techniques demonstrated
        - topics: 3-5 main culinary themes/skills/cuisines covered
        - sentiment: Overall tone (positive, negative, neutral)
        - sentiment_score: Number between -1 and 1
        - sentiment_analysis: Brief explanation of presentation style and recipe complexity
        """
        
    def _get_review_prompt(self) -> str:
        return """
        Analyze this product review/unboxing with special focus on:
        - Product specifications and features
        - Unboxing experience and initial impressions
        - Testing methodology and real-world usage scenarios
        - Performance benchmarks and comparisons
        - Pros and cons clearly articulated
        - Value assessment (price-to-performance ratio)
        - Comparisons to alternatives or previous models
        - Unique selling points highlighted
        - Target user identification
        - Potential deal-breakers mentioned
        - Final recommendation and rating context

        Format the analysis with sections for "Product Specifications," "Testing Results," "Pros/Cons," and "Final Verdict," with particular attention to the reviewer's justification for their conclusions.
        
        Provide your analysis in JSON format including:
        - summary: A concise summary of the review findings (100-150 words)
        - key_points: 5-7 main points about the product and review findings
        - topics: 3-5 main aspects/features assessed in the review
        - sentiment: Overall assessment (positive, negative, neutral)
        - sentiment_score: Number between -1 and 1
        - sentiment_analysis: Brief explanation of the reviewer's assessment and recommendation
        """
        
    def _get_travel_prompt(self) -> str:
        return """
        Analyze this travel content with special focus on:
        - Detailed location information (regions, cities, specific sites)
        - Practical travel logistics covered (transportation, accommodations, costs)
        - Cultural insights and local customs mentioned
        - Seasonal considerations and optimal visiting times
        - Food and dining recommendations
        - Must-see attractions with context
        - Off-the-beaten-path suggestions
        - Safety tips and potential concerns
        - Budget considerations across categories
        - Itinerary structure and time management suggestions
        - Visual highlights of the destination

        Format the analysis as a practical travel guide with sections for "Destination Overview," "Practical Information," "Attractions," "Food & Culture," and "Travel Tips."
        
        Provide your analysis in JSON format including:
        - summary: A concise summary of the travel destination and experience (100-150 words)
        - key_points: 5-7 key locations, attractions or travel tips mentioned
        - topics: 3-5 main aspects of the destination covered
        - sentiment: Overall portrayal (positive, negative, neutral)
        - sentiment_score: Number between -1 and 1
        - sentiment_analysis: Brief explanation of how the destination is presented and author's travel experience
        """
        
    def _get_gaming_prompt(self) -> str:
        return """
        Analyze this gaming content with special focus on:
        - Game title, platform, and version/update covered
        - Gameplay elements demonstrated (mechanics, features, modes)
        - Player skill level and techniques showcased
        - Game progression and achievement context
        - Strategic insights or tactics presented
        - Commentary quality and informativeness
        - Notable game events and highlights with timestamps
        - Technical performance observations
        - Community interactions and references
        - Comparisons to other games or previous versions
        - Creator's personal style and approach to the game

        Format the analysis with gaming-appropriate sections like "Game Overview," "Gameplay Highlights," "Strategies & Tips," and "Creator's Approach," with timestamp references where relevant.
        
        Provide your analysis in JSON format including:
        - summary: A concise summary of the gameplay content (100-150 words)
        - key_points: 5-7 key gameplay moments, strategies or features shown
        - topics: 3-5 main gaming aspects covered (mechanics, story, multiplayer, etc.)
        - sentiment: Overall assessment (positive, negative, neutral)
        - sentiment_score: Number between -1 and 1
        - sentiment_analysis: Brief explanation of the creator's enjoyment and critique of the game
        """
        
    def _get_news_prompt(self) -> str:
        return """
        Analyze this news/commentary content with special focus on:
        - Main topics and events covered
        - Factual information presented (differentiated from opinion)
        - Multiple perspectives presented (if any)
        - Sources cited and their credibility
        - Historical or contextual background provided
        - Key arguments and supporting evidence
        - Potential biases or framing techniques
        - Calls to action or policy recommendations
        - Expert opinions or interviews included
        - Conflicting information or counterarguments addressed
        - Implications and potential developments mentioned

        Format the analysis with clear separation between factual reporting and commentary/opinion, using sections like "Key Facts," "Context," "Analysis," and "Different Perspectives."
        
        Provide your analysis in JSON format including:
        - summary: A concise summary of the news/commentary content (100-150 words)
        - key_points: 5-7 key facts or arguments presented
        - topics: 3-5 main topics or issues discussed
        - sentiment: Overall tone (positive, negative, neutral)
        - sentiment_score: Number between -1 and 1
        - sentiment_analysis: Brief explanation of the perspective and framing of the content
        """
        
    def _get_fitness_prompt(self) -> str:
        return """
        Analyze this health/fitness content with special focus on:
        - Exercise techniques and proper form instructions
        - Workout structure and progression
        - Safety considerations and modification options
        - Target muscle groups or health benefits
        - Equipment requirements and alternatives
        - Scientific or research-based claims and their validity
        - Realistic expectations and timeframes mentioned
        - Nutrition advice and its context
        - Recovery and sustainability considerations
        - Qualifications of the presenter (if mentioned)
        - Appropriate disclaimers and limitations

        Format the analysis with sections for "Workout Overview," "Technique Breakdown," "Scientific Basis," and "Practical Implementation," with attention to both effectiveness and safety considerations.
        
        Provide your analysis in JSON format including:
        - summary: A concise summary of the fitness content (100-150 words)
        - key_points: 5-7 key exercises, techniques or health recommendations
        - topics: 3-5 main fitness/health aspects covered
        - sentiment: Overall tone (positive, negative, neutral)
        - sentiment_score: Number between -1 and 1
        - sentiment_analysis: Brief explanation of the approach to fitness and motivational style
        """
        
    def _get_business_prompt(self) -> str:
        return """
        Analyze this business/finance content with special focus on:
        - Core financial concepts explained
        - Investment strategies or business methods discussed
        - Market trends and data referenced
        - Risk factors and considerations mentioned
        - Historical context and relevant benchmarks
        - Expert credentials and experience
        - Actionable advice versus general principles
        - Time-sensitivity of the information
        - Supporting evidence for claims made
        - Potential conflicts of interest disclosed
        - Legal or regulatory considerations
        - Target audience level (beginner vs. advanced)

        Format the analysis with clear sections for "Key Concepts," "Strategic Insights," "Risk Considerations," and "Actionable Takeaways," with appropriate disclaimers about financial advice.
        
        Provide your analysis in JSON format including:
        - summary: A concise summary of the business/finance content (100-150 words)
        - key_points: 5-7 key financial concepts or strategies discussed
        - topics: 3-5 main business/finance topics covered
        - sentiment: Overall assessment (positive, negative, neutral, balanced)
        - sentiment_score: Number between -1 and 1
        - sentiment_analysis: Brief explanation of the approach to risk and potential returns
        """
        
    def _get_diy_prompt(self) -> str:
        return """
        Analyze this DIY/craft/home improvement content with special focus on:
        - Complete materials list with specifications
        - Tools required and possible alternatives
        - Step-by-step process with clear sequencing
        - Skill level required and learning curve
        - Time investment estimates for each stage
        - Safety precautions and common mistakes to avoid
        - Cost estimates (if provided)
        - Design principles and creative decisions explained
        - Customization opportunities
        - Troubleshooting tips for common issues
        - Before/after comparisons and results assessment
        - Maintenance or care instructions

        Format the analysis as a practical guide with sections for "Materials & Tools," "Project Steps," "Expert Tips," and "Finishing & Results," making it usable as a reference for someone attempting the project.
        
        Provide your analysis in JSON format including:
        - summary: A concise summary of the DIY project (100-150 words)
        - key_points: 5-7 key steps or techniques demonstrated
        - topics: 3-5 main DIY skills or concepts covered
        - sentiment: Overall tone (positive, negative, neutral)
        - sentiment_score: Number between -1 and 1
        - sentiment_analysis: Brief explanation of project complexity and creator's presentation style
        """
        
    def _get_default_analysis_prompt(self) -> str:
        return """
        Provide a comprehensive analysis of this video content including:
        - A concise but detailed summary of the main content
        - Key points and important takeaways
        - Main topics discussed or covered
        - Overall tone and sentiment
        - Unique insights or valuable information presented
        - Structure and flow of the content
        - Intended audience and purpose of the video
        
        Provide your analysis in JSON format including:
        - summary: A concise summary (100-150 words)
        - key_points: 5-7 key takeaways from the content
        - topics: 3-5 main topics covered
        - sentiment: Overall tone (positive, negative, neutral)
        - sentiment_score: Number between -1 and 1
        - sentiment_analysis: Brief explanation of tone and presentation style
        """