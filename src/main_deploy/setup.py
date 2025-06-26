import logging
import google.generativeai as genai
import config

logger = logging.getLogger(__name__)

# --- Global Flag for API to configure once per turn ---
_is_configured = False

def configure_gemini_api():
    global _is_configured
    if _is_configured:
        logger.debug("Gemini API is already configured. Skipping.")
        return True
    
    api_key = config.GEMINI_API_KEY

    if not api_key:
        logger.critical("GEMINI_API_KEY is not available in the configuration.")
        raise ValueError("GEMINI_API_KEY not found. Cannot configure the Gemini client.")

    try:
        genai.configure(api_key=api_key)
        _is_configured = True
        logger.info("Successfully configured the Google Generative AI client.")
    
    except Exception as e:
        logger.critical(f"Failed to configure the Google Generative AI client: {e}", exc_info=True)
        raise


# def load_environment():
#     load_dotenv()

# def configure_genai():
#     load_environment()
#     api_key = os.getenv("GEMINI_API_KEY")
#     if not api_key:
#         raise ValueError("GEMINI_API_KEY not found in environment variables.")
#     genai.configure(api_key=api_key)
#     return True

# def get_gemini_model(model_name: str = "gemini-2.0-flash"):
#     configure_genai()
#     return genai.GenerativeModel(model_name)
    
# def get_api_key():
#     load_environment()
#     api_key = os.getenv("GEMINI_API_KEY")
#     if not api_key:
#         raise ValueError("GEMINI_API_KEY not found in environment variables.")
#     return api_key