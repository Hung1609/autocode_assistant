import json
import os
import logging
import time
import sys
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import BaseTool
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.callbacks.base import BaseCallbackHandler
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from .detect_path import define_project_root, define_python_path

load_dotenv()

# Configuration for the coding agent
class AgentConfig(BaseModel):
    outputs_dir: str = Field(default="src/module_1_vs_2/outputs", description="Directory containing JSON files")
    base_output_dir: str = Field(default="code_generated_result", description="Base directory for generated code")
    python_path: str = Field(default="python", description="Python executable path")
    model_name: str = Field(default="gemini-2.0-flash", description="LLM model name")
    api_delay_seconds: int = Field(default=5, description="Delay between API calls")
    max_retries: int = Field(default=3, description="Maximum retry attempts for LLM calls")
    log_level: str = Field(default="DEBUG", description="Logging level")

    @classmethod
    def from_env(cls) -> 'AgentConfig':
        """Create config from environment variables"""
        return cls(
            outputs_dir=os.getenv('OUTPUTS_DIR', 'src/module_1_vs_2/outputs'),
            base_output_dir=os.getenv('BASE_OUTPUT_DIR', 'code_generated_result'),
            python_path=os.getenv('PYTHON_PATH', 'python'),
            model_name=os.getenv('MODEL_NAME', 'gemini-2.0-flash'),
            api_delay_seconds=int(os.getenv('API_DELAY_SECONDS', '5')),
            max_retries=int(os.getenv('MAX_RETRIES', '3')),
            log_level=os.getenv('LOG_LEVEL', 'DEBUG')
        )

