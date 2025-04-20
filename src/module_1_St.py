import streamlit as st
import google.generativeai as genai
import os
import json
from datetime import datetime
import re  # Import regex for cleaning
from prompts import SPECIFICATION_PROMPT
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_llm_response(response_text):
    match = re.search(r"json\s*(\{.*?\})\s*", response_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    else:
        start_index = response_text.find('{')
        end_index = response_text.rfind('}')
        if start_index != -1 and end_index != -1 and end_index > start_index:
            return response_text[start_index: end_index + 1].strip()
        else:
            st.warning("Could not reliably extract JSON structure. Attempting to parse the full response.")
            return response_text.strip()


def generate_filename(base_name="requirements"):
    timestamp = datetime.now().strftime("%Y%m%d")
    safe_base_name = re.sub(r'[^\w\-]+', '', base_name)
    safe_base_name = safe_base_name.strip('')
    if not safe_base_name:
        safe_base_name = "requirements"
    return f"{safe_base_name}_{timestamp}.json"


def save_json(data, filename, directory):
    filepath = os.path.join(directory, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return filepath
    except Exception as e:
        st.error(f"Error saving file '{filepath}': {e}")
        return None


st.set_page_config(page_title="AI Requirements Analyst", layout="wide", initial_sidebar_state="collapsed")
st.title("🤖 AI Requirements Analyst")
st.markdown("""
Enter your software project description below. The AI will analyze it using a predefined template
and generate a structured requirements document in JSON format. The JSON will be displayed,
automatically saved to the outputs folder, and a download button will be provided.
""")

if 'google_api_key' not in st.session_state:
    st.session_state.google_api_key = GOOGLE_API_KEY

if not st.session_state.google_api_key:
    with st.sidebar:
        st.header("API Configuration")
        entered_key = st.text_input(
            "Enter your Google API Key:",
            type="password",
            help="Get your key from Google AI Studio or Google Cloud.",
            key="api_key_input"
        )
        if entered_key:
            st.session_state.google_api_key = entered_key
            st.success("API Key entered.", icon="✅")
        else:
            st.warning("Please enter your Google API Key to enable analysis.", icon="🔒")
else:
    st.sidebar.info("API Key is configured.")

st.header("1. Project Description")
user_description = st.text_area(
    "Describe your software project requirements here:",
    height=300,
    placeholder="Example: I need a web application for managing personal tasks..."
)

st.header("2. Generate Requirements Document")

button_disabled = not st.session_state.google_api_key or not user_description
if st.button("✨ Analyze and Generate JSON", type="primary", disabled=button_disabled):
    if not st.session_state.google_api_key:
        st.error("❌ Error: Google API Key is missing. Please enter it in the sidebar.")
    elif not user_description:
        st.error("❌ Error: Please enter a project description.")
    else:
        try:
            genai.configure(api_key=st.session_state.google_api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            full_prompt = SPECIFICATION_PROMPT.format(user_description=user_description)

            with st.spinner("🧠 AI is analyzing and structuring the requirements... Please wait."):
                response = model.generate_content(full_prompt)

                try:
                    raw_response_text = response.text
                    cleaned_response_text = clean_llm_response(raw_response_text)
                    requirements_json = json.loads(cleaned_response_text)

                    st.success("✅ Analysis Complete! Requirements structured successfully.", icon="🎉")

                    st.header("3. Generated Requirements (JSON)")
                    st.json(requirements_json, expanded=True)

                    st.header("4. Save & Download")
                    project_name = "requirements"
                    if isinstance(requirements_json, dict):
                        project_overview = requirements_json.get("project_Overview", {})
                        if isinstance(project_overview, dict):
                            project_name = project_overview.get("project_Name", "requirements")

                    output_filename = generate_filename(base_name=project_name)
                    saved_filepath = save_json(requirements_json, output_filename, OUTPUT_DIR)

                    if saved_filepath:
                        st.info(f"📄 JSON automatically saved to: `{saved_filepath}`")
                        try:
                            with open(saved_filepath, 'r', encoding='utf-8') as f:
                                json_data_for_download = f.read()

                            st.download_button(
                                label="⬇️ Download Requirements JSON",
                                data=json_data_for_download,
                                file_name=output_filename,
                                mime="application/json"
                            )
                        except Exception as read_err:
                            st.error(f"Error reading saved file for download: {read_err}")

                except json.JSONDecodeError as json_err:
                    st.error("❌ Error: Failed to parse the AI's response into valid JSON.")
                    st.error(f"Details: {json_err}")
                    st.warning("The AI might not have followed the JSON structure perfectly.")
                    with st.expander("View Raw AI Response for Debugging"):
                        st.text(raw_response_text)
                except AttributeError:
                    st.error("❌ Error: Could not get text from the AI response. It might have been blocked.")
                    st.warning("Check the AI's response details if possible.")
                    with st.expander("View Full AI Response Object"):
                        st.write(response)
                except Exception as parse_err:
                    st.error(f"❌ An unexpected error occurred while processing the AI response: {parse_err}")
                    with st.expander("View Raw AI Response for Debugging"):
                        st.text(raw_response_text if 'raw_response_text' in locals() else "Raw response not available.")

        except Exception as api_err:
            st.error("❌ An error occurred while communicating with the Google AI model:")
            st.error(f"{api_err}")
            st.warning("Please check your API key validity, network connection, model name ('gemini-pro'), and Google Cloud project status.")
