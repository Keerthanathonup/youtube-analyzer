import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "dummy_key")  # Dummy key for now

# Anthropic Claude API configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307")  # Default to Sonnet
# Application settings
PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///youtube_analyzer.db")

# Create a settings dictionary for compatibility
settings = {
    "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "PORT": PORT,
    "DEBUG": DEBUG,
    "DATABASE_URL": DATABASE_URL,  # This is used in db.py
    # Add lowercase versions for backward compatibility
    "youtube_api_key": YOUTUBE_API_KEY,
    "openai_api_key": OPENAI_API_KEY,
    "port": PORT,
    "debug": DEBUG,
    "database_url": DATABASE_URL
}