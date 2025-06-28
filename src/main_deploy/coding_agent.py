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
    
    @classmethod
    def from_env(cls) -> 'AgentConfig':
        """Create config from environment variables - alias for from_central_config()"""
        return cls.from_central_config()
    
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
        project_context_summary = kwargs.get('project_context_summary', '')
        context_instructions = kwargs.get('context_instructions', '')
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
            - Project Context: Cross-file awareness and dependency management.
            - Additional rules for logging, FastAPI static file serving, and CORS configuration.
        - The generated code must be executable, idiomatic, and aligned with the provided design and requirements.

        PROJECT-WIDE CONTEXT AWARENESS:
        {project_context_summary}

        CONTEXT-SPECIFIC INSTRUCTIONS FOR THIS FILE:
        {context_instructions}

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
        - FOLLOW the project context instructions to avoid conflicts and ensure proper imports.
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
        - STRICTLY FOLLOW the required imports specified in the context instructions.
        - DO NOT include forbidden import patterns or redefinitions.
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
        - STRICT adherence to project context instructions (imports, forbidden patterns, etc.).
        - Inclusion of language-specific entry points for executable files.
        - Readiness to run with `python -m uvicorn {backend_module_path}:app --reload --port 8001` for `{backend_module_path.replace('.', '/')}.py`.
    """

# === CODE VALIDATION AND AUTO-FIX LAYER === logic mới vào chiều 28/6

class ContentClassifier:
    """Analyzes file content to determine its actual purpose and type"""
    
    @staticmethod
    def classify_file_content(file_path: str, content: str) -> dict:
        """
        Classify file content by analyzing actual code patterns
        Returns: {
            'content_type': str,
            'contains_pydantic': bool,
            'contains_sqlalchemy': bool,
            'imports_found': list,
            'classes_found': list,
            'functions_found': list
        }
        """
        classification = {
            'content_type': 'unknown',
            'contains_pydantic': False,
            'contains_sqlalchemy': False,
            'imports_found': [],
            'classes_found': [],
            'functions_found': [],
            'schema_classes': [],
            'model_classes': []
        }
        
        lines = content.split('\n')
        filename = os.path.basename(file_path).lower()
        
        for line in lines:
            line = line.strip()
            
            # Track imports
            if line.startswith(('import ', 'from ')):
                classification['imports_found'].append(line)
                
                # Detect framework patterns
                if 'BaseModel' in line or 'pydantic' in line:
                    classification['contains_pydantic'] = True
                if 'declarative_base' in line or 'sqlalchemy' in line or 'Column' in line:
                    classification['contains_sqlalchemy'] = True
            
            # Track class definitions
            elif line.startswith('class ') and ':' in line:
                class_name = line.split('class ')[1].split('(')[0].split(':')[0].strip()
                classification['classes_found'].append(class_name)
                
                # Classify class type based on inheritance
                if 'BaseModel' in line:
                    classification['schema_classes'].append(class_name)
                elif 'Base' in line and not 'BaseModel' in line:
                    classification['model_classes'].append(class_name)
            
            # Track function definitions
            elif line.startswith('def ') and '(' in line:
                func_name = line.split('def ')[1].split('(')[0].strip()
                classification['functions_found'].append(func_name)
        
        # Determine content type based on analysis
        if classification['contains_pydantic'] or 'schema' in filename:
            classification['content_type'] = 'pydantic_schemas'
        elif classification['contains_sqlalchemy'] or 'model' in filename:
            classification['content_type'] = 'sqlalchemy_models'
        elif 'route' in filename or 'api' in filename:
            classification['content_type'] = 'fastapi_routes'
        elif 'database' in filename or 'db' in filename:
            classification['content_type'] = 'database_config'
        elif 'main' in filename or 'app' in filename:
            classification['content_type'] = 'application_entry'
        
        return classification

class ImportAnalyzer:
    """Analyzes and validates imports within project context"""
    
    def __init__(self, project_context):
        self.project_context = project_context
        self.content_cache = {}  # Cache for file content classifications
    
    def analyze_imports(self, file_path: str, content: str, file_classification: dict) -> dict:
        """
        Analyze imports in generated content and detect issues
        Returns: {
            'valid_imports': list,
            'invalid_imports': list,
            'missing_imports': list,
            'import_conflicts': list,
            'auto_fix_suggestions': list
        }
        """
        analysis = {
            'valid_imports': [],
            'invalid_imports': [],
            'missing_imports': [],
            'import_conflicts': [],
            'auto_fix_suggestions': []
        }
        
        # Analyze each import in the content
        current_imports = file_classification['imports_found']
        for import_stmt in current_imports:
            validation_result = self._validate_single_import(import_stmt, file_path, file_classification)
            
            if validation_result['is_valid']:
                analysis['valid_imports'].append(import_stmt)
            else:
                analysis['invalid_imports'].append({
                    'import': import_stmt,
                    'issue': validation_result['issue'],
                    'suggested_fix': validation_result['suggested_fix']
                })
                
                # Add auto-fix suggestion if available
                if validation_result['suggested_fix']:                analysis['auto_fix_suggestions'].append({
                    'action': 'replace_import',
                    'old_import': import_stmt,
                    'new_import': validation_result['suggested_fix'],
                    'reason': validation_result['issue']
                })
                
                # Add additional import if needed (for preserving model imports)
                if validation_result.get('additional_import'):
                    analysis['auto_fix_suggestions'].append({
                        'action': 'add_import',
                        'new_import': validation_result['additional_import'],
                        'reason': 'Preserve model imports after fixing schema imports'
                    })
        
        # Check for missing required imports
        required_imports = self._get_required_imports_for_content(file_path, file_classification)
        for required_import in required_imports:
            if not self._is_import_present(required_import, current_imports):
                analysis['missing_imports'].append(required_import)
                analysis['auto_fix_suggestions'].append({
                    'action': 'add_import',
                    'new_import': required_import,
                    'reason': f"Required import for {file_classification['content_type']}"
                })
        
        return analysis
    
    def _validate_single_import(self, import_stmt: str, current_file_path: str, file_classification: dict) -> dict:
        """Validate a single import statement"""
        validation = {
            'is_valid': True,
            'issue': '',
            'suggested_fix': None
        }
        
        # Parse import statement
        if 'from ' in import_stmt and ' import ' in import_stmt:
            parts = import_stmt.split(' import ')
            module_part = parts[0].replace('from ', '').strip()
            imports_part = parts[1].strip()
            
            # Check for schema/model confusion
            if module_part.endswith('.models') and any(name in imports_part for name in ['Create', 'Update', 'Base']):
                # Check if these are actually Pydantic schemas
                imported_items = [item.strip() for item in imports_part.split(',')]
                schema_items = []
                model_items = []
                
                for item in imported_items:
                    if any(keyword in item for keyword in ['Create', 'Update']) and not item == 'Base':
                        schema_items.append(item)
                    else:
                        model_items.append(item)
                
                if schema_items:
                    validation['is_valid'] = False
                    validation['issue'] = f"Schema classes {schema_items} should be imported from schemas module"
                    validation['suggested_fix'] = f"from {module_part.replace('.models', '.schemas')} import {', '.join(schema_items)}"
                    
                    # If there are still model items, we need to preserve the model import
                    if model_items:
                        validation['additional_import'] = f"from {module_part} import {', '.join(model_items)}"
        
        return validation
    
    def _get_required_imports_for_content(self, file_path: str, file_classification: dict) -> list:
        """Get required imports based on file content type"""
        required_imports = []
        content_type = file_classification['content_type']
        
        if content_type == 'fastapi_routes':
            # Routes need database session and appropriate models/schemas
            if self.project_context.project_structure['database_files']:
                required_imports.append("from sqlalchemy.orm import Session")
                required_imports.extend(self.project_context.get_required_imports(file_path))
            
            # If we see Pydantic class usage, ensure schema imports
            for class_name in file_classification['classes_found']:
                if any(keyword in class_name for keyword in ['Create', 'Update', 'Response']):
                    schema_file = self._find_schema_file()
                    if schema_file:
                        schema_module = os.path.splitext(schema_file)[0].replace('/', '.').replace('\\', '.')
                        required_imports.append(f"from {schema_module} import {class_name}")
        
        elif content_type == 'sqlalchemy_models':
            # Models need Base from database
            if self.project_context.project_structure['database_files']:
                db_file = self.project_context.project_structure['database_files'][0]
                db_module = os.path.splitext(db_file)[0].replace('/', '.').replace('\\', '.')
                required_imports.append(f"from {db_module} import Base")
        
        return required_imports
    
    def _find_schema_file(self) -> str:
        """Find the schema file in the project structure"""
        for file_path in self.project_context.project_structure['model_files']:
            if 'schema' in os.path.basename(file_path).lower():
                return file_path
        return None
    
    def _is_import_present(self, target_import: str, current_imports: list) -> bool:
        """Check if a required import is already present"""
        target_clean = target_import.strip()
        for current_import in current_imports:
            if target_clean == current_import.strip():
                return True
        return False

class AutoFixer:
    """Automatically fixes detected code issues"""
    
    @staticmethod
    def apply_fixes(content: str, fix_suggestions: list) -> str:
        """Apply all auto-fix suggestions to the content"""
        fixed_content = content
        import_fixes = []
        
        for suggestion in fix_suggestions:
            if suggestion['action'] == 'replace_import':
                fixed_content = AutoFixer._replace_import(
                    fixed_content, 
                    suggestion['old_import'], 
                    suggestion['new_import']
                )
            elif suggestion['action'] == 'add_import':
                import_fixes.append(suggestion['new_import'])
            elif suggestion['action'] == 'fix_import_source':
                # Handle complex import source fixes
                fix_info = suggestion.get('new_import', suggestion)
                if isinstance(fix_info, dict):
                    if 'original' in fix_info and 'fixed' in fix_info:
                        fixed_content = AutoFixer._replace_import(
                            fixed_content, 
                            fix_info['original'], 
                            fix_info['fixed']
                        )
                        if fix_info.get('additional_import'):
                            import_fixes.append(fix_info['additional_import'])
        
        # Add all missing imports at the beginning
        if import_fixes:
            fixed_content = AutoFixer._add_imports(fixed_content, import_fixes)
        
        return fixed_content
    
    @staticmethod
    def _replace_import(content: str, old_import: str, new_import: str) -> str:
        """Replace an import statement in the content"""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip() == old_import.strip():
                lines[i] = new_import
                break
        return '\n'.join(lines)
    
    @staticmethod
    def _add_imports(content: str, new_imports: list) -> str:
        """Add new imports at the appropriate location in the file"""
        lines = content.split('\n')
        
        # Find the location to insert imports (after existing imports or at the top)
        insert_index = 0
        last_import_index = -1
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ')) and not stripped.startswith('#'):
                last_import_index = i
            elif stripped and not stripped.startswith('#') and last_import_index != -1:
                # Found first non-import, non-comment line after imports
                insert_index = last_import_index + 1
                break
        
        # If no imports found, insert at the beginning (after any initial comments/docstrings)
        if last_import_index == -1:
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                    insert_index = i
                    break
        else:
            insert_index = last_import_index + 1
        
        # Insert new imports
        for new_import in new_imports:
            if new_import.strip() not in [line.strip() for line in lines]:  # Avoid duplicates
                lines.insert(insert_index, new_import)
                insert_index += 1
        
        return '\n'.join(lines)

class CodeValidator:
    """Main validation orchestrator that coordinates all validation activities"""
    
    def __init__(self, project_context):
        self.project_context = project_context
        self.content_classifier = ContentClassifier()
        self.import_analyzer = ImportAnalyzer(project_context)
        self.auto_fixer = AutoFixer()
        self.validation_cache = {}
    
    def validate_and_fix_generated_code(self, file_path: str, generated_code: str) -> dict:
        """
        Main validation entry point - validates and auto-fixes generated code
        Returns: {
            'is_valid': bool,
            'fixed_code': str,
            'issues_found': list,
            'fixes_applied': list,
            'validation_summary': str
        }
        """
        result = {
            'is_valid': True,
            'fixed_code': generated_code,
            'issues_found': [],
            'fixes_applied': [],
            'validation_summary': ''
        }
        
        try:
            # Step 1: Classify file content
            file_classification = self.content_classifier.classify_file_content(file_path, generated_code)
            
            # Step 2: Analyze imports
            import_analysis = self.import_analyzer.analyze_imports(file_path, generated_code, file_classification)
            
            # Step 3: Collect all issues
            if import_analysis['invalid_imports'] or import_analysis['missing_imports']:
                result['is_valid'] = False
                result['issues_found'].extend(import_analysis['invalid_imports'])
                result['issues_found'].extend([{'type': 'missing_import', 'import': imp} for imp in import_analysis['missing_imports']])
            
            # Step 4: Auto-fix issues
            if import_analysis['auto_fix_suggestions']:
                result['fixed_code'] = self.auto_fixer.apply_fixes(generated_code, import_analysis['auto_fix_suggestions'])
                result['fixes_applied'] = import_analysis['auto_fix_suggestions']
                
                # Re-validate after fixes
                if result['fixed_code'] != generated_code:
                    # Update project context with fixed content
                    self.project_context.update_from_generated_file(file_path, result['fixed_code'])
            
            # Step 5: Generate validation summary
            result['validation_summary'] = self._generate_validation_summary(file_path, file_classification, import_analysis, result['fixes_applied'])
            
        except Exception as e:
            logger.error(f"Validation error for {file_path}: {e}", exc_info=True)
            result['is_valid'] = False
            result['issues_found'].append({'type': 'validation_error', 'error': str(e)})
        
        return result
    
    def _generate_validation_summary(self, file_path: str, classification: dict, analysis: dict, fixes: list) -> str:
        """Generate a human-readable validation summary"""
        summary_parts = []
        summary_parts.append(f"File: {file_path}")
        summary_parts.append(f"Content Type: {classification['content_type']}")
        summary_parts.append(f"Classes Found: {classification['classes_found']}")
        summary_parts.append(f"Schema Classes: {classification['schema_classes']}")
        summary_parts.append(f"Model Classes: {classification['model_classes']}")
        
        if analysis['invalid_imports']:
            summary_parts.append(f"Invalid Imports Fixed: {len(analysis['invalid_imports'])}")
        
        if analysis['missing_imports']:
            summary_parts.append(f"Missing Imports Added: {len(analysis['missing_imports'])}")
        
        if fixes:
            summary_parts.append("Auto-fixes Applied:")
            for fix in fixes:
                summary_parts.append(f"  - {fix['action']}: {fix.get('reason', 'General fix')}")
        
        return '\n'.join(summary_parts)
        
        if fixes:
            summary_parts.append("Auto-fixes Applied:")
            for fix in fixes:
                summary_parts.append(f"  - {fix['action']}: {fix.get('reason', 'General fix')}")
        
        return '\n'.join(summary_parts)

#Project Context Management for Cross-File Awareness
class ProjectContext:
    """Tracks shared definitions and dependencies across files during code generation"""
    
    def __init__(self, project_name: str, tech_stack: str, design_data: dict = None):
        self.project_name = project_name
        self.tech_stack = tech_stack.lower()
        self.design_data = design_data or {}
        
        # Track what's been defined where
        self.defined_classes = {}  # {class_name: file_path}
        self.defined_functions = {}  # {function_name: file_path}
        self.imports_used = {}  # {file_path: [import_statements]}
        self.database_models = []  # [model_class_names]
        self.api_endpoints = []  # [endpoint_info]
        self.shared_components = {}  # {component_name: definition_location}
        
        # Track file generation order and dependencies
        self.generation_order = []
        self.file_dependencies = {}  # {file_path: [required_files]}
        
        # Analyze project structure to determine patterns dynamically
        self.project_structure = self._analyze_project_structure()
        self.established_patterns = self._init_dynamic_framework_patterns()
        
    def _analyze_project_structure(self) -> dict:
        """Dynamically analyze the project structure from design data"""
        structure_info = {
            'files_by_type': {},
            'directories': [],
            'file_relationships': {},
            'entry_points': [],
            'database_files': [],
            'model_files': [],
            'route_files': [],
            'config_files': [],
            'frontend_files': []
        }
        
        if not self.design_data:
            return structure_info
        
        folder_structure = self.design_data.get('folder_Structure', {})
        structure_items = folder_structure.get('structure', [])
        
        for item in structure_items:
            path = item.get('path', '').strip('/\\')
            description = item.get('description', '').lower()
            
            # Skip directories
            if 'directory' in description:
                structure_info['directories'].append(path)
                continue
            
            filename = os.path.basename(path)
            file_ext = os.path.splitext(filename)[1]
            file_base = os.path.splitext(filename)[0]
            
            # Categorize files by extension
            if file_ext not in structure_info['files_by_type']:
                structure_info['files_by_type'][file_ext] = []
            structure_info['files_by_type'][file_ext].append(path)
            
            # Identify specific file types based on name patterns and descriptions
            if filename in ['main.py', 'app.py', 'run.py'] or 'main' in description or 'entry' in description:
                structure_info['entry_points'].append(path)
            
            if any(keyword in filename.lower() for keyword in ['database', 'db']) or 'database' in description:
                structure_info['database_files'].append(path)
            
            if any(keyword in filename.lower() for keyword in ['model', 'schema']) or 'model' in description:
                structure_info['model_files'].append(path)
            
            if any(keyword in filename.lower() for keyword in ['route', 'api', 'endpoint']) or any(keyword in description for keyword in ['route', 'api', 'endpoint']):
                structure_info['route_files'].append(path)
            
            if any(keyword in filename.lower() for keyword in ['config', 'setting']) or 'config' in description:
                structure_info['config_files'].append(path)
            
            if file_ext in ['.html', '.css', '.js'] or any(keyword in description for keyword in ['frontend', 'ui', 'web']):
                structure_info['frontend_files'].append(path)
        
        return structure_info
    
    def _init_dynamic_framework_patterns(self) -> dict:
        """Initialize framework-specific patterns based on actual project structure"""
        patterns = {
            'import_patterns': {},
            'component_locations': {},
            'file_dependencies': {},
            'shared_definitions': {}
        }
        
        if self.tech_stack not in ['fastapi', 'django', 'flask']:
            return patterns
        
        # Dynamically determine component locations based on actual files
        structure = self.project_structure
        
        # Find database-related files
        if structure['database_files']:
            db_file = structure['database_files'][0]  # Use first database file
            patterns['component_locations']['database'] = db_file
            patterns['component_locations']['database_base'] = db_file
            patterns['component_locations']['database_session'] = db_file
            
            # Generate import patterns based on actual file location
            db_module = os.path.splitext(db_file)[0].replace('/', '.').replace('\\', '.')
            patterns['import_patterns']['database_base'] = f'from {db_module} import Base'
            patterns['import_patterns']['database_session'] = f'from {db_module} import get_db'
            patterns['import_patterns']['database_engine'] = f'from {db_module} import engine'
            
            # Mark Base as shared definition that should only be defined once
            patterns['shared_definitions']['Base'] = {
                'location': db_file,
                'definition': 'Base = declarative_base()',
                'import_pattern': patterns['import_patterns']['database_base']
            }
        
        # Find model files
        if structure['model_files']:
            model_file = structure['model_files'][0]  # Use first model file
            patterns['component_locations']['models'] = model_file
            
            model_module = os.path.splitext(model_file)[0].replace('/', '.').replace('\\', '.')
            patterns['import_patterns']['models'] = f'from {model_module} import {{model_name}}'
            
            # Models depend on database if it exists
            if structure['database_files']:
                patterns['file_dependencies'][model_file] = structure['database_files']
        
        # Find route/API files
        if structure['route_files']:
            for route_file in structure['route_files']:
                route_module = os.path.splitext(route_file)[0].replace('/', '.').replace('\\', '.')
                patterns['import_patterns'][f'routes_{os.path.basename(route_file)}'] = f'from {route_module} import router'
                
                # Routes typically depend on models and database
                dependencies = []
                if structure['model_files']:
                    dependencies.extend(structure['model_files'])
                if structure['database_files']:
                    dependencies.extend(structure['database_files'])
                if dependencies:
                    patterns['file_dependencies'][route_file] = dependencies
        
        # Entry points depend on everything except themselves
        for entry_file in structure['entry_points']:
            dependencies = []
            dependencies.extend(structure['database_files'])
            dependencies.extend(structure['model_files'])
            # Only add route files that are not the entry file itself
            dependencies.extend([rf for rf in structure['route_files'] if rf != entry_file])
            if dependencies:
                patterns['file_dependencies'][entry_file] = dependencies
        
        return patterns
    
    def register_class(self, class_name: str, file_path: str, is_database_model: bool = False):
        """Register a class definition"""
        self.defined_classes[class_name] = file_path
        if is_database_model:
            self.database_models.append(class_name)
    
    def register_function(self, function_name: str, file_path: str):
        """Register a function definition"""
        self.defined_functions[function_name] = file_path
    
    def register_import(self, file_path: str, import_statement: str):
        """Register an import statement for a file"""
        if file_path not in self.imports_used:
            self.imports_used[file_path] = []
        if import_statement not in self.imports_used[file_path]:
            self.imports_used[file_path].append(import_statement)
    
    def get_forbidden_redefinitions(self, current_file_path: str) -> list:
        """Get list of things that should NOT be redefined in the current file"""
        forbidden = []
        
        # Don't redefine classes defined elsewhere
        for class_name, file_path in self.defined_classes.items():
            if file_path != current_file_path:
                forbidden.append(f"class {class_name}")
        
        # Don't redefine shared definitions in wrong files
        shared_defs = self.established_patterns.get('shared_definitions', {})
        for def_name, def_info in shared_defs.items():
            if def_info['location'] != current_file_path:
                forbidden.append(def_info['definition'])
        
        return forbidden
    
    def get_required_imports(self, current_file_path: str) -> list:
        """Get list of imports that should be used in the current file based on dependencies"""
        required_imports = []
        
        # Get file dependencies from patterns
        file_deps = self.established_patterns.get('file_dependencies', {})
        if current_file_path in file_deps:
            dependency_files = file_deps[current_file_path]
            
            for dep_file in dependency_files:
                # Add imports based on what's expected to be in dependency files
                if dep_file in self.project_structure['database_files']:
                    # Import database components
                    db_imports = self.established_patterns.get('import_patterns', {})
                    if 'database_base' in db_imports:
                        required_imports.append(db_imports['database_base'])
                    if 'database_session' in db_imports:
                        required_imports.append(db_imports['database_session'])
                
                elif dep_file in self.project_structure['model_files']:
                    # Import models (will be filled in during generation)
                    model_imports = self.established_patterns.get('import_patterns', {})
                    if 'models' in model_imports and self.database_models:
                        # Replace placeholder with actual model names
                        model_import_template = model_imports['models']
                        for model_name in self.database_models:
                            required_imports.append(model_import_template.replace('{model_name}', model_name))
        
        # Add SQLAlchemy imports for route/API files
        if current_file_path in self.project_structure['route_files'] or current_file_path in self.project_structure['entry_points']:
            if self.project_structure['database_files']:
                required_imports.append("from sqlalchemy.orm import Session")
        
        return list(set(required_imports))  # Remove duplicates
    
    def get_generation_context_for_file(self, file_path: str) -> dict:
        """Get comprehensive context for generating a specific file"""
        context = {
            'file_type': self._determine_file_type(file_path),
            'dependencies': self.get_required_imports(file_path),
            'forbidden_redefinitions': self.get_forbidden_redefinitions(file_path),
            'shared_definitions_locations': self.established_patterns.get('shared_definitions', {}),
            'related_files': self._get_related_files(file_path),
            'is_entry_point': file_path in self.project_structure['entry_points'],
            'framework_patterns': self.established_patterns
        }
        return context
    
    def _determine_file_type(self, file_path: str) -> str:
        """Determine the type/purpose of a file based on project structure analysis"""
        if file_path in self.project_structure['database_files']:
            return 'database'
        elif file_path in self.project_structure['model_files']:
            return 'models'
        elif file_path in self.project_structure['route_files']:
            return 'routes'
        elif file_path in self.project_structure['entry_points']:
            return 'entry_point'
        elif file_path in self.project_structure['config_files']:
            return 'config'
        elif file_path in self.project_structure['frontend_files']:
            return 'frontend'
        else:
            return 'utility'
    
    def _get_related_files(self, file_path: str) -> list:
        """Get list of files that are related to the current file"""
        related = []
        
        # Files that depend on this file
        for other_file, deps in self.established_patterns.get('file_dependencies', {}).items():
            if file_path in deps:
                related.append(other_file)
        
        # Files this file depends on
        if file_path in self.established_patterns.get('file_dependencies', {}):
            related.extend(self.established_patterns['file_dependencies'][file_path])
        
        return list(set(related))
    
    
    def update_from_generated_file(self, file_path: str, generated_code: str):
        """Analyze generated code and update context with validation and auto-fixing"""
        # Initialize validator if not already done
        if not hasattr(self, 'code_validator'):
            self.code_validator = CodeValidator(self)
        
        # Validate and auto-fix the generated code
        validation_result = self.code_validator.validate_and_fix_generated_code(file_path, generated_code)
        
        # Use the fixed code for analysis
        final_code = validation_result['fixed_code']
        
        # Log validation results
        if validation_result['fixes_applied']:
            logger.info(f"🔧 Auto-fixed {len(validation_result['fixes_applied'])} issues in {file_path}")
            for fix in validation_result['fixes_applied']:
                logger.debug(f"  Applied: {fix['action']} - {fix.get('reason', '')}")
        
        if not validation_result['is_valid']:
            logger.warning(f"⚠️ Validation issues remain in {file_path}: {len(validation_result['issues_found'])} issues")
        
        # Parse the final code for context tracking
        lines = final_code.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Track class definitions with enhanced classification
            if line.startswith('class ') and ':' in line:
                class_name = line.split('class ')[1].split('(')[0].split(':')[0].strip()
                
                # Enhanced DB model detection
                is_db_model = False
                if 'Base' in line and not 'BaseModel' in line:
                    is_db_model = True
                elif any(keyword in class_name for keyword in ['Model']) and 'BaseModel' not in line:
                    is_db_model = True
                
                self.register_class(class_name, file_path, is_db_model)
            
            # Track function definitions
            elif line.startswith('def ') and '(' in line:
                func_name = line.split('def ')[1].split('(')[0].strip()
                self.register_function(func_name, file_path)
            
            # Track import statements
            elif line.startswith(('import ', 'from ')):
                self.register_import(file_path, line)
        
        # Add to generation order if not already there
        if file_path not in self.generation_order:
            self.generation_order.append(file_path)
        
        # Store validation result for reporting
        if not hasattr(self, 'validation_results'):
            self.validation_results = {}
        self.validation_results[file_path] = validation_result
        
        return validation_result  # Return the validation result for caller use
    
    def get_context_summary(self) -> str:
        """Get a summary of the current project context for prompts"""
        summary = f"""
