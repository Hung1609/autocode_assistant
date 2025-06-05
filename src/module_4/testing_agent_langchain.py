import os
import json
import time
import logging
import ast
import subprocess
import re
import argparse
import sys
from typing import Dict, Any, Optional, Tuple, List
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import initialize_agent, AgentType
from langchain.tools import StructuredTool
from langchain_core.messages import HumanMessage, BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
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
logger.info("Gemini API configured successfully for test generator.")

DEFAULT_MODEL = 'gemini-2.0-flash'
BASE_GENERATED_DIR = os.getenv('BASE_GENERATED_DIR', 'code_generated_result')
OUTPUTS_DIR = os.getenv('OUTPUTS_DIR', r'C:\Users\Hoang Duy\Documents\Phan Lac Hung\autocode_assistant\src\module_1_vs_2\outputs')
TEST_OUTPUT_DIR_NAME = "tests"
UNIT_TEST_SUBDIR = "unit"
INTEGRATION_TEST_SUBDIR = "integration"
TEST_LOG_FILE = "test_results.log"
TEST_HISTORY_LOG_FILE = "test_results_history.log"
TEST_GENERATED_FLAG = ".test_generated"

# Input schemas for tools
class EmptyInput(BaseModel):
    pass

class GenerateUnitTestsInput(BaseModel):
    function_code: str = Field(description="Source code of the function/method to test.")
    function_name: str = Field(description="Name of the function/method.")
    module_path: str = Field(description="Module path (e.g., backend.routes).")
    framework: str = Field(description="Framework (fastapi or flask).")
    context: str = Field(description="Additional context for the function/method.")
    is_method: bool = Field(description="Whether this is a class method.")
    class_name: Optional[str] = Field(description="Class name if is_method is True.", default=None)

class GenerateIntegrationTestsInput(BaseModel):
    app_package: str = Field(description="Application package (e.g., backend).")
    framework: str = Field(description="Framework (fastapi or flask).")
    endpoints: List[Dict[str, Any]] = Field(description="List of API endpoints to test.")
    project_root: str = Field(description="Project root directory.")

