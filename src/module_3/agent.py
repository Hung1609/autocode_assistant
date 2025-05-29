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

SUPPORTED_MODELS = ['gemini-2.0-flash', 'gemini-1.5-flash']
DEFAULT_MODEL = 'gemini-2.0-flash'
BASE_OUTPUT_DIR = 'code_generated_result'
# path in company's computer
OUTPUTS_DIR = r'C:\Users\Hoang Duy\Documents\Phan Lac Hung\autocode_assistant\src\module_1_vs_2\outputs'
PYTHON_PATH = r"C:\Users\Hoang Duy\AppData\Local\Programs\Python\Python310\python.exe"

# my laptop
# OUTPUTS_DIR = r"C:\Users\ADMIN\Documents\Foxconn\autocode_assistant\src\module_1_vs_2\outputs"
# PYTHON_PATH = r"C:\Users\ADMIN\AppData\Local\Programs\Python\Python312\python.exe"

# --- Main functions ---
def slugify(text):
    text = text.lower()
    text = re.sub(r'\s+', '_', text)
    text = re.sub(r'[^\w_.-]', '', text)
    text = text.strip('_.-')
    return text if text else "unnamed_project"

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
    js_path = None

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
            css_path = relative_path[len(frontend_dir) + 1:] if frontend_dir and relative_path.startswith(frontend_dir) else relative_path
            logger.info(f"Detected CSS path: {css_path}")

        # Detect JS file (assume primary JS file is app.js or similar)
        if relative_path.endswith('.js') and ('app.js' in relative_path or 'main.js' in relative_path):
            js_path = relative_path[len(frontend_dir) + 1:] if frontend_dir and relative_path.startswith(frontend_dir) else relative_path
            logger.info(f"Detected JS path: {js_path}")

    # Validate detected paths
    if not backend_module_path:
        logger.error("No main.py found in folder structure. Cannot determine backend module path.")
        raise ValueError("Main backend file 'main.py' not found in folder structure.")
    if not frontend_dir:
        logger.error("No index.html found in folder structure. Cannot determine frontend directory.")
        raise ValueError("Main frontend file 'index.html' not found in folder structure.")
    if not css_path:
        logger.warning("No CSS file found in folder structure. Frontend may lack styling.")
        css_path = "style.css"  # Fallback
    if not js_path:
        logger.warning("No primary JS file (e.g., app.js) found in folder structure. Frontend may lack interactivity.")
        js_path = "app.js"  # Fallback

    # Add the 'logs' directory to the directories to be created
    logs_dir_path = os.path.join(actual_project_root_dir, "logs")
    directories_to_create.add(logs_dir_path)
    logger.info(f"Added logs directory to scaffold plan: {logs_dir_path}")

    bat_file_path = os.path.join(actual_project_root_dir, "setup_and_run.bat")
    files_to_create[bat_file_path] = ""
    logger.info(f"Added setup_and_run.bat to scaffold plan: {bat_file_path}")

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
        "js_path": js_path
    }
    logger.info(f"Scaffold plan generated successfully. Root: {actual_project_root_dir}")
    logger.debug(f"Directories planned: {result['directories_to_create']}")
    logger.debug(f"Files planned: {list(result['files_to_create'].keys())}")
    logger.debug(f"Backend module path: {backend_module_path}, Frontend dir: {frontend_dir}, CSS path: {css_path}, JS path: {js_path}")
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

