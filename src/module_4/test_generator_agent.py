import os
import json
import time
import logging
import ast
import subprocess
import re
import argparse
import sys

from google.generativeai import GenerativeModel, configure, types
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG, # Giữ DEBUG để dễ dàng debug
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
BASE_GENERATED_DIR = "code_generated_result"
# company's computer
OUTPUTS_DIR = r'C:\Users\Hoang Duy\Documents\Phan Lac Hung\autocode_assistant\src\module_1_vs_2\outputs'

# my laptop
# OUTPUTS_DIR = r"C:\Users\ADMIN\Documents\Foxconn\autocode_assistant\src\module_1_vs_2\outputs"
TEST_OUTPUT_DIR_NAME = "tests"
TEST_LOG_FILE = "test_results.log"

def create_pytest_ini(project_root):
    """
    Creates or updates pytest.ini in the project root with recommended configurations
    for asyncio mode and cache directory to handle potential permission issues.
    """
    pytest_ini_path = os.path.join(project_root, "pytest.ini")
    
    # Define the content for pytest.ini
    pytest_ini_content = """\
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
# Configure cachedir to a user-specific temporary directory if default causes issues
# This uses Python's tempfile module and is more robust for permission issues.
# The actual path will be resolved by pytest.
# Note: pytest needs to know the path relative to its rootdir (project_root)
# So, we'll put it in a subdirectory named 'tmp_pytest_cache'
cachedir = tmp_pytest_cache/
"""
    # Check if pytest.ini already exists and has similar content to avoid overwriting unnecessarily
    if os.path.exists(pytest_ini_path):
        try:
            with open(pytest_ini_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
            if "asyncio_mode = auto" in current_content and "asyncio_default_fixture_loop_scope = function" in current_content and "cachedir" in current_content:
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

def detect_project_and_framework(specified_project_name=None, design_file_path=None, spec_file_path=None):
    logger.info("Detecting project and framework...")

    # Validate BASE_GENERATED_DIR existence
    if not os.path.exists(BASE_GENERATED_DIR):
        msg = f"Base directory '{BASE_GENERATED_DIR}' does not exist. Run codegen_agent.py first."
        logger.error(msg)
        raise FileNotFoundError(msg)

    # Validate OUTPUTS_DIR existence
    if not os.path.exists(OUTPUTS_DIR):
        msg = f"Outputs directory '{OUTPUTS_DIR}' does not exist. Ensure your design/spec files are there."
        logger.error(msg)
        raise FileNotFoundError(msg)

    project_root = None
    design_data = None
    spec_data = None

    # First approach for command: Using argparse to choose design/spec files
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
                    project_root = potential_project_root
                    logger.info(f"Detected project root from specified design: {project_root}")
                else:
                    logger.warning(f"Project directory '{potential_project_root}' from specified design not found in '{BASE_GENERATED_DIR}'.")
            else:
                logger.warning("Root project directory name not found in specified design file.")

        except Exception as e:
            logger.error(f"Failed to load/parse specified JSON files: {e}")
            raise ValueError(f"Invalid specified JSON files: {e}")
    
    # Second approach for command: Fallback to specified project name (if provided) and find latest design/spec in OUTPUTS_DIR
    if not project_root and specified_project_name:
        potential_project_root = os.path.join(BASE_GENERATED_DIR, specified_project_name)
        if os.path.isdir(potential_project_root):
            project_root = potential_project_root
            logger.info(f"Using specified project folder: {project_root}")
            
            # Try to find matching design/spec files for the specified project
            # This assumes naming convention like "project_name_timestamp.design.json"
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

    # Third approach for command(Default): Find the most recent project folder and associated design/spec files
    if not project_root:
        projects = [d for d in os.listdir(BASE_GENERATED_DIR) if os.path.isdir(os.path.join(BASE_GENERATED_DIR, d))]
        if not projects:
            msg = f"No project folders found in '{BASE_GENERATED_DIR}'."
            logger.error(msg)
            raise ValueError(msg)
        
        # Select the most recent project folder based on creation time
        project_dir_name = max(projects, key=lambda p: os.path.getctime(os.path.join(BASE_GENERATED_DIR, p)))
        project_root = os.path.join(BASE_GENERATED_DIR, project_dir_name)
        logger.info(f"Using most recent project folder: {project_root}")

        # Find the most recently modified .design.json and .spec.json in OUTPUTS_DIR
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
                backend_dir = os.path.dirname(relative_path)
                # Ensure backend_dir does not start with a slash here if it came from JSON like /backend
                if backend_dir.startswith('/') and len(backend_dir) > 1:
                    backend_dir = backend_dir[1:]
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

def ensure_init_py_recursive(base_directory_path): # duyệt đệ quy để đảm bảo tất cả các dir đều có __init__.py
    for root, dirs, files in os.walk(base_directory_path):
        if 'venv' in dirs:
            dirs.remove('venv') # This modifies dirs in-place for os.walk to skip it
            logger.debug(f"Skipping 'venv' directory in {root}")

        if any(f.endswith(".py") for f in files): # <--- Điều kiện này được kiểm tra cho MỌI thư mục
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
    pytest_asyncio_present = False # Added pytest-asyncio check

    for req in existing_reqs:
        if re.match(r"^pytest($|[<=>~])", req.lower()):
            pytest_present = True
        if re.match(r"^pytest-mock($|[<=>~])", req.lower()):
            pytest_mock_present = True
        if re.match(r"^pytest-asyncio($|[<=>~])", req.lower()): # Check for pytest-asyncio
            pytest_asyncio_present = True

    reqs_to_add = []
    if not pytest_present:
        reqs_to_add.append("pytest")
    if not pytest_mock_present:
        reqs_to_add.append("pytest-mock")
    if not pytest_asyncio_present: # Add if not present
        reqs_to_add.append("pytest-asyncio")

    if reqs_to_add:
        with open(requirements_path, 'a', encoding='utf-8') as f:
            for req in reqs_to_add:
                f.write(f"\n{req}")
        logger.info(f"Added {', '.join(reqs_to_add)} to {requirements_path}")
        return True # Changes were made, installation is needed
    else:
        logger.info("All required test dependencies (pytest, pytest-mock, pytest-asyncio) are already present in requirements.txt. No update needed.")
        return False

def install_project_dependencies(project_root):
    venv_python_path = os.path.join(project_root, "venv", "Scripts", "python.exe")
    requirements_path = os.path.join(project_root, "requirements.txt")

    if not os.path.exists(venv_python_path):
        logger.error(f"Virtual environment python executable not found at {venv_python_path}. Please ensure 'venv' exists and is properly set up in the generated project.")
        # Raise a specific error to indicate this critical failure
        raise FileNotFoundError(f"Project venv not found: {venv_python_path}")
    
    if not os.path.exists(requirements_path):
        logger.warning(f"requirements.txt not found at {requirements_path}. Skipping dependency installation.")
        return

    logger.info(f"Installing dependencies from {requirements_path} into project venv...")
    try:
        # Use the venv's pip
        result = subprocess.run(
            [venv_python_path, "-m", "pip", "install", "-r", "requirements.txt"], # Only pass filename, cwd handles path
            capture_output=True,
            text=True,
            check=True, # Raise CalledProcessError if pip fails
            cwd=project_root
        )
        logger.info(f"Successfully installed dependencies. Pip output:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"Pip warnings/errors during dependency installation:\n{result.stderr}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies. Exit code: {e.returncode}")
        logger.error(f"Pip stdout:\n{e.stdout}")
        logger.error(f"Pip stderr:\n{e.stderr}")
        # Re-raise the exception to stop the pipeline, as this is a critical error
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
    test_file_prefix = "" # New variable for test file naming
    
    if is_method and class_name:
        target_import = f"from {module_path} import {class_name}"
        target_source_info = f"{module_path}.{class_name}.{function_name}"
        method_context = (
            f"This is a method of class `{class_name}`. When testing, you will need to "
            f"instantiate `{class_name}` or mock its instance, and then call its method `{function_name}`. "
            f"Mock `self` if necessary for the method's behavior. "
            f"The source info should be in the format: `module.ClassName.methodName`."
        )
        test_file_prefix = f"test_{class_name}_" # e.g., test_Flashcard_to_dict.py
    else:
        target_import = f"from {module_path} import {function_name}"
        target_source_info = f"{module_path}.{function_name}"
        method_context = f"This is a top-level function. The source info should be in the format: `module.functionName`."
        test_file_prefix = f"test_{function_name}_" # e.g., test_get_db.py

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
        -   Use pytest fixtures for setup/teardown (e.g., for test client, temporary database).
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

def run_tests(project_root):
    test_dir = os.path.join(project_root, TEST_OUTPUT_DIR_NAME)
    log_file = os.path.join(project_root, TEST_LOG_FILE)
    logger.info(f"Running pytest in {test_dir} from project root: {project_root}")

    # --- Use Python executable from the project's virtual environment ---
    venv_python_path = os.path.join(project_root, "venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python_path):
        logger.error(f"Virtual environment python executable not found at {venv_python_path}. Please ensure 'venv' exists and is properly set up in the generated project (run codegen_agent.py first and check its debug.log).")
        sys.exit(1)
    
    try:
        relative_test_dir = os.path.relpath(test_dir, project_root)
        result = subprocess.run(
            [venv_python_path, "-m", "pytest", relative_test_dir, "--tb=short", "-v"],
            capture_output=True,
            text=True,
            check=False, # Set to False here so we can parse output even if tests fail or pytest exits with 1
            cwd=project_root
        )
        
        # Write results to log file, including stderr
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n--- Errors/Warnings (stderr) ---\n")
                f.write(result.stderr)

        if "No module named pytest" in result.stderr:
            logger.error(f"Pytest module not found in venv. Ensure `pip install -r requirements.txt` was run successfully in the project's venv. Full stderr:\n{result.stderr}")
            sys.exit(1)

        failures = []
        # Cải thiện phần Parsing output của pytest
        # Regex này sẽ khớp với định dạng "path/to/file.py::test_function_name PASSED/FAILED"
        # Rất quan trọng: đảm bảo regex này khớp chính xác các dòng bạn muốn parse
        # Tôi sẽ điều chỉnh regex để cố gắng khớp với định dạng có cả PASSED và FAILED
        # và chỉ quan tâm đến các dòng có '::'
        test_result_pattern = re.compile(r"^(.*?)::(\w+)\s+(PASSED|FAILED|SKIPPED|XFAIL|XPASS)")

        for line in result.stdout.splitlines():
            # Chỉ xử lý các dòng có FAILED hoặc PASSED
            if "FAILED" in line: # Chỉ quan tâm đến các dòng FAILED
                match = test_result_pattern.search(line.strip())
                if match:
                    test_file_rel_path = match.group(1) # e.g., 'tests/test_CustomJsonFormatter_format.py'
                    test_name = match.group(2)          # e.g., 'test_CustomJsonFormatter_format_success'
                    status = match.group(3)             # e.g., 'FAILED'

                    # Chỉ thêm vào danh sách failures nếu status là FAILED
                    if status == "FAILED":
                        test_file_full_path = os.path.join(project_root, test_file_rel_path.replace('/', os.sep))
                        
                        # Thêm kiểm tra này để đảm bảo file thực sự tồn tại
                        if not os.path.exists(test_file_full_path):
                            logger.warning(f"Parsed test file path '{test_file_full_path}' does not exist for test '{test_name}'. Skipping mapping.")
                            continue # Bỏ qua dòng này nếu file không tồn tại
                        
                        source_file, source_func = map_test_to_source(test_name, test_file_full_path)

                        failures.append({
                            "test": test_name,
                            "source_file": source_file,
                            "source_function": source_func,
                            "error_line": line # Dòng gốc từ pytest
                        })
                else:
                    # Nếu dòng có FAILED nhưng không khớp với pattern, có thể là một dòng traceback
                    # hoặc tóm tắt. Log cảnh báo và bỏ qua.
                    logger.warning(f"Could not parse potential pytest failure line: {line.strip()}")

        if failures:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write("\n\n--- Failure Summary ---\n")
                for failure in failures:
                    f.write(f"Test: {failure['test']}\n")
                    f.write(f"Source File: {failure['source_file']}\n")
                    f.write(f"Source Function: {failure['source_function']}\n")
                    f.write(f"Error Line: {failure['error_line']}\n\n")
            logger.error(f"Found {len(failures)} test failures. Check {os.path.join(project_root, TEST_LOG_FILE)} for details.")
            sys.exit(1)
        
        if result.returncode == 0:
            logger.info("All tests passed successfully.")
            return True # All tests passed
        else:
            # This case means pytest exited non-zero but no specific FAILED lines were parsed.
            logger.error(f"Pytest exited with non-zero code {result.returncode} but no specific test failures detected in stdout. Check {log_file} for full output and stderr. Stderr: {result.stderr}")
            sys.exit(1) # Dừng ngay lập tức nếu có lỗi thực thi không mong muốn

    except FileNotFoundError: # Catches if venv_python_path itself is not found
        logger.error(f"Pytest executable (via venv Python) not found. Ensure it's installed in the venv and the path is correct: {venv_python_path}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred during test execution: {e}", exc_info=True)
        sys.exit(1)

def map_test_to_source(test_name, specific_test_file_path):
    """
    Attempts to map a test function name to its source file and function/method.
    It now expects the specific test file path where the failure occurred.
    Prioritizes reading 'source_info' comment from the test file.
    """
    logger.debug(f"Attempting to map test '{test_name}' from '{specific_test_file_path}' to source.")

    # directly work with 
    test_file_path = specific_test_file_path # Renaming for consistency with previous variable name
    try:
        with open(test_file_path, 'r', encoding='utf-8') as f:
            test_content = f.read()
        # Find the specific test function block using the exact test_name
        test_func_pattern = rf"(def\s+{re.escape(test_name)}\s*\(.*?\):\s*\n(?:(?!\n\s*def\s+test_).)*?)(?=\n\s*def\s+test_|\Z)"
        test_func_match = re.search(test_func_pattern, test_content, re.DOTALL | re.MULTILINE)

        if test_func_match:
            func_block_content = test_func_match.group(1)
            
            # Search for source_info within the captured function block
            source_info_match = re.search(r"#\s*source_info:\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+)", func_block_content)
            
            if source_info_match:
                full_source_path = source_info_match.group(1)
                parts = full_source_path.split('.')
                
                if len(parts) >= 2:
                    source_func_or_method_name = parts[-1]
                    parent_name = parts[-2]

                    if parent_name[0].isupper() and parent_name.isalpha():
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
        os.makedirs(test_output_dir, exist_ok=True)
        logger.info(f"Ensured test output directory exists: {test_output_dir}")

        # Ensure __init__.py files are present for Python package structure recursively
        logger.info(f"Ensuring __init__.py files in main application package: {os.path.join(project_root, app_package)}")
        ensure_init_py_recursive(os.path.join(project_root, app_package)) # Only for the app_package
        
        logger.info(f"Ensuring __init__.py files in test output directory: {test_output_dir}")
        ensure_init_py_recursive(test_output_dir) # For the test output directory

        # Check and update requirements.txt for testing dependencies
        needs_test_deps_install = update_requirements_for_testing(project_root)
        
        # Only install dependencies if requirements.txt was updated OR if it's the first run
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
                            source = f.read() # Đọc toàn bộ nội dung file
                        tree = ast.parse(source) # Parse AST từ nội dung đã đọc
                        
                        logger.info(f"Scanning '{file_path}' for functions and methods to test...")
                        
                        # Collect top-level functions
                        top_level_functions = [
                            n for n in tree.body
                            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and not n.name.startswith('_') # Skip private functions
                        ]
                        
                        # Collect class methods
                        class_methods = []
                        for node in tree.body:
                            if isinstance(node, ast.ClassDef):
                                class_name = node.name
                                for method_node in node.body:
                                    if isinstance(method_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                        if not method_node.name.startswith('_'): # Skip private methods
                                            class_methods.append((class_name, method_node))
                        
                        # Process Top-Level Functions
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

                        # Process Class Methods
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
                                    test_file = os.path.join(test_output_dir, f"test_{class_name}_{method_name}.py") # Name test file by Class_Method
                                    with open(test_file, 'w', encoding='utf-8') as f:
                                        f.write(test_code)
                                    logger.info(f"Saved unit tests to {test_file}")
                                else:
                                    logger.warning(f"No test code generated by LLM for method '{class_name}.{method_name}' in '{module_name}'. Skipping file creation.")
                            else:
                                logger.warning(f"Could not extract code for method '{class_name}.{method_name}' from '{file_path}'. Skipping unit test generation.")


        # Generate integration tests for API endpoints
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


        # Run tests and log results
        tests_passed = run_tests(project_root)

        # Final outcome log (optional, as run_tests handles exit)
        if tests_passed:
            logger.info("Test generation and execution pipeline completed successfully.")
        else:
            logger.warning("Test generation and execution pipeline completed with failures or errors.")


    except FileNotFoundError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred during test generation pipeline: {e}", exc_info=True)
        sys.exit(1)