# Thiết lập config

import os
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai

def load_environment():
    load_dotenv()

def configure_genai():
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    return True
    # try:
    #     api_key = os.getenv("GEMINI_API_KEY")
    #     if not api_key:
    #         st.error("GEMINI_API_KEY not found in environment variables")
    #         return False
    #     genai.configure(api_key=api_key)
    #     return True
    # except Exception as e:
    #     st.error(f"Error configuring Gemini API: {str(e)}")
    #     return False

def get_gemini_model(model_name=None):
    return genai.GenerativeModel(model_name)
