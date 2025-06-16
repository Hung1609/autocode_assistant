# import json
# import os
# import logging
# import time
# import ast
# from datetime import datetime
# from typing import Dict, List, Optional, Any, Type
# from pathlib import Path
# from langchain_core.tools import BaseTool
# from langchain_core.messages import HumanMessage
# from langchain_core.callbacks.base import BaseCallbackHandler
# from pydantic import BaseModel, Field
# from dotenv import load_dotenv

# load_dotenv()

# # Configuration class for Windows
# class AgentConfig(BaseModel):
#     """Configuration for the coding agent"""
#     outputs_dir: str = Field(default="src/module_1_vs_2/outputs", description="Directory containing JSON files")
#     base_output_dir: str = Field(default="code_generated_result", description="Base directory for generated code")
#     python_path: str = Field(default="python", description="Python executable path")
#     model_name: str = Field(default="gemini-2.0-flash", description="LLM model name")
#     api_delay_seconds: int = Field(default=2, description="Delay between API calls")
#     max_retries: int = Field(default=3, description="Maximum retry attempts for LLM calls")
#     log_level: str = Field(default="DEBUG", description="Logging level")

#     @classmethod
#     def from_env(cls) -> 'AgentConfig':
#         """Create config from environment variables"""
#         return cls(
#             outputs_dir=os.getenv('OUTPUTS_DIR', 'src/module_1_vs_2/outputs'),
#             base_output_dir=os.getenv('BASE_OUTPUT_DIR', 'code_generated_result'),
#             python_path=os.getenv('PYTHON_PATH', 'python'),
#             model_name=os.getenv('MODEL_NAME', 'gemini-2.0-flash'),
#             api_delay_seconds=int(os.getenv('API_DELAY_SECONDS', '2')),
#             max_retries=int(os.getenv('MAX_RETRIES', '3')),
#             log_level=os.getenv('LOG_LEVEL', 'DEBUG')
#         )

# # Error tracking system
# class ErrorTracker:
#     """Tracks and stores errors for debugging agent"""
    
#     def __init__(self, project_root: str):
#         self.project_root = project_root
#         self.errors = []
#         self.error_file = os.path.join(project_root, "errors.json")
    
#     def add_error(self, error_type: str, file_path: str, error_message: str, context: Optional[Dict] = None):
#         """Add an error to the tracking system"""
#         error_entry = {
#             "timestamp": datetime.now().isoformat(),
#             "error_type": error_type,
#             "file_path": file_path,
#             "error_message": error_message,
#             "context": context or {}
#         }
#         self.errors.append(error_entry)
#         self._save_errors()
    
#     def _save_errors(self):
#         """Save errors to file"""
#         os.makedirs(os.path.dirname(self.error_file), exist_ok=True)
#         try:
#             with open(self.error_file, 'w', encoding='utf-8') as f:
#                 json.dump(self.errors, f, indent=2)
#         except Exception as e:
#             logging.error(f"Failed to save errors to {self.error_file}: {e}")

#     def get_errors(self) -> List[Dict]:
#         """Get all tracked errors"""
#         return self.errors

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

# # Technology-specific code generators
# class TechnologyTemplateManager:
#     """Manages templates for different technology stacks"""
    
#     def __init__(self):
#         self.templates = {
#             "fastapi": {
#                 "run_script": self._fastapi_run_script,
#                 "requirements": self._fastapi_requirements,
#                 "env_file": self._fastapi_env,
#                 "prompt_template": self._fastapi_prompt_template
#             },
#             "nodejs": {
#                 "run_script": self._nodejs_run_script,
#                 "requirements": self._nodejs_requirements,
#                 "env_file": self._nodejs_env,
#                 "prompt_template": self._nodejs_prompt_template            }
#         }
    
#     def get_template(self, tech_stack: str, template_type: str, **kwargs):
#         """Get template for specific technology and type"""
#         tech_templates = self.templates.get(tech_stack.lower(), self.templates["fastapi"])
#         return tech_templates.get(template_type, lambda **k: "")(**kwargs)
    
#     def _fastapi_run_script(self, **kwargs):
#         python_path = kwargs.get('python_path', 'python')
#         backend_module = kwargs.get('backend_module_path', 'main')
#         return f"""@echo off
# setlocal EnableDelayedExpansion

# :: Define the log file path explicitly - THIS MUST BE THE VERY FIRST COMMAND THAT USES THE VARIABLE
# set "LOG_FILE=debug_code_agent.log"
# set "PROJECT_ROOT=%~dp0"

# :: Initial log entries. Use > to create/overwrite, then >> to append.
# echo --- run.bat STARTING --- > "%LOG_FILE%"
# echo Timestamp: %DATE% %TIME% >> "%LOG_FILE%"
# echo Current Directory (at start): "%CD%" >> "%LOG_FILE%"
# echo PROJECT_ROOT (calculated): "%PROJECT_ROOT%" >> "%LOG_FILE%"
# echo PYTHON_PATH from config: "{python_path}" >> "%LOG_FILE%"

# :: Change to project root
# echo Changing directory to project root... >> "%LOG_FILE%"
# cd /d "%PROJECT_ROOT%" 1>>"%LOG_FILE%" 2>>&1
# if %ERRORLEVEL% neq 0 (
#     echo ERROR: Failed to change to project root directory. ErrorLevel: %ERRORLEVEL%. >> "%LOG_FILE%"
#     echo ERROR: Failed to change to project root directory. Check "%LOG_FILE%".
#     pause
#     exit /b 1
# )
# echo Current Directory (after cd): "%CD%" >> "%LOG_FILE%"

# :: Check for Python (using the system Python path from PYTHON_PATH)
# echo Checking for Python at "{python_path}"... >> "%LOG_FILE%"
# "{python_path}" --version 1>>"%LOG_FILE%" 2>>&1
# set PYTHON_CHECK_ERRORLEVEL=!ERRORLEVEL!
# if !PYTHON_CHECK_ERRORLEVEL! neq 0 (
#     echo ERROR: Python not found or failed to execute at "{python_path}". ErrorLevel: !PYTHON_CHECK_ERRORLEVEL!. >> "%LOG_FILE%"
#     echo ERROR: Python not found at "{python_path}". Check "%LOG_FILE%".
#     pause
#     exit /b !PYTHON_CHECK_ERRORLEVEL!
# )
# echo Python found at "{python_path}". >> "%LOG_FILE%"

