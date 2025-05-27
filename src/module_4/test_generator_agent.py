import os
import json
import time
import logging
import ast
import subprocess
import re
import argparse
from google.generativeai import GenerativeModel, configure, types
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
BASE_GENERATED_DIR = "code_generated_result"
# company's computer
# OUTPUTS_DIR = r'C:\Users\Hoang Duy\Documents\Phan Lac Hung\autocode_assistant\src\module_1_vs_2\outputs'

# my laptop
OUTPUTS_DIR = r"C:\Users\ADMIN\Documents\Foxconn\autocode_assistant\src\module_1_vs_2\outputs"
TEST_OUTPUT_DIR_NAME = "tests"
TEST_LOG_FILE = "test_results.log"

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
            # If no main.py was found and framework is defaulted, assume a common flask app structure
            app_package = "app"

    logger.info(f"Final detected project: {os.path.basename(project_root)}, Framework: {framework}, App Package: {app_package}")
    return project_root, framework, app_package, design_data, spec_data

def ensure_init_py(directory_path):
    init_py_path = os.path.join(directory_path, "__init__.py")
    if not os.path.exists(init_py_path):
        with open(init_py_path, 'w', encoding='utf-8') as f:
            f.write("# This file makes this directory a Python package.\n")
        logger.info(f"Created missing __init__.py in {directory_path}")
    else:
        logger.debug(f"__init__.py already exists in {directory_path}")

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
    for req in existing_reqs:
        if re.match(r"^pytest($|[<=>~])", req.lower()):
            pytest_present = True
        if re.match(r"^pytest-mock($|[<=>~])", req.lower()):
            pytest_mock_present = True

    reqs_to_add = []
    if not pytest_present:
        reqs_to_add.append("pytest")
    if not pytest_mock_present: # pytest-mock is very useful for mocking
        reqs_to_add.append("pytest-mock")

    if reqs_to_add:
        with open(requirements_path, 'a', encoding='utf-8') as f:
            for req in reqs_to_add:
                f.write(f"\n{req}")
        logger.info(f"Added {', '.join(reqs_to_add)} to {requirements_path}")
    else:
        logger.info("pytest and pytest-mock are already present in requirements.txt.")


