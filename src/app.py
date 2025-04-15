"""
This is the main entry point for the Streamlit application.
"""

import streamlit as st
from src.config import load_environment, configure_genai
from src.views import SpecificationView

def main():
    """
    Main function to run the Streamlit application.
    """
    load_environment()
    
    if not configure_genai():
        st.error("Failed to configure Gemini API. Please check your API key.")
        return
    
    view = SpecificationView()
    view.display_ui()

if __name__ == "__main__":
    main()