class TestingTools:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model=DEFAULT_MODEL, google_api_key=api_key)

    def create_pytest_ini(self, project_root: str) -> None:
        pytest_ini_path = os.path.join(project_root, "pytest.ini")
        pytest_ini_content = """\
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
cachedir = tmp_pytest_cache/
"""
        if os.path.exists(pytest_ini_path):
            try:
                with open(pytest_ini_path, 'r', encoding='utf-8') as f:
                    current_content = f.read()
                if "asyncio_mode = auto" in current_content and \
                   "asyncio_default_fixture_loop_scope = function" in current_content and \
                   "cachedir = tmp_pytest_cache/" in current_content:
                    logger.info(f"pytest.ini already exists with required settings in {project_root}. Skipping creation.")
                    return
            except Exception as e:
                logger.warning(f"Could not read existing pytest.ini in {project_root}: {e}. Overwriting.")

        try:
            with open(pytest_ini_path, 'w', encoding='utf-8') as f:
                f.write(pytest_ini_content)
            logger.info(f"Created/Updated pytest.ini in {project_root}.")
        except Exception as e:
            logger.error(f"Failed to create/update pytest.ini in {project_root}: {e}")

    def generate_run_test_bat_script(self, project_root: str, venv_python_path: str) -> str:
        bat_file_path = os.path.join(project_root, "run_test.bat")
        bat_content = fr"""
@echo off
setlocal EnableDelayedExpansion
echo --- run_test.bat STARTED ---
echo Current Directory: "%CD%" > debug_test_agent.log 2>&1
echo PROJECT_ROOT: "%~dp0" >> debug_test_agent.log 2>&1
cd /d "%~dp0" >> debug_test_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to change to project root directory. >> debug_test_agent.log 2>&1
    exit /b 1
)
echo Current Directory (after cd): "%CD%" >> debug_test_agent.log 2>&1
if exist "{TEST_LOG_FILE}" (
    del "{TEST_LOG_FILE}" >> debug_test_agent.log 2>&1
)
"{venv_python_path}" --version >> debug_test_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found at "{venv_python_path}". >> debug_test_agent.log 2>&1
    exit /b 1
)
call "%~dp0venv\Scripts\activate.bat" >> debug_test_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to activate virtual environment. >> debug_test_agent.log 2>&1
    exit /b 1
)
where python.exe >> debug_test_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo WARNING: python.exe not found in PATH after venv activation. This might indicate an issue with activate.bat. >> debug_test_agent.log 2>&1
)
"{venv_python_path}" -m pytest tests --exitfirst --tb=long -v > "{TEST_LOG_FILE}" 2>&1
set TEST_EXIT_CODE=%ERRORLEVEL%
deactivate >> debug_test_agent.log 2>&1
if %TEST_EXIT_CODE% neq 0 (
    echo ERROR: Tests failed. Check "{TEST_LOG_FILE}". >> debug_test_agent.log 2>&1
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

    def detect_project_and_framework(self, specified_project_name: Optional[str] = None, 
                                    design_file_path: Optional[str] = None, 
                                    spec_file_path: Optional[str] = None) -> Tuple[str, str, str, Optional[Dict], Optional[Dict]]:
        logger.info("Detecting project and framework...")
        if not os.path.exists(BASE_GENERATED_DIR):
            msg = f"Base directory '{BASE_GENERATED_DIR}' does not exist."
            logger.error(msg)
            raise FileNotFoundError(msg)

        if not os.path.exists(OUTPUTS_DIR):
            msg = f"Outputs directory '{OUTPUTS_DIR}' does not exist."
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
                        project_root = os.path.abspath(potential_project_root)
                        logger.info(f"Detected project root from specified design: {project_root}")
                    else:
                        logger.warning(f"Project directory '{potential_project_root}' not found.")
            except Exception as e:
                logger.error(f"Failed to load/parse specified JSON files: {e}")
                raise ValueError(f"Invalid specified JSON files: {e}")

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
                        logger.info(f"Loaded latest design file: {design_file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to load design file '{design_file_path}': {e}")
                if relevant_spec_files:
                    spec_file_path = os.path.join(OUTPUTS_DIR, max(relevant_spec_files, key=lambda f: os.path.getmtime(os.path.join(OUTPUTS_DIR, f))))
                    try:
                        with open(spec_file_path, 'r', encoding='utf-8') as f:
                            spec_data = json.load(f)
                        logger.info(f"Loaded latest spec file: {spec_file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to load spec file '{spec_file_path}': {e}")

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
            if all_spec_files:
                spec_file_path = os.path.join(OUTPUTS_DIR, max(all_spec_files, key=lambda f: os.path.getmtime(os.path.join(OUTPUTS_DIR, f))))
                try:
                    with open(spec_file_path, 'r', encoding='utf-8') as f:
                        spec_data = json.load(f)
                    logger.info(f"Loaded latest specification file: {spec_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to load latest specification file '{spec_file_path}': {e}")

        if not project_root:
            raise ValueError("Could not determine a project root to test.")

        framework = "unknown"
        app_package = "backend"

        if design_data:
            folder_structure = design_data.get('folder_Structure', {}).get('structure', [])
            for item in folder_structure:
                relative_path = item['path'].strip().replace('\\', '/')
                if relative_path.endswith('main.py'):
                    backend_dir = os.path.dirname(relative_path).lstrip('/').lstrip('\\')
                    app_package = backend_dir or "app"
                    logger.info(f"Detected app package from JSON design: {app_package}")
                    break

        if spec_data:
            tech_stack = spec_data.get('technology_Stack', {}).get('backend', {})
            framework_name = tech_stack.get('framework', '').lower()
            if "fastapi" in framework_name:
                framework = "fastapi"
            elif "flask" in framework_name:
                framework = "flask"
            logger.info(f"Detected framework from JSON specification: {framework}")

        if framework == "unknown":
            requirements_path = os.path.join(project_root, "requirements.txt")
            if os.path.exists(requirements_path):
                with open(requirements_path, 'r', encoding='utf-8') as f:
                    reqs = f.read().lower()
                    if "fastapi" in reqs:
                        framework = "fastapi"
                        if app_package == "app":
                            app_package = "backend"
                    elif "flask" in reqs:
                        framework = "flask"
                        if app_package == "app":
                            app_package = "app"

        if framework == "unknown":
            logger.warning("Could not detect framework. Defaulting to FastAPI.")
            framework = "fastapi"
            if app_package == "backend":
                app_package = "backend"

        logger.info(f"Final detected project: {os.path.basename(project_root)}, Framework: {framework}, App Package: {app_package}")
        return project_root, framework, app_package, design_data, spec_data

    def ensure_init_py_recursive(self, base_directory_path: str) -> None:
        for root, dirs, files in os.walk(base_directory_path):
            if 'venv' in dirs:
                dirs.remove('venv')
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

    def update_requirements_for_testing(self, project_root: str) -> bool:
        requirements_path = os.path.join(project_root, "requirements.txt")
        if not os.path.exists(requirements_path):
            logger.warning(f"requirements.txt not found at {requirements_path}. Creating an empty one.")
            with open(requirements_path, 'w', encoding='utf-8') as f:
                f.write("")
            existing_reqs = []
        else:
            with open(requirements_path, 'r', encoding='utf-8') as f:
                existing_reqs = [line.strip() for line in f if line.strip()]

        pytest_present = any(re.match(r"^pytest($|[<=>~])", req.lower()) for req in existing_reqs)
        pytest_mock_present = any(re.match(r"^pytest-mock($|[<=>~])", req.lower()) for req in existing_reqs)
        pytest_asyncio_present = any(re.match(r"^pytest-asyncio($|[<=>~])", req.lower()) for req in existing_reqs)

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
        logger.info("All required test dependencies are already present in requirements.txt.")
        return False

    def install_project_dependencies(self, project_root: str) -> None:
        venv_python_path = os.path.join(project_root, "venv", "Scripts", "python.exe")
        requirements_file_name = "requirements.txt"
        requirements_path_full = os.path.join(project_root, requirements_file_name)

        if not os.path.exists(venv_python_path):
            logger.error(f"Virtual environment python executable not found at {venv_python_path}.")
            raise FileNotFoundError(f"Project venv not found: {venv_python_path}")

        if not os.path.exists(requirements_path_full):
            logger.warning(f"requirements.txt not found at {requirements_path_full}. Skipping dependency installation.")
            return

        logger.info(f"Installing dependencies from {requirements_path_full} into project venv...")
        try:
            result = subprocess.run(
                [venv_python_path, "-m", "pip", "install", "-r", requirements_file_name],
                capture_output=True,
                text=True,
                check=True,
                cwd=project_root
            )
            logger.info(f"Successfully installed dependencies. Pip output:\n{result.stdout}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install dependencies. Exit code: {e.returncode}")
            raise

    def generate_unit_tests(self, function_code: str, function_name: str, module_path: str, 
                           framework: str, context: str, is_method: bool = False, 
                           class_name: Optional[str] = None) -> Optional[str]:
        framework_specific = {
            "flask": {
                "imports": "from flask import request, render_template, redirect, url_for",
                "mock_targets": f"{module_path}.request, {module_path}.render_template, {module_path}.redirect, {module_path}.url_for",
                "context_hint": "Use app.test_request_context() for Flask routes. Mock db.session and models appropriately."
            },
            "fastapi": {
                "imports": "from fastapi import Request, HTTPException, Depends",
                "mock_targets": f"{module_path}.Request, {module_path}.HTTPException",
                "context_hint": "Mock FastAPI dependencies using pytest-mock's mocker fixture. Use TestClient for API calls."
            }
        }.get(framework, {"imports": "", "mock_targets": "", "context_hint": ""})

        target_import = ""
        target_source_info = ""
        test_file_prefix = ""

        if is_method and class_name:
            target_import = f"from {module_path} import {class_name}"
            target_source_info = f"{module_path}.{class_name}.{function_name}"
            method_context = f"This is a method of class `{class_name}`. Instantiate or mock `{class_name}`."
            test_file_prefix = f"test_{class_name}_"
        else:
            target_import = f"from {module_path} import {function_name}"
            target_source_info = f"{module_path}.{function_name}"
            method_context = "This is a top-level function."
            test_file_prefix = f"test_{function_name}_"

        prompt = f"""
