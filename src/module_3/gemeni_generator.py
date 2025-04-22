import google.generativeai as genai
import json
import os
import time
from pathlib import Path
import re # Import regular expressions for cleaning
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file
# --- Configuration ---
SPEC_FILE = os.path.join('outputs', 'flashcard_application_20250422.spec.json')
DESIGN_FILE = os.path.join('outputs', 'flashcard_application_20250422.design.json')
OUTPUT_DIR = 'generated_project_code' # Directory to save the generated code
API_KEY_ENV_VAR = 'GEMINI_API_KEY'
MODEL_NAME = "gemini-1.5-flash" # Use the same model as generation for consistency

# --- Helper Functions ---

def load_json(filepath):
    """Loads JSON data from a file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filepath}")
        exit(1)

def extract_context(spec_data, design_data, target_file_path):
    """
    Extracts relevant context for a specific target file path.
    This is the core logic for tailoring information for the prompt.
    """
    context = {
        "project_overview": spec_data.get("project_Overview", {}),
        "functional_requirements": spec_data.get("functional_Requirements", []),
        "target_file": target_file_path,
        "folder_structure_description": design_data.get("folder_Structure", {}).get("description"),
    }

    # Add component-specific details based on the target file path
    if target_file_path.startswith('/backend'):
        context["backend_component"] = next((comp for comp in design_data.get("system_Architecture", {}).get("components", []) if comp.get("name") == "Backend API"), None)
        context["backend_dependencies"] = design_data.get("dependencies", {}).get("backend", [])
        context["api_specs"] = design_data.get("interface_Design", {}).get("api_Specifications", [])
        context["data_model"] = design_data.get("data_Design", {}).get("data_Models", [])[0] # Assuming one model for now
        context["database_info"] = {
            "type": design_data.get("data_Design", {}).get("database_Type"),
            "storage_type": design_data.get("data_Design", {}).get("storage_Type"),
        }
        # Specific files context
        if target_file_path.endswith('app.py'):
            context["file_purpose"] = "Main Flask application setup, configuration, and potentially CORS handling. Should import and register blueprints if routes are separate."
        elif target_file_path.endswith('models.py'):
            context["file_purpose"] = f"Database model definitions using an appropriate ORM like SQLAlchemy for {context['database_info']['type']} based on the data_Model schema provided."
        elif target_file_path.endswith('routes.py'):
            context["file_purpose"] = f"API route definitions using Flask Blueprints, implementing the logic described in api_specs and interacting with models defined in models.py."

    elif target_file_path.startswith('/frontend'):
        context["frontend_component"] = next((comp for comp in design_data.get("system_Architecture", {}).get("components", []) if comp.get("name") == "Web Frontend"), None)
        context["frontend_dependencies"] = design_data.get("dependencies", {}).get("frontend", [])
        context["ui_notes"] = design_data.get("interface_Design", {}).get("ui_Interaction_Notes")
        context["api_endpoints_to_call"] = [spec.get("endpoint") for spec in design_data.get("interface_Design", {}).get("api_Specifications", [])]
         # Specific files context
        if target_file_path.endswith('App.js'):
            context["file_purpose"] = "Main React application component. Should handle fetching tasks (GET /api/tasks) and creating tasks (POST /api/tasks) using libraries like axios, manage state, and render UI elements based on ui_notes."
        elif target_file_path.startswith('/frontend/src/components'):
             context["file_purpose"] = "Reusable React UI components (e.g., TaskList, AddTaskForm) based on the overall frontend requirements and ui_notes."
             # Note: The design doesn't *specify* components, so the AI needs to infer standard ones.

    # Add other relevant general info
    context["workflows"] = design_data.get("workflow_Interaction", [])

    # Convert context dict to a readable string format for the prompt
    context_str = json.dumps(context, indent=2)
    return context_str

def create_prompt(context_str, target_file_path, design_data):
    """Creates a tailored prompt for the Gemini API."""

    # Find the specific file description from the folder structure
    file_desc = "No specific description found in design."
    for item in design_data.get("folder_Structure", {}).get("structure", []):
        if item.get("path") == target_file_path:
            file_desc = item.get("description", file_desc)
            break

    prompt = f"""
Based on the following project specification and design context:

--- START CONTEXT ---
{context_str}
--- END CONTEXT ---

Your task is to generate the complete code content for the following file:

File Path: {target_file_path}
File Description: {file_desc}