# :: Create virtual environment
# echo Creating virtual environment in "%PROJECT_ROOT%\\venv"... >> "%LOG_FILE%"
# if not exist "%PROJECT_ROOT%\\venv" (
#     "{python_path}" -m venv "%PROJECT_ROOT%\\venv" 1>>"%LOG_FILE%" 2>>&1
#     set VENV_CREATE_ERRORLEVEL=!ERRORLEVEL!
#     if !VENV_CREATE_ERRORLEVEL! neq 0 (
#         echo ERROR: Failed to create virtual environment. ErrorLevel: !VENV_CREATE_ERRORLEVEL!. >> "%LOG_FILE%"
#         echo ERROR: Failed to create virtual environment. Check "%LOG_FILE%".
#         pause
#         exit /b !VENV_CREATE_ERRORLEVEL!
#     )
# ) else (
#     echo Virtual environment already exists. Skipping creation. >> "%LOG_FILE%"
# )
# echo Virtual environment creation check complete. >> "%LOG_FILE%"

# :: Activate virtual environment
# echo Activating virtual environment... >> "%LOG_FILE%"
# call "%PROJECT_ROOT%\\venv\\Scripts\\activate.bat" 1>>"%LOG_FILE%" 2>>&1
# set VENV_ACTIVATE_ERRORLEVEL=!ERRORLEVEL!
# if !VENV_ACTIVATE_ERRORLEVEL! neq 0 (
#     echo ERROR: Failed to activate virtual environment. ErrorLevel: !VENV_ACTIVATE_ERRORLEVEL!. Check if venv\\Scripts\\activate.bat exists and is not corrupted. >> "%LOG_FILE%"
#     echo ERROR: Failed to activate virtual environment. Check "%LOG_FILE%".
#     pause
#     exit /b !VENV_ACTIVATE_ERRORLEVEL!
# )
# echo Virtual environment activated. >> "%LOG_FILE%"

# :: Verify python path after activation (Crucial for debugging)
# echo Verifying python path after venv activation: >> "%LOG_FILE%"
# where python 1>>"%LOG_FILE%" 2>>&1
# if %ERRORLEVEL% neq 0 (
#     echo WARNING: python.exe not found in PATH after venv activation. This indicates activate.bat failed or PATH not updated. >> "%LOG_FILE%"
# )
# echo Verifying pip path after venv activation: >> "%LOG_FILE%"
# where pip 1>>"%LOG_FILE%" 2>>&1
# if %ERRORLEVEL% neq 0 (
#     echo WARNING: pip.exe not found in PATH after venv activation. This indicates activate.bat failed or PATH not updated. >> "%LOG_FILE%"
# )

# :: Install dependencies
# echo Installing dependencies... >> "%LOG_FILE%"
# if exist "requirements.txt" (
#     pip install -r requirements.txt 1>>"%LOG_FILE%" 2>>&1
#     set PIP_INSTALL_ERRORLEVEL=!ERRORLEVEL!
#     if !PIP_INSTALL_ERRORLEVEL! neq 0 (
#         echo ERROR: Failed to install dependencies. ErrorLevel: !PIP_INSTALL_ERRORLEVEL!. Check requirements.txt. >> "%LOG_FILE%"
#         echo ERROR: Failed to install dependencies. Check "%LOG_FILE%".
#         pause
#         exit /b !PIP_INSTALL_ERRORLEVEL!
#     )
# ) else (
#     echo WARNING: requirements.txt not found. Skipping dependency installation. >> "%LOG_FILE%"
# )
# echo Dependencies installation check complete. >> "%LOG_FILE%"

# :: Run the application
# echo Starting the application with uvicorn... >> "%LOG_FILE%"
# python -m uvicorn {backend_module}:app --reload --port 8001 1>>"%LOG_FILE%" 2>>&1
# set UVICORN_RUN_ERRORLEVEL=!ERRORLEVEL!
# if !UVICORN_RUN_ERRORLEVEL! neq 0 (
#     echo ERROR: Failed to start the application. ErrorLevel: !UVICORN_RUN_ERRORLEVEL!. Check {backend_module.replace('.', '/')}.py and uvicorn configuration. >> "%LOG_FILE%"
#     echo ERROR: Failed to start the application. Check "%LOG_FILE%".
#     pause
#     exit /b !UVICORN_RUN_ERRORLEVEL!
# )
# echo Application started. >> "%LOG_FILE%"

# echo --- run.bat FINISHED SUCCESSFULLY --- >> "%LOG_FILE%"
# pause
# exit /b 0
# """
    
#     def _fastapi_requirements(self, **kwargs):
#         dependencies = kwargs.get('dependencies', [])
#         base_deps = ['fastapi[all]', 'uvicorn[standard]', 'sqlalchemy', 'pydantic']
#         all_deps = list(set(dependencies + base_deps))
#         return '\n'.join(all_deps) + '\n'
    
#     def _fastapi_env(self, **kwargs):
#         storage_type = kwargs.get('storage_type', 'sqlite')
#         return f"DATABASE_URL={storage_type}:///app.db\nSECRET_KEY=your-secret-key-here\n"
    
#     def _fastapi_prompt_template(self, **kwargs):
#         file_path = kwargs.get('file_path', '')
#         project_name = kwargs.get('project_name', 'this application')
#         backend_language_framework = kwargs.get('backend_language_framework', 'FastAPI')
#         frontend_language_framework = kwargs.get('frontend_language_framework', 'Vanilla HTML/CSS/JS')
#         storage_type = kwargs.get('storage_type', 'sqlite')
#         backend_module_path = kwargs.get('backend_module_path', 'main')
#         frontend_dir = kwargs.get('frontend_dir', 'frontend')
#         css_path = kwargs.get('css_path', 'css/style.css')
#         js_files = kwargs.get('js_files_to_link', [])
#         json_design = kwargs.get('json_design', {})
#         json_spec = kwargs.get('json_spec', {})
        
#         js_links_for_prompt = "\n".join([f"- /{js_file}" for js_file in js_files]) or "No JavaScript files detected."
        
#         return f"""
# CONTEXT:
# - You are an expert Senior Software Engineer tasked with generating complete, syntactically correct code for a web application named {project_name}. The application uses:
#     - Backend: {backend_language_framework}
#     - Frontend: {frontend_language_framework}
#     - Storage: {storage_type}
# - Your goal is to produce code for a specific file based on:
#     - JSON Design: Technical implementation details (architecture, data models, APIs).
#     - JSON Specification: Functional and non-functional requirements.
#     - Additional rules for logging, FastAPI static file serving, and CORS configuration.
# - The generated code must be executable, idiomatic, and aligned with the provided design and requirements.