PROJECT CONTEXT SUMMARY:
- Project: {self.project_name}
- Framework: {self.tech_stack}
- Generated Files: {len(self.generation_order)}

PROJECT STRUCTURE ANALYSIS:
- Database Files: {self.project_structure['database_files']}
- Model Files: {self.project_structure['model_files']}
- Route Files: {self.project_structure['route_files']}
- Entry Points: {self.project_structure['entry_points']}
- Frontend Files: {len(self.project_structure['frontend_files'])} files

DEFINED CLASSES: {list(self.defined_classes.keys())}
DATABASE MODELS: {self.database_models}
DEFINED FUNCTIONS: {list(self.defined_functions.keys())}

DYNAMIC PATTERNS DETECTED:
{json.dumps(self.established_patterns, indent=2)}

GENERATION ORDER: {self.generation_order}
        """.strip()
        return summary
    
    def get_context_for_prompt(self, current_file_path: str) -> str:
        """Get context-aware instructions for LLM prompt"""
        context = self.get_generation_context_for_file(current_file_path)
        file_type = context['file_type']
        
        instructions = []
        
        # Add file-specific instructions
        instructions.append(f"FILE TYPE: {file_type.upper()}")
        
        # Add forbidden redefinitions
        if context['forbidden_redefinitions']:
            instructions.append("FORBIDDEN PATTERNS (DO NOT include these):")
            for forbidden in context['forbidden_redefinitions']:
                instructions.append(f"  - {forbidden}")
        
        # Add required imports
        if context['dependencies']:
            instructions.append("REQUIRED IMPORTS:")
            for imp in context['dependencies']:
                instructions.append(f"  - {imp}")
        
        # Add shared definitions info
        if context['shared_definitions_locations']:
            instructions.append("SHARED DEFINITIONS (already defined elsewhere):")
            for def_name, def_info in context['shared_definitions_locations'].items():
                if def_info['location'] != current_file_path:
                    instructions.append(f"  - {def_name} is defined in {def_info['location']}")
                    instructions.append(f"    Use: {def_info['import_pattern']}")
        
        # Add file-specific guidance
        if file_type == 'models' and self.project_structure['database_files']:
            instructions.append("MODEL FILE GUIDANCE:")
            instructions.append("  - Import Base from database module")
            instructions.append("  - Define SQLAlchemy models inheriting from Base")
            instructions.append("  - Do NOT redefine declarative_base()")
        
        elif file_type == 'database':
            instructions.append("DATABASE FILE GUIDANCE:")
            instructions.append("  - Define Base = declarative_base() HERE")
            instructions.append("  - Define database engine and session factory")
            instructions.append("  - This file provides shared database components")
        
        elif file_type == 'routes':
            instructions.append("ROUTES FILE GUIDANCE:")
            instructions.append("  - Import models and database session")
            instructions.append("  - Define FastAPI router with endpoints")
            instructions.append("  - Use dependency injection for database sessions")
        
        elif file_type == 'entry_point':
            instructions.append("ENTRY POINT GUIDANCE:")
            instructions.append("  - Import and configure all application components")
            instructions.append("  - Set up CORS, static files, and routes")
            instructions.append("  - Make runnable with uvicorn")
        
        return "\n".join(instructions)
# --- end logic mới 28/6 ---

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
        
        # --- modify lại dựa trên logic mới 28/6 ---
        # Generate code using LLM with retries
        for attempt in range(self._config.max_retries):
            try:
                # Build enhanced prompt with project context
                base_prompt_args = {
                    'file_path': file_path,
                    'project_name': requirements.get('project_Overview', {}).get('project_Name', 'this application'),
                    'backend_language_framework': f"{requirements.get('technology_Stack', {}).get('backend', {}).get('language', 'Python')} {requirements.get('technology_Stack', {}).get('backend', {}).get('framework', 'FastAPI')}",
                    'frontend_language_framework': f"{requirements.get('technology_Stack', {}).get('frontend', {}).get('language', 'HTML/CSS/JS')} {requirements.get('technology_Stack', {}).get('frontend', {}).get('framework', 'Vanilla')}",
                    'storage_type': context.get('design_data', {}).get('data_Design', {}).get('storage_Type', 'sqlite'),
                    'backend_module_path': context.get('backend_module_path', 'main'),
                    'frontend_dir': context.get('frontend_dir', 'frontend'),
                    'css_path': context.get('css_path', 'css/style.css'),
                    'js_files_to_link': context.get('js_files_to_link', []),
                    'json_design': context.get('design_data', {}),
                    'json_spec': requirements
                }
                
                # Add project context if available
                if 'project_context' in context:
                    project_context = context['project_context']
                    base_prompt_args['project_context_summary'] = project_context.get_context_summary()
                    base_prompt_args['context_instructions'] = context.get('context_instructions', '')
                else:
                    base_prompt_args['project_context_summary'] = "No project context available"
                    base_prompt_args['context_instructions'] = ""
                
                prompt_template = self._template_manager.get_template(
                    tech_stack, 'prompt_template',
                    **base_prompt_args
                )
                # --- end modify ---
                
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
            logger.info("🚀 Starting project generation...")
            logger.info(f"Design data keys: {list(design_data.keys()) if design_data else 'None'}")
            logger.info(f"Spec data keys: {list(spec_data.keys()) if spec_data else 'None'}")
            
            # 1. Determine project root and initialize tools/error tracker for this run
            project_name = design_data.get('folder_Structure', {}).get('root_Project_Directory_Name')
            if not project_name:
                logger.error("❌ Missing 'root_Project_Directory_Name' in design data")
                raise ValueError("Design data is missing 'root_Project_Directory_Name'.")
            
            logger.info(f"📁 Project name: {project_name}")
            project_root = os.path.abspath(os.path.join(self.config.base_output_dir, project_name))
            logger.info(f"📂 Project root: {project_root}")
            
            self._setup_project_tools(project_root)
            
            logger.info(f"Starting project generation for: {project_name} at {project_root}")
            
            # 2. Validate JSON inputs
            self._validate_json(design_data, spec_data)
            logger.info("✅ JSON inputs validated successfully.")

            # 3. Create project structure
            structure_result = self._create_project_structure(design_data, project_root)
            logger.info(f"✅ Structure creation result: {structure_result}")
            
            # 4. Generate all project files
            files_result = self._generate_project_files(design_data, spec_data, project_root)
            logger.info(f"✅ File generation result: {files_result}")
            
            # 5. Create the run script to start the application
            self._create_run_script(project_root, spec_data, design_data)
            logger.info(f"✅ Created run script for project '{project_name}'.")
            
            logger.info(f"🎉 Project generation completed successfully for: {project_root}")
            
            # This success message is what the AutoGen Coder will report back to the ProjectManager.
            return f"Successfully generated project '{project_name}' at {project_root}. The 'run.bat' script is ready."

        except Exception as e:
            error_project_name = project_name or "unknown_project"
            logger.error(f"❌ Project generation failed for '{error_project_name}': {e}", exc_info=True)
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
        
        # Initialize project context for cross-file awareness
        project_name = design_data.get('folder_Structure', {}).get('root_Project_Directory_Name', 'project')
        tech_stack = spec_data.get('technology_Stack', {}).get('backend', {}).get('framework', 'fastapi')
        project_context = ProjectContext(project_name, tech_stack, design_data)
        
        logger.info(f"🧠 Initialized ProjectContext with structure analysis:")
        logger.info(f"   Database files: {project_context.project_structure['database_files']}")
        logger.info(f"   Model files: {project_context.project_structure['model_files']}")
        logger.info(f"   Route files: {project_context.project_structure['route_files']}")
        logger.info(f"   Entry points: {project_context.project_structure['entry_points']}")
        
        file_generator = next(t for t in self.tools if isinstance(t, FileGeneratorTool))
        generated_files = []
        
        # Sort files to generate database/model files first, then routes, then entry points
        sorted_files = self._sort_files_by_dependency_order(structure, project_context)
        
        for item in sorted_files:
            if 'directory' not in item.get('description', '').lower():
                # Validate and sanitize the path to prevent directory traversal
                item_path = item['path'].strip('/\\')
                if '..' in item_path or item_path.startswith('/') or item_path.startswith('\\'):
                    logger.warning(f"Skipping potentially unsafe path: {item_path}")
                    continue
                
                file_path = os.path.join(project_root, item_path)
                
                # Ensure the directory exists before creating the file
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # --- logic mới 28/6 ---
                # Build enhanced context with project-wide awareness
                file_context = context_for_generation.copy()
                file_context['file_info'] = item
                file_context['project_context'] = project_context
                file_context['context_instructions'] = project_context.get_context_for_prompt(item_path)
                
                logger.info(f"📝 Generating {item_path} (type: {project_context._determine_file_type(item_path)})")
                
                code = file_generator._run(file_path, file_context, spec_data)
                
                # Update project context with what was generated (includes validation and auto-fixing)
                validation_result = project_context.update_from_generated_file(item_path, code)
                
                # Use the fixed code for writing to file
                final_code = validation_result['fixed_code']
                # --- end logic mới ---
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(final_code)
                
                generated_files.append(file_path)
                
                # Log validation results
                if validation_result['fixes_applied']:
                    logger.info(f"  ✅ Auto-fixed {len(validation_result['fixes_applied'])} issues")
                else:
                    logger.debug(f"  ✅ No issues found")
                logger.debug(f"✅ Generated and analyzed {item_path}")
        
        logger.info(f"📊 Final project context summary:")
        logger.info(project_context.get_context_summary())
        
        return f"Generated {len(generated_files)} files with project-wide context awareness"
    
    def _sort_files_by_dependency_order(self, structure: list, project_context: ProjectContext) -> list:
        """Sort files by dependency order to generate foundational files first"""
        files_by_priority = {
            'config': [],
            'database': [], 
            'models': [],
            'routes': [],
            'entry_points': [],
            'frontend': [],
            'other': []
        }
        
        for item in structure:
            if 'directory' in item.get('description', '').lower():
                continue
                
            item_path = item['path'].strip('/\\')
            file_type = project_context._determine_file_type(item_path)
            
            if file_type in files_by_priority:
                files_by_priority[file_type].append(item)
            else:
                files_by_priority['other'].append(item)
        
        # Return in dependency order
        sorted_files = []
        for priority in ['config', 'database', 'models', 'routes', 'other', 'frontend', 'entry_points']:
            sorted_files.extend(files_by_priority[priority])
        
        return sorted_files
    
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