import json
import os
import logging
import time
import sys
import subprocess
import argparse
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
from detect_path import define_project_root, define_python_path
import config

logger = logging.getLogger(__name__)

# Configuration for the coding agent
class AgentConfig(BaseModel):
    base_output_dir: str = Field(description="Base directory for generated code.")
    python_path: str = Field(description="Python executable path for generated run scripts.")
    model_name: str = Field(description="LLM model name for code generation.")
    api_delay_seconds: int = Field(description="Delay between API calls.")
    max_retries: int = Field(description="Maximum retry attempts for LLM calls.")
    
    @classmethod
    def from_central_config(cls) -> 'AgentConfig':
        return cls(
            base_output_dir=config.BASE_OUTPUT_DIR,
            python_path=config.PYTHON_EXECUTABLE,
            model_name=config.CURRENT_MODELS['coding'],
            api_delay_seconds=config.API_DELAY_SECONDS,
            max_retries=config.MAX_LLM_RETRIES
        )
    
    # @classmethod
    # def from_user_input(cls) -> 'AgentConfig':
    #     """Create config by prompting user for paths using detect_path functions"""
    #     print("Setting up coding agent configuration...")
        
    #     # Use detect_path functions to get user-defined paths
    #     base_output_dir = define_project_root()
    #     python_path = define_python_path()
        
    #     return cls(
    #         outputs_dir=os.getenv('OUTPUTS_DIR', 'src/module_1_vs_2/outputs'),
    #         base_output_dir=base_output_dir,
    #         python_path=python_path,
    #         model_name=os.getenv('MODEL_NAME', 'gemini-2.0-flash'),
    #         api_delay_seconds=int(os.getenv('API_DELAY_SECONDS', '5')),
    #         max_retries=int(os.getenv('MAX_RETRIES', '3')),
    #         log_level=os.getenv('LOG_LEVEL', 'DEBUG')
    #     )
    
    # def validate_paths(self) -> bool:
    #     """Validate that the configured paths exist and are accessible"""
    #     # Validate base output directory
    #     try:
    #         os.makedirs(self.base_output_dir, exist_ok=True)
    #         print(f"✓ Base output directory validated: {self.base_output_dir}")
    #     except Exception as e:
    #         print(f"✗ Error with base output directory {self.base_output_dir}: {e}")
    #         return False
        
    #     # Validate Python path
    #     try:
    #         result = subprocess.run([self.python_path, '--version'], 
    #                               capture_output=True, text=True, timeout=10)
    #         if result.returncode == 0:
    #             print(f"✓ Python executable validated: {self.python_path}")
    #             print(f"  Version: {result.stdout.strip()}")
    #         else:
    #             print(f"✗ Python executable failed: {self.python_path}")
    #             return False
    #     except Exception as e:
    #         print(f"✗ Error validating Python executable {self.python_path}: {e}")
    #         return False
        
    #     return True

