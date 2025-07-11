import json
import os
import logging
import time
import re
from datetime import datetime
import subprocess
from google.generativeai import GenerativeModel, configure
from dotenv import load_dotenv

API_CALL_DELAY_SECONDS = 5
load_dotenv()

logging.basicConfig(
    level=logging.DEBUG, # Thay đổi từ INFO thành DEBUG để dễ track issues, dễ debug, reverting to INFO in production to reduce noise.
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('codegen.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

api_key = os.getenv('GEMINI_API_KEY')
configure(api_key=api_key)
logger.info("Gemini API configured successfully.")

DEFAULT_MODEL = 'gemini-2.0-flash'
BASE_OUTPUT_DIR = 'code_generated_result'
# path in company's computer
OUTPUTS_DIR = r'C:\Users\Hoang Duy\Documents\Phan Lac Hung\autocode_assistant\src\module_1_vs_2\outputs'
PYTHON_PATH = r"C:\Users\Hoang Duy\AppData\Local\Programs\Python\Python310\python.exe"

# my laptop
# OUTPUTS_DIR = r"C:\Users\ADMIN\Documents\Foxconn\autocode_assistant\src\module_1_vs_2\outputs"
# PYTHON_PATH = r"C:\Users\ADMIN\AppData\Local\Programs\Python\Python312\python.exe"

# --- Main functions ---
def validate_json_design(json_data):# Validate the JSON design file against expected structure.
    logger.debug("Validating JSON design file.")
    required_fields = ['system_Architecture', 'data_Design', 'interface_Design', 'folder_Structure', 'dependencies']
    for field in required_fields:
        if field not in json_data:
            logger.error(f"Missing required field: {field}")
            raise ValueError(f"JSON design file must contain '{field}'")

    folder_structure = json_data.get('folder_Structure')
    if not isinstance(folder_structure, dict):
        logger.error("folder_Structure must be a dictionary.")
        raise ValueError("folder_Structure must be a dictionary.")

    root_dir_name = folder_structure.get('root_Project_Directory_Name')
    if not root_dir_name or not isinstance(root_dir_name, str) or not root_dir_name.strip():
        logger.error("folder_Structure must contain a non-empty 'root_Project_Directory_Name' string.")
        raise ValueError("folder_Structure must contain a non-empty 'root_Project_Directory_Name' string.")

    structure_list = folder_structure.get('structure')
    if not isinstance(structure_list, list):
        logger.error("folder_Structure.structure must be a list.")
        raise ValueError("folder_Structure.structure must be a list.")
    
    for i, item in enumerate(structure_list):
        if not isinstance(item, dict):
            logger.error(f"Item at index {i} in folder_Structure.structure is not a dictionary.")
            raise ValueError(f"Item at index {i} in folder_Structure.structure is not a dictionary.")
        if 'path' not in item or not isinstance(item['path'], str) or not item['path'].strip():
            logger.error(f"Item at index {i} in folder_Structure.structure must have a non-empty 'path' string.")
            raise ValueError(f"Item at index {i} in folder_Structure.structure must have a non-empty 'path' string.")
        if 'description' not in item or not isinstance(item['description'], str):
            logger.error(f"Item at index {i} ('{item.get('path')}') in folder_Structure.structure must have a 'description' string.")
            raise ValueError(f"Item at index {i} ('{item.get('path')}') in folder_Structure.structure must have a 'description' string.")

    dependencies = json_data.get('dependencies')
    if not isinstance(dependencies, dict):
        logger.error("dependencies must be a dictionary.")
        raise ValueError("dependencies must be a dictionary.")
    if 'backend' not in dependencies or not isinstance(dependencies['backend'], list):
        logger.error("dependencies must contain a 'backend' list.")
        raise ValueError("dependencies must contain a 'backend' list.")
    if 'frontend' not in dependencies or not isinstance(dependencies['frontend'], list):
        logger.error("dependencies must contain a 'frontend' list.")
        raise ValueError("dependencies must contain a 'frontend' list.")
    logger.debug("JSON design validation successful.")

# Validate the JSON specification file against expected structure.
def validate_json_spec(json_data):
    logger.debug("Validating JSON specification structure.")
    required_fields = ['project_Overview', 'functional_Requirements', 'technology_Stack', 'data_Storage']
    for field in required_fields:
        if field not in json_data:
            logger.error(f"JSON specification must contain '{field}'.")
            raise ValueError(f"JSON specification must contain '{field}'.")
    project_overview = json_data.get('project_Overview')
    if not isinstance(project_overview, dict) or not project_overview.get('project_Name'):
        logger.error("JSON specification's project_Overview must be a dictionary with a 'project_Name'.")
        raise ValueError("JSON specification's project_Overview must be a dictionary with a 'project_Name'.")
    logger.debug("JSON specification validation successful.")

# Parse the JSON design file and generate a scaffold plan.
def parse_json_and_generate_scaffold_plan(json_design, json_spec):
    logger.info("Generating scaffold plan from JSON design file.")
    validate_json_design(json_design)
    validate_json_spec(json_spec)
    
    project_root_name = json_design['folder_Structure']['root_Project_Directory_Name']
    actual_project_root_dir = os.path.join(BASE_OUTPUT_DIR, project_root_name)
    logger.info(f"Target project root directory: {actual_project_root_dir}")
    folder_structure_items = json_design['folder_Structure']['structure']
    directories_to_create = set()
    files_to_create = {}

    # Initialize variables for dynamic folder detection
    backend_module_path = None
    frontend_dir = None
    css_path = None
    js_files_to_link = [] 

    # Parse folder structure to detect backend and frontend directories
    for item in folder_structure_items:
        relative_path = item['path'].strip()
        relative_path = relative_path.replace('\\', '/')
        if relative_path.startswith('/'):
            relative_path = relative_path[1:]
            logger.warning(f"Path '{item['path']}' started with '/'. Corrected to '{relative_path}'. Ensure DESIGN_PROMPT output is correct.")
        
        current_path = os.path.join(actual_project_root_dir, relative_path)
        is_directory = 'directory' in item['description'].lower()

        if is_directory:
            directories_to_create.add(current_path)
        else:
            parent_dir = os.path.dirname(current_path)
            if parent_dir and parent_dir != actual_project_root_dir:
                directories_to_create.add(parent_dir)
            files_to_create[current_path] = ""

        # Detect backend directory (contains main.py)
        if relative_path.endswith('main.py'):
            backend_dir = os.path.dirname(relative_path)
            if backend_dir.startswith('/') and len(backend_dir) > 1: # Only remove if it's not just "/"
                backend_dir = backend_dir[1:]
            backend_module_path = backend_dir.replace('/', '.') + '.main' if backend_dir else 'main'
            logger.info(f"Detected backend module path: {backend_module_path}")

        # Detect frontend directory (contains index.html)
        if relative_path.endswith('index.html'):
            frontend_dir = os.path.dirname(relative_path)
            logger.info(f"Detected frontend directory: {frontend_dir}")

        # Detect CSS file
        if relative_path.endswith('.css'):
            css_path = os.path.relpath(relative_path, frontend_dir).replace('\\', '/') if frontend_dir and relative_path.startswith(frontend_dir) else relative_path
            logger.info(f"Detected CSS path: {css_path}")

        if relative_path.endswith('.js') and not is_directory:
            if frontend_dir and relative_path.startswith(frontend_dir):
                js_file_rel_to_frontend = os.path.relpath(relative_path, frontend_dir).replace('\\', '/')
                js_files_to_link.append(js_file_rel_to_frontend)
            else:
                js_files_to_link.append(relative_path)
            logger.info(f"Detected JS file for linking: {js_files_to_link[-1]}")

    # Validate detected paths
    if not backend_module_path:
        logger.error("No main.py found in folder structure. Cannot determine backend module path.")
        raise ValueError("Main backend file 'main.py' not found in folder structure.")
    if not frontend_dir:
        logger.error("No index.html found in folder structure. Cannot determine frontend directory.")
        raise ValueError("Main frontend file 'index.html' not found in folder structure.")
    if not css_path:
        logger.warning("No CSS file found in folder structure. Frontend may lack styling.")
        raise ValueError("No CSS file found in folder structure.")
    
    if not js_files_to_link:
        logger.warning("No JavaScript files detected in folder structure. Frontend may lack interactivity.")

    # Add the 'logs' directory to the directories to be created
    logs_dir_path = os.path.join(actual_project_root_dir, "logs")
    directories_to_create.add(logs_dir_path)
    logger.info(f"Added logs directory to scaffold plan: {logs_dir_path}")

    bat_file_path = os.path.join(actual_project_root_dir, "run.bat")
    files_to_create[bat_file_path] = ""
    logger.info(f"Added run.bat to scaffold plan: {bat_file_path}")

    # Shell commands (for logging purposes)
    shell_commands_log = [f"mkdir -p \"{d}\"" for d in sorted(list(directories_to_create))] + [f"touch \"{f}\"" for f in files_to_create.keys()]
    result = {
        "project_root_directory": actual_project_root_dir,
        "directories_to_create": sorted(list(directories_to_create)),
        "files_to_create": files_to_create,
        "shell_commands_log": shell_commands_log,
        "backend_module_path": backend_module_path,
        "frontend_dir": frontend_dir,
        "css_path": css_path,
        "js_files_to_link": sorted(list(set(js_files_to_link))) # Ensure unique and sorted
    }
    logger.info(f"Scaffold plan generated successfully. Root: {actual_project_root_dir}")
    logger.debug(f"Directories planned: {result['directories_to_create']}")
    logger.debug(f"Files planned: {list(result['files_to_create'].keys())}")
    logger.debug(f"Backend module path: {backend_module_path}, Frontend dir: {frontend_dir}, CSS path: {css_path}, JS files: {result['js_files_to_link']}")
    return result

# Create the project structure based on the scaffold plan.
def create_project_structure(plan):
    project_root = plan["project_root_directory"]
    logger.info(f"Creating project structure in {project_root}.")
    os.makedirs(project_root, exist_ok=True)
    logger.info(f"Ensured base project directory exists: {project_root}")
    
    try:
        os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
        logger.info(f"Created output directory: {BASE_OUTPUT_DIR}")
    except OSError as e:
        logger.error(f"Failed to create output directory {BASE_OUTPUT_DIR}: {e}")
        raise
    
    for directory in plan['directories_to_create']:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")
    for file_path in plan["files_to_create"].keys():
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            pass 
        logger.info(f"Created empty file: {file_path}")
    logger.info("Project structure created successfully.")

def ensure_init_py_files(project_root_directory):
    logger.info(f"Ensuring __init__.py files in Python package directories under {project_root_directory}.")
    for root, dirs, files in os.walk(project_root_directory):
        if 'venv' in dirs:
            dirs.remove('venv') 
            logger.debug(f"Skipping 'venv' directory in {root}")
        has_python_files = any(f.endswith(".py") and f != "__init__.py" for f in files)
        
        # If it contains Python files, ensure __init__.py exists
        if has_python_files:
            init_py_path = os.path.join(root, "__init__.py")
            if not os.path.exists(init_py_path):
                try:
                    with open(init_py_path, 'w', encoding='utf-8') as f:
                        f.write("# This file makes this directory a Python package.\n")
                    logger.info(f"Created missing __init__.py in {root}")
                except Exception as e:
                    logger.error(f"Failed to create __init__.py in {root}: {e}")
            else:
                logger.debug(f"__init__.py already exists in {root}")
    logger.info("Finished ensuring __init__.py files.")

def generate_code_for_each_file(json_design, json_spec, file_path, project_root_dir, llm_model, plan):
    logger.info(f"Attempting to generate code for file: {file_path}")
    if not all(isinstance(arg, dict) for arg in [json_design, json_spec]):
        raise ValueError("json_design and json_spec must be dictionaries.")
    if not isinstance(file_path, str):
        raise ValueError("file_path must be a string.")

    relative_file_path = os.path.relpath(file_path, project_root_dir).replace('\\', '/')
    if relative_file_path == 'run.bat':
        logger.info(f"Generating content for run.bat: {file_path}")
        if not os.path.exists(PYTHON_PATH):
            logger.error(f"Python path {PYTHON_PATH} does not exist.")
            raise FileNotFoundError(f"Python path {PYTHON_PATH} does not exist.")
        backend_framework = json_spec.get('technology_Stack', {}).get('backend', {}).get('framework', 'FastAPI')
        run_command = f'python -m uvicorn {plan["backend_module_path"]}:app --reload --port 8001' if backend_framework.lower() == 'fastapi' else f'python {plan["backend_module_path"].replace(".", "/")}.py'
        bat_content = fr"""@echo off
setlocal EnableDelayedExpansion

:: Setup and run the generated application
echo Setting up and running the application... > debug_code_agent.log 2>&1

:: Set project root
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%" >> debug_code_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to change to project root directory %PROJECT_ROOT%. >> debug_code_agent.log 2>&1
    echo ERROR: Failed to change to project root directory %PROJECT_ROOT%.
    pause
    exit /b 1
)
echo Project root set to: %PROJECT_ROOT% >> debug_code_agent.log 2>&1

:: Check for Python
echo Checking for Python... >> debug_code_agent.log 2>&1
"{PYTHON_PATH}" --version >> debug_code_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python is not installed at {PYTHON_PATH}. Please ensure Python 3.8+ is installed. >> debug_code_agent.log 2>&1
    echo ERROR: Python is not installed at {PYTHON_PATH}. Please ensure Python 3.8+ is installed.
    pause
    exit /b 1
)
echo Python found. >> debug_code_agent.log 2>&1

:: Create and activate virtual environment in project directory
echo Setting up virtual environment in !PROJECT_ROOT!\venv... >> debug_code_agent.log 2>&1
if not exist "!PROJECT_ROOT!\venv" (
    "{PYTHON_PATH}" -m venv "!PROJECT_ROOT!\venv" >> debug_code_agent.log 2>&1
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to create virtual environment in !PROJECT_ROOT!\venv. >> debug_code_agent.log 2>&1
        echo ERROR: Failed to create virtual environment in !PROJECT_ROOT!\venv.
        pause
        exit /b 1
    )
)
call "!PROJECT_ROOT!\venv\Scripts\activate.bat" >> debug_code_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to activate virtual environment. Check !PROJECT_ROOT!\venv\Scripts\activate.bat. >> debug_code_agent.log 2>&1
    echo ERROR: Failed to activate virtual environment. Check !PROJECT_ROOT!\venv\Scripts\activate.bat.
    pause
    exit /b 1
)
echo Virtual environment activated. >> debug_code_agent.log 2>&1

:: Install dependencies
echo Installing dependencies... >> debug_code_agent.log 2>&1
if exist "requirements.txt" (
    pip install -r requirements.txt >> debug_code_agent.log 2>&1
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to install dependencies. Check requirements.txt. >> debug_code_agent.log 2>&1
        echo ERROR: Failed to install dependencies. Check requirements.txt.
        pause
        exit /b 1
    )
) else (
    echo WARNING: requirements.txt not found. Skipping dependency installation. >> debug_code_agent.log 2>&1
    echo WARNING: requirements.txt not found. Skipping dependency installation.
)
echo Dependencies installed. >> debug_code_agent.log 2>&1

:: Run the application
echo Starting the application... >> debug_code_agent.log 2>&1
{run_command} >> debug_code_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to start the application. Check {plan['backend_module_path'].replace('.', '/')}.py and uvicorn configuration. >> debug_code_agent.log 2>&1
    echo ERROR: Failed to start the application. Check {plan['backend_module_path'].replace('.', '/')}.py and uvicorn configuration.
    pause
    exit /b 1
)
echo Application started. >> debug_code_agent.log 2>&1

pause
exit /b 0
"""
        logger.debug(f"Generated run.bat content:\n{bat_content}")
        if any(ord(char) > 127 for char in bat_content):
            logger.error("Invalid non-ASCII characters detected in run.bat content.")
            raise ValueError("Generated run.bat contains invalid non-ASCII characters.")
        return bat_content

    if relative_file_path == '.env': # hardcoded for now, can be changed later
        logger.info(f"Generating content for .env: {file_path}")
        return "DATABASE_URL=sqlite:///todo.db\n"

    if relative_file_path == 'requirements.txt':
        logger.info(f"Generating content for backend requirements.txt: {file_path}")
        backend_deps = json_design.get('dependencies', {}).get('backend', [])
        if 'fastapi' in backend_deps and 'fastapi[all]' not in backend_deps:
            backend_deps = [dep if dep != 'fastapi' else 'fastapi[all]' for dep in backend_deps]
        if 'uvicorn[standard]' not in backend_deps:
            backend_deps.append('uvicorn[standard]')
        if not backend_deps:
            logger.warning(f"No backend dependencies found in design for {file_path}. Adding minimal FastAPI dependencies.")
            backend_deps = ['fastapi[all]', 'uvicorn[standard]', 'sqlalchemy', 'pydantic']
        return '\n'.join(backend_deps) + '\n'
    
    logger.info(f"Proceeding with LLM generation for: {file_path}")
    project_name = json_spec.get('project_Overview', {}).get('project_Name', 'this application')
    backend_language_framework = f"{json_spec.get('technology_Stack', {}).get('backend', {}).get('language', '')} {json_spec.get('technology_Stack', {}).get('backend', {}).get('framework', '')}".strip()
    frontend_language_framework = f"{json_spec.get('technology_Stack', {}).get('frontend', {}).get('language', '')} {json_spec.get('technology_Stack', {}).get('frontend', {}).get('framework', '')}".strip()
    storage_type = json_design.get('data_Design', {}).get('storage_Type', 'not specified')

    # Prepare JS links for the prompt
    js_links_for_prompt = "\n".join([f"- /{js_file}" for js_file in plan['js_files_to_link']])
    if not js_links_for_prompt:
        js_links_for_prompt = "No JavaScript files detected. If interactivity is needed, you might need to add script tags manually or specify JS files in the design JSON."
    
    # NOTE: The file_path passed to prompt is the absolute one.
    prompt = f"""
    CONTEXT:
    - You are an expert Senior Software Engineer tasked with generating complete, syntactically correct code for a web application named {project_name}. The application uses:
        - Backend: `{backend_language_framework}`
        - Frontend: `{frontend_language_framework}`
        - Storage: `{storage_type}`
    - Your goal is to produce code for a specific file based on:
        - JSON Design: Technical implementation details (architecture, data models, APIs).
        - JSON Specification: Functional and non-functional requirements.
        - Additional rules for logging, FastAPI static file serving, and CORS configuration.
    - The generated code must be executable, idiomatic, and aligned with the provided design and requirements.


    TARGET FILE INFORMATION:
    - Full Path of the File to Generate: `{file_path}`
    - Project Structure: This file is part of the project structure defined in the `folder_Structure` section of the JSON Design. The `folder_Structure.root_Project_Directory_Name` indicates the main project folder, and `folder_Structure.structure` lists all files and directories relative to that root.
    - Backend Module Path: `{plan['backend_module_path']}` (e.g., 'backend.main' or 'app.main').
    - Frontend Directory: `{plan['frontend_dir']}` (e.g., 'frontend').
    - CSS File Path: Relative to frontend directory, `{plan['css_path']}`
    - JS Files: List of JavaScript files relative to frontend directory, {js_links_for_prompt}
    
    
    INTERNAL THOUGHT PROCESS
    - Before generating code, follow these steps to ensure a comprehensive understanding:
        1. Analyze File Role:
        - Identify the file's purpose based on `{file_path}` and `json_design.folder_Structure`.
        - If the file is `{plan['backend_module_path'].replace('.', '/')}.py`, it's the main backend entry point; include FastAPI initialization, StaticFiles mounting, logging, and CORS setup.
        - If the file is a Python module (e.g., `backend/routes.py`), include function-level logging.
        - If the file is `{plan['frontend_dir']}/index.html`, reference CSS and JS files using `{plan['css_path']}` and all files in `JS Files` section.
        2. Identify Key Requirements (from JSON Specification):
        - Determine which Functional Requirements (FRs) this file must help implement.
        - Determine which Non-Functional Requirements (NFRs, e.g., Security, Performance, Usability) this file must adhere to.
        3. Map to Design (from JSON Design):
        - Implement API endpoints from `interface_Design.api_Specifications`.
        - Use or define data models from `data_Design.data_Models` for CRUD operations.
        - Follow workflows from `workflow_Interaction`.
        4. Plan Implementation:
        - Outline the high-level structure of the code (Classes, Functions, Imports).
        - Use FastAPI conventions, Python logging, and StaticFiles for frontend serving.
        - Incorporate dependencies from `json_design.dependencies`.
        5. Determine Entry Point Requirements:
        - For the main backend file `{plan['backend_module_path'].replace('.', '/')}.py`, include FastAPI app initialization, StaticFiles mounting, and CORS setup.
        - Ensure the file is executable via `uvicorn {plan['backend_module_path']}:app --reload --port 8001`.
        - For other executable files, include language-specific entry points (e.g., if __name__ == "__main__": for Python).


    CODE GENERATION RULES:
    1. Output Format:
        - Your response MUST contain only the raw code for the file.
        - Do NOT include explanations, comments outside the code, or markdown formatting.
    2. Python Imports (Python files only):
        - Place all `import` statements at the very top of the file, before any function definitions, class definitions, or other executable code. (e.g., variable assignments, route definitions outside functions).
    3. Advanced Logging (Python files only):
        - For Main Backend File `{plan['backend_module_path'].replace('.', '/')}.py`:
            - Import `logging`, `logging.handlers`, `json`.
            - Define a custom JSON formatter to convert `logging.LogRecord` attributes into JSON string, including `timestamp` (from `asctime`), `level` (from `levelname`), `logger_name` (from `name`), `message`, `pathname`, `funcName`, `lineno`, with proper `exc_info` formatting for exceptions.
            - Configure a `RotatingFileHandler` to write to `logs/app.log` with `maxBytes` (e.g., 10MB) and `backupCount` (e.g., 5), using the custom JSON formatter.
            - Configure a `StreamHandler` for console output with a human-readable format (e.g., `%(asctime)s - %(levelname)s - %(name)s - %(message)s`).
            - Set up the root logger with `logging.basicConfig(level=logging.DEBUG)` and register both the `RotatingFileHandler` and `StreamHandler`.
        - For Other Python Files:
            - Import logging and initialize logger at the top of the file: `logger = logging.getLogger(__name__)`.
            - In every function, add logging for:
                -   Log function entry: `logger.info("Entering <function_name> with args: <args>, kwargs: <kwargs>")`.
                -   Log function exit: `logger.info("Exiting <function_name> with result: <result>")` (if applicable).
                -   Log errors in try-except blocks: `logger.error("Error in <function_name>: <dynamic_error_message>", exc_info=True)`.
            - For FastAPI route handlers, log incoming requests and responses, including basic path and method.
        - For Non-Python Files: DO NOT add logging.
    4. FastAPI CORS Configuration (ONLY in `{plan['backend_module_path'].replace('.', '/')}.py`):
        - In `{plan['backend_module_path'].replace('.', '/')}.py`, configure Cross-Origin Resource Sharing (CORS) using `fastapi.middleware.cors.CORSMiddleware`.
        - Add the `CORSMiddleware` after FastAPI app initialization and logging setup.
        - Example:
            ```python
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware
            
            app = FastAPI()
            
            # Configure CORS
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],  # In production, replace with specific origins
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            ```
        - Place this before route definitions but after imports and logging.
    5. FastAPI StaticFiles (only in `{plan['backend_module_path'].replace('.', '/')}.py`):
        - In `{plan['backend_module_path'].replace('.', '/')}.py`, configure FastAPI to serve frontend static files (HTML, CSS, JavaScript) using `fastapi.StaticFiles`.
        - Mount the frontend directory at `/`:
            ```python
            from fastapi.staticfiles import StaticFiles
            # ... other setup ...
            app.mount("/", StaticFiles(directory="{plan['frontend_dir']}", html=True), name="static")
            ```
        - This line MUST be placed at the very end of the file, after: All import statements, all middleware (e.g., CORS middleware), all logging setup, all route definitions (e.g., @app.get(...)) and any dependency injection or startup events.
        - Ensure the app is runnable with uvicorn `{plan['backend_module_path']}:app --reload --port 8001`.
    6. Frontend File Paths (HTML Files Only):
        - In `{plan['frontend_dir']}/index.html`, reference CSS with `<link rel="stylesheet" href="/{plan['css_path']}">`.
        - For JavaScript files, include ALL detected JS files by creating a `<script>` tag for each. The detected JS files are: {js_links_for_prompt}
        - Example for multiple JS files:
          ```html
          <script src="/script.js"></script>
          <script src="/utils.js"></script>
          ```
        - Ensure paths are relative to the frontend directory and compatible with StaticFiles.
    7. Technology-Specific Conventions:
        - Python/FastAPI:
            - Include necessary imports.
            - Use Pydantic for data validation, ensuring required fields are correctly handled.
            - For SQLAlchemy models, define primary keys (e.g., `id`) with `primary_key=True` and exclude them from instantiation.
            - Follow FastAPI conventions for routes and dependencies.
        - Frontend (HTML/CSS/JS):
            - Ensure compatibility with FastAPI's StaticFiles.
            - Use vanilla JavaScript unless otherwise specified.
    8. Completeness: 
        - Include all necessary imports, classes, functions, and logic.
        - For frontend files, provide a complete HTML structure with basic styling compatible with StaticFiles.
    9. JSON Design and Specification:
        - Design (json_design):
            - `system_Architecture`: Guides component layout.
            - `data_Design.data_Models`: Defines schemas for `{storage_type}`.
            - `interface_Design.api_Specifications`: Defines API endpoints to implement in backend or call in frontend.
            - `workflow_Interaction`: Guides logic for user/system flows.
            - `dependencies`: Libraries to use.
        - Specification (json_spec):
            - `project_Overview.project_Purpose`, `project_Overview.product_Scope`: Defines goals and scope.
            - `functional_Requirements`: Features to implement, with `acceptance_criteria`.
            - `non_Functional_Requirements`: Quality attributes like security, performance.
    10. Entry Points: For files that serve as application entry points, include the appropriate language-specific entry point pattern:
        -   Automatically detect if {file_path} is an entry point.
        -   Generate fully executable code, including appropriate initialization code and language-specific entry point patterns (like `if __name__ == "__main__":` in Python) for any file that serves as an application entry point or executable script without requiring explicit instructions.

    Here is the design file in JSON format:
    ```json
    {json.dumps(json_design, indent=2)}
    ```

    Here is the specification file in JSON format:
    ```json
    {json.dumps(json_spec, indent=2)}
    ```

    
    TASK:
    Generate the complete code for `{file_path}`, ensuring:
    - Ensure it is complete with FastAPI conventions, logging, CORS, and StaticFiles and ready to run.
    - Alignment with `json_design` and `json_spec`.
    - Inclusion of language-specific entry points for executable files.
    - Readiness to run with uvicorn `{plan['backend_module_path']}:app --reload --port 8001` for `{plan['backend_module_path'].replace('.', '/')}.py`.
    """

    if API_CALL_DELAY_SECONDS > 0:
        logger.info(f"Waiting for {API_CALL_DELAY_SECONDS} seconds before API call for {os.path.basename(file_path)}...")
        time.sleep(API_CALL_DELAY_SECONDS)

    try:
        logger.info(f"Sending generation request to model {llm_model.model_name} for {os.path.basename(file_path)}.")
        response = llm_model.generate_content(prompt)
        generated_text = ""
        if hasattr(response, 'text'):
            generated_text = response.text
        elif hasattr(response, 'parts') and response.parts:
            generated_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
        else:
            logger.warning(f"Unexpected response structure from LLM for {file_path}. Full response: {response}")
            generated_text = str(response)

        generated_text = response.text.strip()
        if generated_text.startswith("```") and generated_text.endswith("```"):
            lines = generated_text.splitlines()
            if len(lines) > 1:
                if lines[0].startswith("```") and len(lines[0]) > 3:
                    generated_text = "\n".join(lines[1:-1]).strip()
                else:
                    generated_text = "\n".join(lines[1:-1]).strip()
            elif len(lines) == 1:
                generated_text = lines[0][3:-3].strip()
        if not generated_text:
            logger.warning(f"LLM returned empty content for {file_path}. The file will be empty.")
        logger.info(f"Code successfully generated by LLM for {os.path.basename(file_path)} ({len(generated_text)} chars).")
        return generated_text
    except Exception as e:
        logger.error(f"LLM API call or response processing failed for {file_path}: {e}")
        logger.debug(f"Prompt (first 500 chars) for {file_path}: {prompt[:500]}")
        raise

def write_code_to_file(file_path, code):
    logger.info(f"Writing code to file: {file_path}")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        logger.info(f"Successfully wrote {len(code)} characters to {file_path}")
        # Validate batch file content if it's setup_and_run.bat
        if file_path.endswith('run.bat'):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if any(ord(char) > 127 for char in content):
                    logger.error(f"Non-ASCII characters detected in {file_path}: {content}")
                    raise ValueError(f"Non-ASCII characters detected in {file_path}")
                if '�' in content:
                    logger.error(f"Invalid character '�' detected in {file_path}: {content}")
                    raise ValueError(f"Invalid character '�' detected in {file_path}")
    except OSError as e:
        logger.error(f"Failed to write to {file_path}: {e}")
        raise

def run_codegen_pipeline(json_design, json_spec, llm_model_instance):
    logger.info(f"Starting code generation pipeline using model: {llm_model_instance.model_name}")
    try:
        plan = parse_json_and_generate_scaffold_plan(json_design, json_spec)
        create_project_structure(plan)
        
        ensure_init_py_files(plan["project_root_directory"])

        total_files = len(plan["files_to_create"])
        logger.info(f"Attempting to generate code for {total_files} file(s).")
        for i, file_path in enumerate(plan["files_to_create"].keys()):
            code = generate_code_for_each_file(json_design, json_spec, file_path, plan["project_root_directory"], llm_model_instance, plan)
            write_code_to_file(file_path, code)
        
        bat_file = os.path.join(plan["project_root_directory"], "run.bat")
        absolute_project_root_dir = os.path.abspath(plan["project_root_directory"]) # dùng đường dẫn tuyệt đối
        absolute_bat_file_path = os.path.join(absolute_project_root_dir, "run.bat")

        if os.path.exists(absolute_bat_file_path):
            logger.info(f"Executing {absolute_bat_file_path} to setup and run the application...")
            try:
                result = subprocess.run(
                    f'"{absolute_bat_file_path}"',
                    shell=True,
                    check=True,
                    cwd=absolute_project_root_dir, # đường dẫn tuyệt đối
                    capture_output=True,
                    text=True
                )
                logger.info(f"Successfully executed {absolute_bat_file_path}. Output:\n{result.stdout}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to execute {absolute_bat_file_path}. Exit code: {e.returncode}")
                logger.error(f"Batch file stdout:\n{e.stdout}")
                logger.error(f"Batch file stderr:\n{e.stderr}")
                raise
        else:
            logger.warning(f"{absolute_bat_file_path} not found. Skipping execution.")
        
        logger.info("Code generation pipeline completed.")
    except ValueError as e:
        logger.error(f"Input validation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Code generation pipeline failed: {e}")
        raise

def find_json_files():
    if not os.path.exists(OUTPUTS_DIR):
        logger.error(f"Outputs directory '{OUTPUTS_DIR}' does not exist.")
        raise FileNotFoundError(f"Outputs directory '{OUTPUTS_DIR}' does not exist.")

    all_files = os.listdir(OUTPUTS_DIR)

    spec_candidate_paths = [os.path.join(OUTPUTS_DIR, f) for f in all_files if f.endswith('.spec.json')]
    design_candidate_paths = [os.path.join(OUTPUTS_DIR, f) for f in all_files if f.endswith('.design.json')]

    spec_candidate_paths.sort(key=os.path.getmtime, reverse=True)
    design_candidate_paths.sort(key=os.path.getmtime, reverse=True)

    latest_spec_file = None
    if spec_candidate_paths:
        latest_spec_file = spec_candidate_paths[0]
        logger.info(f"Latest specification file found: {latest_spec_file}")
    else:
        logger.error(f"No .spec.json files found in '{OUTPUTS_DIR}'.")
        raise FileNotFoundError(f"No .spec.json file found in '{OUTPUTS_DIR}'.")

    latest_design_file = None
    if design_candidate_paths:
        latest_design_file = design_candidate_paths[0]
        logger.info(f"Latest design file found: {latest_design_file}")
    else:
        logger.error(f"No .design.json files found in '{OUTPUTS_DIR}'.")
        raise FileNotFoundError(f"No .design.json file found in '{OUTPUTS_DIR}'.")
        
    return latest_design_file, latest_spec_file

if __name__ == "__main__":
    llm_for_codegen = None

    try:
        logger.info(f"Initializing LLM model for code generation: {DEFAULT_MODEL}")
        llm_for_codegen = GenerativeModel(DEFAULT_MODEL)
        logger.info(f"Successfully initialized LLM: {DEFAULT_MODEL}")

        logger.info("Scanning outputs directory for JSON files...")
        design_file, spec_file = find_json_files()

        logger.info(f"Loading design file: {design_file}")
        with open(design_file, 'r', encoding='utf-8') as f:
            json_design_data = json.load(f)
        
        logger.info(f"Loading specification file: {spec_file}")
        with open(spec_file, 'r', encoding='utf-8') as f:
            json_spec_data = json.load(f)
        
        design_meta_ts = json_design_data.get('metadata', {}).get('source_specification_timestamp')
        spec_meta_ts = json_spec_data.get('metadata', {}).get('timestamp')
        if design_meta_ts and spec_meta_ts and design_meta_ts != spec_meta_ts:
            logger.warning(
                f"Timestamp mismatch: Design's source_spec_timestamp ('{design_meta_ts}') "
                f"differs from Spec's timestamp ('{spec_meta_ts}'). Ensure they are compatible."
            )
        elif not design_meta_ts or not spec_meta_ts:
            logger.warning("Metadata timestamps for compatibility check are missing in one or both files.")
        
        run_codegen_pipeline(json_design_data, json_spec_data, llm_for_codegen)
        logger.info("Application generation process finished.")

    except FileNotFoundError as e:
        logger.error(f"Input file not found: {e}")
        print(f"Error: File not found - {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format in one of the input files: {e}")
        print(f"Error: Invalid JSON - {e}")
    except ValueError as e:
        logger.error(f"Configuration or Data Error: {e}")
        print(f"Error: {e}")
    except SystemExit as e:
        print(f"System Exit: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        print(f"An unexpected error occurred. Check codegen.log for details. Error: {e}")

# Run file in C:\Users\Hoang Duy\Documents\Phan Lac Hung\autocode_assistant> python src/module_3/coding_agent.py


### Vấn đề hardcode của coding agent: 
# - Đường dẫn tuyệt đối cho thư mục đầu ra và trình thông dịch Python:
# OUTPUTS_DIR = r'C:\Users\Hoang Duy\Documents\Phan Lac Hung\autocode_assistant\src\module_1_vs_2\outputs'
# PYTHON_PATH = r"C:\Users\Hoang Duy\AppData\Local\Programs\Python\Python310\python.exe"
# - Thư mục đầu ra cơ sở: BASE_OUTPUT_DIR = 'code_generated_result'
#  Là một tên thư mục cố định, không thể thay đổi dễ dàng mà không chỉnh sửa code. Mặc dù là tương đối, nó vẫn là hardcode.
#  - Logic phát hiện và tạo tệp .bat (Windows-specific):
# bat_file_path = os.path.join(actual_project_root_dir, "run.bat")
# Phần lớn nội dung của run.bat được tạo ra trong hàm generate_code_for_each_file là Windows-specific (.bat extension, setlocal EnableDelayedExpansion, call "!PROJECT_ROOT!\venv\Scripts\activate.bat").
# - Logic tạo tệp .env và requirements.txt mặc định:
# if relative_file_path == '.env': return "DATABASE_URL=sqlite:///todo.db\n"
# Logic cho requirements.txt thêm fastapi[all], uvicorn[standard], sqlalchemy, pydantic nếu không có dependency nào khác được tìm thấy.
# Vấn đề: Giả định mạnh mẽ về công nghệ (FastAPI, SQLite, Python virtual environments). Nếu dự án được tạo không phải là FastAPI/Python, những tệp này sẽ không chính xác.
# - Nội dung Prompt cho LLM:
# Toàn bộ chuỗi prompt trong generate_code_for_each_file là hardcode. Mặc dù nó sử dụng các biến động (project name, tech stack), các hướng dẫn và yêu cầu cốt lõi (như cách xử lý logging Python, StaticFiles của FastAPI, cấu trúc HTML) đều được nhúng cứng vào prompt.
# giới hạn khả năng của agent chỉ tạo ra các ứng dụng Python với FastAPI làm backend, HTML/CSS/JS thuần túy làm frontend và một số quy ước nhất định. Để hỗ trợ các công nghệ khác (Node.js, Java, React, Angular, v.v.), prompt sẽ phải thay đổi đáng kể.