def generate_code_for_each_file(json_design, json_spec, file_path, project_root_dir, llm_model, plan):
    logger.info(f"Attempting to generate code for file: {file_path}")
    if not all(isinstance(arg, dict) for arg in [json_design, json_spec]):
        raise ValueError("json_design and json_spec must be dictionaries.")
    if not isinstance(file_path, str):
        raise ValueError("file_path must be a string.")

    relative_file_path = os.path.relpath(file_path, project_root_dir).replace('\\', '/')
    if relative_file_path == 'setup_and_run.bat':
        logger.info(f"Generating content for setup_and_run.bat: {file_path}")
        if not os.path.exists(PYTHON_PATH):
            logger.error(f"Python path {PYTHON_PATH} does not exist.")
            raise FileNotFoundError(f"Python path {PYTHON_PATH} does not exist.")
        backend_framework = json_spec.get('technology_Stack', {}).get('backend', {}).get('framework', 'FastAPI')
        run_command = f'python -m uvicorn {plan["backend_module_path"]}:app --reload --port 8001' if backend_framework.lower() == 'fastapi' else f'python {plan["backend_module_path"].replace(".", "/")}.py'
        bat_content = fr"""@echo off
setlocal EnableDelayedExpansion

:: Setup and run the generated application
echo Setting up and running the application... > debug.log 2>&1

:: Set project root
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%" >> debug.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to change to project root directory %PROJECT_ROOT%. >> debug.log 2>&1
    echo ERROR: Failed to change to project root directory %PROJECT_ROOT%.
    pause
    exit /b 1
)
echo Project root set to: %PROJECT_ROOT% >> debug.log 2>&1

:: Check for Python
echo Checking for Python... >> debug.log 2>&1
"{PYTHON_PATH}" --version >> debug.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python is not installed at {PYTHON_PATH}. Please ensure Python 3.8+ is installed. >> debug.log 2>&1
    echo ERROR: Python is not installed at {PYTHON_PATH}. Please ensure Python 3.8+ is installed.
    pause
    exit /b 1
)
echo Python found. >> debug.log 2>&1

:: Create and activate virtual environment in project directory
echo Setting up virtual environment in !PROJECT_ROOT!\venv... >> debug.log 2>&1
if not exist "!PROJECT_ROOT!\venv" (
    "{PYTHON_PATH}" -m venv "!PROJECT_ROOT!\venv" >> debug.log 2>&1
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to create virtual environment in !PROJECT_ROOT!\venv. >> debug.log 2>&1
        echo ERROR: Failed to create virtual environment in !PROJECT_ROOT!\venv.
        pause
        exit /b 1
    )
)
call "!PROJECT_ROOT!\venv\Scripts\activate.bat" >> debug.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to activate virtual environment. Check !PROJECT_ROOT!\venv\Scripts\activate.bat. >> debug.log 2>&1
    echo ERROR: Failed to activate virtual environment. Check !PROJECT_ROOT!\venv\Scripts\activate.bat.
    pause
    exit /b 1
)
echo Virtual environment activated. >> debug.log 2>&1

:: Install dependencies
echo Installing dependencies... >> debug.log 2>&1
if exist "requirements.txt" (
    pip install -r requirements.txt >> debug.log 2>&1
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to install dependencies. Check requirements.txt. >> debug.log 2>&1
        echo ERROR: Failed to install dependencies. Check requirements.txt.
        pause
        exit /b 1
    )
) else (
    echo WARNING: requirements.txt not found. Skipping dependency installation. >> debug.log 2>&1
    echo WARNING: requirements.txt not found. Skipping dependency installation.
)
echo Dependencies installed. >> debug.log 2>&1

:: Run the application
echo Starting the application... >> debug.log 2>&1
{run_command} >> debug.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to start the application. Check {plan['backend_module_path'].replace('.', '/')}.py and uvicorn configuration. >> debug.log 2>&1
    echo ERROR: Failed to start the application. Check {plan['backend_module_path'].replace('.', '/')}.py and uvicorn configuration.
    pause
    exit /b 1
)
echo Application started. >> debug.log 2>&1

pause
exit /b 0
"""
        logger.debug(f"Generated setup_and_run.bat content:\n{bat_content}")
        if any(ord(char) > 127 for char in bat_content):
            logger.error("Invalid non-ASCII characters detected in setup_and_run.bat content.")
            raise ValueError("Generated setup_and_run.bat contains invalid non-ASCII characters.")
        return bat_content

    if relative_file_path == '.env':
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

    # NOTE: The file_path passed to prompt is the absolute one.
    prompt = f"""
    Context:
    You are an expert Senior Software Engineer acting as a meticulous code writer for a {project_name} with a {backend_language_framework} 
backend technology, {frontend_language_framework} frontend technology, and {storage_type} storage type.
    Your task is to generate complete, syntactically correct code for the specified file, based on the JSON design file (technical implementation) 
and JSON specification file (requirements), adhering to additional rules for logging and FastAPI static file serving.

    Target File Information:
    - Full Path of the file to generate: `{file_path}`
    - This file is part of the project structure defined in the `folder_Structure` section of the JSON Design. The `folder_Structure.root_Project_Directory_Name` indicates the main project folder. The `folder_Structure.structure` lists all files and directories relative to that root.
    - Backend module path: `{plan['backend_module_path']}` (e.g., 'backend.main' or 'app.main').
    - Frontend directory: `{plan['frontend_dir']}` (e.g., 'frontend').
    - CSS file path relative to frontend directory: `{plan['css_path']}` (e.g., 'style.css' or 'css/style.css').
    - JS file path relative to frontend directory: `{plan['js_path']}` (e.g., 'app.js' or 'js/app.js').
    
    INTERNAL THOUGHT PROCESS (Follow these steps to build a comprehensive understanding before writing code):
    1. **Analyze File Role**: Determine the file's purpose based on its path and the JSON Design's `folder_Structure`.
       - If the file is `{plan['backend_module_path'].replace('.', '/')}.py`, include FastAPI initialization, StaticFiles mounting, and logging setup.
       - If the file is a Python module (e.g., `backend/routes.py`), include function-level logging.
       - If the file is `{plan['frontend_dir']}/index.html`, reference CSS and JS files using `{plan['css_path']}` and `{plan['js_path']}`.
    2. **Identify Key Requirements (from JSON Specification)**:
       - Which Functional Requirements (FRs) must this file help implement?
       - Which Non-Functional Requirements (NFRs, e.g., Security, Performance, Usability) must this file adhere to?
    3. **Map to Design (from JSON Design)**:
       - Which API endpoints (`interface_Design`) does this file define or call?
       - Which Data Models (`data_Design`) does this file define or use (CRUD)?
       - Which Workflows (`workflow_Interaction`) does this file participate in?
    4. **Plan Implementation & Patterns**:
       - What is the high-level structure (Classes, Functions, Imports)?
       - Use FastAPI conventions, Python logging, and StaticFiles for frontend serving.
       - Ensure dependencies from the `dependencies` section are utilized.
    5. **Determine Entry Point Requirements**:
       - For `{plan['backend_module_path'].replace('.', '/')}.py`, include FastAPI app initialization, StaticFiles mounting.
       - Ensure the file is executable via `uvicorn {plan['backend_module_path']}:app --reload --port 8001`.

    Instructions for Code Generation:
    1.  **Output Code Only**: Your response MUST be only the raw code for the file. Do NOT include any explanations, comments outside the code, or markdown formatting (like ```language ... ```).
    2.  **Python Import Placement (Python Files Only)**: All `import` statements MUST be placed at the very top of the file, before any function definitions, class definitions, or any other executable code (e.g., variable assignments, route definitions outside functions). This is crucial for correct module loading and dependency resolution.
    3.  **Advanced Logging Setup for Debug Agent (Python Files Only)**
        -   **Objective**: Generate structured, rotatable logs in a dedicated `logs/` directory for easy processing by a debug agent.
        -   **Detailed Initialization (ONLY in `{plan['backend_module_path'].replace('.', '/')}.py`):**
            -   **Import necessary modules:** `logging`, `logging.handlers`, `json` (for custom JSON formatting), `contextvars`, `uuid`. If `python-json-logger` is intended for structured logging, attempt to import it and handle `ImportError` gracefully by providing a fallback custom JSON formatter.
            -   **Define a custom JSON formatter:**
                -   This formatter should convert `logging.LogRecord` attributes into a JSON string.
                -   It must include the following fields: `timestamp` (from `asctime`), `level` (from `levelname`), `logger_name` (from `name`), `message`, `pathname`, `funcName`, `lineno`.
                -   Crucially, it must **also include a `request_id` field** if it's present on the `LogRecord` (e.g., `record.request_id`).
                -   For exceptions, ensure `exc_info` is properly formatted and included.
            -   **Configure a `RotatingFileHandler`:**
                -   It should write to `logs/app.log` (path relative to the project root).
                -   Set a `maxBytes` limit (e.g., 10 * 1024 * 1024 bytes for 10MB) and `backupCount` (e.g., 5) to enable log rotation.
                -   Set its formatter to the custom JSON formatter defined above.
            -   **Configure a `StreamHandler`:**
                -   For console output.
                -   Use a standard, human-readable format (not JSON) for console logs (e.g., `%(asctime)s - %(levelname)s - %(name)s - %(message)s`).
            -   **Root Logger Configuration:**
                -   Call `logging.basicConfig` with `level=logging.DEBUG` and register both the `RotatingFileHandler` and `StreamHandler`.
                -   Get the initial logger instance: `logger = logging.getLogger(__name__)`.
        -   **Request ID (Correlation ID) Implementation (ONLY in `{plan['backend_module_path'].replace('.', '/')}.py`):**
            -   **Objective**: Trace individual HTTP requests across all related log messages.
            -   **`ContextVar`:** Declare a `contextvars.ContextVar` (e.g., `request_id_ctx`) to store the unique request ID for the current request context.
            -   **FastAPI Middleware:** Implement a `starlette.middleware.base.BaseHTTPMiddleware`.
                -   Inside its `dispatch` method, generate a unique ID for each incoming request (e.g., using `uuid.uuid4()`).
                -   Set this ID in `request_id_ctx` using `token = request_id_ctx.set(request_id)`.
                -   Reset the `ContextVar` using `request_id_ctx.reset(token)` in a `finally` block **after** `call_next(request)` to ensure context is cleaned up. This is CRITICAL for correct ContextVar behavior.
            -   **Logging Filter:** Create a custom `logging.Filter`.
                -   Its `filter` method should retrieve the `request_id` from `request_id_ctx.get()` and attach it as an attribute to the `logging.LogRecord` (e.g., `record.request_id = request_id_value`).
            -   **Registration:** Register the custom middleware with the FastAPI `app` using `app.add_middleware()`. Also, add the custom logging filter to the root logger (e.g., `logger.addFilter(YourRequestIdFilter())`) after `basicConfig`.
        -   **Logging in Other Python Files (e.g., `backend/routes.py`, `backend/models.py`):**
            -   Simply import `logging` and get the logger instance at the top of the file:
                ```python
                import logging
                logger = logging.getLogger(__name__)
                ```
            -   Log messages will automatically inherit the global logging configuration and Request ID from the context.
        -   **Content of Logs:** In every function, add logging for:
            -   Entry: `logger.info("Entering <function_name> with args: <args>, kwargs: <kwargs>")`
            -   Exit: `logger.info("Exiting <function_name> with result: <result>")` (if applicable)
            -   Errors: Wrap function logic in a try-except block and log errors with `logger.error("Error in <function_name>: <dynamic_error_message>", exc_info=True)` (message should be informative).
            -   For FastAPI route handlers, log incoming requests and responses, including basic path and method.
            -   Do NOT add logging to non-Python files (e.g., HTML, CSS, JavaScript).
    4.  **FastAPI StaticFiles for Frontend ({plan['backend_module_path'].replace('.', '/')}.py Only)**:
       - In `{plan['backend_module_path'].replace('.', '/')}.py`, configure FastAPI to serve frontend static files (HTML, CSS, JavaScript) using `fastapi.StaticFiles`.
       - Mount the frontend directory `{plan['frontend_dir']}` at the root path `/`:
         ```python
         from fastapi import FastAPI
         from fastapi.staticfiles import StaticFiles
         app = FastAPI()
         app.mount("/", StaticFiles(directory="{plan['frontend_dir']}", html=True), name="static")
         ```
        - Ensure the frontend files (e.g., `frontend/index.html`, `frontend/css/style.css`, `frontend/js/app.js`) are structured to be served statically.
        - The application should be runnable with a single command: `uvicorn {plan['backend_module_path']}:app --reload --port 8001`.
    5. **Frontend File Paths (HTML Files Only)**:
        - In HTML files (e.g., `{plan['frontend_dir']}/index.html`), reference CSS and JS files using paths relative to the frontend directory.
        - Use `{plan['css_path']}` for the CSS file (e.g., `<link rel="stylesheet" href="/{plan['css_path']}">`).
        - Use `{plan['js_path']}` for the JS file (e.g., `<script src="/{plan['js_path']}"></script>`).
        - Ensure paths are correct whether assets are in the frontend root (e.g., `frontend/style.css`) or subdirectories (e.g., `frontend/css/style.css`).
    6.  **General Requirements**:
        - Ensure the code aligns with the JSON Design and Specification.
        - For Python files, include necessary imports and follow FastAPI conventions.
        - For frontend files, ensure compatibility with FastAPI’s StaticFiles.
    7.  **Implement Functionality**: Base the code on BOTH the JSON Design and JSON Specification provided below, incorporating logging and StaticFiles as specified.
        -   **JSON Design (Technical Implementation Details)**:
            -   `system_Architecture`: Overall component layout.
            -   `data_Design.data_Models`: Define database schemas/models, considering the `storage_Type`.
            -   **Pydantic Model Data Validation**: For Pydantic models, ensure that all required fields are provided correctly during instantiation. Pay close attention to field names (e.g., 'front_text' vs 'question') and whether a field is optional or required. If a field is `required`, it must always be present when creating an instance of the Pydantic model.
            -   **SQLAlchemy Model Instantiation**: When defining Python classes that map to database tables (e.g., SQLAlchemy models), ensure that primary key fields (like 'id') are correctly defined as `primary_key=True` and are NOT passed as arguments during object instantiation. SQLAlchemy handles the ID generation upon commit.
            -   `interface_Design.api_Specifications`: For backend files, implement these API endpoints (routes, controllers, handlers). For frontend files, prepare to call these APIs.
            -   `workflow_Interaction`: Implement the logic described in these user/system flows.
            -   `dependencies`: Utilize libraries listed here where appropriate for the file's purpose.
        -   **JSON Specification (Requirements & Scope)**:
            -   `project_Overview.project_Purpose`, `project_Overview.product_Scope`: Understand the overall goals and boundaries.
            -   `functional_Requirements`: Ensure the code implements the specified features and actions. Pay attention to `acceptance_criteria`.
            -   `non_Functional_Requirements`: Adhere to quality attributes like security (e.g., input validation, auth checks if applicable to the file), usability, performance).
    8.  **Infer Role from Path**: Deduce the file's purpose from its path and the overall project structure (e.g., a backend model, a frontend UI component, a utility script, a configuration file).
    9.  **Completeness**: Generate all necessary imports, class/function definitions, and logic. For frontend files, include basic HTML structure and styling compatible with StaticFiles.
    10. **Implement Entry Points Correctly**: For files that serve as application entry points, include the appropriate language-specific entry point pattern:
        -   Automatically identify if this file serves as an application entry point, main execution file, or server startup file based on its path, name, and role in the system architecture.
        -   Generate fully executable code, including appropriate initialization code and language-specific entry point patterns (like `if __name__ == "__main__":`) for any file that serves as an application entry point or executable script without requiring explicit instructions.
    11. **Technology Specifics**: Use idiomatic code and conventions for the specified technologies (e.g., FastAPI/SQLAlchemy for Python backend, React/VanillaJS for frontend).

    Here is the design file in JSON format:
    ```json
    {json.dumps(json_design, indent=2)}
    ```

    Here is the specification file in JSON format:
    ```json
    {json.dumps(json_spec, indent=2)}
    ```

    Now, generate the code for the file: `{file_path}`. Ensure it is complete and ready to run, includes advanced logging for Python functions tailored 
for a debug agent, and supports FastAPI StaticFiles for frontend serving in `{plan['backend_module_path'].replace('.', '/')}.py`. If any file should serve as an entry point or executable file, include the appropriate language-specific entry point code.
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
        if file_path.endswith('setup_and_run.bat'):
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
        total_files = len(plan["files_to_create"])
        logger.info(f"Attempting to generate code for {total_files} file(s).")
        for i, file_path in enumerate(plan["files_to_create"].keys()):
            code = generate_code_for_each_file(json_design, json_spec, file_path, plan["project_root_directory"], llm_model_instance, plan)
            write_code_to_file(file_path, code)
        
        bat_file = os.path.join(plan["project_root_directory"], "setup_and_run.bat")
        absolute_project_root_dir = os.path.abspath(plan["project_root_directory"]) # dùng đường dẫn tuyệt đối
        absolute_bat_file_path = os.path.join(absolute_project_root_dir, "setup_and_run.bat")

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

# Run file in C:\Users\Hoang Duy\Documents\Phan Lac Hung\autocode_assistant> python src/module_3/agent.py


### Vấn đề hardcode của coding agent: 
# - Đường dẫn tuyệt đối cho thư mục đầu ra và trình thông dịch Python:
# OUTPUTS_DIR = r'C:\Users\Hoang Duy\Documents\Phan Lac Hung\autocode_assistant\src\module_1_vs_2\outputs'
# PYTHON_PATH = r"C:\Users\Hoang Duy\AppData\Local\Programs\Python\Python310\python.exe"
# - Thư mục đầu ra cơ sở: BASE_OUTPUT_DIR = 'code_generated_result'
#  Là một tên thư mục cố định, không thể thay đổi dễ dàng mà không chỉnh sửa code. Mặc dù là tương đối, nó vẫn là hardcode.
#  - Logic phát hiện và tạo tệp .bat (Windows-specific):
# bat_file_path = os.path.join(actual_project_root_dir, "setup_and_run.bat")
# Phần lớn nội dung của setup_and_run.bat được tạo ra trong hàm generate_code_for_each_file là Windows-specific (.bat extension, setlocal EnableDelayedExpansion, call "!PROJECT_ROOT!\venv\Scripts\activate.bat").
# - Logic tạo tệp .env và requirements.txt mặc định:
# if relative_file_path == '.env': return "DATABASE_URL=sqlite:///todo.db\n"
# Logic cho requirements.txt thêm fastapi[all], uvicorn[standard], sqlalchemy, pydantic nếu không có dependency nào khác được tìm thấy.
# Vấn đề: Giả định mạnh mẽ về công nghệ (FastAPI, SQLite, Python virtual environments). Nếu dự án được tạo không phải là FastAPI/Python, những tệp này sẽ không chính xác.
# - Nội dung Prompt cho LLM:
# Toàn bộ chuỗi prompt trong generate_code_for_each_file là hardcode. Mặc dù nó sử dụng các biến động (project name, tech stack), các hướng dẫn và yêu cầu cốt lõi (như cách xử lý logging Python, StaticFiles của FastAPI, cấu trúc HTML) đều được nhúng cứng vào prompt.
# giới hạn khả năng của agent chỉ tạo ra các ứng dụng Python với FastAPI làm backend, HTML/CSS/JS thuần túy làm frontend và một số quy ước nhất định. Để hỗ trợ các công nghệ khác (Node.js, Java, React, Angular, v.v.), prompt sẽ phải thay đổi đáng kể.