You are an expert Python test engineer specializing in pytest and {framework} applications.
Generate comprehensive unit tests for the following function/method using pytest and pytest-mock.

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

Requirements:
1. Output only raw Python code for the test file.
2. Name test file as `{test_file_prefix}test_scenario.py`.
3. Test functions must start with `test_` followed by function/method name and scenario.
4. Include imports: pytest, unittest.mock, {framework_specific['imports']}, {target_import}.
5. Mock dependencies: {framework_specific['mock_targets']}.
6. Test happy path, edge cases, and error conditions.
7. Include `# source_info: {target_source_info}` in each test function.
8. Ensure tests are runnable with pytest from project root.
"""
        time.sleep(API_CALL_DELAY_SECONDS)
        try:
            response = self.llm.invoke(prompt)
            generated_text = response.content.strip()
            if generated_text.startswith("```python"):
                generated_text = generated_text[len("```python"):].strip()
            if generated_text.endswith("```"):
                generated_text = generated_text[:-3].strip()
            if not generated_text.strip():
                logger.warning(f"LLM returned empty content for unit tests for {function_name}.")
                return None
            return generated_text
        except Exception as e:
            logger.error(f"Failed to generate unit tests for {function_name}: {e}", exc_info=True)
            return None

    def generate_integration_tests(self, app_package: str, framework: str, 
                                  endpoints: List[Dict[str, Any]], project_root: str) -> Optional[str]:
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
            logger.warning("No API endpoints provided for integration testing.")
            return None

        prompt = f"""