# TARGET FILE INFORMATION:
# - Full Path of the File to Generate: {file_path}
# - Project Structure: This file is part of the project structure defined in the `folder_Structure` section of the JSON Design. The `folder_Structure.root_Project_Directory_Name` indicates the main project folder, and `folder_Structure.structure` lists all files and directories relative to that root.
# - Backend Module Path: {backend_module_path}
# - Frontend Directory: {frontend_dir}
# - CSS File Path: Relative to frontend directory, {css_path}
# - JS Files: List of JavaScript files relative to frontend directory:
# {js_links_for_prompt}

# INTERNAL THOUGHT PROCESS:
# 1. Analyze File Role:
#    - Identify the file's purpose based on `{file_path}` and `json_design.folder_Structure`.
#    - If the file is `{backend_module_path.replace('.', '/')}.py`, it's the main backend entry point; include FastAPI initialization, StaticFiles mounting, logging, and CORS setup.
#    - If the file is a Python module (e.g., `backend/routes.py`), include function-level logging.
#    - If the file is `{frontend_dir}/index.html`, reference CSS and JS files using `{css_path}` and all files in `JS Files` section.
# 2. Identify Key Requirements (from JSON Specification):
#    - Determine which Functional Requirements (FRs) this file must help implement.
#    - Determine which Non-Functional Requirements (NFRs, e.g., Security, Performance, Usability) this file must adhere to.
# 3. Map to Design (from JSON Design):
#    - Implement API endpoints from `interface_Design.api_Specifications`.
#    - Use or define data models from `data_Design.data_Models` for CRUD operations.
#    - Follow workflows from `workflow_Interaction`.
# 4. Plan Implementation:
#    - Outline the high-level structure of the code (Classes, Functions, Imports).
#    - Use FastAPI conventions, Python logging, and StaticFiles for frontend serving.
#    - Incorporate dependencies from `json_design.dependencies`.
# 5. Determine Entry Point Requirements:
#    - For the main backend file `{backend_module_path.replace('.', '/')}.py`, include FastAPI app initialization, StaticFiles mounting, and CORS setup.
#    - Ensure the file is executable via `python -m uvicorn {backend_module_path}:app --reload --port 8001`.
#    - For other executable files, include language-specific entry points (e.g., `if __name__ == "__main__":` for Python).

# CODE GENERATION RULES:
# 1. Output Format:
#    - Generate only the raw code for the file.
#    - Do NOT include explanations, comments outside the code, or markdown formatting.
# 2. Python Imports (Python files only):
#    - Place all `import` statements at the top, before any executable code.
# 3. Advanced Logging (Python files only):
#    - For Main Backend File `{backend_module_path.replace('.', '/')}.py`:
#      - Import `logging`, `logging.handlers`, `json`.
#      - Define a custom JSON formatter to convert `logging.LogRecord` attributes into JSON string, including `timestamp` (from `asctime`), `level` (from `levelname`), `logger_name` (from `name`), `message`, `pathname`, `funcName`, `lineno`, with proper `exc_info` formatting for exceptions.
#      - Configure a `RotatingFileHandler` to write to `logs/app.log` with `maxBytes=10MB` and `backupCount=5`, using the JSON formatter.
#      - Configure a `StreamHandler` for console output with format `%(asctime)s - %(levelname)s - %(name)s - %(message)s`.
#      - Set up the root logger with `logging.basicConfig(level=logging.DEBUG)` and register both handlers.
#    - For Other Python Files:
#      - Import logging and initialize logger: `logger = logging.getLogger(__name__)`.
#      - Log function entry: `logger.info("Entering <function_name> with args: <args>, kwargs: <kwargs>")`.
#      - Log function exit: `logger.info("Exiting <function_name> with result: <result>")` (if applicable).
#      - Log errors: `logger.error("Error in <function_name>: <dynamic_error_message>", exc_info=True)`.
#      - For FastAPI routes, log incoming requests and responses.
#    - For Non-Python Files: Do not add logging.
# 4. FastAPI CORS Configuration (only in `{backend_module_path.replace('.', '/')}.py`):
#    - Configure `fastapi.middleware.cors.CORSMiddleware` after app initialization and logging.
#    - Example:
#      ```python
#      from fastapi import FastAPI
#      from fastapi.middleware.cors import CORSMiddleware
#      app = FastAPI()
#      app.add_middleware(
#          CORSMiddleware,
#          allow_origins=["http://localhost", "http://localhost:8000"],
#          allow_credentials=True,
#          allow_methods=["*"],
#          allow_headers=["*"],
#      )
#      ```
# 5. FastAPI StaticFiles (only in `{backend_module_path.replace('.', '/')}.py`):
#    - Mount the frontend directory at `/`:
#      ```python
#      from fastapi.staticfiles import StaticFiles
#      app.mount("/", StaticFiles(directory="{frontend_dir}", html=True), name="static")
#      ```
#    - Place this at the end of the file, after all imports, middleware, logging, and routes.
#    - Ensure the app is runnable with `python -m uvicorn {backend_module_path}:app --reload --port 8001`.
# 6. Frontend File Paths (HTML files only):
#    - In `{frontend_dir}/index.html`, reference CSS: `<link rel="stylesheet" href="/{css_path}">`.
#    - For each JS file, add: `<script src="/{{js_file}}"></script>`.
#    - Example for multiple JS files:
#      ```html
#      <script src="/script.js"></script>
#      <script src="/utils.js"></script>
#      ```
# 7. Technology-Specific Conventions:
#    - Python/FastAPI:
#      - Use Pydantic for data validation, ensuring required fields are handled.
#      - For SQLAlchemy models, define primary keys (e.g., `id`) with `primary_key=True` and exclude from instantiation.
#      - Follow FastAPI conventions for routes and dependencies.
#    - Frontend (HTML/CSS/JS):
#      - Ensure compatibility with FastAPI's StaticFiles.
#      - Use vanilla JavaScript unless specified otherwise.
# 8. Completeness:
#    - Include all necessary imports, classes, functions, and logic.
#    - For frontend files, provide complete HTML structure with basic styling.
# 9. JSON Design and Specification:
#    - Design: {json.dumps(json_design, indent=2)}
#    - Specification: {json.dumps(json_spec, indent=2)}
# 10. Entry Points:
#     - Automatically detect if `{file_path}` is an entry point.
#     - Include `if __name__ == "__main__":` for Python entry points.

