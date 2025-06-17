import os
from dotenv import load_dotenv
import google.generativeai as genai

def load_environment():
    """Load environment variables from .env file."""
    load_dotenv()

def configure_genai():
    """Configure the Gemini API with the API key."""
    load_environment()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    genai.configure(api_key=api_key)
    return True

def get_gemini_model(model_name: str = "gemini-2.0-flash"):
    """Initialize and return a Gemini generative model."""
    configure_genai()
    return genai.GenerativeModel(model_name)
    
def get_api_key():
    """Get the Gemini API key from environment variables."""
    load_environment()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    return api_key