You are an expert Python test engineer specializing in pytest and {framework} applications.
Generate comprehensive pytest integration tests for the {framework} application.

Module Path: {app_package}.main
Application Entry Point: `app`

API Endpoints:
{json.dumps(endpoints, indent=2)}

Requirements:
1. Output only raw Python code for the test file.
2. Name test file as `test_integration.py`.
3. Test functions must start with `test_` followed by API action and scenario.
4. Include `# source_info: backend.routers.your_router_file.your_endpoint_function` in each test function.
5. Include imports: pytest, {framework_specific['client_import']}, {framework_specific['app_import']}.
6. Set up test client using `{framework_specific['client_setup']}`.
7. Test valid inputs, invalid inputs, edge cases, and sequential operations.
8. Verify status codes and JSON payloads.
9. Ensure tests are runnable with pytest from project root.
"""
        time.sleep(API_CALL_DELAY_SECONDS)
        try:
            response = self.llm.invoke(prompt)
            generated_text = response.content.strip()
            if generated_text.startswith("```python"):
                generated_text = generated_text[len("```python"):].strip()
            if generated_text.endswith("```"):
                generated_text = generated_text[:-3].strip()
            if not generated_text.strip():
                logger.warning("LLM returned empty content for integration tests.")
                return None
            return generated_text
        except Exception as e:
            logger.error(f"Failed to generate integration tests for {app_package}: {e}", exc_info=True)
            return None

    def run_test(self, project_root: str) -> List[Dict[str, Any]]:
        bat_file = os.path.join(project_root, "run_test.bat")
        test_log_file = os.path.join(project_root, TEST_LOG_FILE)

        if not os.path.exists(bat_file):
            logger.error(f"run_test.bat not found at {bat_file}.")
            return []

        try:
            result = subprocess.run(
                f'"{bat_file}"',
                shell=True,
                capture_output=True,
                text=True,
                cwd=project_root,
                check=False
            )
            if result.stdout:
                logger.debug(f"run_test.bat stdout:\n{result.stdout}")
            if result.stderr:
                logger.error(f"run_test.bat stderr:\n{result.stderr}")
            logger.info(f"Pytest run completed. Exit code: {result.returncode}")

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
                                logger.warning(f"Test file path '{test_file_full_path}' does not exist for test '{test_name}'.")
                                continue
                            source_file, source_func = self._map_test_to_source(test_file_full_path, test_name)
                            failures.append({
                                "test": test_name,
                                "test_file_path": test_file_full_path,
                                "source_file": source_file,
                                "source_function": source_func,
                            })
                            error_details = []
                            logger.error(f"Test failure: {failure}")
                            with open(failure_log_file, 'a', encoding='utf-8') as f:
                                f.write(f"\nTest: {failure['test']}\n")
                                f.write(f"Test File Path: {failure['test_file_path']}\n")
                                f.write(f"Source File: {failure['source_file']}\n")
                                f.write(f"Source Function: {failure['source_function']}\n")
                                f.write(f"Error Line Summary: {failure['error_line_summary']}\n")
                            error_details = []
                            test_name = None
                            test_file_rel_path = None

                if capture_error and test_name:
                    test_file_full_path = os.path.join(project_root, test_file_rel_path.replace('/', os.sep))
                    if os.path.exists(test_file_full_path):
                        source_file, source_func = self._map_test_to_source(test_file_full_path, test_name)
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
                    logger.error("No tests were executed.")
                    return []
                if failures:
                    logger.error(f"Tests failed. Returning failure information.")
                    return failures
                logger.info("All tests passed successfully.")
                return []
            logger.error(f"Pytest log file '{test_log_file}' not found.")
            return []
        except Exception as e:
            logger.error(f"Error during test execution: {e}", exc_info=True)
            return []

    def _map_test_to_source(self, test_file_path: str, test_name: str) -> Tuple[str, str]:
        logger.debug(f"Mapping test '{test_name}' from '{test_file_path}' to source.")
        try:
            with open(test_file_path, 'r', encoding='utf-8') as f:
                test_content = f.read()
            test_func_pattern = rf"(def\s+{re.escape(test_name)}\s*\(.*?\):\s*\n(?:(?!\n\s*def\s+test_).)*?)(?=\n\s*def\s+test_|\Z)"
            test_func_match = re.search(test_func_pattern, test_content, re.DOTALL | re.MULTILINE)
            if test_func_match:
                func_block_content = test_func_match.group(1)
                source_info_match = re.search(r"#\s*source_info:\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+)", func_block_content)
                if source_info_match:
                    full_source_path = source_info_match.group(1)
                    parts = full_source_path.split('.')
                    if len(parts) >= 2:
                        source_func_or_method_name = parts[-1]
                        parent_name = os.path.dirname(parts[0])
                        if parent_name and parent_name[0].isupper() and parent_name.isalpha():
                            if len(parts) >= 3:
                                module_part = ".".join(parts[:-2])
                                return f"{module_part.replace('.', os.sep)}.py", f"{parent_name}.{source_func_or_method}"
                            else:
                                logger.warning(f"Failed to find source_info for '{test_name}' in '{test_file_path}'. Returning 'unknown_file.py'.")
                                return "unknown_file.py", f"{parent_name}.{source_func_or_method}"
                        else:
                            module_part = ".".join(parts[:-1])
                            return f"{module_part.replace('.', os.sep)}.py", source_func_or_method_name
                    logger.warning(f"Malformed source_info in {test_file_path} for {test_name}: {full_source_path}")
            logger.debug(f"No source_info found for {test_name}")
 in {test_file_path}")
        except Exception as e:
            logger.error(f"Error parsing test file {test_file_path} for {test_name}: {source_info: {e}")
            return "unknown_file.py", "unknown_function"

        heuristic_func_name_match = re.match(r"test_([a-zA-Z0-9_]+)(?:_test_|$)", test_name)
        heuristic_func_name = heuristic_func_name_match.group(1) if if heuristic_func_name_match else "unknown_function"
        return "integration" if "integration" in in test_file_path.lower():
            return os.path.basename(test_file_path), heuristic_func_name
        return "unknown_file.py", heuristic_func_name

    # Define StructuredTools
    def get_tools(self):
        return [
            StructuredTool.from_function(
                func=self.detect_project_and_framework,
                name="detect_project_and_framework",
                description="Detects project root, framework, and app package. Returns project_root, framework, app_package, design_data, spec_data.",
                args_schema=class DetectInput(BaseModel):
                    specified_project_name: Optional[str] = Field(description="Project name.", default=None)
                    design_file_path: Optional[str] = Field(description="Design file path.", default=None)
                    spec_file_path:: Optional[str] = Field(description="Spec file path.", default=None)
                ,
                return_direct=False
            ),
            StructuredTool.from_function(
                func=self.create_pytest_ini,
                name="create_pytest_ini",
                description="Creates or updates pytest.ini with asyncio and cachedir settings.",
                args_schema=class CreatePytestIniInput(BaseModel):
                    project_root: str = Field(description="Project root directory.")
                ,
                return_direct=False
            ),
            StructuredTool.from_function(
                func=self.generate_run_test_bat_script,
                name="generate_run_test_bat_script",
                description="Generates run_test.bat script.",
                args_schema=class GenerateRunTestBatInput(BaseModel):
                    project_root: str = Field(description="Project root directory.")
                    venv_python_path: str = Field(description="Path to venv Python executable.")
                ,
                return_direct=True
            ),
            StructuredTool.from_function(
                func=self.ensure_init_py_recursive,
                name="ensure_init_py_recursive",
                description="Ensures __init__.py files exist in directories with Python files.",
                args_schema=class EnsureInitPyInput(BaseModel):
                    base_directory_path: str = Field(description="Base directory path.")
                ,
                return_direct=False
            ),
            StructuredTool.from_function(
                func=self.update_requirements_for_testing,
                name="update_requirements_for_testing",
                description="Updates requirements.txt with test dependencies.",
                args_schema=class UpdateRequirementsInput(BaseModel):
                    project_root: str = Field(description="Project root directory.")
                ,
                return_direct=True
            ),
            StructuredTool.from_function(
                func=self.install_project_dependencies,
                name="install_project_dependencies",
                description="Installs project dependencies from requirements.txt.",
                args_schema=class InstallDependenciesInput(BaseModel):
                    project_root: str = Field(description="Project root directory.")
                ,
                return_direct=False
            ),
            StructuredTool.from_function(
                func=self.generate_unit_tests,
                name="generate_unit_tests",
                description="Generates unit tests for a function/method.",
                args_schema=GenerateUnitTestsInput,
                return_direct=True
            ),
            StructuredTool.from_function(
                func=self.generate_integration_tests,
                name="generate_integration_tests",
                description="Generates integration tests for API endpoints.",
                args_schema=GenerateIntegrationTestsInput,
                return_direct=True
            ),
            StructuredTool.from_function(
                func=self.run_test,
                name="run_test",
                description="Runs the test suite and returns failures.",
                args_schema=class RunTestInput(BaseModel):
                    project_root: str = Field(description="Project root directory.")
                ,
                return_direct=True
            )
        ]

async def main():
    parser = argparse.ArgumentParser(description="Testing Agent using LangChain.")
    parser.add_argument('--project', type=str, help="Specify project directory name.")
    parser.add_argument('--design_file', type=str, help="Path to JSON design file.")
    parser.add_argument('--spec_file', type=str, help="Path to JSON specification file.")
    args = parser.parse_args()

    tools_instance = TestingTools()
    tools = tools_instance.get_tools()
    llm = ChatGoogleGenerativeAI(model=DEFAULT_MODEL, google_api_key=api_key)
    memory = MemorySaver()

    agent = create_react_agent(llm, tools, checkpointer=memory)

    async def stream_agent_execution(prompt: str, thread_id: str):
        config = {"configurable": {"thread_id": thread_id}}
        async for event in agent.astream_events({"messages": [HumanMessage(content=prompt)]}, config=config, version="v1"):
            if event["event"] == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    print(content, end="", flush=True)
            elif event["event"] == "on_tool_call":
                logger.info(f"Tool called: {event['data']['name']}")

    prompt = f"""