# Error tracking system
class ErrorTracker:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.errors = []
        self.error_file = os.path.join(project_root, "coder_errors.json")

    def add_error(self, error_type: str, file_path: str, error_message: str, context: dict = None):
        error_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "error_type": error_type,
            "file_path": file_path,
            "error_message": error_message,
            "context": context or {}
        }
        self.errors.append(error_entry)
        self._save_errors()

    def _save_errors(self):
        os.makedirs(os.path.dirname(self.error_file), exist_ok=True)
        try:
            with open(self.error_file, 'w', encoding='utf-8') as f:
                json.dump(self.errors, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save coder errors to {self.error_file}: {e}")
            
    def get_errors(self) -> List[Dict]:
        return self.errors

# # Custom callback handler for logging
# class CodingAgentCallback(BaseCallbackHandler):
#     """Custom callback handler for the coding agent"""
    
#     def __init__(self, logger):
#         self.logger = logger
    
#     def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs):
#         self.logger.info(f"Tool started: {serialized.get('name', 'Unknown')} with input: {input_str[:100]}...")
    
#     def on_tool_end(self, output: str, **kwargs):
#         self.logger.info(f"Tool completed with output length: {len(str(output))}")
    
#     def on_tool_error(self, error: Exception, **kwargs):
#         self.logger.error(f"Tool error: {error}")

# Technology-specific code generators
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
        - Ensure the file is runnable with `python -m uvicorn {backend_module_path}:app --reload --port 8001`.
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

#Tool for generating individual files
class FileGeneratorTool(BaseTool):
    name: str = "file_generator"
    description: str = "Generates code for individual files based on specifications"
    
    def __init__(self, llm, template_manager: TechnologyTemplateManager, error_tracker: ErrorTracker, config: AgentConfig):
        super().__init__()
        self._llm = llm
        self._template_manager = template_manager
        self._error_tracker = error_tracker
        self._config = config
        
    #Generate code for a specific file with retry logic
    def _run(self, file_path: str, context: Dict, requirements: Dict) -> str:
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

#Tool for creating project structure
class ProjectStructureTool(BaseTool):
    name: str = "project_structure"
    description: str = "Creates the complete project directory structure, including all subdirectories and empty files, based on a design specification. This must be run before files can be generated."
    
    def __init__(self, error_tracker: ErrorTracker):
        super().__init__()
        self._error_tracker = error_tracker
    
    #Create project structure
    def _run(self, project_root: str, structure: List[Dict[str, str]]) -> str:
        logger.info(f"Creating project structure at: {project_root}")
        created_items = []
        try:
            os.makedirs(project_root, exist_ok=True)
            if not structure:
                raise ValueError("The 'structure' list cannot be empty.")
            for item in structure:
                path = os.path.join(project_root, item['path'].strip('/\\'))
                description = item.get('description', '').lower()
                
                # # Check if it's a directory based on description or if it ends with '/'
                # is_directory = (
                #     'directory' in description or 
                #     item['path'].rstrip('/\\').endswith('/') or
                #     item['path'].rstrip('/\\').endswith('\\') or
                #     ('file' not in description and not os.path.splitext(path)[1] and not any(
                #         special_file in os.path.basename(path).lower() 
                #         for special_file in ['.gitignore', '.env', 'dockerfile', 'makefile', 'readme']
                #     ))
                # )
                is_directory = 'directory' in description
                
                if is_directory:
                    os.makedirs(path, exist_ok=True)
                    created_items.append(f"Directory: {path}")
                    logger.debug(f"Created directory: {path}")
                else:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write("")  # Create empty file
                    created_items.append(f"File: {path}")
                    logger.debug(f"Created file: {path}")
            
            # Ensure logs directory
            logs_dir = os.path.join(project_root, 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            created_items.append(f"Directory: {logs_dir}")
            logger.debug(f"Ensured logs directory exists: {logs_dir}")
            
            result_message = f"Successfully created project structure with {len(created_items)} items in '{project_root}'"
            logger.info(result_message)
            return result_message
            
        except Exception as e:
            error_message = f"Error creating project structure: {e}"
            self._error_tracker.add_error(
                "structure_creation", project_root, str(e),
                {"structure": structure}
            )
            logger.error(error_message, exc_info=True)
            # Propagate the exception to halt the process if structure creation fails
            raise RuntimeError(error_message) from e

#Tool for validating generated project
class ProjectValidatorTool(BaseTool):
    name: str = "project_validator"
    description: str = "Validates the generated project for common issues"
    
    def __init__(self, error_tracker: ErrorTracker):
        super().__init__()
        self._error_tracker = error_tracker
    
    #Validate the generated project
    def _run(self, project_root: str, tech_stack: str) -> str:
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
    
    #Find if a file exists in the directory tree
    def _find_file(self, root_dir: str, filename: str) -> bool:
        for root, _, files in os.walk(root_dir):
            if filename in files:
                return True
        return False

# Main Coding Agent
class LangChainCodingAgent:
    def __init__(self, agent_config: AgentConfig):
        self.config = agent_config
        self.template_manager = TechnologyTemplateManager()
        self.error_tracker = None  # Initialized per-project in generate_project
        
        logger.info(f"LangChainCodingAgent initialized with model: {self.config.model_name}")
        
        self.llm = ChatGoogleGenerativeAI(
            model=self.config.model_name,
            google_api_key=config.GEMINI_API_KEY,
            temperature=0.1,
            convert_system_message_to_human=True
        )
        self.tools = []

    #Initializes tools for a specific project run.
    def _setup_project_tools(self, project_root: str):
        self.error_tracker = ErrorTracker(project_root)
        self.tools = [
            ProjectStructureTool(self.error_tracker),
            FileGeneratorTool(self.llm, self.template_manager, self.error_tracker, self.config),
            ProjectValidatorTool(self.error_tracker)
        ]
        logger.debug("Coding agent tools initialized for new project.")

    #Generates a complete project from design and specification dictionaries.
    def generate_project(self, design_data: dict, spec_data: dict) -> str:
        project_name = None
        try:
            # 1. Determine project root and initialize tools/error tracker for this run
            project_name = design_data.get('folder_Structure', {}).get('root_Project_Directory_Name')
            if not project_name:
                raise ValueError("Design data is missing 'root_Project_Directory_Name'.")
            
            project_root = os.path.abspath(os.path.join(self.config.base_output_dir, project_name))
            self._setup_project_tools(project_root)
            
            logger.info(f"Starting project generation for: {project_name} at {project_root}")
            
            # 2. Validate JSON inputs
            self._validate_json(design_data, spec_data)
            logger.info("JSON inputs validated successfully.")

            # 3. Create project structure
            structure_result = self._create_project_structure(design_data, project_root)
            logger.info(f"Structure creation result: {structure_result}")
            
            # 4. Generate all project files
            files_result = self._generate_project_files(design_data, spec_data, project_root)
            logger.info(f"File generation result: {files_result}")
            
            # 5. Create the run script to start the application
            self._create_run_script(project_root, spec_data, design_data)
            logger.info(f"Created run script for project '{project_name}'.")
            
            logger.info(f"Project generation completed successfully for: {project_root}")
            
            # This success message is what the AutoGen Coder will report back to the ProjectManager.
            return f"Successfully generated project '{project_name}' at {project_root}. The 'run.bat' script is ready."

        except Exception as e:
            error_project_name = project_name or "unknown_project"
            logger.error(f"Project generation failed for '{error_project_name}': {e}", exc_info=True)
            if self.error_tracker:
                self.error_tracker.add_error("project_generation_fatal", error_project_name, str(e))
            # Re-raise the exception so the orchestrator (AutoGen) knows something went wrong.
            raise

    # --- Helper Methods ---
    # Validate JSON design and specification files
    def _validate_json(self, design_data: dict, spec_data: dict):
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
    
    def _create_project_structure(self, design_data: dict, project_root: str) -> str:
        """Wrapper for ProjectStructureTool"""
        structure_tool = next(t for t in self.tools if isinstance(t, ProjectStructureTool))
        return structure_tool._run(
            project_root,
            design_data['folder_Structure']['structure']
        )
    
    # Wrapper for FileGeneratorTool actions
    def _generate_project_files(self, design_data: dict, spec_data: dict, project_root: str) -> str:
        structure = design_data['folder_Structure']['structure']
        context_for_generation = self._build_context(design_data, spec_data, project_root)
        
        file_generator = next(t for t in self.tools if isinstance(t, FileGeneratorTool))
        generated_files = []
        
        for item in structure:
            if 'directory' not in item.get('description', '').lower():
                # Validate and sanitize the path to prevent directory traversal
                item_path = item['path'].strip('/\\')
                if '..' in item_path or item_path.startswith('/') or item_path.startswith('\\'):
                    logger.warning(f"Skipping potentially unsafe path: {item_path}")
                    continue
                
                file_path = os.path.join(project_root, item_path)
                
                # Ensure the directory exists before creating the file
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                file_context = context_for_generation.copy()
                file_context['file_info'] = item
                
                code = file_generator._run(file_path, file_context, spec_data)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                generated_files.append(file_path)
                
        return f"Generated {len(generated_files)} files"
    
    def _build_context(self, design_data: dict, spec_data: dict, project_root: str) -> dict:
        """Build a comprehensive context dictionary for prompt generation"""
        backend_module_path = 'main'
        frontend_dir_rel = 'frontend'
        css_path_rel_to_frontend = 'style.css'
        js_files_to_link_rel_to_frontend = []
        
        for item in design_data['folder_Structure']['structure']:
            relative_item_path = item['path'].strip('/\\').replace('\\', '/')
            if relative_item_path.endswith('main.py'):
                parts = relative_item_path.split('/')
                backend_module_path = '.'.join(parts[:-1] + ['main']) if len(parts) > 1 else 'main'
            elif relative_item_path.endswith('index.html'):
                frontend_dir_rel = os.path.dirname(relative_item_path) or 'frontend'
            elif relative_item_path.endswith('.css'):
                if relative_item_path.startswith(frontend_dir_rel):
                    css_path_rel_to_frontend = os.path.relpath(relative_item_path, frontend_dir_rel).replace('\\', '/')
                else:
                    css_path_rel_to_frontend = relative_item_path
            elif relative_item_path.endswith('.js') and 'directory' not in item.get('description', '').lower():
                if relative_item_path.startswith(frontend_dir_rel):
                    js_files_to_link_rel_to_frontend.append(os.path.relpath(relative_item_path, frontend_dir_rel).replace('\\', '/'))
                else:
                    js_files_to_link_rel_to_frontend.append(relative_item_path)

        return {
            'tech_stack': spec_data.get('technology_Stack', {}).get('backend', {}).get('framework', 'fastapi'),
            'project_root': project_root,
            'design_data': design_data,
            'backend_module_path': backend_module_path,
            'frontend_dir': frontend_dir_rel,
            'css_path': css_path_rel_to_frontend,
            'js_files_to_link': sorted(list(set(js_files_to_link_rel_to_frontend)))
        }
    
    def _create_run_script(self, project_root: str, spec_data: dict, design_data: dict):
        """Create the run script for the project"""
        tech_stack = spec_data.get('technology_Stack', {}).get('backend', {}).get('framework', 'fastapi')
        backend_module_path = self._find_backend_module(design_data)
        
        script_content = self.template_manager.get_template(
            tech_stack, 'run_script',
            python_path=self.config.python_path,
            backend_module_path=backend_module_path
        )
        
        script_path = os.path.join(project_root, 'run.bat')
        with open(script_path, 'w', encoding='utf-8', newline='\r\n') as f: # Ensure Windows line endings
            f.write(script_content)

    def _find_backend_module(self, design_data: dict) -> str:
        """Find the backend module path from the design structure"""
        structure = design_data['folder_Structure']['structure']
        for item in structure:
            if 'main.py' in item['path']:
                path_parts = item['path'].strip('/\\').replace('\\', '/').split('/')
                # e.g., 'backend/app/main.py' -> 'backend.app.main'
                # Remove the '.py' extension from the last part
                if path_parts[-1].endswith('.py'):
                    path_parts[-1] = path_parts[-1][:-3]  # Remove '.py'
                return '.'.join(path_parts)
        # Fallback if not found
        return 'main'

#     def find_latest_json_files(self) -> tuple[str, str]:
#         """Find the latest JSON specification and design files"""
#         outputs_dir = Path(self.config.outputs_dir)
        
#         if not outputs_dir.exists():
#             raise FileNotFoundError(f"Outputs directory '{outputs_dir}' does not exist")
        
#         spec_files = list(outputs_dir.glob('*.spec.json'))
#         design_files = list(outputs_dir.glob('*.design.json'))
        
#         if not spec_files:
#             raise FileNotFoundError("No .spec.json files found in output directory.")
#         if not design_files:
#             raise FileNotFoundError("No .design.json files found in output directory.")
        
#         # Sort by modification time, newest first
#         latest_spec = max(spec_files, key=lambda p: p.stat().st_mtime)
#         latest_design = max(design_files, key=lambda p: p.stat().st_mtime)
        
#         self.logger.info(f"Found latest spec file: {latest_spec}")
#         self.logger.info(f"Found latest design file: {latest_design}")
        
#         return str(latest_design), str(latest_spec)

# def setup_agent_with_path_detection() -> LangChainCodingAgent:
#     """Convenience function to set up agent with interactive path detection"""
#     print("=== Setting up Coding Agent with Path Detection ===")
    
#     config = AgentConfig.from_user_input()
    
#     if not config.validate_paths():
#         raise ValueError("Path validation failed. Please check your configuration.")
    
#     agent = LangChainCodingAgent(config)
#     print("Agent setup complete!")
#     return agent

# def setup_agent_with_env_fallback() -> LangChainCodingAgent:
#     """Setup agent with environment variables, with fallback to path detection if validation fails"""
#     print("=== Setting up Coding Agent (Environment + Fallback) ===")
    
#     config = AgentConfig.from_env()
    
#     if not config.validate_paths():
#         print("Environment configuration validation failed. Switching to interactive setup...")
#         config = AgentConfig.from_user_input()
        
#         if not config.validate_paths():
#             raise ValueError("Path validation failed after interactive setup.")
    
#     agent = LangChainCodingAgent(config)
#     print("Agent setup complete!")
#     return agent

# def demo_path_integration():
#     """Demonstration of how the path detection functions are integrated"""
#     print("=== Path Integration Demo ===")
    
#     print("\n1. Environment Variables Method:")
#     print("   - Uses os.getenv() for configuration")
#     print("   - Falls back to defaults if env vars not set")
    
#     print("\n2. Interactive Setup Method:")
#     print("   - Uses define_project_root() to get output directory")
#     print("   - Uses define_python_path() to get Python executable")
#     print("   - Persists choices to .env file for future runs")
    
#     print("\n3. Validation:")
#     print("   - Checks if paths exist and are accessible")
#     print("   - Validates Python executable by running --version")
    
#     print("\n4. Runtime Reconfiguration:")
#     print("   - Allows changing paths during execution")
#     print("   - Uses the same detect_path functions")
    
#     print("\nAvailable setup functions:")
#     print("   - AgentConfig.from_env() - Environment variables")
#     print("   - AgentConfig.from_user_input() - Interactive with detect_path")
#     print("   - setup_agent_with_path_detection() - Convenience function")
#     print("   - setup_agent_with_env_fallback() - Env with fallback")
    
#     print("\nAgent methods:")
#     print("   - agent.reconfigure_paths() - Runtime reconfiguration")
#     print("   - agent.get_current_config() - View current settings")

# def parse_arguments():
#     """Parse command line arguments for input file selection"""
#     parser = argparse.ArgumentParser(
#         description="LangChain Coding Agent - Generate code projects from JSON specifications",
#         formatter_class=argparse.RawDescriptionHelpFormatter,
#         epilog=""":
# Examples:
#   # Use latest files from outputs directory (default behavior)
#   python coding_agent_langchain.py
  
#   # Specify specific design and spec files
#   python coding_agent_langchain.py --design design.json --spec spec.json
  
#   # Specify only design file (will find matching spec file)
#   python coding_agent_langchain.py --design myproject_20250625.design.json
#         """
#     )
    
#     # File selection arguments
#     parser.add_argument(
#         "--design", "-d",
#         type=str,
#         help="Path to the design JSON file (.design.json). Can be absolute or relative to outputs directory."
#     )
    
#     parser.add_argument(
#         "--spec", "-s", 
#         type=str,
#         help="Path to the specification JSON file (.spec.json). Can be absolute or relative to outputs directory."
#     )
    
#     # Configuration method arguments
#     parser.add_argument(
#         "--interactive", "-i",
#         action="store_true",
#         help="Use interactive path detection setup instead of environment variables"
#     )
    
#     parser.add_argument(
#         "--outputs-dir", "-o",
#         type=str,
#         help="Override the outputs directory path (default: src/module_1_vs_2/outputs)"
#     )
    
#     parser.add_argument(
#         "--verbose", "-v",
#         action="store_true",
#         help="Enable verbose output and debug logging"
#     )
    
#     return parser.parse_args()

# def find_json_files_from_args(args, config: AgentConfig) -> tuple[str, str]:
#     """Find JSON files based on command line arguments"""
#     outputs_dir = Path(args.outputs_dir if args.outputs_dir else config.outputs_dir)
    
#     if not outputs_dir.exists():
#         raise FileNotFoundError(f"Outputs directory '{outputs_dir}' does not exist")
    
#     design_file = None
#     spec_file = None
    
#     # Handle design file argument
#     if args.design:
#         design_path = Path(args.design)
#         if design_path.is_absolute() and design_path.exists():
#             design_file = str(design_path)
#         else:
#             # Try relative to outputs directory
#             design_path = outputs_dir / args.design
#             if design_path.exists():
#                 design_file = str(design_path)
#             else:
#                 raise FileNotFoundError(f"Design file not found: {args.design}")
    
#     # Handle spec file argument
#     if args.spec:
#         spec_path = Path(args.spec)
#         if spec_path.is_absolute() and spec_path.exists():
#             spec_file = str(spec_path)
#         else:
#             # Try relative to outputs directory
#             spec_path = outputs_dir / args.spec
#             if spec_path.exists():
#                 spec_file = str(spec_path)
#             else:
#                 raise FileNotFoundError(f"Spec file not found: {args.spec}")
    
#     # If only one file is specified, try to find the matching pair
#     if design_file and not spec_file:
#         # Extract base name and look for matching spec file
#         design_path = Path(design_file)
#         base_name = design_path.stem.replace('.design', '')
        
#         # Look for matching spec file
#         possible_spec_files = [
#             outputs_dir / f"{base_name}.spec.json",
#             design_path.parent / f"{base_name}.spec.json"
#         ]
        
#         for possible_spec in possible_spec_files:
#             if possible_spec.exists():
#                 spec_file = str(possible_spec)
#                 break
        
#         if not spec_file:
#             raise FileNotFoundError(f"Could not find matching spec file for design file: {design_file}")
    
#     elif spec_file and not design_file:
#         # Extract base name and look for matching design file
#         spec_path = Path(spec_file)
#         base_name = spec_path.stem.replace('.spec', '')
        
#         # Look for matching design file
#         possible_design_files = [
#             outputs_dir / f"{base_name}.design.json",
#             spec_path.parent / f"{base_name}.design.json"
#         ]
        
#         for possible_design in possible_design_files:
#             if possible_design.exists():
#                 design_file = str(possible_design)
#                 break
        
#         if not design_file:
#             raise FileNotFoundError(f"Could not find matching design file for spec file: {spec_file}")
    
#     # If neither file is specified, use the latest files (existing behavior)
#     if not design_file and not spec_file:
#         spec_files = list(outputs_dir.glob('*.spec.json'))
#         design_files = list(outputs_dir.glob('*.design.json'))
        
#         if not spec_files:
#             raise FileNotFoundError("No .spec.json files found in output directory.")
#         if not design_files:
#             raise FileNotFoundError("No .design.json files found in output directory.")
        
#         # Sort by modification time, newest first
#         latest_spec = max(spec_files, key=lambda p: p.stat().st_mtime)
#         latest_design = max(design_files, key=lambda p: p.stat().st_mtime)
        
#         design_file = str(latest_design)
#         spec_file = str(latest_spec)
    
#     # Validate that both files exist and are readable
#     for file_path, file_type in [(design_file, "design"), (spec_file, "spec")]:
#         if not os.path.exists(file_path):
#             raise FileNotFoundError(f"{file_type.capitalize()} file not found: {file_path}")
        
#         try:
#             with open(file_path, 'r', encoding='utf-8') as f:
#                 json.load(f)
#         except json.JSONDecodeError as e:
#             raise ValueError(f"Invalid JSON in {file_type} file {file_path}: {e}")
#         except Exception as e:
#             raise ValueError(f"Cannot read {file_type} file {file_path}: {e}")
    
#     return design_file, spec_file

# def main():
#     """Main function to run the coding agent"""
#     try:
#         print("=== LangChain Coding Agent ===")
        
#         # Parse command line arguments
#         args = parse_arguments()
        
#         # Set log level based on verbose flag
#         if args.verbose:
#             os.environ["LOG_LEVEL"] = "DEBUG"
#         else:
#             os.environ["LOG_LEVEL"] = "INFO"
        
#         # Override outputs directory if specified
#         if args.outputs_dir:
#             os.environ["OUTPUTS_DIR"] = args.outputs_dir
        
#         # Determine configuration method
#         if args.interactive:
#             print("\n--- Interactive Setup (from command line flag) ---")
#             config = AgentConfig.from_user_input()
#         else:
#             # Check if we need to ask for configuration method (if no specific files given)
#             if not args.design and not args.spec:
#                 print("Choose configuration method:")
#                 print("1. Use environment variables (default)")
#                 print("2. Interactive setup with path detection")
#                 print("3. Use environment variables, then allow reconfiguration")
                
#                 try:
#                     choice = input("Enter choice (1, 2, or 3) [Default: 1]: ").strip()
#                 except EOFError:
#                     choice = "1"
                
#                 if choice == "2":
#                     print("\n--- Interactive Setup ---")
#                     config = AgentConfig.from_user_input()
#                 elif choice == "3":
#                     print("\n--- Using Environment Variables (with reconfiguration option) ---")
#                     config = AgentConfig.from_env()
#                 else:
#                     print("\n--- Using Environment Variables ---")
#                     config = AgentConfig.from_env()
#             else:
#                 # Files specified via command line, use environment config
#                 print("\n--- Using Environment Variables (files specified via command line) ---")
#                 config = AgentConfig.from_env()
        
#         print("\n--- Validating Configuration ---")
#         if not config.validate_paths():
#             print("Configuration validation failed.")
#             if not args.interactive and not args.design and not args.spec:
#                 print("Would you like to reconfigure paths? (y/n): ", end="")
#                 try:
#                     reconfigure = input().strip().lower()
#                     if reconfigure in ['y', 'yes']:
#                         # Create a temporary agent to use reconfigure method
#                         temp_agent = LangChainCodingAgent(config)
#                         if temp_agent.reconfigure_paths():
#                             config = temp_agent.config
#                         else:
#                             print("Reconfiguration failed. Exiting.")
#                             return
#                     else:
#                         print("Exiting due to configuration validation failure.")
#                         return
#                 except EOFError:
#                     print("Exiting due to configuration validation failure.")
#                     return
#             else:
#                 print("Please check your paths and try again.")
#                 return
        
#         print("\n--- Final Configuration ---")
#         for key, value in config.__dict__.items():
#             print(f"  {key}: {value}")
        
#         print("\n--- Initializing Agent ---")
#         agent = LangChainCodingAgent(config)
        
#         # Find JSON files based on arguments or fallback to latest
#         print("\n--- Finding JSON Files ---")
#         design_file, spec_file = find_json_files_from_args(args, config)
#         print(f"Using design file: {design_file}")
#         print(f"Using spec file: {spec_file}")
        
#         print("\n--- Loading JSON Data ---")
#         with open(design_file, 'r', encoding='utf-8') as f:
#             design_data = json.load(f)
        
#         with open(spec_file, 'r', encoding='utf-8') as f:
#             spec_data = json.load(f)
        
#         print("\n--- Generating Project ---")
#         result = agent.generate_project(design_data, spec_data)
#         print(result)
        
#         # Display results
#         project_name = design_data['folder_Structure']['root_Project_Directory_Name']
#         project_root_for_errors = os.path.join(config.base_output_dir, project_name)
        
#         print(f"\n--- Project Generation Complete ---")
#         print(f"Project location: {project_root_for_errors}")
#         print(f"Check {os.path.join(project_root_for_errors, 'errors.json')} for any issues")
#         print(f"Python path used: {config.python_path}")
#         print(f"Base output directory: {config.base_output_dir}")
        
#     except Exception as e:
#         logging.getLogger(__name__).error(f"Main execution failed: {e}", exc_info=True)
#         print(f"Error: {e}")
#         print("Check the log file for detailed error information.")

# if __name__ == "__main__":
#     main()