# TASK:
# Generate the complete code for `{file_path}`, ensuring:
# - Compliance with FastAPI conventions, logging, CORS, and StaticFiles (if applicable).
# - Alignment with `json_design` and `json_spec`.
# - Inclusion of language-specific entry points for executable files.
# - Readiness to run with `python -m uvicorn {backend_module_path}:app --reload --port 8001` for `{backend_module_path.replace('.', '/')}.py`.
# """

#     def _nodejs_run_script(self, **kwargs):
#         return f"""@echo off
# setlocal EnableDelayedExpansion

# :: Setup and run the Node.js application
# echo Setting up and running the application... > debug_code_agent.log 2>&1

# :: Set project root
# set "PROJECT_ROOT=%~dp0"
# cd /d "%PROJECT_ROOT%" >> debug_code_agent.log 2>&1
# if %ERRORLEVEL% neq 0 (
#     echo ERROR: Failed to change to project root directory %PROJECT_ROOT%. >> debug_code_agent.log 2>&1
#     echo ERROR: Failed to change to project root directory %PROJECT_ROOT%.
#     pause
#     exit /b 1
# )

# :: Check for Node.js
# echo Checking for Node.js... >> debug_code_agent.log 2>&1
# node --version >> debug_code_agent.log 2>&1
# if %ERRORLEVEL% neq 0 (
#     echo ERROR: Node.js is not installed. Please ensure Node.js is installed. >> debug_code_agent.log 2>&1
#     echo ERROR: Node.js is not installed. Please ensure Node.js is installed.
#     pause
#     exit /b 1
# )
# echo Node.js found. >> debug_code_agent.log 2>&1

# :: Install dependencies
# echo Installing dependencies... >> debug_code_agent.log 2>&1
# if exist "package.json" (
#     npm install >> debug_code_agent.log 2>&1
#     if %ERRORLEVEL% neq 0 (
#         echo ERROR: Failed to install dependencies. Check package.json. >> debug_code_agent.log 2>&1
#         echo ERROR: Failed to install dependencies. Check package.json.
#         pause
#         exit /b 1
#     )
# ) else (
#     echo WARNING: package.json not found. Skipping dependency installation. >> debug_code_agent.log 2>&1
#     echo WARNING: package.json not found. Skipping dependency installation.
# )
# echo Dependencies installed. >> debug_code_agent.log 2>&1

# :: Run the application
# echo Starting the application... >> debug_code_agent.log 2>&1
# npm start >> debug_code_agent.log 2>&1
# if %ERRORLEVEL% neq 0 (
#     echo ERROR: Failed to start the application. Check package.json and npm start script. >> debug_code_agent.log 2>&1
#     echo ERROR: Failed to start the application. Check package.json and npm start script.
#     pause
#     exit /b 1
# )
# echo Application started. >> debug_code_agent.log 2>&1

# pause
# exit /b 0
# """
    
#     def _nodejs_requirements(self, **kwargs):
#         dependencies = kwargs.get('dependencies', {})
#         base_package = {
#             "name": "generated-app",
#             "version": "1.0.0",
#             "scripts": {"start": "node index.js"},
#             "dependencies": {"express": "^4.18.2"}
#         }
#         base_package["dependencies"].update(dependencies)
#         return json.dumps(base_package, indent=2) + '\n'
    
#     def _nodejs_env(self, **kwargs):
#         return "PORT=3000\nDB_URL=mongodb://localhost:27017/app\n"
    
#     def _nodejs_prompt_template(self, **kwargs):
#         file_path = kwargs.get('file_path', '')
#         project_name = kwargs.get('project_name', 'this application')
#         backend_language_framework = kwargs.get('backend_language_framework', 'Node.js Express')
#         frontend_language_framework = kwargs.get('frontend_language_framework', 'Vanilla HTML/CSS/JS')
#         storage_type = kwargs.get('storage_type', 'mongodb')
#         json_design = kwargs.get('json_design', {})
#         json_spec = kwargs.get('json_spec', {})
        
#         return f"""
# CONTEXT:
# - You are an expert Senior Software Engineer tasked with generating complete, syntactically correct code for a web application named {project_name}. The application uses:
#     - Backend: {backend_language_framework}
#     - Frontend: {frontend_language_framework}
#     - Storage: {storage_type}
# - Your goal is to produce code for a specific file based on:
#     - JSON Design: Technical implementation details (architecture, data models, APIs).
#     - JSON Specification: Functional and non-functional requirements.
# - The generated code must be executable, idiomatic, and aligned with the provided design and requirements.

# TARGET FILE INFORMATION:
# - Full Path of the File to Generate: {file_path}
# - Project Structure: This file is part of the project structure defined in the `folder_Structure` section of the JSON Design.

# INTERNAL THOUGHT PROCESS:
# 1. Analyze File Role:
#    - Identify the file's purpose based on `{file_path}` and `json_design.folder_Structure`.
#    - If the file is the main entry point (e.g., `index.js`, `server.js`), include Express initialization, middleware setup, and route mounting.
#    - If it's a route file, implement RESTful API endpoints based on the JSON design.
#    - If it's a model file, implement data schemas and database interactions.

# 2. Extract Requirements:
#    - From JSON Specification: Functional requirements, technology stack, and data models.
#    - From JSON Design: API endpoints, data flow, and component interactions.

# 3. Follow Node.js/Express Best Practices:
#    - Use modern JavaScript (ES6+) features.
#    - Implement proper error handling and validation.
#    - Include security middleware (helmet, cors).
#    - Follow RESTful API conventions.
#    - Use environment variables for configuration.

# 4. Generate Complete Code:
#    - Include all necessary imports and dependencies.
#    - Implement full functionality as specified in the requirements.
#    - Add proper error handling and logging.
#    - Ensure code is production-ready and well-structured.

# RULES:
# 1. Generate ONLY the code for the specified file - no explanations, comments, or markdown.
# 2. The code must be complete, syntactically correct, and ready to run.
# 3. Include proper error handling and input validation.
# 4. Follow Express.js and Node.js best practices.
# 5. Use async/await for asynchronous operations.
# 6. Implement proper middleware and security measures.

# JSON DESIGN CONTEXT:
# {json.dumps(json_design, indent=2)}