You are an expert Testing Agent for a Python web application (FastAPI/Flask, HTML/CSS/JS, Windows-only).
Your goal is to generate and run tests, log failures, and prepare data for the Debug Agent.

**Process**:
1. Call `detect_project_and_framework` with specified_project_name='{args.project}', design_file_path='{args.design_file}', spec_file_path='{args.spec_file}'.
2. Call `create_pytest_ini` with the project_root from step 1.
3. Check if '{TEST_GENERATED_FLAG}' exists in project_root. If not:
   - Create test directories: '{TEST_OUTPUT_DIR_NAME}/{UNIT_TEST_SUBDIR}' and '{TEST_OUTPUT_DIR_NAME}/{INTEGRATION_TEST_SUBDIR}'.
   - Call `ensure_init_py_recursive` for app_package directory and test directories.
   - Call `update_requirements_for_testing` and `install_project_dependencies` if needed.
   - Scan source directory (app_package) for Python files.
   - For each function/method, call `generate_unit_tests`.
   - For API endpoints from design_data, call `generate_integration_tests`.
   - Create '{TEST_GENERATED_FLAG}' file.
4. Call `generate_run_test_bat_script` with venv_python_path='{os.path.join('{project_root}', 'venv', 'Scripts', 'python.exe')}'.
5. Call `run_test` and log failures to '{TEST_LOG_FILE}' and '{TEST_HISTORY_LOG_FILE}'.
6. If failures exist, exit with code 1. Otherwise, report success.

**Inputs**:
- Project: {args.project}
- Design File: {args.design_file}
- Spec File: {args.spec_file}

Start by calling `detect_project_and_framework`.
"""
    try:
        await stream_agent_execution(prompt, thread_id="test_agent_thread")
    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())