# tests/test_claude_analysis.py
import sys
import os

# Add the parent directory to the Python path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from services.claude_service import ClaudeService
import json

# Load environment variables
load_dotenv()

def test_claude_analysis():
    """Test analyzing a sample text with Claude."""
    # Initialize the Claude service
    service = ClaudeService()
    
    # Sample transcript (a short paragraph for testing)
    sample_transcript = """
    Hello everyone, welcome to this tutorial on Python programming. 
    Today we're going to learn about the basics of Python, including variables, 
    data types, and simple operations. Python is one of the most popular 
    programming languages because it's easy to learn and has many applications 
    in data science, web development, and more.
    """
    
    # Sample metadata
    sample_metadata = {
        "title": "Python Tutorial for Beginners",
        "description": "Learn the basics of Python programming",
        "channel_title": "Coding Tutorials"
    }
    
    print("Attempting to analyze sample transcript with Claude API...")
    
    try:
        # Test analyze_transcript method
        results = service.analyze_transcript(sample_transcript, sample_metadata)
        
        print(f"SUCCESS! Claude analysis returned results.")
        print("\nAnalysis results:")
        print(json.dumps(results, indent=2))
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    print("Testing Claude Analysis API...")
    test_claude_analysis()