# JSON SPECIFICATION CONTEXT:
# {json.dumps(json_spec, indent=2)}

# Generate the complete code for: {file_path}
# """

# # Tool input schemas
# class FileGeneratorInput(BaseModel):
#     file_path: str = Field(description="Absolute path to the file to generate")
#     context: Dict = Field(description="Context data including design_data, project_root, tech_stack")
#     requirements: Dict = Field(description="Requirements data from spec.json")

# class ProjectStructureInput(BaseModel):
#     project_root: str = Field(description="Root directory of the project")
#     structure: List[Dict] = Field(description="List of files and directories to create")

# class ProjectValidatorInput(BaseModel):
#     project_root: str = Field(description="Root directory of the project to validate")
#     tech_stack: str = Field(description="Technology stack being used (e.g., 'fastapi', 'nodejs')")

# # LangChain Tools
# class FileGeneratorTool(BaseTool):
#     """Tool for generating individual files"""
    
#     name: str = "file_generator"
#     description: str = "Generates code for individual files based on specifications"
#     args_schema: Type[BaseModel] = FileGeneratorInput
#     def __init__(self, llm, template_manager: TechnologyTemplateManager, error_tracker: ErrorTracker, config: AgentConfig):
#         super().__init__()
#         self._llm = llm
#         self._template_manager = template_manager
#         self._error_tracker = error_tracker
#         self._config = config
    
#     def _run(self, file_path: str, context: Dict, requirements: Dict, project_root: str = "", **kwargs) -> str:
#         """Generate code for a specific file with retry logic"""
#         tech_stack = context.get('tech_stack', 'fastapi')
#         # Use project_root parameter if provided, otherwise get from context
#         project_root = project_root or context.get('project_root', '')
        
#         # Ensure we have an absolute path for file creation
#         if project_root and not Path(file_path).is_absolute():
#             # Make the file path absolute by joining with project root
#             absolute_file_path = Path(project_root) / file_path
#         else:
#             absolute_file_path = Path(file_path)
            
#         # Use the absolute path for all file operations
#         absolute_file_path = absolute_file_path.resolve()
        
#         # For template purposes, get relative path 
#         try:
#             relative_file_path = str(Path(file_path).name) if project_root else str(Path(file_path).name)
#         except:
#             relative_file_path = Path(file_path).name
        
#         # Handle special files
#         if relative_file_path == 'requirements.txt':
#             return self._template_manager.get_template(
#                 tech_stack, 'requirements',
#                 dependencies=context.get('design_data', {}).get('dependencies', {}).get('backend', [])
#             )
#         elif relative_file_path == '.env':
#             return self._template_manager.get_template(
#                 tech_stack, 'env_file',
#                 storage_type=context.get('design_data', {}).get('data_Design', {}).get('storage_Type', 'sqlite')
#             )
        
#         # Generate code using LLM with retries
#         for attempt in range(self._config.max_retries):
#             try:
#                 prompt_template = self._template_manager.get_template(
#                     tech_stack, 'prompt_template',
#                     file_path=file_path,
#                     project_name=requirements.get('project_Overview', {}).get('project_Name', 'this application'),
#                     backend_language_framework=f"{requirements.get('technology_Stack', {}).get('backend', {}).get('language', 'Python')} {requirements.get('technology_Stack', {}).get('backend', {}).get('framework', 'FastAPI')}",
#                     frontend_language_framework=f"{requirements.get('technology_Stack', {}).get('frontend', {}).get('language', 'HTML/CSS/JS')} {requirements.get('technology_Stack', {}).get('frontend', {}).get('framework', 'Vanilla')}",
#                     storage_type=context.get('design_data', {}).get('data_Design', {}).get('storage_Type', 'sqlite'),
#                     backend_module_path=context.get('backend_module_path', 'main'),
#                     frontend_dir=context.get('frontend_dir', 'frontend'),
#                     css_path=context.get('css_path', 'css/style.css'),
#                     js_files_to_link=context.get('js_files_to_link', []),
#                     json_design=context.get('design_data', {}),
#                     json_spec=requirements
#                 )
                
#                 response = self._llm.invoke([HumanMessage(content=prompt_template)])
#                 generated_code = response.content.strip()
                
#                 # Clean up code blocks
#                 if generated_code.startswith("```") and generated_code.endswith("```"):
#                     lines = generated_code.splitlines()
#                     if len(lines) > 2:
#                         generated_code = "\n".join(lines[1:-1])
#                     else:
#                         generated_code = ""
                
#                 if not generated_code:
#                     raise ValueError("LLM returned empty code")                
#                 # Basic syntax validation for Python files
#                 if file_path.endswith('.py'):
#                     try:
#                         ast.parse(generated_code)
#                     except SyntaxError as e:
#                         raise ValueError(f"Syntax error in generated Python code: {e}")
#                   # Save generated code to file using absolute path
#                 try:
#                     absolute_file_path.parent.mkdir(parents=True, exist_ok=True)
#                     with open(absolute_file_path, 'w', encoding='utf-8') as f:
#                         f.write(generated_code)
#                 except Exception as e:
#                     self._error_tracker.add_error(
#                         "file_write", str(absolute_file_path), str(e),
#                         {"context": context, "attempt": attempt + 1}
#                     )
#                     raise ValueError(f"Failed to write file: {e}")
                
#                 return f"Successfully generated file: {absolute_file_path}"
                
#             except Exception as e:
#                 self._error_tracker.add_error(
#                     "code_generation", file_path, str(e),
#                     {"context": context, "requirements": requirements, "attempt": attempt + 1}
#                 )
#                 if attempt == self._config.max_retries - 1:
#                     return f"# Error generating code: {str(e)}\n# TODO: Fix this file"
#                 time.sleep(self._config.api_delay_seconds * (2 ** attempt))  # Exponential backoff
        
#         return "# Error: Max retries reached"

# class ProjectStructureTool(BaseTool):
#     """Tool for creating project structure"""
    
#     name: str = "project_structure"
#     description: str = "Creates the project directory structure"
#     args_schema: Type[BaseModel] = ProjectStructureInput
    
#     def __init__(self, error_tracker: ErrorTracker):
#         super().__init__()
#         self._error_tracker = error_tracker
    
#     def _run(self, project_root: str, structure: List[Dict]) -> str:
#         """Create project structure"""
#         try:
#             os.makedirs(project_root, exist_ok=True)
#             created_items = []
            
