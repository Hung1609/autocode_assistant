import json

class TechnologyTemplateManager:
    def __init__(self):
        self.templates = {
            "python": {
                "run_script": self._python_run_script,
                "requirements": self._python_requirements,
                "env_file": self._python_env,
                "prompt_template": self._python_prompt_template
            }
        }
    
    #template for specification technology and type    
    def get_template(self, tech_stack: str, template_type: str, **kwargs):
        tech_templates = self.templates.get(tech_stack.lower(), self.templates["python"])
        return tech_templates.get(template_type, lambda **k: "")(**kwargs)
    
    def _python_run_script(self, **kwargs):
        python_path = kwargs.get('python_path', 'python')
        backend_module = kwargs.get('backend_module_path', 'main')
        return rf"""@echo off
setlocal EnableDelayedExpansion

:: Define the log file path explicitly - THIS MUST BE THE VERY FIRST COMMAND THAT USES THE VARIABLE
set "LOG_FILE=debug_code_agent.log"

:: Initial log entries. Use > to create/overwrite, then >> to append.
echo --- run.bat STARTING --- > "%LOG_FILE%"
echo Timestamp: %DATE% %TIME% >> "%LOG_FILE%"
echo Current Directory (at start): "%CD%" >> "%LOG_FILE%"
echo PROJECT_ROOT (calculated): "%~dp0" >> "%LOG_FILE%"
echo PYTHON_PATH from config: "{python_path}" >> "%LOG_FILE%"

:: Change to project root
echo Changing directory to project root... >> "%LOG_FILE%"
cd /d "%~dp0" 1>>"%LOG_FILE%" 2>>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to change to project root directory. >> "%LOG_FILE%"
    echo ERROR: Failed to change to project root directory. Check "%LOG_FILE%".
    pause
    exit /b 1
)
echo Current Directory (after cd): %CD% >> "%LOG_FILE%"

:: Check for Python (using the system Python path from PYTHON_PATH)
echo Checking for Python at "{python_path}"... >> "%LOG_FILE%"
"{python_path}" --version 1>>"%LOG_FILE%" 2>>&1
set PYTHON_CHECK_ERRORLEVEL=!ERRORLEVEL!
if !PYTHON_CHECK_ERRORLEVEL! neq 0 (
    echo ERROR: Python not found or failed to execute at "{python_path}". ErrorLevel: !PYTHON_CHECK_ERRORLEVEL!. >> "%LOG_FILE%"
    echo ERROR: Python not found at "{python_path}". Check "%LOG_FILE%".
    pause
    exit /b !PYTHON_CHECK_ERRORLEVEL!
)
echo Python found at "{python_path}". >> "%LOG_FILE%"

:: Create virtual environment
echo Creating virtual environment in %CD%\venv... >> "%LOG_FILE%"
if not exist "venv" (
    "{python_path}" -m venv "venv" 1>>"%LOG_FILE%" 2>>&1
    set VENV_CREATE_ERRORLEVEL=!ERRORLEVEL!
    if !VENV_CREATE_ERRORLEVEL! neq 0 (
        echo ERROR: Failed to create virtual environment. ErrorLevel: !VENV_CREATE_ERRORLEVEL!. >> "%LOG_FILE%"
        echo ERROR: Failed to create virtual environment. Check "%LOG_FILE%".
        pause
        exit /b !VENV_CREATE_ERRORLEVEL!
    )
) else (
    echo Virtual environment already exists. Skipping creation. >> "%LOG_FILE%"
)
echo Virtual environment creation check complete. >> "%LOG_FILE%"

:: Activate virtual environment
echo Activating virtual environment... >> "%LOG_FILE%"
call "venv\Scripts\activate.bat" 1>>"%LOG_FILE%" 2>>&1
set VENV_ACTIVATE_ERRORLEVEL=!ERRORLEVEL!
if !VENV_ACTIVATE_ERRORLEVEL! neq 0 (
    echo ERROR: Failed to activate virtual environment. ErrorLevel: !VENV_ACTIVATE_ERRORLEVEL!. Check if venv\Scripts\activate.bat exists and is not corrupted. >> "%LOG_FILE%"
    echo ERROR: Failed to activate virtual environment. Check "%LOG_FILE%".
    pause
    exit /b !VENV_ACTIVATE_ERRORLEVEL!
)
echo Virtual environment activated. >> "%LOG_FILE%"

:: Verify python path after activation (Crucial for debugging)
echo Verifying python path after venv activation: >> "%LOG_FILE%"
where python 1>>"%LOG_FILE%" 2>>&1
if %ERRORLEVEL% neq 0 (
    echo WARNING: python.exe not found in PATH after venv activation. This indicates activate.bat failed or PATH not updated. >> "%LOG_FILE%"
)
echo Verifying pip path after venv activation: >> "%LOG_FILE%"
where pip 1>>"%LOG_FILE%" 2>>&1
if %ERRORLEVEL% neq 0 (
    echo WARNING: pip.exe not found in PATH after venv activation. This indicates activate.bat failed or PATH not updated. >> "%LOG_FILE%"
)

:: Install dependencies
echo Installing dependencies... >> "%LOG_FILE%"
if exist "requirements.txt" (
    pip install -r requirements.txt 1>>"%LOG_FILE%" 2>>&1
    set PIP_INSTALL_ERRORLEVEL=!ERRORLEVEL!
    if !PIP_INSTALL_ERRORLEVEL! neq 0 (
        echo ERROR: Failed to install dependencies. ErrorLevel: !PIP_INSTALL_ERRORLEVEL!. Check requirements.txt. >> "%LOG_FILE%"
        echo ERROR: Failed to install dependencies. Check "%LOG_FILE%".
        pause
        exit /b !PIP_INSTALL_ERRORLEVEL!
    )
) else (
    echo WARNING: requirements.txt not found. Skipping dependency installation. >> "%LOG_FILE%"
)
echo Dependencies installation check complete. >> "%LOG_FILE%"

:: Run the application
echo Starting the application with uvicorn... >> "%LOG_FILE%"
python -m uvicorn {backend_module}:app --reload --port 8001 1>>"%LOG_FILE%" 2>>&1
set UVICORN_RUN_ERRORLEVEL=!ERRORLEVEL!
if !UVICORN_RUN_ERRORLEVEL! neq 0 (
    echo ERROR: Failed to start the application. ErrorLevel: !UVICORN_RUN_ERRORLEVEL!. Check {backend_module.replace('.', '/')}.py and uvicorn configuration. >> "%LOG_FILE%"
    echo ERROR: Failed to start the application. Check "%LOG_FILE%".
    pause
    exit /b !UVICORN_RUN_ERRORLEVEL!
)
echo Application started. >> "%LOG_FILE%"

echo --- run.bat FINISHED SUCCESSFULLY --- >> "%LOG_FILE%"
pause
exit /b 0
"""
    def _python_requirements(self, **kwargs):
        dependencies = kwargs.get('dependencies', [])
        base_deps = ['fastapi[all]', 'uvicorn[standard]', 'sqlalchemy', 'pydantic', 'python-dotenv']
        all_deps = list(set(dependencies + base_deps))
        return '\n'.join(all_deps) + '\n'
    
    def _python_env(self, **kwargs):
        storage_type = kwargs.get('storage_type', 'sqlite')
        return f"DATABASE_URL={storage_type}:///app.db\nSECRET_KEY=your-secret-key-here\n"
    
    def _python_prompt_template(self, **kwargs):
        file_path = kwargs.get('file_path', '')
        project_name = kwargs.get('project_name', 'this application')
        backend_language_framework = kwargs.get('backend_language_framework', 'FastAPI')
        frontend_language_framework = kwargs.get('frontend_language_framework', 'Vanilla HTML/CSS/JS')
        storage_type = kwargs.get('storage_type', 'sqlite')
        backend_module_path = kwargs.get('backend_module_path', 'main')
        frontend_dir = kwargs.get('frontend_dir', 'frontend')
        css_path = kwargs.get('css_path', 'css/style.css')
        js_files = kwargs.get('js_files_to_link', [])
        json_design = kwargs.get('json_design', {})
        json_spec = kwargs.get('json_spec', {})
        js_links_for_prompt = "\n".join([f"- /{js_file}" for js_file in js_files]) or "No JavaScript files detected."
        return f"""
        CONTEXT:
        - You are an expert Senior Software Engineer tasked with generating complete, syntactically correct code for a web application named {project_name}. The application uses:
            - Backend: {backend_language_framework}
            - Frontend: {frontend_language_framework}
            - Storage: {storage_type}
        - Your goal is to produce code for a specific file based on:
            - JSON Design: Technical implementation details (architecture, data models, APIs).
            - JSON Specification: Functional and non-functional requirements.
            - Additional rules for logging, FastAPI static file serving, and CORS configuration.
        - The generated code must be executable, idiomatic, and aligned with the provided design and requirements.

        TARGET FILE INFORMATION:
        - Full Path of the File to Generate: {file_path}
        - Project Structure: This file is part of the project structure defined in the `folder_Structure` section of the JSON Design. The `folder_Structure.root_Project_Directory_Name` indicates the main project folder, and `folder_Structure.structure` lists all files and directories relative to that root.
        - Backend Module Path: {backend_module_path}
        - Frontend Directory: {frontend_dir}
        - CSS File Path: Relative to frontend directory, {css_path}
        - JS Files: List of JavaScript files relative to frontend directory:
        {js_links_for_prompt}

        INTERNAL THOUGHT PROCESS:
        1. Analyze File Role:
        - Identify the file's purpose based on `{file_path}` and `json_design.folder_Structure`.
        - If the file is `{backend_module_path.replace('.', '/')}.py`, it's the main backend entry point; include FastAPI initialization, StaticFiles mounting, logging, and CORS setup.
        - If the file is a Python module (e.g., `backend/routes.py`), include function-level logging.
        - If the file is `{frontend_dir}/index.html`, reference CSS and JS files using `{css_path}` and all files in `JS Files` section.
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
        - For the main backend file `{backend_module_path.replace('.', '/')}.py`, include FastAPI app initialization, StaticFiles mounting, and CORS setup.
        - Ensure the file is executable via `python -m uvicorn {backend_module_path}:app --reload --port 8001`.
        - For other executable files, include language-specific entry points (e.g., `if __name__ == "__main__":` for Python).

        CODE GENERATION RULES:
        1. Output Format:
        - Generate only the raw code for the file.
        - Do NOT include explanations, comments outside the code, or markdown formatting.
        2. Python Imports (Python files only):
        - Place all `import` statements at the top, before any executable code.
        3. Advanced Logging (Python files only):
        - For Main Backend File `{backend_module_path.replace('.', '/')}.py`:
            - Import `logging`, `logging.handlers`, `json`.
            - Define a custom JSON formatter to convert `logging.LogRecord` attributes into JSON string, including `timestamp` (from `asctime`), `level` (from `levelname`), `logger_name` (from `name`), `message`, `pathname`, `funcName`, `lineno`, with proper `exc_info` formatting for exceptions.
            - Configure a `RotatingFileHandler` to write to `logs/app.log` with `maxBytes=10MB` and `backupCount=5`, using the JSON formatter.
            - Configure a `StreamHandler` for console output with format `%(asctime)s - %(levelname)s - %(name)s - %(message)s`.
            - Set up the root logger with `logging.basicConfig(level=logging.DEBUG)` and register both handlers.
        - For Other Python Files:
            - Import logging and initialize logger: `logger = logging.getLogger(__name__)`.
            - Log function entry: `logger.info("Entering <function_name> with args: <args>, kwargs: <kwargs>")`.
            - Log function exit: `logger.info("Exiting <function_name> with result: <result>")` (if applicable).
            - Log errors: `logger.error("Error in <function_name>: <dynamic_error_message>", exc_info=True)`.
            - For FastAPI routes, log incoming requests and responses.
        - For Non-Python Files: Do not add logging.
        4. FastAPI CORS Configuration (only in `{backend_module_path.replace('.', '/')}.py`):
        - Configure `fastapi.middleware.cors.CORSMiddleware` after app initialization and logging.
        - Example:
            ```python
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware
            app = FastAPI()
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["http://localhost", "http://localhost:8000"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            ```
        5. FastAPI StaticFiles (only in `{backend_module_path.replace('.', '/')}.py`):
        - Mount the frontend directory at `/`:
            ```python
            from fastapi.staticfiles import StaticFiles
            app.mount("/", StaticFiles(directory="{frontend_dir}", html=True), name="static")
            ```
        - Place this at the end of the file, after all imports, middleware, logging, and routes.
        - Ensure the app is runnable with `python -m uvicorn {backend_module_path}:app --reload --port 8001`.
        6. Frontend File Paths (HTML files only):
        - In `{frontend_dir}/index.html`, reference CSS: `<link rel="stylesheet" href="/{css_path}">`.
        - For each JS file, add: `<script src="/{{js_file}}"></script>`.
        - Example for multiple JS files:
            ```html
            <script src="/script.js"></script>
            <script src="/utils.js"></script>
            ```
        7. Technology-Specific Conventions:
        - Python/FastAPI:
            - Use Pydantic for data validation, ensuring required fields are handled.
            - For SQLAlchemy models, define primary keys (e.g., `id`) with `primary_key=True` and exclude from instantiation.
            - Follow FastAPI conventions for routes and dependencies.
        - Frontend (HTML/CSS/JS):
            - Ensure compatibility with FastAPI's StaticFiles.
            - Use vanilla JavaScript unless specified otherwise.
        8. Completeness:
        - Include all necessary imports, classes, functions, and logic.
        - For frontend files, provide complete HTML structure with basic styling.
        9. JSON Design and Specification:
        - Design: {json.dumps(json_design, indent=2)}
        - Specification: {json.dumps(json_spec, indent=2)}
        10. Entry Points:
            - Automatically detect if `{file_path}` is an entry point.
            - Include `if __name__ == "__main__":` for Python entry points.

        TASK:
        Generate the complete code for `{file_path}`, ensuring:
        - Compliance with FastAPI conventions, logging, CORS, and StaticFiles (if applicable).
        - Alignment with `json_design` and `json_spec`.
        - Inclusion of language-specific entry points for executable files.
        - Readiness to run with `python -m uvicorn {backend_module_path}:app --reload --port 8001` for `{backend_module_path.replace('.', '/')}.py`.
    """