# Error tracking system
class ErrorTracker:
    """Tracks and stores errors for debugging agent"""
    
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.errors = []
        self.error_file = os.path.join(project_root, "errors.json")
    
    def add_error(self, error_type: str, file_path: str, error_message: str, context: Optional[Dict] = None):
        """Add an error to the tracking system"""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "file_path": file_path,
            "error_message": error_message,
            "context": context or {}
        }
        self.errors.append(error_entry)
        self._save_errors()
    
    def _save_errors(self):
        """Save errors to file"""
        os.makedirs(os.path.dirname(self.error_file), exist_ok=True)
        try:
            with open(self.error_file, 'w', encoding='utf-8') as f:
                json.dump(self.errors, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save errors to {self.error_file}: {e}")

    def get_errors(self) -> List[Dict]:
        """Get all tracked errors"""
        return self.errors

# Custom callback handler for logging
class CodingAgentCallback(BaseCallbackHandler):
    """Custom callback handler for the coding agent"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs):
        self.logger.info(f"Tool started: {serialized.get('name', 'Unknown')} with input: {input_str[:100]}...")
    
    def on_tool_end(self, output: str, **kwargs):
        self.logger.info(f"Tool completed with output length: {len(str(output))}")
    
    def on_tool_error(self, error: Exception, **kwargs):
        self.logger.error(f"Tool error: {error}")

# Technology-specific code generators
class TechnologyTemplateManager:
    """Manages templates for different technology stacks"""
    
    def __init__(self):
        self.templates = {
            "fastapi": {
                "run_script": self._fastapi_run_script,
                "requirements": self._fastapi_requirements,
                "env_file": self._fastapi_env,
                "prompt_template": self._fastapi_prompt_template
            },
            "nodejs": {
                "run_script": self._nodejs_run_script,
                "requirements": self._nodejs_requirements,
                "env_file": self._nodejs_env,
                "prompt_template": self._nodejs_prompt_template
            }
        }
    
    def get_template(self, tech_stack: str, template_type: str, **kwargs):
        """Get template for specific technology and type"""
        tech_templates = self.templates.get(tech_stack.lower(), self.templates["fastapi"])
        return tech_templates.get(template_type, lambda **k: "")(**kwargs)
    
    def _fastapi_run_script(self, **kwargs):
        python_path = kwargs.get('python_path', 'python')
        backend_module = kwargs.get('backend_module_path', 'main')
        return f"""@echo off
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
    echo ERROR: Failed to change to project root directory. ErrorLevel: %ERRORLEVEL%. >> "%LOG_FILE%"
    echo ERROR: Failed to change to project root directory. Check "%LOG_FILE%".
    pause
    exit /b 1
)
echo Current Directory (after cd): "%CD%" >> "%LOG_FILE%"

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
echo Creating virtual environment in "!PROJECT_ROOT!\\venv"... >> "%LOG_FILE%"
if not exist "!PROJECT_ROOT!\\venv" (
    "{python_path}" -m venv "!PROJECT_ROOT!\\venv" 1>>"%LOG_FILE%" 2>>&1
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
call "!PROJECT_ROOT!\\venv\\Scripts\\activate.bat" 1>>"%LOG_FILE%" 2>>&1
set VENV_ACTIVATE_ERRORLEVEL=!ERRORLEVEL!
if !VENV_ACTIVATE_ERRORLEVEL! neq 0 (
    echo ERROR: Failed to activate virtual environment. ErrorLevel: !VENV_ACTIVATE_ERRORLEVEL!. Check if venv\\Scripts\\activate.bat exists and is not corrupted. >> "%LOG_FILE%"
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
    
    def _fastapi_requirements(self, **kwargs):
        dependencies = kwargs.get('dependencies', [])
        base_deps = ['fastapi[all]', 'uvicorn[standard]', 'sqlalchemy', 'pydantic', 'python-dotenv']
        all_deps = list(set(dependencies + base_deps))
        return '\n'.join(all_deps) + '\n'
        
    def _fastapi_env(self, **kwargs):
        storage_type = kwargs.get('storage_type', 'sqlite')
        return f"DATABASE_URL={storage_type}:///app.db\nSECRET_KEY=your-secret-key-here\n"
    
    def _fastapi_prompt_template(self, **kwargs):
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

    def _nodejs_run_script(self, **kwargs):
        return f"""@echo off
setlocal EnableDelayedExpansion

:: Setup and run the Node.js application
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

:: Check for Node.js
echo Checking for Node.js... >> debug_code_agent.log 2>&1
node --version >> debug_code_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Node.js is not installed. Please ensure Node.js is installed. >> debug_code_agent.log 2>&1
    echo ERROR: Node.js is not installed. Please ensure Node.js is installed.
    pause
    exit /b 1
)
echo Node.js found. >> debug_code_agent.log 2>&1

:: Install dependencies
echo Installing dependencies... >> debug_code_agent.log 2>&1
if exist "package.json" (
    npm install >> debug_code_agent.log 2>&1
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to install dependencies. Check package.json. >> debug_code_agent.log 2>&1
        echo ERROR: Failed to install dependencies. Check package.json.
        pause
        exit /b 1
    )
) else (
    echo WARNING: package.json not found. Skipping dependency installation. >> debug_code_agent.log 2>&1
    echo WARNING: package.json not found. Skipping dependency installation.
)
echo Dependencies installed. >> debug_code_agent.log 2>&1

:: Run the application
echo Starting the application... >> debug_code_agent.log 2>&1
npm start >> debug_code_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to start the application. Check package.json and npm start script. >> debug_code_agent.log 2>&1
    echo ERROR: Failed to start the application. Check package.json and npm start script.
    pause
    exit /b 1
)
echo Application started. >> debug_code_agent.log 2>&1

pause
exit /b 0
"""
    
    def _nodejs_requirements(self, **kwargs):
        dependencies = kwargs.get('dependencies', {})
        base_package = {
            "name": "generated-app",
            "version": "1.0.0",
            "scripts": {"start": "node index.js"},
            "dependencies": {"express": "^4.18.2"}
        }
        base_package["dependencies"].update(dependencies)
        return json.dumps(base_package, indent=2) + '\n'
    
    def _nodejs_env(self, **kwargs):
        return "PORT=3000\nDB_URL=mongodb://localhost:27017/app\n"
    
    def _nodejs_prompt_template(self, **kwargs):
        file_path = kwargs.get('file_path', '')
        project_name = kwargs.get('project_name', 'this application')
        backend_language_framework = kwargs.get('backend_language_framework', 'Node.js Express')
        frontend_language_framework = kwargs.get('frontend_language_framework', 'Vanilla HTML/CSS/JS')
        storage_type = kwargs.get('storage_type', 'mongodb')
        json_design = kwargs.get('json_design', {})
        json_spec = kwargs.get('json_spec', {})
        
        return f"""
CONTEXT:
- You are an expert Senior Software Engineer tasked with generating complete, syntactically correct code for a web application named {project_name}. The application uses:
    - Backend: {backend_language_framework}
    - Frontend: {frontend_language_framework}
    - Storage: {storage_type}
- Your goal is to produce code for a specific file based on:
    - JSON Design: Technical implementation details (architecture, data models, APIs).
    - JSON Specification: Functional and non-functional requirements.
- The generated code must be executable, idiomatic, and aligned with the provided design and requirements.

TARGET FILE INFORMATION:
- Full Path of the File to Generate: {file_path}
- Project Structure: This file is part of the project structure defined in the `folder_Structure` section of the JSON Design.

INTERNAL THOUGHT PROCESS:
1. Analyze File Role:
   - Identify the file's purpose based on `{file_path}` and `json_design.folder_Structure`.
   - If the file is the main entry point (e.g., `index.js`, `server.js`), include Express initialization, middleware setup, and route mounting.
   - If it's a route file, implement RESTful API endpoints based on the JSON design.
   - If it's a model file, implement data schemas and database interactions.

2. Extract Requirements:
   - From JSON Specification: Functional requirements, technology stack, and data models.
   - From JSON Design: API endpoints, data flow, and component interactions.

3. Follow Node.js/Express Best Practices:
   - Use modern JavaScript (ES6+) features.
   - Implement proper error handling and validation.
   - Include security middleware (helmet, cors).
   - Follow RESTful API conventions.
   - Use environment variables for configuration.

4. Generate Complete Code:
   - Include all necessary imports and dependencies.
   - Implement full functionality as specified in the requirements.
   - Add proper error handling and logging.
   - Ensure code is production-ready and well-structured.

RULES:
1. Generate ONLY the code for the specified file - no explanations, comments, or markdown.
2. The code must be complete, syntactically correct, and ready to run.
3. Include proper error handling and input validation.
4. Follow Express.js and Node.js best practices.
5. Use async/await for asynchronous operations.
6. Implement proper middleware and security measures.

JSON DESIGN CONTEXT:
{json.dumps(json_design, indent=2)}

JSON SPECIFICATION CONTEXT:
{json.dumps(json_spec, indent=2)}

Generate the complete code for: {file_path}
"""

# LangChain Tools
class FileGeneratorTool(BaseTool):
    """Tool for generating individual files"""
    
    # KHẮC PHỤC LỖI: Thêm type annotations cho 'name' và 'description'
    name: str = "file_generator"
    description: str = "Generates code for individual files based on specifications"
    
    def __init__(self, llm, template_manager: TechnologyTemplateManager, error_tracker: ErrorTracker, config: AgentConfig):
        super().__init__()
        self._llm = llm
        self._template_manager = template_manager
        self._error_tracker = error_tracker
        self._config = config
    
    def _run(self, file_path: str, context: Dict, requirements: Dict) -> str:
        """Generate code for a specific file with retry logic"""
        tech_stack = context.get('tech_stack', 'fastapi')
        project_root = context.get('project_root', '')
        relative_file_path = os.path.relpath(file_path, project_root).replace('\\', '/')
        
        # Handle special files
        if relative_file_path == 'requirements.txt':
            return self._template_manager.get_template(
                tech_stack, 'requirements',
                dependencies=context.get('design_data', {}).get('dependencies', {}).get('backend', [])
            )
        elif relative_file_path == '.env':
            return self._template_manager.get_template(
                tech_stack, 'env_file',
                storage_type=context.get('design_data', {}).get('data_Design', {}).get('storage_Type', 'sqlite')
            )
        
        # Generate code using LLM with retries
        for attempt in range(self._config.max_retries):
            try:
                prompt_template = self._template_manager.get_template(
                    tech_stack, 'prompt_template',
                    file_path=file_path,
                    project_name=requirements.get('project_Overview', {}).get('project_Name', 'this application'),
                    backend_language_framework=f"{requirements.get('technology_Stack', {}).get('backend', {}).get('language', 'Python')} {requirements.get('technology_Stack', {}).get('backend', {}).get('framework', 'FastAPI')}",
                    frontend_language_framework=f"{requirements.get('technology_Stack', {}).get('frontend', {}).get('language', 'HTML/CSS/JS')} {requirements.get('technology_Stack', {}).get('frontend', {}).get('framework', 'Vanilla')}",
                    storage_type=context.get('design_data', {}).get('data_Design', {}).get('storage_Type', 'sqlite'),
                    backend_module_path=context.get('backend_module_path', 'main'),
                    frontend_dir=context.get('frontend_dir', 'frontend'),
                    css_path=context.get('css_path', 'css/style.css'),
                    js_files_to_link=context.get('js_files_to_link', []),
                    json_design=context.get('design_data', {}),
                    json_spec=requirements
                )
                
                response = self._llm.invoke([HumanMessage(content=prompt_template)])
                generated_code = response.content.strip()
                
                # Clean up code blocks
                if generated_code.startswith("```") and generated_code.endswith("```"):
                    lines = generated_code.splitlines()
                    if len(lines) > 2:
                        generated_code = "\n".join(lines[1:-1])
                    else:
                        generated_code = ""
                
                if not generated_code:
                    raise ValueError("LLM returned empty code")
                
                # Basic syntax validation for Python files
                if file_path.endswith('.py'):
                    import ast
                    try:
                        ast.parse(generated_code)
                    except SyntaxError as e:
                        raise ValueError(f"Syntax error in generated Python code: {e}")
                
                return generated_code
                
            except Exception as e:
                self._error_tracker.add_error(
                    "code_generation", file_path, str(e),
                    {"context": context, "requirements": requirements, "attempt": attempt + 1}
                )
                if attempt == self._config.max_retries - 1:
                    return f"# Error generating code: {str(e)}\n# TODO: Fix this file"
                time.sleep(self._config.api_delay_seconds * (2 ** attempt))  # Exponential backoff
        
        return "# Error: Max retries reached"

class ProjectStructureTool(BaseTool):
    """Tool for creating project structure"""
    
    # KHẮC PHỤC LỖI: Thêm type annotations cho 'name' và 'description'
    name: str = "project_structure"
    description: str = "Creates the project directory structure"
    
    def __init__(self, error_tracker: ErrorTracker):
        super().__init__()
        self._error_tracker = error_tracker
    
    def _run(self, project_root: str, structure: List[Dict]) -> str:
        """Create project structure"""
        try:
            os.makedirs(project_root, exist_ok=True)
            created_items = []
            for item in structure:
                path = os.path.join(project_root, item['path'].strip('/\\'))
                description = item.get('description', '').lower()
                
                # Check if it's a directory based on description or if it ends with '/'
                is_directory = (
                    'directory' in description or 
                    item['path'].rstrip('/\\').endswith('/') or
                    item['path'].rstrip('/\\').endswith('\\') or
                    ('file' not in description and not os.path.splitext(path)[1] and not any(
                        special_file in os.path.basename(path).lower() 
                        for special_file in ['.gitignore', '.env', 'dockerfile', 'makefile', 'readme']
                    ))
                )
                
                if is_directory:
                    os.makedirs(path, exist_ok=True)
                    created_items.append(f"Directory: {path}")
                else:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write("")  # Create empty file
                    created_items.append(f"File: {path}")
            
            # Ensure logs directory
            logs_dir = os.path.join(project_root, 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            created_items.append(f"Directory: {logs_dir}")
            
            return f"Created {len(created_items)} items:\n" + "\n".join(created_items)
            
        except Exception as e:
            self._error_tracker.add_error(
                "structure_creation", project_root, str(e),
                {"structure": structure}
            )
            return f"Error creating structure: {str(e)}"

class ProjectValidatorTool(BaseTool):
    """Tool for validating generated project"""
    
    # KHẮC PHỤC LỖI: Thêm type annotations cho 'name' và 'description'
    name: str = "project_validator"
    description: str = "Validates the generated project for common issues"
    
    def __init__(self, error_tracker: ErrorTracker):
        super().__init__()
        self._error_tracker = error_tracker
    
    def _run(self, project_root: str, tech_stack: str) -> str:
        """Validate the generated project"""
        issues = []
        
        try:
            # Check for required files
            required_files = ['main.py', 'requirements.txt'] if tech_stack.lower() == 'fastapi' else ['index.js', 'package.json']
            for req_file in required_files:
                if not self._find_file(project_root, req_file):
                    issues.append(f"Missing required file: {req_file}")
            
            # Check for empty files
            for root, _, files in os.walk(project_root):
                for file in files:
                    if file.endswith(('.py', '.js', '.html', '.css')):
                        file_path = os.path.join(root, file)
                        if os.path.getsize(file_path) == 0:
                            issues.append(f"Empty file: {file_path}")
            
            # Check for non-ASCII characters in batch files
            for file in ['run.bat']:
                file_path = os.path.join(project_root, file)
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if any(ord(char) > 127 for char in content):
                            issues.append(f"Non-ASCII characters in {file}")
            
            # Log issues
            for issue in issues:
                self._error_tracker.add_error(
                    "validation", project_root, issue,
                    {"tech_stack": tech_stack}
                )
            
            if issues:
                return f"Found {len(issues)} validation issues:\n" + "\n".join(issues)
            return "Project validation passed successfully"
            
        except Exception as e:
            self._error_tracker.add_error(
                "validation_error", project_root, str(e)
            )
            return f"Validation error: {str(e)}"
    
    def _find_file(self, root_dir: str, filename: str) -> bool:
        """Find if a file exists in the directory tree"""
        for root, _, files in os.walk(root_dir):
            if filename in files:
                return True
        return False

# Main Coding Agent
class LangChainCodingAgent:
    """Main coding agent using LangChain framework"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = self._setup_logging()
        self.error_tracker = None # Sẽ được khởi tạo sau khi biết project_root
        self.template_manager = TechnologyTemplateManager()
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model=config.model_name,
            google_api_key=os.getenv('GEMINI_API_KEY'),
            temperature=0.1
        )
        
        # Setup agent (tools will be initialized/updated in generate_project)
        self._setup_agent()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('langchain_coding_agent.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    def _setup_tools(self):
        """Setup LangChain tools with the actual error_tracker"""
        # Đảm bảo self.error_tracker đã được khởi tạo
        if self.error_tracker is None:
            raise ValueError("ErrorTracker must be initialized before setting up tools.")
            
        self.tools = [
            ProjectStructureTool(self.error_tracker),
            FileGeneratorTool(self.llm, self.template_manager, self.error_tracker, self.config),
            ProjectValidatorTool(self.error_tracker)
        ]
        
        # Cần cập nhật lại AgentExecutor nếu tools thay đổi sau khi khởi tạo ban đầu
        # Nếu _setup_agent được gọi trong __init__, thì agent_executor sẽ có tools cũ.
        # Một cách là tạo lại agent_executor ở đây, hoặc đảm bảo tools được truyền đúng lúc.
        # Để đơn giản, sẽ tạo lại agent_executor trong generate_project.

    def _setup_agent(self):
        """Setup LangChain agent components (prompt, memory). AgentExecutor created later."""
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are an expert software architect and developer. 
Your job is to generate complete, production-ready applications based on JSON specifications.

You have access to tools for:
- Creating project structure
- Generating individual files
- Validating the project

Always ensure the generated code is:
1. Complete and executable
2. Follows best practices
3. Includes proper error handling
4. Is well-documented

Work systematically: create structure first, generate files, validate, and create run script."""),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessage(content="{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")        ])
        
        # Use simple list for chat history instead of deprecated ConversationBufferMemory
        self.chat_history = []
        # AgentExecutor sẽ được khởi tạo trong generate_project sau khi tools có error_tracker thật

    def generate_project(self, design_data: Dict, spec_data: Dict) -> str:
        """Generate complete project from specifications"""
        try:
            # 1. Initialize ErrorTracker for this specific project
            project_name = design_data['folder_Structure']['root_Project_Directory_Name']
            project_root = os.path.abspath(os.path.join(self.config.base_output_dir, project_name))
            self.error_tracker = ErrorTracker(project_root)
            
            # 2. Setup tools with the correct ErrorTracker instance
            self._setup_tools() # Gọi lại để tools sử dụng self.error_tracker đã khởi tạo
            # 3. Create AgentExecutor with the now correctly initialized tools
            agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
            self.agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True,
                callbacks=[CodingAgentCallback(self.logger)]
            )

            self.logger.info(f"Starting project generation for: {project_name}")
            
            # Use LangChain AgentExecutor for higher-level decision making (Optional for now, but good practice)
            # For this fixed flow, we'll call the steps directly as before, but the AgentExecutor is ready.
            # If you want to use the agent_executor to decide steps:
            # response = self.agent_executor.invoke({"input": f"Create the application '{project_name}' based on the design and specification. First, create the structure, then generate files, then validate, then create and execute the run script."})
            # self.logger.info(f"AgentExecutor response: {response['output']}")
            
            # Current sequential flow (as in your code)
            # 1. Validate JSON inputs
            self.logger.info("Validating JSON inputs...")
            self._validate_json(design_data, spec_data)
            self.logger.info("JSON validation passed.")

            # 2. Create structure
            self.logger.info(f"Creating project structure for: {project_name}")
            structure_result = self._create_project_structure(design_data, spec_data)
            self.logger.info(f"Structure creation result: {structure_result}")
            
            # 3. Generate files
            self.logger.info(f"Generating project files for: {project_name}")
            files_result = self._generate_project_files(design_data, spec_data, project_root)
            self.logger.info(f"Files generation result: {files_result}")
            
            # 4. Validate project
            self.logger.info(f"Validating project: {project_name}")
            validation_result = self._validate_project(project_root, spec_data)
            self.logger.info(f"Validation result: {validation_result}")
            
            # 5. Create and execute run script
            self.logger.info(f"Creating and executing run script for: {project_name}")
            self._create_run_script(project_root, spec_data, design_data)
            execution_result = self._execute_run_script(project_root)
            self.logger.info(f"Run script execution result: {execution_result}")
            
            self.logger.info(f"Project generation completed: {project_root}")
            return f"Project generated at: {project_root}\nStructure: {structure_result}\nFiles: {files_result}\nValidation: {validation_result}\nExecution: {execution_result}"
            
        except Exception as e:
            self.logger.error(f"Project generation failed: {e}", exc_info=True) # Log full traceback
            if self.error_tracker:
                self.error_tracker.add_error(
                    "project_generation", "overall", str(e),
                    {"design_data": design_data, "spec_data": spec_data}
                )
            raise
    
    def _validate_json(self, design_data: Dict, spec_data: Dict):
        """Validate JSON design and specification files"""
        # NOTE: You might want to move these validation rules outside this class
        # to a dedicated validation module, as they were in the previous version.
        # This keeps the agent's logic cleaner. For now, kept as is.
        
        required_design_fields = ['folder_Structure', 'data_Design', 'interface_Design', 'dependencies']
        for field in required_design_fields:
            if field not in design_data:
                self.error_tracker.add_error("validation", "design.json", f"Missing field: {field}")
                raise ValueError(f"JSON design must contain '{field}'")
        
        folder_structure = design_data.get('folder_Structure', {})
        if not folder_structure.get('root_Project_Directory_Name') or not folder_structure.get('structure'):
            self.error_tracker.add_error("validation", "design.json", "Invalid folder_Structure")
            raise ValueError("folder_Structure must contain 'root_Project_Directory_Name' and 'structure'")
        
        required_spec_fields = ['project_Overview', 'functional_Requirements', 'technology_Stack']
        for field in required_spec_fields:
            if field not in spec_data:
                self.error_tracker.add_error("validation", "spec.json", f"Missing field: {field}")
                raise ValueError(f"JSON specification must contain '{field}'")
        
        if not spec_data.get('project_Overview', {}).get('project_Name'):
            self.error_tracker.add_error("validation", "spec.json", "Missing project_Name in project_Overview")
            raise ValueError("project_Overview must contain 'project_Name'")
    
    def _create_project_structure(self, design_data: Dict, spec_data: Dict) -> str:
        """Wrapper for ProjectStructureTool"""
        structure_tool = next(t for t in self.tools if isinstance(t, ProjectStructureTool))
        return structure_tool._run(
            os.path.join(self.config.base_output_dir, design_data['folder_Structure']['root_Project_Directory_Name']),
            design_data['folder_Structure']['structure']
        )
    
    def _generate_project_files(self, design_data: Dict, spec_data: Dict, project_root: str) -> str:
        """Wrapper for FileGeneratorTool actions"""
        structure = design_data['folder_Structure']['structure']
        
        # Parse structure for frontend/backend details needed for prompt context
        context_for_generation = self._build_context(design_data, spec_data, project_root)
        
        file_generator = next(t for t in self.tools if isinstance(t, FileGeneratorTool))
        generated_files = []
        
        for item in structure:
            if 'directory' not in item.get('description', '').lower():
                file_path = os.path.join(project_root, item['path'].strip('/\\'))
                
                # Update context with specific file info for the LLM
                file_context = context_for_generation.copy()
                file_context['file_info'] = item
                
                code = file_generator._run(file_path, file_context, spec_data)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                generated_files.append(file_path)
                
        return f"Generated {len(generated_files)} files"
    
    def _build_context(self, design_data: Dict, spec_data: Dict, project_root: str) -> Dict:
        """Build a comprehensive context dictionary for prompt generation"""
        backend_module_path = 'main'
        frontend_dir_rel = 'frontend' # Relative path within project
        css_path_rel_to_frontend = 'style.css' # Relative path within frontend_dir
        js_files_to_link_rel_to_frontend = []
        
        # Iterate through folder structure to find paths
        for item in design_data['folder_Structure']['structure']:
            relative_item_path = item['path'].strip('/\\').replace('\\', '/')
            
            if relative_item_path.endswith('main.py'):
                # e.g., 'backend/main.py' -> 'backend.main'
                parts = relative_item_path.split('/')
                backend_module_path = '.'.join(parts[:-1] + ['main']) if len(parts) > 1 else 'main'
            
            elif relative_item_path.endswith('index.html'):
                # e.g., 'frontend/index.html' -> 'frontend'
                frontend_dir_rel = os.path.dirname(relative_item_path) or 'frontend'
            
            elif relative_item_path.endswith('.css'):
                # e.g., 'frontend/css/style.css', frontend_dir_rel='frontend' -> 'css/style.css'
                # Ensure it's under the detected frontend_dir, otherwise use as is
                if relative_item_path.startswith(frontend_dir_rel):
                    css_path_rel_to_frontend = os.path.relpath(relative_item_path, frontend_dir_rel).replace('\\', '/')
                else:
                    css_path_rel_to_frontend = relative_item_path # Fallback if not neatly nested
            
            elif relative_item_path.endswith('.js') and 'directory' not in item.get('description', '').lower():
                # e.g., 'frontend/js/script.js', frontend_dir_rel='frontend' -> 'js/script.js'
                if relative_item_path.startswith(frontend_dir_rel):
                    js_files_to_link_rel_to_frontend.append(os.path.relpath(relative_item_path, frontend_dir_rel).replace('\\', '/'))
                else:
                    js_files_to_link_rel_to_frontend.append(relative_item_path) # Fallback

        return {
            'tech_stack': spec_data.get('technology_Stack', {}).get('backend', {}).get('framework', 'fastapi'),
            'project_root': project_root,
            'design_data': design_data, # Pass full design for LLM context
            'backend_module_path': backend_module_path,
            'frontend_dir': frontend_dir_rel,
            'css_path': css_path_rel_to_frontend,
            'js_files_to_link': sorted(list(set(js_files_to_link_rel_to_frontend))) # Ensure unique and sorted
        }
    
    def _validate_project(self, project_root: str, spec_data: Dict) -> str:
        """Wrapper for ProjectValidatorTool"""
        validator = next(t for t in self.tools if isinstance(t, ProjectValidatorTool))
        return validator._run(project_root, spec_data.get('technology_Stack', {}).get('backend', {}).get('framework', 'fastapi'))
    
    def _create_run_script(self, project_root: str, spec_data: Dict, design_data: Dict):
        """Create the run script for the project"""
        tech_stack = spec_data.get('technology_Stack', {}).get('backend', {}).get('framework', 'fastapi')
        backend_module_path = self._find_backend_module(design_data)
        
        script_content = self.template_manager.get_template(
            tech_stack, 'run_script',
            python_path=self.config.python_path,
            backend_module_path=backend_module_path
        )
        
        script_path = os.path.join(project_root, 'run.bat') # Fixed to run.bat as per your current setup
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
    
    def _execute_run_script(self, project_root: str) -> str:
        script_path = os.path.join(project_root, 'run.bat')
        script_path = os.path.abspath(script_path)  # Convert to absolute path
        if not os.path.exists(script_path):
            self.error_tracker.add_error("execution", script_path, "Run script not found")
            self.logger.error(f"Run script not found: {script_path}")
            return "Run script not found"
        try:
            self.logger.info(f"Current working directory: {os.getcwd()}")
            self.logger.info(f"Executing run script: {script_path} from {project_root}")
            command_string = f'"{script_path}"'
            result = subprocess.run(
                command_string,
                shell=True,
                check=True,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            self.logger.info(f"Run script executed successfully. Stdout:\n{result.stdout}")
            if result.stderr:
                self.logger.warning(f"Run script Std_error:\n{result.stderr}")
            return f"Run script executed: {result.stdout}"
        except subprocess.CalledProcessError as e:
            error_output = f"Exit code: {e.returncode}\nStdout:\n{e.stdout}\nStderr:\n{e.stderr}"
            self.error_tracker.add_error(
                "execution", script_path, f"Run script failed: {error_output}",
                {"exit_code": e.returncode, "stdout": e.stdout, "stderr": e.stderr}
            )
            self.logger.error(f"Run script failed: {error_output}")
            return f"Run script failed. Check logs for details: {error_output}"
        except subprocess.TimeoutExpired:
            self.error_tracker.add_error("execution", script_path, "Run script timed out")
            self.logger.error(f"Run script timed out: {script_path}")
            return "Run script timed out"
        except Exception as e:
            self.error_tracker.add_error("execution", script_path, f"Unexpected error during run script execution: {e}")
            self.logger.error(f"Unexpected error during run script execution: {e}", exc_info=True)
            return f"Unexpected error during run script execution: {e}"
    
    def _find_backend_module(self, design_data: Dict) -> str:
        """Find the backend module path"""
        structure = design_data['folder_Structure']['structure']
        for item in structure:
            if item['path'].endswith('main.py'):
                path_parts = item['path'].strip('/\\').split('/')
                return '.'.join(path_parts[:-1] + ['main']) if len(path_parts) > 1 else 'main'
        return 'main'

    def find_latest_json_files(self) -> tuple[str, str]:
        """Find the latest JSON specification and design files"""
        outputs_dir = Path(self.config.outputs_dir)
        
        if not outputs_dir.exists():
            raise FileNotFoundError(f"Outputs directory '{outputs_dir}' does not exist")
        
        spec_files = list(outputs_dir.glob('*.spec.json'))
        design_files = list(outputs_dir.glob('*.design.json'))
        
        if not spec_files:
            raise FileNotFoundError("No .spec.json files found in output directory.")
        if not design_files:
            raise FileNotFoundError("No .design.json files found in output directory.")
        
        # Sort by modification time, newest first
        latest_spec = max(spec_files, key=lambda p: p.stat().st_mtime)
        latest_design = max(design_files, key=lambda p: p.stat().st_mtime)
        
        self.logger.info(f"Found latest spec file: {latest_spec}")
        self.logger.info(f"Found latest design file: {latest_design}")
        
        return str(latest_design), str(latest_spec)

def main():
    """Main function to run the coding agent"""
    try:
        config = AgentConfig.from_env()
        agent = LangChainCodingAgent(config) # Agent now initializes tools later.
        
        design_file, spec_file = agent.find_latest_json_files()
        
        with open(design_file, 'r', encoding='utf-8') as f:
            design_data = json.load(f)
        
        with open(spec_file, 'r', encoding='utf-8') as f:
            spec_data = json.load(f)
        
        result = agent.generate_project(design_data, spec_data)
        print(result)
        # Assuming project_name is available from design_data
        project_name = design_data['folder_Structure']['root_Project_Directory_Name']
        project_root_for_errors = os.path.join(config.base_output_dir, project_name)
        print(f"Check {os.path.join(project_root_for_errors, 'errors.json')} for any issues")
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Main execution failed: {e}", exc_info=True)
        print(f"Error: {e}")

if __name__ == "__main__":
    main()