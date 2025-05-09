import streamlit as st
from config import load_environment, configure_genai
from views import SpecificationView

def main():
    load_environment()
    st.set_option('client.showErrorDetails', True)
    
    if not configure_genai():
        st.error("Failed to configure Gemini API. Please check your API key.")
        return
    
    view = SpecificationView()
    view.display_ui()

if __name__ == "__main__":
    main()