#             for item in structure:
#                 # Use pathlib for better path handling
#                 item_path = Path(project_root) / item['path'].strip('/\\')
#                 description = item.get('description', '').lower()
                
#                 # Simplified directory detection logic
#                 is_directory = (
#                     'directory' in description or 
#                     item['path'].endswith(('/')) or
#                     (not item_path.suffix and 'file' not in description)
#                 )
                
#                 if is_directory:
#                     item_path.mkdir(parents=True, exist_ok=True)
#                     created_items.append(f"Directory: {item_path}")
#                 else:
#                     # Ensure parent directory exists
#                     item_path.parent.mkdir(parents=True, exist_ok=True)
#                     # Create empty file
#                     item_path.touch(exist_ok=True)
#                     created_items.append(f"File: {item_path}")
            
#             # Ensure logs directory
#             logs_dir = Path(project_root) / 'logs'
#             logs_dir.mkdir(exist_ok=True)
#             created_items.append(f"Directory: {logs_dir}")
            
#             return f"Successfully created {len(created_items)} items:\n" + "\n".join(created_items)
            
#         except Exception as e:
#             self._error_tracker.add_error(
#                 "structure_creation", project_root, str(e),
#                 {"structure": structure}
#             )
#             return f"Error creating structure: {str(e)}"

# class ProjectValidatorTool(BaseTool):
#     """Tool for validating generated project"""
    
#     name: str = "project_validator"
#     description: str = "Validates the generated project for common issues"
#     args_schema: Type[BaseModel] = ProjectValidatorInput
    
#     def __init__(self, error_tracker: ErrorTracker):
#         super().__init__()
#         self._error_tracker = error_tracker
    
#     def _run(self, project_root: str, tech_stack: str) -> str:
#         """Validate the generated project"""
#         issues = []
        
#         try:
#             # Check for required files
#             required_files = ['main.py', 'requirements.txt'] if tech_stack.lower() == 'fastapi' else ['index.js', 'package.json']
#             for req_file in required_files:
#                 if not self._find_file(project_root, req_file):
#                     issues.append(f"Missing required file: {req_file}")
            
#             # Check for empty files (with improved performance)
#             project_path = Path(project_root)
#             for file_path in project_path.rglob('*'):
#                 if file_path.is_file() and file_path.suffix in {'.py', '.js', '.html', '.css'}:
#                     try:
#                         if file_path.stat().st_size == 0:
#                             issues.append(f"Empty file: {file_path}")
#                     except (OSError, PermissionError):
#                         # Skip files we can't access
#                         continue
            
#             # Check for non-ASCII characters in batch files
#             for file_name in ['run.bat']:
#                 file_path = Path(project_root) / file_name
#                 if file_path.exists():
#                     try:
#                         with open(file_path, 'r', encoding='utf-8') as f:
#                             content = f.read()
#                             if any(ord(char) > 127 for char in content):
#                                 issues.append(f"Non-ASCII characters in {file_name}")
#                     except (UnicodeDecodeError, PermissionError):
#                         issues.append(f"Cannot read {file_name} - encoding or permission issue")
            
#             # Log issues
#             for issue in issues:
#                 self._error_tracker.add_error(
#                     "validation", project_root, issue,
#                     {"tech_stack": tech_stack}
#                 )
            
#             if issues:
#                 return f"Found {len(issues)} validation issues:\n" + "\n".join(issues)
#             return "Project validation passed successfully"
            
#         except Exception as e:
#             self._error_tracker.add_error(
#                 "validation_error", project_root, str(e)
#             )
#             return f"Validation error: {str(e)}"    
#     def _find_file(self, root_dir: str, filename: str) -> bool:
#         """Find if a file exists in the directory tree"""
#         try:
#             root_path = Path(root_dir)
#             for file_path in root_path.rglob(filename):
#                 if file_path.is_file():
#                     return True
#             return False
#         except (OSError, PermissionError):
#             return False
        
        
import json
import os
import logging
import time
import ast
from datetime import datetime
from typing import Dict, List, Optional, Any, Type
from pathlib import Path
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage
from langchain_core.callbacks.base import BaseCallbackHandler
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CÁC LỚP TIỆN ÍCH (KHÔNG THAY ĐỔI)
# ==============================================================================

class AgentConfig(BaseModel):
    """Configuration for the coding agent"""
    outputs_dir: str = Field(default="src/module_1_vs_2/outputs", description="Directory containing JSON files")
    base_output_dir: str = Field(default="code_generated_result", description="Base directory for generated code")
    python_path: str = Field(default="python", description="Python executable path")
    model_name: str = Field(default="gemini-2.0-flash", description="LLM model name")
    api_delay_seconds: int = Field(default=2, description="Delay between API calls")
    max_retries: int = Field(default=3, description="Maximum retry attempts for LLM calls")
    log_level: str = Field(default="DEBUG", description="Logging level")

    @classmethod
    def from_env(cls) -> 'AgentConfig':
        return cls(
            outputs_dir=os.getenv('OUTPUTS_DIR', 'src/module_1_vs_2/outputs'),
            base_output_dir=os.getenv('BASE_OUTPUT_DIR', 'code_generated_result'),
            python_path=os.getenv('PYTHON_PATH', 'python'),
            model_name=os.getenv('MODEL_NAME', 'gemini-2.0-flash'),
            api_delay_seconds=int(os.getenv('API_DELAY_SECONDS', '2')),
            max_retries=int(os.getenv('MAX_RETRIES', '3')),
            log_level=os.getenv('LOG_LEVEL', 'DEBUG')
        )

