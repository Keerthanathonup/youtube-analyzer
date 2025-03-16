# test_claude_api.py
import os
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv()

def test_claude_api():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found in environment variables")
        return
    
    print(f"Found API key: {api_key[:5]}...{api_key[-4:] if len(api_key) > 8 else ''}")
    
    try:
        # Initialize Claude client
        client = Anthropic(api_key=api_key)
        
        # Use a current model name - claude-3-haiku-20240307 is a good choice for testing
        # Alternatively, you can use "claude-3-opus-20240229" or "claude-3-sonnet-20240307"
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Hello Claude! Please respond with 'API key is working correctly!'"}
            ]
        )
        
        print("SUCCESS! Claude API is working.")
        print("Response:", response.content[0].text)
        
    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    print("Testing Claude API connection...")
    test_claude_api()