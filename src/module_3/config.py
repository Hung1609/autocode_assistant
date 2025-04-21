import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def load_environment():
    load_dotenv()

def configure_genai():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment variables.")
        return False
    try:
        genai.configure(api_key=api_key)
        logger.info("Gemini API configured successfully.")
        return True
    except Exception as e:
        logger.error(f"Error configuring Gemini API: {e}")
        return False

def get_gemini_model(model_name="gemini-1.5-flash"):
    load_environment()
    if not configure_genai():
        raise ValueError("Gemini API Key not configured. Cannot get model.")
    try:
        model = genai.GenerativeModel(model_name)
        logger.info(f"Gemini model '{model_name}' initialized.")
        return model
    except Exception as e:
        logger.error(f"Failed to initialize Gemini model '{model_name}': {e}")
        raise