class ErrorTracker:
    """Tracks and stores errors for debugging agent"""
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.errors = []
        self.error_file = os.path.join(project_root, "errors.json")
    
    def add_error(self, error_type: str, file_path: str, error_message: str, context: Optional[Dict] = None):
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
        os.makedirs(os.path.dirname(self.error_file), exist_ok=True)
        try:
            with open(self.error_file, 'w', encoding='utf-8') as f:
                json.dump(self.errors, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save errors to {self.error_file}: {e}")

    def get_errors(self) -> List[Dict]:
        return self.errors

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
        tech_templates = self.templates.get(tech_stack.lower(), self.templates["fastapi"])
        return tech_templates.get(template_type, lambda **k: "")(**kwargs)
    
    # --- CÁC PHƯƠNG THỨC TEMPLATE (ví dụ: _fastapi_run_script, ...) được giữ nguyên ---
    def _fastapi_run_script(self, **kwargs):
        python_path = kwargs.get('python_path', 'python')
        backend_module = kwargs.get('backend_module_path', 'main')
        return f"""@echo off
setlocal EnableDelayedExpansion

:: Define the log file path explicitly - THIS MUST BE THE VERY FIRST COMMAND THAT USES THE VARIABLE
set "LOG_FILE=debug_code_agent.log"
set "PROJECT_ROOT=%~dp0"

:: Initial log entries. Use > to create/overwrite, then >> to append.
echo --- run.bat STARTING --- > "%LOG_FILE%"
echo Timestamp: %DATE% %TIME% >> "%LOG_FILE%"
echo Current Directory (at start): "%CD%" >> "%LOG_FILE%"
echo PROJECT_ROOT (calculated): "%PROJECT_ROOT%" >> "%LOG_FILE%"
echo PYTHON_PATH from config: "{python_path}" >> "%LOG_FILE%"

:: Change to project root
echo Changing directory to project root... >> "%LOG_FILE%"
cd /d "%PROJECT_ROOT%" 1>>"%LOG_FILE%" 2>>&1
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
echo Creating virtual environment in "%PROJECT_ROOT%\\venv"... >> "%LOG_FILE%"
if not exist "%PROJECT_ROOT%\\venv" (
    "{python_path}" -m venv "%PROJECT_ROOT%\\venv" 1>>"%LOG_FILE%" 2>>&1
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
call "%PROJECT_ROOT%\\venv\\Scripts\\activate.bat" 1>>"%LOG_FILE%" 2>>&1
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
        base_deps = ['fastapi[all]', 'uvicorn[standard]', 'sqlalchemy', 'pydantic']
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
        # Giữ nguyên như cũ
        return ""
    
    def _nodejs_requirements(self, **kwargs):
        # Giữ nguyên như cũ
        return ""
    
    def _nodejs_env(self, **kwargs):
        # Giữ nguyên như cũ
        return ""
    
    def _nodejs_prompt_template(self, **kwargs):
        # Giữ nguyên như cũ
        return ""
        
# ==============================================================================
# SỬA ĐỔI CÁC TOOL VÀ INPUT SCHEMA
# ==============================================================================

# <<< SỬA ĐỔI 1: Đơn giản hóa các Input Schema >>>
# Chúng ta chỉ yêu cầu LLM cung cấp thông tin tối thiểu.
# Phần còn lại sẽ được agent tự động inject hoặc tool tự xử lý.

class FileGeneratorInput(BaseModel):
    file_path: str = Field(description="Relative path of the file to generate (e.g., 'src/main.py')")

class ProjectStructureInput(BaseModel):
    # Tool này không cần input từ LLM nữa, vì nó sẽ lấy `design_data` từ agent state
    pass

class ProjectValidatorInput(BaseModel):
    # Tool này không cần input từ LLM nữa, vì nó sẽ lấy `spec_data` từ agent state
    pass

# LangChain Tools
class FileGeneratorTool(BaseTool):
    """Tool for generating individual files"""
    
    name: str = "file_generator"
    description: str = "Generates code and content for a single project file. Use this for every file in the project structure."
    args_schema: Type[BaseModel] = FileGeneratorInput
    
    def __init__(self, llm, template_manager: TechnologyTemplateManager, error_tracker: ErrorTracker, config: AgentConfig):
        super().__init__()
        self._llm = llm
        self._template_manager = template_manager
        self._error_tracker = error_tracker
        self._config = config
    
    # <<< SỬA ĐỔI 2: Thay đổi chữ ký của _run và logic bên trong >>>
    def _run(self, file_path: str, project_root: str, design_data: Dict, spec_data: Dict, **kwargs) -> str:
        """Generate code for a specific file using data from agent state."""
        
        # --- Logic xây dựng ngữ cảnh được chuyển vào trong tool ---
        tech_stack = spec_data.get('technology_Stack', {}).get('backend', {}).get('framework', 'fastapi')
        absolute_file_path = (Path(project_root) / file_path).resolve()
        
        # Build context from injected state
        context = self._build_context(design_data, spec_data, project_root)

        # Handle special files
        relative_file_path = Path(file_path).name
        if relative_file_path == 'requirements.txt':
            content = self._template_manager.get_template(
                tech_stack, 'requirements',
                dependencies=design_data.get('dependencies', {}).get('backend', [])
            )
        elif relative_file_path == '.env':
            content = self._template_manager.get_template(
                tech_stack, 'env_file',
                storage_type=design_data.get('data_Design', {}).get('storage_Type', 'sqlite')
            )
        else:
            # Generate code using LLM
            for attempt in range(self._config.max_retries):
                try:
                    # Tạo prompt với ngữ cảnh đầy đủ
                    prompt_template = self._template_manager.get_template(
                        tech_stack, 'prompt_template',
                        file_path=str(absolute_file_path),
                        project_name=spec_data.get('project_Overview', {}).get('project_Name', 'this application'),
                        backend_language_framework=f"{spec_data.get('technology_Stack', {}).get('backend', {}).get('language', 'Python')} {spec_data.get('technology_Stack', {}).get('backend', {}).get('framework', 'FastAPI')}",
                        frontend_language_framework=f"{spec_data.get('technology_Stack', {}).get('frontend', {}).get('language', 'HTML/CSS/JS')} {spec_data.get('technology_Stack', {}).get('frontend', {}).get('framework', 'Vanilla')}",
                        storage_type=design_data.get('data_Design', {}).get('storage_Type', 'sqlite'),
                        json_design=design_data,
                        json_spec=spec_data,
                        **context  # Add the rest of the context
                    )
                    
                    response = self._llm.invoke([HumanMessage(content=prompt_template)])
                    generated_code = response.content.strip()
                    
                    if generated_code.startswith("```") and generated_code.endswith("```"):
                        lines = generated_code.splitlines()
                        generated_code = "\n".join(lines[1:-1]) if len(lines) > 2 else ""
                    
                    if not generated_code:
                        raise ValueError("LLM returned empty code")                
                    
                    if file_path.endswith('.py'):
                        try:
                            ast.parse(generated_code)
                        except SyntaxError as e:
                            raise ValueError(f"Syntax error in generated Python code: {e}")

                    # Gán nội dung để ghi file
                    content = generated_code
                    break # Thoát khỏi vòng lặp retry khi thành công

                except Exception as e:
                    self._error_tracker.add_error(
                        "code_generation", str(absolute_file_path), str(e),
                        {"attempt": attempt + 1}
                    )
                    if attempt == self._config.max_retries - 1:
                        return f"Error: Failed to generate code for {file_path} after {self._config.max_retries} attempts: {e}"
                    time.sleep(self._config.api_delay_seconds * (2 ** attempt))
            else: # Chạy khi vòng lặp hoàn thành mà không break
                return f"Error: Max retries reached for {file_path}"
        
        # --- Logic ghi file được gộp vào cuối ---
        try:
            absolute_file_path.parent.mkdir(parents=True, exist_ok=True)
            absolute_file_path.write_text(content, encoding='utf-8')
            return f"Successfully generated and wrote file: {file_path}"
        except Exception as e:
            error_msg = f"Error writing file {file_path}: {e}"
            self._error_tracker.add_error("file_write", str(absolute_file_path), str(e))
            return error_msg

    def _build_context(self, design_data: Dict, spec_data: Dict, project_root: str) -> Dict:
        """Builds a comprehensive context dictionary for prompt generation."""
        # (This logic is moved from the old agent class into the tool)
        context = {
            'backend_module_path': 'main',
            'frontend_dir': 'frontend',
            'css_path': 'css/style.css',
            'js_files_to_link': []
        }
        structure = design_data.get('folder_Structure', {}).get('structure', [])
        for item in structure:
            path = item.get('path', '').strip('/\\').replace('\\', '/')
            if path.endswith('main.py'):
                parts = Path(path).parts
                context['backend_module_path'] = '.'.join(parts[:-1] + ('main',)) if len(parts) > 1 else 'main'
            elif path.endswith('index.html'):
                context['frontend_dir'] = str(Path(path).parent)
        
        # Find CSS and JS relative to frontend_dir
        for item in structure:
            path = item.get('path', '').strip('/\\').replace('\\', '/')
            if path.startswith(context['frontend_dir']):
                relative_path_to_frontend = str(Path(path).relative_to(context['frontend_dir'])).replace('\\', '/')
                if path.endswith('.css'):
                    context['css_path'] = relative_path_to_frontend
                elif path.endswith('.js'):
                    context['js_files_to_link'].append(relative_path_to_frontend)

        context['js_files_to_link'] = sorted(list(set(context['js_files_to_link'])))
        return context

class ProjectStructureTool(BaseTool):
    """Tool for creating project structure"""
    
    name: str = "project_structure"
    description: str = "Creates the complete project directory structure including empty files, based on the design file."
    args_schema: Type[BaseModel] = ProjectStructureInput
    
    def __init__(self, error_tracker: ErrorTracker):
        super().__init__()
        self._error_tracker = error_tracker
    
    # <<< SỬA ĐỔI 3: Thay đổi chữ ký của _run và logic bên trong >>>
    def _run(self, project_root: str, design_data: Dict, **kwargs) -> str:
        """Create project structure based on design_data from agent state."""
        try:
            # Lấy cấu trúc từ design_data được inject
            structure = design_data.get('folder_Structure', {}).get('structure', [])
            if not structure:
                return "Error: 'structure' not found in design_data."

            Path(project_root).mkdir(exist_ok=True)
            created_items = []
            
            for item in structure:
                item_path = Path(project_root) / item['path'].strip('/\\')
                description = item.get('description', '').lower()
                
                is_directory = (
                    'directory' in description or 
                    item['path'].endswith(('/')) or
                    (not item_path.suffix and 'file' not in description)
                )
                
                if is_directory:
                    item_path.mkdir(parents=True, exist_ok=True)
                    created_items.append(f"Directory: {item_path}")
                else:
                    item_path.parent.mkdir(parents=True, exist_ok=True)
                    item_path.touch(exist_ok=True)
                    created_items.append(f"File: {item_path}")
            
            logs_dir = Path(project_root) / 'logs'
            logs_dir.mkdir(exist_ok=True)
            created_items.append(f"Directory: {logs_dir}")
            
            return f"Successfully created {len(created_items)} directories and empty files."
            
        except Exception as e:
            self._error_tracker.add_error("structure_creation", project_root, str(e), {"structure": structure})
            return f"Error creating structure: {str(e)}"

class ProjectValidatorTool(BaseTool):
    """Tool for validating generated project"""
    
    name: str = "project_validator"
    description: str = "Validates the generated project for common issues like missing or empty files."
    args_schema: Type[BaseModel] = ProjectValidatorInput
    
    def __init__(self, error_tracker: ErrorTracker):
        super().__init__()
        self._error_tracker = error_tracker
    
    # <<< SỬA ĐỔI 4: Thay đổi chữ ký của _run và logic bên trong >>>
    def _run(self, project_root: str, spec_data: Dict, **kwargs) -> str:
        """Validate the generated project based on spec_data from agent state."""
        issues = []
        try:
            # Lấy tech_stack từ spec_data được inject
            tech_stack = spec_data.get('technology_Stack', {}).get('backend', {}).get('framework', 'fastapi')
            
            required_files = ['main.py', 'requirements.txt'] if tech_stack.lower() == 'fastapi' else ['index.js', 'package.json']
            for req_file in required_files:
                # Tìm file ở bất cứ đâu trong project
                found = any(Path(project_root).rglob(req_file))
                if not found:
                    issues.append(f"Missing required file: {req_file}")
            
            project_path = Path(project_root)
            for file_path in project_path.rglob('*'):
                if file_path.is_file() and file_path.suffix in {'.py', '.js', '.html', '.css'}:
                    try:
                        if file_path.stat().st_size == 0 and file_path.name not in ['__init__.py']:
                            issues.append(f"Empty file: {file_path.relative_to(project_root)}")
                    except OSError:
                        continue
            
            for file_name in ['run.bat']:
                file_path = Path(project_root) / file_name
                if file_path.exists():
                    try:
                        file_path.read_text(encoding='utf-8')
                    except Exception:
                         issues.append(f"Cannot read or decode {file_name} as UTF-8.")
            
            for issue in issues:
                self._error_tracker.add_error("validation", project_root, issue, {"tech_stack": tech_stack})
            
            if issues:
                return f"Found {len(issues)} validation issues:\n" + "\n".join(issues)
            return "Project validation passed successfully."
            
        except Exception as e:
            self._error_tracker.add_error("validation_error", project_root, str(e))
            return f"Validation error: {str(e)}"