def get_function_code(filepath, function_name):
    """Extracts the source code of a given function from a Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)

        func_code_lines = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
                start_line = node.lineno - 1
                end_line = node.end_lineno
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                func_code_lines = lines[start_line:end_line]
                break
            elif isinstance(node, ast.ClassDef): # Check methods within classes
                for method in [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
                    if method.name == function_name:
                        start_line = method.lineno - 1
                        end_line = method.end_lineno
                        with open(filepath, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        func_code_lines = lines[start_line:end_line]
                        break
        if not func_code_lines:
            logger.warning(f"Function '{function_name}' not found in '{filepath}'.")
            return None
        return "".join(func_code_lines)
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        return None
    except Exception as e:
        logger.error(f"Error extracting function '{function_name}' from '{filepath}': {e}", exc_info=True)
        return None

def generate_unit_tests(function_code, function_name, module_path, framework, context):
    """Generates unit tests for a given Python function using LLM."""
    if not function_code:
        logger.warning(f"No function code provided for {function_name}. Skipping unit test generation.") # Added warning
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
            "imports": "from fastapi import Request, HTTPException, Depends", # Added Depends
            "mock_targets": f"{module_path}.Request, {module_path}.HTTPException",
            "context_hint": "Mock FastAPI dependencies (like Depends) using pytest-mock's `mocker` fixture or `unittest.mock.patch` where the dependency is looked up. For routes, use FastAPI's `TestClient` for API calls from the test suite. Ensure mocks for database sessions are handled correctly."
        }
    }.get(framework, {"imports": "", "mock_targets": "", "context_hint": ""})

    prompt = f"""
    You are an expert Python test engineer specializing in the pytest framework and testing {framework} applications.
    Your task is to generate comprehensive unit tests for the Python function below using the pytest framework and `pytest-mock`.

    Function Name: {function_name}
    Module Path: {module_path}
    Framework: {framework}

    Function Code:
    ```python
    {function_code}
    ```

    Context:
    {context}
    {framework_specific['context_hint']}

    Requirements for Test Generation:
    1.  **Strictly Output Code Only**: Your response MUST be only the raw Python code for the test file. Do NOT include any explanations, comments outside the code blocks, or markdown formatting (like ```python ... ```).
    2.  **Imports**: Include all necessary imports: `pytest`, `unittest.mock` (or `pytest-mock`'s `mocker` fixture), relevant modules from `{framework_specific['imports']}`, and import the function under test `from {module_path} import {function_name}`.
    3.  **Mocking Dependencies**:
        -   Properly mock all external dependencies.
        -   Specifically mock: {framework_specific['mock_targets']}.
        -   Crucially, ensure patches target the **correct module where the object is looked up by the function under test**, not just where it's defined. For example, if a function in `my_module.py` does `from another_module import SomeClass` and then uses `SomeClass`, you should mock `my_module.SomeClass`. If it uses a database session (e.g., `db: Session = Depends(get_db)`), mock `get_db` or the database session itself.
        -   Use `pytest-mock`'s `mocker` fixture where appropriate, or `unittest.mock.patch`.
    4.  **Test Scenarios**:
        -   Test the "happy path" where the function behaves as expected with valid inputs.
        -   Test edge cases, invalid inputs, and error conditions (e.g., missing data, database errors, HTTP exceptions).
        -   Verify that mocks for collaborators (like database session methods or external API calls) are called with the expected arguments.
        -   Assert the function's return value or expected side effects.
    5.  **Test Naming and Structure**:
        -   Write clear, well-named test functions (e.g., `test_{function_name}_success`, `test_{function_name}_invalid_input`).
        -   Use pytest conventions (test functions prefixed with `test_`, fixtures).
        -   **Important for `map_test_to_source`**: Include a comment like `# source_info: {module_path}.{function_name}` at the beginning of each test function's body. This metadata is critical for tracing test failures back to the source.
    6.  **Runnability**: Ensure tests are runnable with `pytest` from the project root.

    Generate the Python code for the test file now.
    """
    logger.debug(f"Unit test prompt for {function_name}:\n{prompt[:1000]}...") # Log first 1000 chars of prompt
    time.sleep(API_CALL_DELAY_SECONDS)

    try:
        response = model.generate_content(prompt)
        generated_text = response.text.strip()
        if generated_text.startswith("```python"):
            generated_text = generated_text[len("```python"):].strip()
        if generated_text.endswith("```"):
            generated_text = generated_text[:-3].strip()
        
        if not generated_text.strip(): # Check if text is empty after stripping
            logger.warning(f"LLM returned empty content for unit tests for {function_name}. Skipping file creation.") # Added warning
            return None
        return generated_text
    except Exception as e:
        logger.error(f"Failed to generate unit tests for {function_name}: {e}", exc_info=True)
        return None

def generate_integration_tests(app_package, framework, endpoints, project_root):
    """Generates integration tests for API endpoints using LLM."""
    model = GenerativeModel(DEFAULT_MODEL)
    logger.info(f"Generating integration tests for {app_package} using {DEFAULT_MODEL}")
    
    # Corrected setup for FastAPI TestClient
    framework_specific = {
        "flask": {
            "client_import": "from flask.testing import FlaskClient",
            "client_setup": "client = app.test_client()",
            "request_example": "client.get('/your-endpoint')",
            "app_import": "from app import app" # Assuming 'app' is the main app instance
        },
        "fastapi": {
            "client_import": "from fastapi.testclient import TestClient",
            "client_setup": f"from {app_package}.main import app; client = TestClient(app)", # Corrected
            "request_example": "client.get('/your-endpoint')",
            "app_import": f"from {app_package}.main import app"
        }
    }.get(framework, {"client_import": "", "client_setup": "", "request_example": "", "app_import": ""})

    if not endpoints:
        logger.warning("No API endpoints provided for integration testing. Skipping integration test generation.") # Added warning
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
    2.  **Imports**: Include all necessary imports: `pytest`, `{framework_specific['client_import']}`, `{framework_specific['app_import']}` (to get the `app` instance for the client), and any other standard libraries like `json`, `os`, `uuid` if needed for test data.
    3.  **Test Client Setup**: Set up a test client using `{framework_specific['client_setup']}`.
    4.  **Test Scenarios**:
        -   For each endpoint:
            -   Test with valid inputs and verify successful responses (status code 200/201, correct JSON payload).
            -   Test with invalid inputs (e.g., wrong data types, missing fields) and verify appropriate error responses (e.g., 400, 422).
            -   Test edge cases (e.g., empty lists, boundary conditions if applicable).
            -   If applicable, test sequential operations (e.g., create an item, then retrieve it, then update it, then delete it).
        -   Verify response status codes (e.g., `assert response.status_code == 200`).
        -   Verify JSON payloads (e.g., `assert response.json() == expected_data`).
        -   If database interaction is involved, consider setting up and tearing down a temporary test database using pytest fixtures.
    5.  **Test Structure**:
        -   Write clear, well-named test functions (e.g., `test_create_task_success`, `test_get_tasks_empty`).
        -   Use pytest fixtures for setup/teardown (e.g., for test client, temporary database).
        -   Organize tests logically.
    6.  **Runnability**: Ensure tests are runnable with `pytest` when executed from the project root (`{project_root}`).

    Generate the Python code for the integration test file now.
    """
    logger.debug(f"Integration test prompt:\n{prompt[:1000]}...") # Log first 1000 chars of prompt
    time.sleep(API_CALL_DELAY_SECONDS)

    try:
        response = model.generate_content(prompt)
        generated_text = response.text.strip()
        if generated_text.startswith("```python"):
            generated_text = generated_text[len("```python"):].strip()
        if generated_text.endswith("```"):
            generated_text = generated_text[:-3].strip()
        
        if not generated_text.strip(): # Check if text is empty after stripping
            logger.warning("LLM returned empty content for integration tests. Skipping file creation.") # Added warning
            return None
        return generated_text
    except Exception as e:
        logger.error(f"Failed to generate integration tests for {app_package}: {e}", exc_info=True)
        return None

def run_tests(project_root):
    """
    Runs pytest tests within the generated project's virtual environment.
    Logs output and summarizes failures.
    """
    test_dir = os.path.join(project_root, TEST_OUTPUT_DIR_NAME)
    log_file = os.path.join(project_root, TEST_LOG_FILE)
    logger.info(f"Running pytest in {test_dir} from project root: {project_root}")

    # --- Use Python executable from the project's virtual environment ---
    venv_python_path = os.path.join(project_root, "venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python_path):
        logger.error(f"Virtual environment python executable not found at {venv_python_path}. Please ensure 'venv' exists and is properly set up in the generated project (run codegen_agent.py first).")
        return []
    
    try:
        # Call pytest using the venv's python executable
        result = subprocess.run(
            [venv_python_path, "-m", "pytest", test_dir, "--tb=short", "-v"],
            capture_output=True,
            text=True,
            cwd=project_root # Set cwd to project root
        )
        
        # Write results to log file
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
            if result.stderr: # Only write stderr if it's not empty
                f.write("\n--- Errors/Warnings (stderr) ---\n")
                f.write(result.stderr)

        failures = []
        # Parse stdout for test failures
        for line in result.stdout.splitlines():
            if "FAILED" in line and "::" in line: # Ensure it's a test failure line
                # Extract test name, e.g., "test_read_tasks_success"
                test_match = re.match(r"^(?:.*?::)?(test_[a-zA-Z0-9_]+)\s+FAILED", line)
                test_name = test_match.group(1) if test_match else "UnknownTest"

                # Attempt to map test name to source file/function using heuristic and source_info comment
                source_file, source_func = map_test_to_source(test_name, project_root, test_dir)

                failures.append({
                    "test": test_name,
                    "source_file": source_file,
                    "source_function": source_func,
                    "error_line": line # Keep the specific failure line for context
                })

        if failures:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write("\n\n--- Failure Summary ---\n")
                for failure in failures:
                    f.write(f"Test: {failure['test']}\n")
                    f.write(f"Source File: {failure['source_file']}\n")
                    f.write(f"Source Function: {failure['source_function']}\n")
                    f.write(f"Error Line: {failure['error_line']}\n\n")
            logger.warning(f"Found {len(failures)} test failures. Check {os.path.join(project_root, TEST_LOG_FILE)} for details.")
        else:
            logger.info("All tests passed successfully.")
            
        return failures
    except FileNotFoundError:
        logger.error(f"Pytest executable not found. Ensure it's installed in the venv and the path is correct: {venv_python_path}")
        return []
    except subprocess.CalledProcessError as e:
        logger.error(f"Pytest command failed with exit code {e.returncode}. Check {log_file} for full output.")
        logger.debug(f"Pytest stdout:\n{e.stdout}")
        logger.debug(f"Pytest stderr:\n{e.stderr}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred during test execution: {e}", exc_info=True)
        return []

def map_test_to_source(test_name, project_root, test_dir):
    """
    Attempts to map a test function name to its source file and function using heuristics.
    Prioritizes reading 'source_info' comment from the test file.
    """
    # Search in all generated test files for the test function name
    # It's more reliable to search for the test function name and then find the nearest source_info
    for root, _, files in os.walk(test_dir):
        for file_name in files:
            if file_name.startswith("test_") and file_name.endswith(".py"):
                test_file_path = os.path.join(root, file_name)
                try:
                    with open(test_file_path, 'r', encoding='utf-8') as f:
                        test_content = f.read()
                        # Look for test function definition
                        # This regex finds a test function definition
                        test_func_pattern = rf"def\s+{re.escape(test_name)}\s*\(.*?\):"
                        test_func_match = re.search(test_func_pattern, test_content)

                        if test_func_match:
                            # Search for source_info in the vicinity of the test function or file-wide
                            source_info_match = re.search(r"#\s*source_info:\s*([a-zA-Z0-9_.]+)", test_content)
                            if source_info_match:
                                full_source_path = source_info_match.group(1)
                                parts = full_source_path.split('.')
                                # Assuming module.function format, e.g., 'backend.routes.read_tasks'
                                if len(parts) >= 2:
                                    source_module_name = parts[-2]
                                    source_func_name = parts[-1]
                                    return f"{source_module_name}.py", source_func_name
                                else:
                                    logger.warning(f"Malformed source_info in {test_file_path}: {full_source_path}")

                except Exception as e:
                    logger.warning(f"Error reading test file {test_file_path} for source info: {e}")

    # Fallback to heuristic if source_info comment is not found or malformed
    logger.debug(f"Source info comment not found for '{test_name}'. Falling back to heuristic.")
    # Heuristic based on test naming convention
    heuristic_func_name_match = re.match(r"test_([a-zA-Z0-9_]+)(?:_|$)", test_name)
    heuristic_func_name = heuristic_func_name_match.group(1) if heuristic_func_name_match else "unknown_function"

    # Default common modules for these functions
    if "routes" in test_name.lower(): # Common for test_create_task, test_read_tasks
        return "routes.py", heuristic_func_name
    elif "main" in test_name.lower(): # For functions in main.py
        return "main.py", heuristic_func_name
    elif "database" in test_name.lower(): # For functions in database.py
        return "database.py", heuristic_func_name
    elif "models" in test_name.lower(): # For functions in models.py
        return "models.py", heuristic_func_name
    
    return "unknown_file.py", heuristic_func_name # Default fallback

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

        test_output_dir = os.path.join(project_root, TEST_OUTPUT_DIR_NAME)
        os.makedirs(test_output_dir, exist_ok=True)
        logger.info(f"Ensured test output directory exists: {test_output_dir}")

        # Ensure __init__.py files are present for Python package structure
        ensure_init_py(project_root)
        # Check if app_package is a sub-directory, then ensure __init__.py
        # This handles cases where app_package might be empty (e.g., main.py directly in root)
        app_package_full_path = os.path.join(project_root, app_package) if app_package else project_root
        if os.path.exists(app_package_full_path) and os.path.isdir(app_package_full_path):
            ensure_init_py(app_package_full_path)
        ensure_init_py(test_output_dir)

        # Ensure pytest is in the project's requirements.txt
        update_requirements_for_testing(project_root)

        # Scan for Python files to test and generate unit tests
        source_dir = os.path.join(project_root, app_package)
        if not os.path.exists(source_dir):
            logger.error(f"Source directory '{source_dir}' (app package) not found. Cannot generate unit tests. Ensure the project code is generated correctly by codegen_agent.py.")
        else:
            for root, _, files in os.walk(source_dir):
                for file in files:
                    if file.endswith(".py") and file != "__init__.py":
                        file_path = os.path.join(root, file)
                        # Construct module_name correctly, relative to project_root
                        # Example: if project_root is /app, file_path is /app/backend/routes.py
                        # module_name should be 'backend.routes'
                        relative_to_project_root = os.path.relpath(file_path, project_root)
                        module_name = relative_to_project_root.replace(os.sep, ".")[:-3] # Remove .py

                        with open(file_path, 'r', encoding='utf-8') as f:
                            tree = ast.parse(f.read())
                        
                        logger.info(f"Scanning '{file_path}' for functions to test...")
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                func_name = node.name
                                if func_name.startswith('_'): # Skip private/internal functions by convention
                                    logger.debug(f"Skipping private/internal function: {func_name}")
                                    continue

                                func_code = get_function_code(file_path, func_name)
                                if func_code: # get_function_code now logs warning if not found
                                    logger.debug(f"Generating unit tests for function: {func_name} in module: {module_name}")
                                    test_code = generate_unit_tests(
                                        func_code,
                                        func_name,
                                        module_name, # Pass correct module name for imports
                                        framework,
                                        f"Function {func_name} is in module {module_name}. Ensure all its dependencies are mocked effectively."
                                    )
                                    if test_code: # generate_unit_tests now logs warning if empty
                                        test_file = os.path.join(test_output_dir, f"test_{func_name}.py")
                                        with open(test_file, 'w', encoding='utf-8') as f:
                                            f.write(test_code)
                                        logger.info(f"Saved unit tests to {test_file}")
                                    else:
                                        logger.warning(f"No test code generated by LLM for '{func_name}' in '{module_name}'. Skipping file creation.")
                                else:
                                    logger.warning(f"Could not extract code for function '{func_name}' from '{file_path}'. Skipping unit test generation.")

        # Generate integration tests for API endpoints
        # Extract endpoints from design_data
        endpoints = []
        if design_data and 'interface_Design' in design_data and 'api_Specifications' in design_data['interface_Design']:
            endpoints = design_data['interface_Design']['api_Specifications']
            logger.info(f"Extracted {len(endpoints)} API endpoints from design file for integration testing.")
        else:
            logger.warning("No API specifications found in design file for integration testing.")

        test_code = generate_integration_tests(app_package, framework, endpoints, project_root)
        if test_code: # generate_integration_tests now logs warning if empty
            test_file = os.path.join(test_output_dir, "test_integration.py")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(test_code)
            logger.info(f"Saved integration tests to {test_file}")
        else:
            logger.warning("No integration test code generated by LLM. Skipping file creation.")


        # Run tests and log results
        failures = run_tests(project_root)
        if failures:
            logger.warning(f"Found {len(failures)} test failures. Check {os.path.join(project_root, TEST_LOG_FILE)} for details.")
        else:
            logger.info("All tests passed successfully.")

    except FileNotFoundError as e:
        logger.error(f"Error: {e}")
    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during test generation pipeline: {e}", exc_info=True)


#     prompt = f"""
#     You are an expert Python test engineer specializing in the pytest framework and testing Flask applications.
#     Your task is to generate comprehensive pytest unit tests for the following Python function.

#     Function Name: {function_name}
#     Target Module for Imports within test: {full_module_path}(e.g., if function is in 'app.routes', tests will 'from app.routes import function_name')

#     Function Code:
#     ```python
#     {function_code}

#     Context and Instructions:
#     {context_description}

#     Please generate pytest unit tests that cover the following:
#     1. Mocking Dependencies: Properly mock all external dependencies. For Flask routes, this typically includes:
#     - flask.request (e.g., request.form, request.args, request.json).
#     - Database sessions/objects (e.g., db.session.add, db.session.commit, db.session.delete, model query methods like Flashcard.query.get_or_404).
#     - Flask utility functions like flask.render_template, flask.redirect, flask.url_for.
#     - The Flashcard model constructor or any methods it might call if relevant to the function's logic beyond simple instantiation.
#     - Use unittest.mock.patch or pytest fixtures with mocker (from pytest-mock) for mocking. 
#     - Crucially, ensure patches target the correct module where the object is looked up by the function under test, not where it's defined (e.g., patch '{full_module_path}.request', '{full_module_path}.db', '{full_module_path}.Flashcard'). For example, if {full_module_path}.py contains from flask import request and uses request, you'd patch {full_module_path}.request. If it uses db.session.add after from . import db (where db is from app/__init__.py), you'd patch {full_module_path}.db.session.add.

#     2. Test Scenarios:
#     - Test the "happy path" where the function behaves as expected with valid inputs.
#     - Test edge cases and error conditions (e.g., missing required form data, database errors if applicable, object not found).
#     - Verify that mocks for collaborators (like db.session.add, db.session.commit) are called with the expected arguments.
#     - Assert the function's return value (e.g., the response from render_template or redirect).

#     3. Test Structure:
#     - Write clear, well-named test functions (e.g., test_create_card_success, test_create_card_missing_front_content).
#     - Use pytest conventions (e.g., test functions prefixed with test_).
#     - Ensure necessary imports are included at the top of the test file (e.g., pytest, unittest.mock.patch, the function/module under test like from {full_module_path} import {function_name}, any necessary Flask objects if not fully mocked).
#     - If testing Flask routes, using app.test_request_context() from a pytest fixture providing a Flask app instance is common, especially if url_for or other context-dependent Flask features are involved (even if also mocked).

#     Output ONLY the Python code for the test file. Do not include any explanations or markdown formatting around the code block.
#     The test code should be runnable using pytest when executed from the root directory of the application being tested (i.e., the directory containing the '{FLASK_APP_PACKAGE_NAME}' package).
#     The function under test will be imported as from {full_module_path} import {function_name}.
#     """