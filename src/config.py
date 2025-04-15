"""
This module handles configuration settings for the application.
"""

import os
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai

def load_environment():
    """Load environment variables from .env file."""
    load_dotenv()

def configure_genai():
    """
    Configure the Gemini API with the API key from environment variables.
    
    Returns:
        bool: True if configuration was successful, False otherwise.
    """
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            st.error("GEMINI_API_KEY not found in environment variables")
            return False
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"Error configuring Gemini API: {str(e)}")
        return False

def get_gemini_model(model_name='gemini-2.0-flash'):
    """
    Get a Gemini model instance.
    
    Args:
        model_name (str): The name of the model to use.
        
    Returns:
        GenerativeModel: A Gemini model instance.
    """
    return genai.GenerativeModel(model_name)
