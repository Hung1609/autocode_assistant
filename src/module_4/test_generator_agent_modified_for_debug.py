import os
import json
import time
import logging
import ast
import subprocess
import re
import argparse
import sys

from google.generativeai import GenerativeModel, configure
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('testgen.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

API_CALL_DELAY_SECONDS = 5
api_key = os.getenv('GEMINI_API_KEY')
configure(api_key=api_key)
logger.info("Gemini API configured successfully for test generator.")

DEFAULT_MODEL = 'gemini-2.0-flash'
# Sử dụng os.getenv để linh hoạt cấu hình thư mục gốc
BASE_GENERATED_DIR = os.getenv('BASE_GENERATED_DIR', 'code_generated_result')
OUTPUTS_DIR = os.getenv('OUTPUTS_DIR', r'C:\Users\Hoang Duy\Documents\Phan Lac Hung\autocode_assistant\src\module_1_vs_2\outputs')
# OUTPUTS_DIR = os.getenv('OUTPUTS_DIR', r'C:\Users\ADMIN\Documents\Foxconn\autocode_assistant\src\module_1_vs_2\outputs')
TEST_OUTPUT_DIR_NAME = "tests"
TEST_LOG_FILE = "test_results.log"
TEST_HISTORY_LOG_FILE = "test_results_history.log"
TEST_GENERATED_FLAG = ".test_generated" # Đánh dấu các file test đã được sinh ra

def create_pytest_ini(project_root):
    pytest_ini_path = os.path.join(project_root, "pytest.ini")
    pytest_ini_content = """\
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
# Configure cachedir to a user-specific temporary directory if default causes issues.
# pytest will create this directory if it doesn't exist.
cachedir = tmp_pytest_cache/
"""
    # Kiểm tra xem pytest.ini đã tồn tại và có nội dung tương tự chưa để tránh ghi đè không cần thiết
    if os.path.exists(pytest_ini_path):
        try:
            with open(pytest_ini_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
            # Kiểm tra sự hiện diện của các cấu hình chính
            if "asyncio_mode = auto" in current_content and \
               "asyncio_default_fixture_loop_scope = function" in current_content and \
               "cachedir = tmp_pytest_cache/" in current_content:
                logger.info(f"pytest.ini already exists with required asyncio and cachedir settings in {project_root}. Skipping creation.")
                return
        except Exception as e:
            logger.warning(f"Could not read existing pytest.ini in {project_root}: {e}. Overwriting.")

    try:
        with open(pytest_ini_path, 'w', encoding='utf-8') as f:
            f.write(pytest_ini_content)
        logger.info(f"Created/Updated pytest.ini in {project_root} with asyncio and cachedir configurations.")
    except Exception as e:
        logger.error(f"Failed to create/update pytest.ini in {project_root}: {e}")

def generate_run_test_bat_script(project_root, venv_python_path):
    bat_file_path = os.path.join(project_root, "run_test.bat")
    bat_content = fr"""
@echo off  REM Turn off echo to make Python capture output easier to read
setlocal EnableDelayedExpansion

REM Write directly to stdout so Python can capture, don't use log file immediately
echo --- run_test.bat STARTED ---

REM The following commands are redirected to debug_test_agent.log
echo Current Directory (when batch started): "%CD%" > debug_test_agent.log 2>&1
echo PROJECT_ROOT variable (calculated): "%~dp0" >> debug_test_agent.log 2>&1

echo Changing directory to project root... >> debug_test_agent.log 2>&1
cd /d "%~dp0" >> debug_test_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to change to project root directory. Exiting with code %ERRORLEVEL%. >> debug_test_agent.log 2>&1
    exit /b 1
)
echo Current Directory (after cd): "%CD%" >> debug_test_agent.log 2>&1

echo Cleaning up previous test log file... >> debug_test_agent.log 2>&1
if exist "{TEST_LOG_FILE}" (
    del "{TEST_LOG_FILE}" >> debug_test_agent.log 2>&1
    if %ERRORLEVEL% neq 0 (
        echo WARNING: Failed to delete old test log file: "{TEST_LOG_FILE}". >> debug_test_agent.log 2>&1
    ) else (
        echo Old test log file deleted: "{TEST_LOG_FILE}". >> debug_test_agent.log 2>&1
    )
) else (
    echo No old test log file to delete: "{TEST_LOG_FILE}". >> debug_test_agent.log 2>&1
)

echo Checking for Python at: "{venv_python_path}" >> debug_test_agent.log 2>&1
"{venv_python_path}" --version >> debug_test_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found at "{venv_python_path}". Exiting with code %ERRORLEVEL%. >> debug_test_agent.log 2>&1
    exit /b 1
)

echo Attempting to activate virtual environment... >> debug_test_agent.log 2>&1
echo Activating script path: "%~dp0venv\Scripts\activate.bat" >> debug_test_agent.log 2>&1
call "%~dp0venv\Scripts\activate.bat" >> debug_test_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to activate virtual environment. Error code: %ERRORLEVEL%. >> debug_test_agent.log 2>&1
    echo Please ensure the venv\Scripts\activate.bat exists and is not corrupted. >> debug_test_agent.log 2>&1
    exit /b 1
)
echo Virtual environment activated successfully. >> debug_test_agent.log 2>&1

echo Now, checking python.exe in PATH from activated venv: >> debug_test_agent.log 2>&1
where python.exe >> debug_test_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo WARNING: python.exe not found in PATH after venv activation. This might indicate an issue with activate.bat. >> debug_test_agent.log 2>&1
)

echo Running pytest with --exitfirst and --tb=long... >> debug_test_agent.log 2>&1
"{venv_python_path}" -m pytest tests --exitfirst --tb=long -v > "{TEST_LOG_FILE}" 2>&1
set TEST_EXIT_CODE=%ERRORLEVEL%

echo Deactivating virtual environment... >> debug_test_agent.log 2>&1
deactivate >> debug_test_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo WARNING: Failed to deactivate virtual environment. >> debug_test_agent.log 2>&1
)

if %TEST_EXIT_CODE% neq 0 (
    echo ERROR: Tests failed. Check "{TEST_LOG_FILE}" for details. >> debug_test_agent.log 2>&1
    exit /b %TEST_EXIT_CODE%
)

echo Tests completed successfully. >> debug_test_agent.log 2>&1
exit /b 0
"""
    try:
        with open(bat_file_path, 'w', encoding='utf-8') as f:
            f.write(bat_content)
        logger.info(f"Created run_test.bat at {bat_file_path}")
        return bat_file_path
    except Exception as e:
        logger.error(f"Failed to create run_test.bat: {e}")
        raise

def detect_project_and_framework(specified_project_name=None, design_file_path=None, spec_file_path=None):
    logger.info("Detecting project and framework...")

    if not os.path.exists(BASE_GENERATED_DIR):
        msg = f"Base directory '{BASE_GENERATED_DIR}' does not exist. Run codegen_agent.py first."
        logger.error(msg)
        raise FileNotFoundError(msg)

    if not os.path.exists(OUTPUTS_DIR):
        msg = f"Outputs directory '{OUTPUTS_DIR}' does not exist. Ensure your design/spec files are there."
        logger.error(msg)
        raise FileNotFoundError(msg)

    project_root = None
    design_data = None
    spec_data = None

    # First approach: Using argparse to choose design/spec files
    if design_file_path and spec_file_path:
        logger.info(f"Using specified design file: {design_file_path} and spec file: {spec_file_path}")
        try:
            with open(design_file_path, 'r', encoding='utf-8') as f:
                design_data = json.load(f)
            with open(spec_file_path, 'r', encoding='utf-8') as f:
                spec_data = json.load(f)

            project_name = design_data.get('folder_Structure', {}).get('root_Project_Directory_Name')
            if project_name:
                potential_project_root = os.path.join(BASE_GENERATED_DIR, project_name)
                if os.path.isdir(potential_project_root):
                    project_root = os.path.abspath(potential_project_root) # đường dẫn tuyệt đối
                    logger.info(f"Detected project root from specified design: {project_root}")
                else:
                    logger.warning(f"Project directory '{potential_project_root}' from specified design not found in '{BASE_GENERATED_DIR}'.")
            else:
                logger.warning("Root project directory name not found in specified design file.")

        except Exception as e:
            logger.error(f"Failed to load/parse specified JSON files: {e}")
            raise ValueError(f"Invalid specified JSON files: {e}")
    
    # Second approach: Fallback to specified project name (if provided) and find latest design/spec in OUTPUTS_DIR
    if not project_root and specified_project_name:
        potential_project_root = os.path.join(BASE_GENERATED_DIR, specified_project_name)
        if os.path.isdir(potential_project_root):
            project_root = os.path.abspath(potential_project_root)
            logger.info(f"Using specified project folder: {project_root}")
            
            relevant_design_files = [f for f in os.listdir(OUTPUTS_DIR) if f.endswith('.design.json') and specified_project_name in f]
            relevant_spec_files = [f for f in os.listdir(OUTPUTS_DIR) if f.endswith('.spec.json') and specified_project_name in f]

            if relevant_design_files:
                design_file_path = os.path.join(OUTPUTS_DIR, max(relevant_design_files, key=lambda f: os.path.getmtime(os.path.join(OUTPUTS_DIR, f))))
                try:
                    with open(design_file_path, 'r', encoding='utf-8') as f:
                        design_data = json.load(f)
                    logger.info(f"Loaded latest design file for specified project: {design_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to load design file '{design_file_path}' for specified project: {e}")
            if relevant_spec_files:
                spec_file_path = os.path.join(OUTPUTS_DIR, max(relevant_spec_files, key=lambda f: os.path.getmtime(os.path.join(OUTPUTS_DIR, f))))
                try:
                    with open(spec_file_path, 'r', encoding='utf-8') as f:
                        spec_data = json.load(f)
                    logger.info(f"Loaded latest spec file for specified project: {spec_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to load spec file '{spec_file_path}' for specified project: {e}")
        else:
            logger.warning(f"Specified project folder '{specified_project_name}' not found. Falling back to most recent project/files.")

    # Third approach (Default): Find the most recent project folder and associated design/spec files
    if not project_root:
        projects = [d for d in os.listdir(BASE_GENERATED_DIR) if os.path.isdir(os.path.join(BASE_GENERATED_DIR, d))]
        if not projects:
            msg = f"No project folders found in '{BASE_GENERATED_DIR}'."
            logger.error(msg)
            raise ValueError(msg)
        
        project_dir_name = max(projects, key=lambda p: os.path.getctime(os.path.join(BASE_GENERATED_DIR, p)))
        project_root = os.path.abspath(os.path.join(BASE_GENERATED_DIR, project_dir_name))
        logger.info(f"Using most recent project folder: {project_root}")

        all_design_files = [f for f in os.listdir(OUTPUTS_DIR) if f.endswith('.design.json')]
        all_spec_files = [f for f in os.listdir(OUTPUTS_DIR) if f.endswith('.spec.json')]

        if all_design_files:
            design_file_path = os.path.join(OUTPUTS_DIR, max(all_design_files, key=lambda f: os.path.getmtime(os.path.join(OUTPUTS_DIR, f))))
            try:
                with open(design_file_path, 'r', encoding='utf-8') as f:
                    design_data = json.load(f)
                logger.info(f"Loaded latest design file: {design_file_path}")
            except Exception as e:
                logger.warning(f"Failed to load latest design file '{design_file_path}': {e}")
        else:
            logger.warning("No .design.json file found in OUTPUTS_DIR.")

        if all_spec_files:
            spec_file_path = os.path.join(OUTPUTS_DIR, max(all_spec_files, key=lambda f: os.path.getmtime(os.path.join(OUTPUTS_DIR, f))))
            try:
                with open(spec_file_path, 'r', encoding='utf-8') as f:
                    spec_data = json.load(f)
                logger.info(f"Loaded latest specification file: {spec_file_path}")
            except Exception as e:
                logger.warning(f"Failed to load latest specification file '{spec_file_path}': {e}")
        else:
            logger.warning("No .spec.json file found in OUTPUTS_DIR.")

    if not project_root:
        raise ValueError("Could not determine a project root to test.")
    if not design_data:
        logger.warning(f"No valid design data found for project {os.path.basename(project_root)}. Framework detection might be less accurate.")
    if not spec_data:
        logger.warning(f"No valid specification data found for project {os.path.basename(project_root)}. Framework detection might be less accurate.")

    framework = "unknown"
    app_package = "app"  # Default app package

    if design_data:
        folder_structure = design_data.get('folder_Structure', {}).get('structure', [])
        for item in folder_structure:
            relative_path = item['path'].strip().replace('\\', '/')
            if relative_path.endswith('main.py'):
                backend_dir = os.path.dirname(relative_path).lstrip('/').lstrip('\\') # Use lstrip for robustness
                app_package = backend_dir or "app"
                logger.info(f"Detected app package from JSON design: {app_package}")
                break # Found main.py, so app_package is set
    
    if spec_data:
        tech_stack = spec_data.get('technology_Stack', {}).get('backend', {})
        framework_name = tech_stack.get('framework', '').lower()
        if "fastapi" in framework_name:
            framework = "fastapi"
        elif "flask" in framework_name:
            framework = "flask"
        logger.info(f"Detected framework from JSON specification: {framework}")

    # Fallback: Check requirements.txt (only if framework is still unknown)
    if framework == "unknown":
        requirements_path = os.path.join(project_root, "requirements.txt")
        if os.path.exists(requirements_path):
            with open(requirements_path, 'r', encoding='utf-8') as f:
                reqs = f.read().lower()
                if "fastapi" in reqs:
                    framework = "fastapi"
                    if app_package == "app":  # Only override if JSON didn't set it
                        app_package = "backend" # Common FastAPI app_package name
                elif "flask" in reqs:
                    framework = "flask"
                    if app_package == "app":  # Only override if JSON didn't set it
                        app_package = "app" # Common Flask app_package name

    # Fallback: Inspect source files (only if framework is still unknown)
    if framework == "unknown":
        for root, _, files in os.walk(project_root):
            for file in files:
                if file.endswith(".py"):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            content = f.read().lower()
                            if "from fastapi import" in content:
                                framework = "fastapi"
                                if app_package == "app":
                                    app_package = "backend"
                                break
                            elif "from flask import" in content:
                                framework = "flask"
                                if app_package == "app":
                                    app_package = "app"
                                break
                    except Exception as e:
                        logger.warning(f"Failed to read {file} for framework detection: {e}")
            if framework != "unknown":
                break

    if framework == "unknown":
        logger.warning("Could not detect framework. Defaulting to Flask.")
        framework = "flask"
        if app_package == "app":
            app_package = "app"

    logger.info(f"Final detected project: {os.path.basename(project_root)}, Framework: {framework}, App Package: {app_package}")
    return project_root, framework, app_package, design_data, spec_data

def ensure_init_py_recursive(base_directory_path):
    """
    Ensures all subdirectories within base_directory_path have an __init__.py file
    to make them recognized Python packages.
    """
    for root, dirs, files in os.walk(base_directory_path):
        if 'venv' in dirs:
            dirs.remove('venv') # This modifies dirs in-place for os.walk to skip it
            logger.debug(f"Skipping 'venv' directory in {root}")

        if any(f.endswith(".py") for f in files):
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

def update_requirements_for_testing(project_root):
    """
    Adds pytest, pytest-mock, pytest-asyncio to requirements.txt if not present.
    Returns True if changes were made, False otherwise.
    """
    requirements_path = os.path.join(project_root, "requirements.txt")
    
    if not os.path.exists(requirements_path):
        logger.warning(f"requirements.txt not found at {requirements_path}. Creating an empty one.")
        with open(requirements_path, 'w', encoding='utf-8') as f:
            f.write("")
        existing_reqs = []
    else:
        with open(requirements_path, 'r', encoding='utf-8') as f:
            existing_reqs = [line.strip() for line in f if line.strip()]

    pytest_present = False
    pytest_mock_present = False
    pytest_asyncio_present = False

    for req in existing_reqs:
        if re.match(r"^pytest($|[<=>~])", req.lower()):
            pytest_present = True
        if re.match(r"^pytest-mock($|[<=>~])", req.lower()):
            pytest_mock_present = True
        if re.match(r"^pytest-asyncio($|[<=>~])", req.lower()):
            pytest_asyncio_present = True

    reqs_to_add = []
    if not pytest_present:
        reqs_to_add.append("pytest")
    if not pytest_mock_present:
        reqs_to_add.append("pytest-mock")
    if not pytest_asyncio_present:
        reqs_to_add.append("pytest-asyncio")

    if reqs_to_add:
        with open(requirements_path, 'a', encoding='utf-8') as f:
            for req in reqs_to_add:
                f.write(f"\n{req}")
        logger.info(f"Added {', '.join(reqs_to_add)} to {requirements_path}")
        return True
    else:
        logger.info("All required test dependencies (pytest, pytest-mock, pytest-asyncio) are already present in requirements.txt. No update needed.")
        return False

def install_project_dependencies(project_root):
    venv_python_path = os.path.join(project_root, "venv", "Scripts", "python.exe")
    requirements_file_name = "requirements.txt" # Chỉ lấy tên file
    requirements_path_full = os.path.join(project_root, requirements_file_name)

    if not os.path.exists(venv_python_path):
        logger.error(f"Virtual environment python executable not found at {venv_python_path}. Please ensure 'venv' exists and is properly set up in the generated project.")
        raise FileNotFoundError(f"Project venv not found: {venv_python_path}")
    
    if not os.path.exists(requirements_path_full): # Kiểm tra đường dẫn đầy đủ
        logger.warning(f"requirements.txt not found at {requirements_path_full}. Skipping dependency installation.")
        return

    logger.info(f"Installing dependencies from {requirements_path_full} into project venv...")
    try:
        result = subprocess.run(
            [venv_python_path, "-m", "pip", "install", "-r", requirements_file_name], # <--- Thay đổi ở đây
            capture_output=True,
            text=True,
            check=True,
            cwd=project_root # project_root là thư mục chứa requirements.txt
        )
        logger.info(f"Successfully installed dependencies. Pip output:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"Pip warnings/errors during dependency installation:\n{result.stderr}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies. Exit code: {e.returncode}")
        logger.error(f"Pip stdout:\n{e.stdout}")
        logger.error(f"Pip stderr:\n{e.stderr}")
        raise

def generate_unit_tests(function_code, function_name, module_path, framework, context, is_method=False, class_name=None):
    if not function_code:
        logger.warning(f"No function code provided for {function_name}. Skipping unit test generation.")
        return None

    model = GenerativeModel(DEFAULT_MODEL)
    logger.info(f"Using model: {DEFAULT_MODEL} for unit test generation for '{function_name}'.")

    framework_specific = {
        "flask": {
            "imports": "from flask import request, render_template, redirect, url_for",
            "mock_targets": f"{module_path}.request, {module_path}.render_template, {module_path}.redirect, {module_path}.url_for",
            "context_hint": "Use app.test_request_context() for Flask routes. Mock db.session and models appropriately. Target mocks at the module where the function under test looks up the dependency."
        },
        "fastapi": {
            "imports": "from fastapi import Request, HTTPException, Depends",
            "mock_targets": f"{module_path}.Request, {module_path}.HTTPException",
            "context_hint": "Mock FastAPI dependencies (like Depends) using pytest-mock's `mocker` fixture or `unittest.mock.patch` where the dependency is looked up. For routes, use FastAPI's `TestClient` for API calls from the test suite. Ensure mocks for database sessions are handled correctly."
        }
    }.get(framework, {"imports": "", "mock_targets": "", "context_hint": ""})

    target_import = ""
    target_source_info = ""
    test_file_prefix = "" 
    
    if is_method and class_name:
        target_import = f"from {module_path} import {class_name}"
        target_source_info = f"{module_path}.{class_name}.{function_name}"
        method_context = (
            f"This is a method of class `{class_name}`. When testing, you will need to "
            f"instantiate `{class_name}` or mock its instance, and then call its method `{function_name}`. "
            f"Mock `self` if necessary for the method's behavior. "
            f"The source info should be in the format: `module.ClassName.methodName`."
        )
        test_file_prefix = f"test_{class_name}_"
    else:
        target_import = f"from {module_path} import {function_name}"
        target_source_info = f"{module_path}.{function_name}"
        method_context = f"This is a top-level function. The source info should be in the format: `module.functionName`."
        test_file_prefix = f"test_{function_name}_"

    # Khôi phục prompt template chi tiết hơn
    prompt = f"""
    You are an expert Python test engineer specializing in the pytest framework and testing {framework} applications.
    Your task is to generate comprehensive unit tests for the Python function/method below using the pytest framework and `pytest-mock`.

    Function Name: {function_name}
    Module Path: {module_path}
    Framework: {framework}
    {method_context}

    Function Code:
    ```python
    {function_code}
    ```

    Context:
    {context}
    {framework_specific['context_hint']}

    Requirements for Test Generation:
    1.  **Strictly Output Code Only**: Your response MUST be only the raw Python code for the test file. Do NOT include any explanations, comments outside the code blocks, or markdown formatting (like ```python ... ```).
    2.  **File Naming Convention**: The generated test file should be named based on the function/method, for example: `{test_file_prefix}test_scenario.py` or just `{test_file_prefix}scenarios.py`.
    3.  **Test Naming Convention**: All test functions within the file MUST start with `test_` followed by the function/method name, and then a descriptive suffix for the test scenario. 
        For example: `def test_{function_name}_success(...)`, `def test_{function_name}_invalid_input(...)`.
        If testing a method (e.g., `{class_name}.{function_name}`), the test function name should be `test_{class_name}_{function_name}_scenario`.
        Example: `def test_Flashcard_to_dict_success(...)`.
    4.  **Imports**: Include all necessary imports: `pytest`, `unittest.mock` (or `pytest-mock`'s `mocker` fixture), relevant modules from `{framework_specific['imports']}`, and **specifically import the target for testing: `{target_import}`.**
        - **Critical Import Note**: When importing functions/classes from modules, ensure the module path exactly matches `{module_path}`. For example, if `get_db` is in `backend.database`, import it as `from backend.database import get_db`, not `from backend.db import get_db`. LLM, always use the `Module Path` provided (`{module_path}`) for imports.
    5.  **Mocking Dependencies**:
        -   Properly mock all external dependencies.
        -   Specifically mock: {framework_specific['mock_targets']}.
        -   Crucially, ensure patches target the **correct module where the object is looked up by the function under test**, not just where it's defined.
        -   Use `pytest-mock`'s `mocker` fixture where appropriate, or `unittest.mock.patch`.
    6.  **Test Scenarios**:
        -   Test the "happy path" where the function/method behaves as expected with valid inputs.
        -   Test edge cases, invalid inputs, and error conditions (e.g., missing data, database errors, HTTP exceptions).
        -   Verify that mocks for collaborators (like database session methods or external API calls) are called with the expected arguments.
        -   Assert the function/method's return value or expected side effects.
    7.  **Test Structure**:
        -   Use pytest conventions (fixtures).
        -   **Important for `map_test_to_source`**: Include a comment like `# source_info: {target_source_info}` at the beginning of each test function's body. This metadata is critical for tracing test failures back to the source.
    8.  **Runnability**: Ensure tests are runnable with `pytest` from the project root.

    Generate the Python code for the test file now.
    """
    # logger.debug(f"Unit test prompt for {function_name}:\n{prompt[:1000]}...") # Log first 1000 chars of prompt
    time.sleep(API_CALL_DELAY_SECONDS)

    try:
        response = model.generate_content(prompt)
        generated_text = response.text.strip()
        if generated_text.startswith("```python"):
            generated_text = generated_text[len("```python"):].strip()
        if generated_text.endswith("```"):
            generated_text = generated_text[:-3].strip()
        
        if not generated_text.strip():
            logger.warning(f"LLM returned empty content for unit tests for {function_name}. Skipping file creation.")
            return None
        return generated_text
    except Exception as e:
        logger.error(f"Failed to generate unit tests for {function_name}: {e}", exc_info=True)
        return None

def generate_integration_tests(app_package, framework, endpoints, project_root):
    model = GenerativeModel(DEFAULT_MODEL)
    logger.info(f"Generating integration tests for {app_package} using {DEFAULT_MODEL}")
    
    framework_specific = {
        "flask": {
            "client_import": "from flask.testing import FlaskClient",
            "client_setup": "client = app.test_client()",
            "request_example": "client.get('/your-endpoint')",
            "app_import": "from app import app"
        },
        "fastapi": {
            "client_import": "from fastapi.testclient import TestClient",
            "client_setup": f"from {app_package}.main import app; client = TestClient(app)",
            "request_example": "client.get('/your-endpoint')",
            "app_import": f"from {app_package}.main import app"
        }
    }.get(framework, {"client_import": "", "client_setup": "", "request_example": "", "app_import": ""})

    if not endpoints:
        logger.warning("No API endpoints provided for integration testing. Skipping integration test generation.")
        return None
    
    # Khôi phục prompt template chi tiết hơn
    prompt = f"""
    You are an expert Python test engineer specializing in the pytest framework and testing {framework} applications.
    Your task is to generate comprehensive pytest integration tests for the {framework} application.

    Module Path of main app: {app_package}.main
    Application Entry Point: `app` (e.g., `from {app_package}.main import app`)

    API Endpoints to Test:
    {json.dumps(endpoints, indent=2)}

    Requirements for Test Generation:
    1.  **Strictly Output Code Only**: Your response MUST be only the raw Python code for the test file. Do NOT include any explanations, comments outside the code blocks, or markdown formatting (like ```python ... ```).
    2.  **File Naming Convention**: The generated test file for integration tests should be named `test_integration.py`.
    3.  **Test Naming Convention**: All test functions within `test_integration.py` MUST start with `test_` followed by the API action and scenario (e.g., `test_create_flashcard_success`, `test_get_flashcards_empty`).
    4.  **Crucial Source Information (for Debugging)**: For EACH test function in `test_integration.py`, you MUST include a comment indicating the source endpoint function it tests. This is CRITICAL for our automated debugging system.
        The format MUST be: `# source_info: backend.routers.your_router_file.your_endpoint_function`
        If the endpoint is in `backend.main.py`, use: `# source_info: backend.main.your_endpoint_function`
        Example: For a test of `POST /api/flashcards` (handled by `create_flashcard` in `backend.routers.flashcards.py`), the comment in the test function should be `# source_info: backend.routers.flashcards.create_flashcard`.
        **DO NOT OMIT THIS COMMENT.** Its presence and exact format are essential.
    5.  **Imports**: Include all necessary imports: `pytest`, `{framework_specific['client_import']}`, `{framework_specific['app_import']}` (to get the `app` instance for the client), and any other standard libraries like `json`, `os`, `uuid` if needed for test data.
    6.  **Test Client Setup**: Set up a test client using `{framework_specific['client_setup']}`.
    7.  **Test Scenarios**:
        -   For each endpoint:
            -   Test with valid inputs and verify successful responses (status code 200/201, correct JSON payload).
            -   Test with invalid inputs (e.g., wrong data types, missing fields) and verify appropriate error responses (e.g., 400, 422).
            -   Test edge cases (e.g., empty lists, boundary conditions if applicable).
            -   If applicable, test sequential operations (e.g., create an item, then retrieve it, then update it, then delete it).
        -   Verify response status codes (e.g., `assert response.status_code == 200`).
        -   Verify JSON payloads (e.g., `assert response.json() == expected_data`).
        -   If database interaction is involved, consider setting up and tearing down a temporary test database using pytest fixtures.
    8.  **Test Structure**:
        -   Use pytest conventions (fixtures).
        -   Organize tests logically.
    9.  **Runnability**: Ensure tests are runnable with `pytest` from the project root (`{project_root}`).

    Generate the Python code for the integration test file now.
    """
    time.sleep(API_CALL_DELAY_SECONDS)

    try:
        response = model.generate_content(prompt)
        generated_text = response.text.strip()
        if generated_text.startswith("```python"):
            generated_text = generated_text[len("```python"):].strip()
        if generated_text.endswith("```"):
            generated_text = generated_text[:-3].strip()
        
        if not generated_text.strip():
            logger.warning("LLM returned empty content for integration tests. Skipping file creation.")
            return None
        return generated_text
    except Exception as e:
        logger.error(f"Failed to generate integration tests for {app_package}: {e}", exc_info=True)
        return None

def run_test(project_root):
    bat_file = os.path.join(project_root, "run_test.bat")
    test_log_file = os.path.join(project_root, TEST_LOG_FILE)

    logger.info(f"Attempting to execute batch file: {bat_file}")
    logger.info(f"Current working directory for batch: {project_root}")
    if not os.path.exists(bat_file):
        logger.error(f"run_test.bat not found at {bat_file}. Cannot run tests.")
        return [] # Return empty list if script not found

    logger.info(f"Executing run_test.bat from {project_root}. Results will be in {test_log_file}")
    
    try:
        # Chạy script batch. Nó sẽ ghi output của pytest vào test_results.log
        result = subprocess.run(
            f'"{bat_file}"',
            shell=True,
            capture_output=True,
            text=True,
            cwd=project_root,
            check=False
        )
        
        # Log stdout/stderr của script batch
        if result.stdout:
            logger.debug(f"run_test.bat stdout (from debug_test_agent.log):\n{result.stdout}")
        if result.stderr:
            logger.error(f"run_test.bat stderr (from debug_test_agent.log):\n{result.stderr}")

        logger.info(f"Pytest run completed. Batch script exit code: {result.returncode}")

        failures = []
        if os.path.exists(test_log_file):
            with open(test_log_file, 'r', encoding='utf-8') as f:
                pytest_output = f.read()

            test_failure_pattern = re.compile(r"^(.*?)::(\w+)\s+FAILED\s*(?:\[\s*\d+%\s*\])?\s*(?:(?:-\s*)?.*)?$")
            error_details = []
            capture_error = False
            test_name = None
            test_file_rel_path = None

            for line in pytest_output.splitlines():
                if "FAILED" in line and not capture_error:
                    match = test_failure_pattern.search(line.strip())
                    if match:
                        test_file_rel_path = match.group(1).strip()
                        test_name = match.group(2).strip()
                        error_details.append(line.strip())
                        capture_error = True
                        continue
                if capture_error:
                    if line.strip() and not line.startswith("="):
                        error_details.append(line.strip())
                    else:
                        capture_error = False
                        test_file_full_path = os.path.join(project_root, test_file_rel_path.replace('/', os.sep))

                        if not os.path.exists(test_file_full_path):
                            logger.warning(f"Parsed test file path '{test_file_full_path}' does not exist for test '{test_name}'. Skipping mapping for this failure.")
                            continue
                        
                        source_file, source_func = map_test_to_source(test_name, test_file_full_path)

                        failures.append({
                            "test": test_name,
                            "test_file_path": test_file_full_path,
                            "source_file": source_file,
                            "source_function": source_func,
                            "error_line_summary": "\n".join(error_details)
                        })
                        error_details = []
                        test_name = None
                        test_file_rel_path = None

            # Handle case where error capture was not terminated
            if capture_error and test_name:
                test_file_full_path = os.path.join(project_root, test_file_rel_path.replace('/', os.sep))
                if os.path.exists(test_file_full_path):
                    source_file, source_func = map_test_to_source(test_name, test_file_full_path)
                    failures.append({
                        "test": test_name,
                        "test_file_path": test_file_full_path,
                        "source_file": source_file,
                        "source_function": source_func,
                        "error_line_summary": "\n".join(error_details)
                    })

            if not failures and "FAILED" in pytest_output:
                logger.warning("Failed to parse test failures from pytest output.")

            if "no tests ran" in pytest_output.lower():
                logger.error("No tests were executed. Check test configuration.")
                return []

            if failures:
                logger.error(f"Tests failed. Returning failure information.")
                return failures
            else:
                logger.info("All tests passed successfully.")
                return []
        else:
            logger.error(f"Pytest log file '{test_log_file}' not found after running tests. Batch script output: {result.stdout}\nErrors: {result.stderr}")
            return []

    except Exception as e:
        logger.error(f"An unexpected error occurred during test execution or result parsing: {e}", exc_info=True)
        return [] # Return empty list on critical error

def map_test_to_source(test_name, specific_test_file_path):
    logger.debug(f"Attempting to map test '{test_name}' from '{specific_test_file_path}' to source.")

    test_file_path = specific_test_file_path
    try:
        with open(test_file_path, 'r', encoding='utf-8') as f:
            test_content = f.read()
        
        # Cố gắng tìm khối hàm test cụ thể
        test_func_pattern = rf"(def\s+{re.escape(test_name)}\s*\(.*?\):\s*\n(?:(?!\n\s*def\s+test_).)*?)(?=\n\s*def\s+test_|\Z)"
        test_func_match = re.search(test_func_pattern, test_content, re.DOTALL | re.MULTILINE)

        if test_func_match:
            func_block_content = test_func_match.group(1)
            
            # Tìm kiếm source_info trong khối hàm
            source_info_match = re.search(r"#\s*source_info:\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+)", func_block_content)
            
            if source_info_match:
                full_source_path = source_info_match.group(1)
                parts = full_source_path.split('.')
                
                if len(parts) >= 2:
                    source_func_or_method_name = parts[-1]
                    parent_name = parts[-2]

                    if parent_name and parent_name[0].isupper() and parent_name.isalpha(): # Kiểm tra parent_name không rỗng và bắt đầu bằng chữ hoa
                        if len(parts) >= 3:
                            module_part = ".".join(parts[:-2])
                            return f"{module_part.replace('.', os.sep)}.py", f"{parent_name}.{source_func_or_method_name}"
                        else:
                            logger.warning(f"Malformed source_info (Class.method without full module path) in {test_file_path} for {test_name}: {full_source_path}")
                            return "unknown_file.py", f"{parent_name}.{source_func_or_method_name}"
                    else:
                        module_part = ".".join(parts[:-1])
                        return f"{module_part.replace('.', os.sep)}.py", source_func_or_method_name
                else:
                    logger.warning(f"Malformed source_info (too few parts) in {test_file_path} for {test_name}: {full_source_path}. Expected module.function or module.Class.method.")
            else:
                logger.debug(f"No # source_info comment found within test function block for '{test_name}' in '{test_file_path}'.")
        else:
            logger.debug(f"Test function definition for '{test_name}' not found in '{test_file_path}'. This might indicate a pytest collection issue or a malformed test file.")

    except FileNotFoundError:
        logger.error(f"Test file '{test_file_path}' not found during mapping for test '{test_name}'.")
    except re.error as re_err:
        logger.error(f"Regex error in map_test_to_source for test '{test_name}' in '{test_file_path}': {re_err}")
    except Exception as e:
        logger.warning(f"Error reading or parsing test file '{test_file_path}' for '{test_name}' source info: {e}", exc_info=True)

    # Fallback heuristic (only if source_info or specific test file parsing failed)
    logger.warning(f"Failed to find reliable # source_info for '{test_name}' in '{test_file_path}'. Falling back to simple heuristic/unknown.")
    
    heuristic_func_name_match = re.match(r"test_([a-zA-Z0-9_]+)(?:_|$)", test_name)
    heuristic_func_name = heuristic_func_name_match.group(1) if heuristic_func_name_match else "unknown_function"

    if test_name.startswith("test_integration"):
        return "test_integration.py", heuristic_func_name
    
    return "unknown_file.py", heuristic_func_name

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate and run tests for a generated application.")
    parser.add_argument('--project', type=str, help="Specify a project directory name (e.g., 'my_todo_app') in 'code_generated_result'.")
    parser.add_argument('--design_file', type=str, help="Path to the JSON design file (e.g., outputs/my_app.design.json).")
    parser.add_argument('--spec_file', type=str, help="Path to the JSON specification file (e.g., outputs/my_app.spec.json).")
    args = parser.parse_args()

    try:
        project_root, framework, app_package, design_data, spec_data = detect_project_and_framework(
            specified_project_name=args.project,
            design_file_path=args.design_file,
            spec_file_path=args.spec_file
        )

        create_pytest_ini(project_root)

        test_output_dir = os.path.join(project_root, TEST_OUTPUT_DIR_NAME)
        test_flag_file = os.path.join(project_root, TEST_GENERATED_FLAG)
        venv_python_path = os.path.join(project_root, "venv", "Scripts", "python.exe")

        # Kiểm tra cờ .test_generated để chỉ sinh test một lần
        if not os.path.exists(test_flag_file):
            logger.info("Test generation flag not found. Generating tests...")
            os.makedirs(test_output_dir, exist_ok=True)
            logger.info(f"Ensured test output directory exists: {test_output_dir}")

            logger.info(f"Ensuring __init__.py files in main application package: {os.path.join(project_root, app_package)}")
            ensure_init_py_recursive(os.path.join(project_root, app_package))
            
            logger.info(f"Ensuring __init__.py files in test output directory: {test_output_dir}")
            ensure_init_py_recursive(test_output_dir)

            needs_test_deps_install = update_requirements_for_testing(project_root)
            
            if needs_test_deps_install:
                logger.info("Test dependencies (pytest, pytest-mock, pytest-asyncio) were added/updated in requirements.txt. Installing/Updating dependencies in project venv.")
                install_project_dependencies(project_root)
            else:
                logger.info("No new test dependencies detected in requirements.txt. Skipping dependency installation.")

            # Scan for Python files to test and generate unit tests
            source_dir = os.path.join(project_root, app_package)
            if not os.path.exists(source_dir):
                logger.error(f"Source directory '{source_dir}' (app package) not found. Cannot generate unit tests. Ensure the project code is generated correctly by codegen_agent.py.")
                sys.exit(1)
            else:
                for root, _, files in os.walk(source_dir):
                    for file in files:
                        if file.endswith(".py") and file != "__init__.py":
                            file_path = os.path.join(root, file)
                            relative_to_project_root = os.path.relpath(file_path, project_root)
                            module_name = relative_to_project_root.replace(os.sep, ".")[:-3]

                            with open(file_path, 'r', encoding='utf-8') as f:
                                source = f.read()
                            tree = ast.parse(source)
                            
                            top_level_functions = [
                                n for n in tree.body
                                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                                and not n.name.startswith('_')
                            ]
                            
                            class_methods = []
                            for node in tree.body:
                                if isinstance(node, ast.ClassDef):
                                    class_name = node.name
                                    for method_node in node.body:
                                        if isinstance(method_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                            if not method_node.name.startswith('_'):
                                                class_methods.append((class_name, method_node))
                            
                            for func_node in top_level_functions:
                                func_name = func_node.name
                                func_code = ast.get_source_segment(source, func_node)
                                if func_code:
                                    logger.debug(f"Generating unit tests for function: {func_name} in module: {module_name}")
                                    test_code = generate_unit_tests(
                                        func_code,
                                        func_name,
                                        module_name,
                                        framework,
                                        f"Function {func_name} is in module {module_name}. Ensure all its dependencies are mocked effectively.",
                                        is_method=False,
                                        class_name=None
                                    )
                                    if test_code:
                                        test_file = os.path.join(test_output_dir, f"test_{func_name}.py")
                                        with open(test_file, 'w', encoding='utf-8') as f:
                                            f.write(test_code)
                                        logger.info(f"Saved unit tests to {test_file}")
                                    else:
                                        logger.warning(f"No test code generated by LLM for '{func_name}' in '{module_name}'. Skipping file creation.")
                                else:
                                    logger.warning(f"Could not extract code for function '{func_name}' from '{file_path}'. Skipping unit test generation.")

                            for class_name, method_node in class_methods:
                                method_name = method_node.name
                                method_code = ast.get_source_segment(source, method_node)
                                if method_code:
                                    logger.debug(f"Generating unit tests for method: {class_name}.{method_name} in module: {module_name}")
                                    test_code = generate_unit_tests(
                                        method_code,
                                        method_name,
                                        module_name,
                                        framework,
                                        f"Method {method_name} is part of class {class_name} in module {module_name}. Ensure you instantiate or mock the class to test this method. Mock its `self` argument if necessary.",
                                        is_method=True,
                                        class_name=class_name
                                    )
                                    if test_code:
                                        test_file = os.path.join(test_output_dir, f"test_{class_name}_{method_name}.py")
                                        with open(test_file, 'w', encoding='utf-8') as f:
                                            f.write(test_code)
                                        logger.info(f"Saved unit tests to {test_file}")
                                    else:
                                        logger.warning(f"No test code generated by LLM for method '{class_name}.{method_name}' in '{module_name}'. Skipping file creation.")
                                else:
                                    logger.warning(f"Could not extract code for method '{class_name}.{method_name}' from '{file_path}'. Skipping unit test generation.")

            endpoints = []
            if design_data and 'interface_Design' in design_data and 'api_Specifications' in design_data['interface_Design']:
                endpoints = design_data['interface_Design']['api_Specifications']
                logger.info(f"Extracted {len(endpoints)} API endpoints from design file for integration testing.")
            else:
                logger.warning("No API specifications found in design file for integration testing.")

            test_code = generate_integration_tests(app_package, framework, endpoints, project_root)
            if test_code:
                test_file = os.path.join(test_output_dir, "test_integration.py")
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(test_code)
                logger.info(f"Saved integration tests to {test_file}")
            else:
                logger.warning("No integration test code generated by LLM. Skipping file creation.")

            with open(test_flag_file, 'w', encoding='utf-8') as f:
                f.write("Tests generated successfully.")
            logger.info(f"Marked tests as generated: {test_flag_file}")
        else:
            logger.info(f"Test generation flag found at {test_flag_file}. Skipping test generation.")

        generate_test_run_script(project_root, venv_python_path)
        failed_tests_info = run_test(project_root)

        if failed_tests_info:
            logger.error(f"Found {len(failed_tests_info)} test failures. Details below:")
            for failure in failed_tests_info:
                logger.error(f"  Test: {failure['test']}")
                logger.error(f"  Test File: {os.path.relpath(failure['test_file_path'], project_root)}")
                logger.error(f"  Source File: {failure['source_file']}")
                logger.error(f"  Source Function: {failure['source_function']}")
                logger.error(f"  Error Summary: {failure['error_line_summary']}\n")
            
            # Ghi thêm vào test_results.log để Debugging Agent có thể đọc
            log_file_path = os.path.join(project_root, TEST_LOG_FILE)
            with open(log_file_path, 'a', encoding='utf-8') as f:
                f.write("\n\n--- Failure Summary (Mapped) ---\n")
                for failure in failed_tests_info:
                    f.write(f"Test: {failure['test']}\n")
                    f.write(f"Test File Path: {failure['test_file_path']}\n")
                    f.write(f"Source File: {failure['source_file']}\n")
                    f.write(f"Source Function: {failure['source_function']}\n")
                    f.write(f"Error Line Summary: {failure['error_line_summary']}\n\n")
            
            history_log_path = os.path.join(project_root, TEST_HISTORY_LOG_FILE)
            with open(history_log_path, 'a', encoding='utf-8') as f:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n\n--- Test Run: {timestamp} - FAILED ---\n")
                f.write(f"Project: {os.path.basename(project_root)}\n")
                f.write(f"Framework: {framework}\n")
                f.write(f"Number of failures: {len(failed_tests_info)}\n") 
                for failure in failed_tests_info:
                    f.write(f"  Test: {failure['test']}\n")
                    f.write(f"  Test File Path: {failure['test_file_path']}\n")
                    f.write(f"  Source File: {failure['source_file']}\n")
                    f.write(f"  Source Function: {failure['source_function']}\n")
                    f.write(f"  Error Summary: {failure['error_line_summary']}\n")
                f.write("--- End of this run's failures ---\n")

            # Để tự động gọi Debug Agent khi có lỗi, bỏ comment đoạn code sau:
            # logger.error("Calling Debug Agent...")
            # subprocess.run(["python", "debug_agent.py", "--project", os.path.basename(project_root)])

            sys.exit(1)
        else:
            logger.info("All tests passed successfully.")

    except FileNotFoundError as e:
        logger.error(f"File/Directory not found error: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        logger.error(f"Subprocess command failed with exit code {e.returncode}: {e.cmd}. Stderr: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred during test generation pipeline: {e}", exc_info=True)
        sys.exit(1)