Instructions:
1.  Generate the full, runnable code for this specific file ({os.path.basename(target_file_path)}).
2.  Adhere to the technologies specified in the context (e.g., Flask/Python for backend, React/JS for frontend, PostgreSQL for DB).
3.  Implement the functionality relevant to this file as described in the context (e.g., API endpoints, data models, UI interactions).
4.  Use the specified dependencies where appropriate.
5.  Ensure the code is well-commented where necessary, explaining key logic.
6.  **IMPORTANT:** Output *only* the raw code content for the file. Do *not* include any explanatory text, markdown formatting (like ```python ... ``` or ```javascript ... ```), or anything else before or after the code block. Just the code itself.
"""
    return prompt

def clean_code_response(response_text):
    """Removes potential markdown fences and leading/trailing whitespace."""
    # Regex to find code blocks fenced by ``` possibly followed by a language identifier
    match = re.search(r"```(?:\w*\n)?(.*?)```", response_text, re.DOTALL | re.IGNORECASE)
    if match:
        # If a fenced block is found, return its content
        return match.group(1).strip()
    else:
        # If no fences are found, assume the whole response is code and just strip whitespace
        return response_text.strip()


def generate_code(model, prompt):
    """Calls the Gemini API to generate code."""
    print(f"   Sending prompt to Gemini ({MODEL_NAME})...")
    try:
        # Increase timeout if needed, especially for larger code generation
        response = model.generate_content(prompt, request_options={"timeout": 120}) # 120 seconds timeout
        # Simple retry logic
        retries = 2
        while not response.parts and retries > 0:
             print(f"   Gemini returned empty response. Retrying... ({retries} left)")
             time.sleep(5) # Wait before retrying
             response = model.generate_content(prompt, request_options={"timeout": 120})
             retries -= 1

        if not response.parts:
             print("   Error: Gemini returned an empty response after retries.")
             # Investigate response.prompt_feedback if available for safety blocks etc.
             if hasattr(response, 'prompt_feedback'):
                 print(f"   Prompt Feedback: {response.prompt_feedback}")
             return None

        raw_code = response.text
        cleaned_code = clean_code_response(raw_code)
        print(f"   Code received (approx {len(cleaned_code)} chars).")
        return cleaned_code
    except Exception as e:
        print(f"   Error during Gemini API call: {e}")
        return None

def save_code(logical_path, code, base_output_dir):
    """Saves the generated code to the correct file path."""
    # Remove leading slash and convert to system-specific path
    relative_path = logical_path.lstrip('/')
    full_path = Path(base_output_dir) / relative_path

    try:
        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the code to the file
        with open(full_path, 'w') as f:
            f.write(code)
        print(f"   Successfully saved code to: {full_path}")
        return True
    except OSError as e:
        print(f"   Error saving file {full_path}: {e}")
        return False
    except Exception as e:
        print(f"   An unexpected error occurred during file save: {e}")
        return False

# --- Main Execution ---

if __name__ == "__main__":
    print("Starting Code Generation Agent...")

    # 1. Load API Key
    api_key = os.getenv(API_KEY_ENV_VAR)
    if not api_key:
        print(f"Error: Gemini API key not found in environment variable {API_KEY_ENV_VAR}")
        exit(1)
    print("API Key loaded.")

    # 2. Configure Gemini
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(MODEL_NAME)
        print(f"Gemini model '{MODEL_NAME}' configured.")
    except Exception as e:
        print(f"Error configuring Gemini: {e}")
        exit(1)

    # 3. Load Specification and Design
    print(f"Loading specification from: {SPEC_FILE}")
    spec_data = load_json(SPEC_FILE)
    print(f"Loading design from: {DESIGN_FILE}")
    design_data = load_json(DESIGN_FILE)
    print("Specification and Design files loaded.")

    # 4. Create Base Output Directory
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    print(f"Output directory '{OUTPUT_DIR}' ensured.")

    # 5. Iterate through Folder Structure and Generate Code
    files_to_generate = design_data.get("folder_Structure", {}).get("structure", [])
    if not files_to_generate:
        print("Error: No folder structure found in the design file.")
        exit(1)

    print("\n--- Starting Code Generation Loop ---")
    generated_files_count = 0
    failed_files_count = 0

    for file_info in files_to_generate:
        logical_path = file_info.get("path")
        if not logical_path or not os.path.basename(logical_path): # Skip directories, only process files
             print(f"Skipping directory entry: {logical_path}")
             continue

        print(f"\nProcessing file: {logical_path}")

        # a. Extract Context
        print("   Extracting context...")
        context_str = extract_context(spec_data, design_data, logical_path)

        # b. Create Prompt
        print("   Creating prompt...")
        prompt = create_prompt(context_str, logical_path, design_data)
        # print(f"DEBUG: Prompt for {logical_path}:\n{prompt[:500]}...\n") # Optional: Print start of prompt for debugging

        # c. Generate Code
        generated_code = generate_code(model, prompt)

        # d. Save Code
        if generated_code:
            if save_code(logical_path, generated_code, OUTPUT_DIR):
                generated_files_count += 1
            else:
                failed_files_count += 1
        else:
            print(f"   Skipping save for {logical_path} due to generation error.")
            failed_files_count += 1

        # Optional: Add a small delay between API calls to avoid rate limits
        time.sleep(2) # Adjust as needed

    print("\n--- Code Generation Complete ---")
    print(f"Successfully generated: {generated_files_count} files.")
    print(f"Failed to generate/save: {failed_files_count} files.")
    print(f"Generated code saved in: {OUTPUT_DIR}")

    # --- Post-Generation Steps (Manual) ---
    print("\n--- Next Steps ---")
    print("1. Review the generated code in the '{OUTPUT_DIR}' directory.")
    print("2. Install dependencies:")
    print("   - Backend: cd generated_project/backend && pip install -r requirements.txt (You may need to create requirements.txt based on generated imports or dependencies section)")
    print("   - Frontend: cd generated_project/frontend && npm install")
    print("3. Set up the PostgreSQL database according to the generated models.py (or manually create the table).")
    print("4. Configure database connection details in the backend code (likely in app.py or a config file).")
    print("5. Run the backend (e.g., python app.py) and frontend (e.g., npm start).")
    print("6. Test thoroughly and debug as needed. AI-generated code requires validation!")