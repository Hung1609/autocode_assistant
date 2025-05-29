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
BASE_GENERATED_DIR = os.getenv('BASE_GENERATED_DIR', 'code_generated_result')
OUTPUTS_DIR = os.getenv('OUTPUTS_DIR', r'C:\Users\Hoang Duy\Documents\Phan Lac Hung\autocode_assistant\src\module_1_vs_2\outputs')
TEST_OUTPUT_DIR_NAME = "tests"
TEST_LOG_FILE = "test_results.log"
TEST_GENERATED_FLAG = ".test_generated"

def create_pytest_ini(project_root):
    pytest_ini_path = os.path.join(project_root, "pytest.ini")
    pytest_ini_content = """\
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
"""
    if os.path.exists(pytest_ini_path):
        with open(pytest_ini_path, 'r', encoding='utf-8') as f:
            current_content = f.read()
        if "asyncio_mode = auto" in current_content:
            logger.info(f"pytest.ini already exists in {project_root}. Skipping creation.")
            return
    with open(pytest_ini_path, 'w', encoding='utf-8') as f:
        f.write(pytest_ini_content)
    logger.info(f"Created pytest.ini in {project_root}")

def generate_test_run_script(project_root, venv_python_path):
    bat_file_path = os.path.join(project_root, "run_tests.bat")
    bat_content = fr"""@echo off
setlocal EnableDelayedExpansion

echo Running tests... > debug_tests.log 2>&1

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%" >> debug_tests.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to change to project root directory %PROJECT_ROOT%. >> debug_tests.log 2>&1
    exit /b 1
)

echo Checking for Python... >> debug_tests.log 2>&1
"{venv_python_path}" --version >> debug_tests.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found at {venv_python_path}. >> debug_tests.log 2>&1
    exit /b 1
)

echo Activating virtual environment... >> debug_tests.log 2>&1
call "%PROJECT_ROOT%venv\Scripts\activate.bat" >> debug_tests.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to activate virtual environment. >> debug_tests.log 2>&1
    exit /b 1
)

echo Running pytest... >> debug_tests.log 2>&1
"{venv_python_path}" -m pytest tests --exitfirst --tb=short -v > {TEST_LOG_FILE} 2>&1
set TEST_EXIT_CODE=%ERRORLEVEL%

echo Deactivating virtual environment... >> debug_tests.log 2>&1
deactivate >> debug_tests.log 2>&1

if %TEST_EXIT_CODE% neq 0 (
    echo ERROR: Tests failed. Check {TEST_LOG_FILE} for details. >> debug_tests.log 2>&1
    exit /b %TEST_EXIT_CODE%
)

echo Tests completed successfully. >> debug_tests.log 2>&1
exit /b 0
"""
    with open(bat_file_path, 'w', encoding='utf-8') as f:
        f.write(bat_content)
    logger.info(f"Created run_tests.bat at {bat_file_path}")
    return bat_file_path

def detect_project_and_framework(specified_project_name=None, design_file_path=None, spec_file_path=None):
    logger.info("Detecting project and framework...")
    if not os.path.exists(BASE_GENERATED_DIR):
        msg = f"Base directory '{BASE_GENERATED_DIR}' does not exist. Run codegen_agent.py first."
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
                    project_root = potential_project_root
                    logger.info(f"Detected project root from specified design: {project_root}")
                else:
                    logger.warning(f"Project directory '{potential_project_root}' not found.")
        except Exception as e:
            logger.error(f"Failed to load specified JSON files: {e}")
            raise ValueError(f"Invalid specified JSON files: {e}")

    if not project_root and specified_project_name:
        potential_project_root = os.path.join(BASE_GENERATED_DIR, specified_project_name)
        if os.path.isdir(potential_project_root):
            project_root = potential_project_root
            logger.info(f"Using specified project folder: {project_root}")
            relevant_design_files = [f for f in os.listdir(OUTPUTS_DIR) if f.endswith('.design.json') and specified_project_name in f]
            relevant_spec_files = [f for f in os.listdir(OUTPUTS_DIR) if f.endswith('.spec.json') and specified_project_name in f]
            if relevant_design_files:
                design_file_path = os.path.join(OUTPUTS_DIR, max(relevant_design_files, key=lambda f: os.path.getmtime(os.path.join(OUTPUTS_DIR, f))))
                try:
                    with open(design_file_path, 'r', encoding='utf-8') as f:
                        design_data = json.load(f)
                    logger.info(f"Loaded design file: {design_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to load design file '{design_file_path}': {e}")
            if relevant_spec_files:
                spec_file_path = os.path.join(OUTPUTS_DIR, max(relevant_spec_files, key=lambda f: os.path.getmtime(os.path.join(OUTPUTS_DIR, f))))
                try:
                    with open(spec_file_path, 'r', encoding='utf-8') as f:
                        spec_data = json.load(f)
                    logger.info(f"Loaded spec file: {spec_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to load spec file '{spec_file_path}': {e}")
        else:
            logger.warning(f"Specified project folder '{specified_project_name}' not found.")

    if not project_root:
        projects = [d for d in os.listdir(BASE_GENERATED_DIR) if os.path.isdir(os.path.join(BASE_GENERATED_DIR, d))]
        if not projects:
            msg = f"No project folders found in '{BASE_GENERATED_DIR}'."
            logger.error(msg)
            raise ValueError(msg)
        project_dir_name = max(projects, key=lambda p: os.path.getctime(os.path.join(BASE_GENERATED_DIR, p)))
        project_root = os.path.join(BASE_GENERATED_DIR, project_dir_name)
        logger.info(f"Using most recent project folder: {project_root}")
        all_design_files = [f for f in os.listdir(OUTPUTS_DIR) if f.endswith('.design.json')]
        all_spec_files = [f for f in os.listdir(OUTPUTS_DIR) if f.endswith('.spec.json')]
        if all_design_files:
            design_file_path = os.path.join(OUTPUTS_DIR, max(all_design_files, key=lambda f: os.path.getmtime(os.path.join(OUTPUTS_DIR, f))))
            try:
                with open(design_file_path, 'r', encoding='utf-8') as f:
                    design_data = json.load(f)
                logger.info(f"Loaded design file: {design_file_path}")
            except Exception as e:
                logger.warning(f"Failed to load design file '{design_file_path}': {e}")
        if all_spec_files:
            spec_file_path = os.path.join(OUTPUTS_DIR, max(all_spec_files, key=lambda f: os.path.getmtime(os.path.join(OUTPUTS_DIR, f))))
            try:
                with open(spec_file_path, 'r', encoding='utf-8') as f:
                    spec_data = json.load(f)
                logger.info(f"Loaded spec file: {spec_file_path}")
            except Exception as e:
                logger.warning(f"Failed to load spec file '{spec_file_path}': {e}")

    if not project_root:
        raise ValueError("Could not determine project root.")
    if not design_data:
        logger.warning("No valid design data found.")
    if not spec_data:
        logger.warning("No valid specification data found.")

    framework = "unknown"
    app_package = "app"

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

    if framework == "unknown":
        logger.warning("Could not detect framework. Defaulting to Flask.")
        framework = "flask"

    logger.info(f"Final detected project: {os.path.basename(project_root)}, Framework: {framework}, App Package: {app_package}")
    return project_root, framework, app_package, design_data, spec_data

def ensure_init_py_recursive(base_directory_path):
    for root, dirs, files in os.walk(base_directory_path):
        if 'venv' in dirs:
            dirs.remove('venv')
            logger.debug(f"Skipping 'venv' directory in {root}")
        if any(f.endswith(".py") for f in files):
            init_py_path = os.path.join(root, "__init__.py")
            if not os.path.exists(init_py_path):
                with open(init_py_path, 'w', encoding='utf-8') as f:
                    f.write("# This file makes this directory a Python package.\n")
                logger.info(f"Created missing __init__.py in {root}")

def update_requirements_for_testing(project_root):
    requirements_path = os.path.join(project_root, "requirements.txt")
    if not os.path.exists(requirements_path):
        with open(requirements_path, 'w', encoding='utf-8') as f:
            f.write("")
    with open(requirements_path, 'r', encoding='utf-8') as f:
        existing_reqs = [line.strip() for line in f if line.strip()]
    reqs_to_add = []
    for req in ["pytest", "pytest-mock", "pytest-asyncio"]:
        if not any(re.match(rf"^{req}($|[<=>~])", r.lower()) for r in existing_reqs):
            reqs_to_add.append(req)
    if reqs_to_add:
        with open(requirements_path, 'a', encoding='utf-8') as f:
            for req in reqs_to_add:
                f.write(f"\n{req}")
        logger.info(f"Added {', '.join(reqs_to_add)} to {requirements_path}")
        return True
    return False

def install_project_dependencies(project_root):
    venv_python_path = os.path.join(project_root, "venv", "Scripts", "python.exe")
    requirements_path = os.path.join(project_root, "requirements.txt")
    if not os.path.exists(venv_python_path):
        logger.error(f"Virtual environment not found at {venv_python_path}")
        raise FileNotFoundError(f"Virtual environment not found: {venv_python_path}")
    if not os.path.exists(requirements_path):
        logger.warning(f"requirements.txt not found at {requirements_path}")
        return
    logger.info(f"Installing dependencies from {requirements_path}")
    result = subprocess.run(
        [venv_python_path, "-m", "pip", "install", "-r", requirements_path],
        capture_output=True,
        text=True,
        cwd=project_root
    )
    if result.returncode != 0:
        logger.error(f"Failed to install dependencies: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, result.args)

def generate_unit_tests(function_code, function_name, module_path, framework, context, is_method=False, class_name=None):
    model = GenerativeModel(DEFAULT_MODEL)
    framework_specific = {
        "flask": {
            "imports": "from flask import request, render_template, redirect, url_for",
            "mock_targets": f"{module_path}.request, {module_path}.render_template, {module_path}.redirect, {module_path}.url_for",
            "context_hint": "Use app.test_request_context() for Flask routes. Mock db.session and models appropriately."
        },
        "fastapi": {
            "imports": "from fastapi import Request, HTTPException, Depends",
            "mock_targets": f"{module_path}.Request, {module_path}.HTTPException",
            "context_hint": "Mock FastAPI dependencies and use TestClient for API calls."
        }
    }.get(framework, {"imports": "", "mock_targets": "", "context_hint": ""})
    target_import = f"from {module_path} import {class_name}" if is_method else f"from {module_path} import {function_name}"
    target_source_info = f"{module_path}.{class_name}.{function_name}" if is_method else f"{module_path}.{function_name}"
    test_file_prefix = f"test_{class_name}_" if is_method else f"test_{function_name}_"
    prompt = f"""
    Generate pytest unit tests for the Python function/method below.

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

    Requirements:
    1. Output only Python code.
    2. Include imports: pytest, unittest.mock, {framework_specific['imports']}, {target_import}.
    3. Mock dependencies: {framework_specific['mock_targets']}.
    4. Test happy path, edge cases, and errors.
    5. Test names: test_{function_name}_<scenario> or test_{class_name}_{function_name}_<scenario>.
    6. Add comment: # source_info: {target_source_info}
    """
    time.sleep(API_CALL_DELAY_SECONDS)
    try:
        response = model.generate_content(prompt)
        generated_text = response.text.strip()
        if generated_text.startswith("```python"):
            generated_text = generated_text[len("```python"):].strip()
        if generated_text.endswith("```"):
            generated_text = generated_text[:-3].strip()
        return generated_text
    except Exception as e:
        logger.error(f"Failed to generate unit tests for {function_name}: {e}")
        return None

def generate_integration_tests(app_package, framework, endpoints, project_root):
    model = GenerativeModel(DEFAULT_MODEL)
    framework_specific = {
        "fastapi": {
            "client_import": "from fastapi.testclient import TestClient",
            "client_setup": f"from {app_package}.main import app; client = TestClient(app)",
            "app_import": f"from {app_package}.main import app"
        }
    }.get(framework, {"client_import": "", "client_setup": "", "app_import": ""})
    prompt = f"""
    Generate pytest integration tests for the {framework} application.

    Module Path: {app_package}.main
    Endpoints:
    {json.dumps(endpoints, indent=2)}

    Requirements:
    1. Output only Python code.
    2. Include imports: pytest, {framework_specific['client_import']}, {framework_specific['app_import']}.
    3. Set up test client: {framework_specific['client_setup']}.
    4. Test valid/invalid inputs, status codes, payloads.
    5. Add comment: # source_info: {app_package}.<endpoint_function>
    """
    time.sleep(API_CALL_DELAY_SECONDS)
    try:
        response = model.generate_content(prompt)
        generated_text = response.text.strip()
        if generated_text.startswith("```python"):
            generated_text = generated_text[len("```python"):].strip()
        if generated_text.endswith("```"):
            generated_text = generated_text[:-3].strip()
        return generated_text
    except Exception as e:
        logger.error(f"Failed to generate integration tests: {e}")
        return None

def run_tests(project_root):
    bat_file = os.path.join(project_root, "run_tests.bat")
    if not os.path.exists(bat_file):
        logger.error(f"run_tests.bat not found at {bat_file}")
        return False
    try:
        result = subprocess.run(
            f'"{bat_file}"',
            shell=True,
            capture_output=True,
            text=True,
            cwd=project_root
        )
        logger.info(f"Pytest exit code: {result.returncode}")
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Failed to run tests: {e}")
        return False

def map_test_to_source(test_name, test_file_path):
    try:
        with open(test_file_path, 'r', encoding='utf-8') as f:
            test_content = f.read()
        pattern = rf"(def\s+{re.escape(test_name)}\s*\(.*?\):\s*\n(?:(?!\n\s*def\s+test_).)*?)(?=\n\s*def\s+test_|\Z)"
        match = re.search(pattern, test_content, re.DOTALL | re.MULTILINE)
        if match:
            func_block = match.group(1)
            source_info_match = re.search(r"#\s*source_info:\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+)", func_block)
            if source_info_match:
                full_source_path = source_info_match.group(1)
                parts = full_source_path.split('.')
                if len(parts) >= 2:
                    source_func = parts[-1]
                    if len(parts) >= 3 and parts[-2][0].isupper():
                        module_part = ".".join(parts[:-2])
                        return f"{module_part.replace('.', os.sep)}.py", f"{parts[-2]}.{source_func}"
                    else:
                        module_part = ".".join(parts[:-1])
                        return f"{module_part.replace('.', os.sep)}.py", source_func
        logger.warning(f"No source_info found for {test_name} in {test_file_path}")
        return "unknown_file.py", test_name.replace("test_", "", 1)
    except Exception as e:
        logger.error(f"Error mapping test {test_name}: {e}")
        return "unknown_file.py", test_name.replace("test_", "", 1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate and run tests for a generated application.")
    parser.add_argument('--project', type=str, help="Specify project directory name.")
    parser.add_argument('--design_file', type=str, help="Path to JSON design file.")
    parser.add_argument('--spec_file', type=str, help="Path to JSON specification file.")
    args = parser.parse_args()

    try:
        project_root, framework, app_package, design_data, spec_data = detect_project_and_framework(
            args.project, args.design_file, args.spec_file
        )
        create_pytest_ini(project_root)

        test_output_dir = os.path.join(project_root, TEST_OUTPUT_DIR_NAME)
        test_flag_file = os.path.join(project_root, TEST_GENERATED_FLAG)
        venv_python_path = os.path.join(project_root, "venv", "Scripts", "python.exe")

        if not os.path.exists(test_flag_file):
            os.makedirs(test_output_dir, exist_ok=True)
            ensure_init_py_recursive(os.path.join(project_root, app_package))
            ensure_init_py_recursive(test_output_dir)

            needs_test_deps_install = update_requirements_for_testing(project_root)
            if needs_test_deps_install:
                install_project_dependencies(project_root)

            source_dir = os.path.join(project_root, app_package)
            for root, _, files in os.walk(source_dir):
                for file in files:
                    if file.endswith(".py") and file != "__init__.py":
                        file_path = os.path.join(root, file)
                        module_name = os.path.relpath(file_path, project_root).replace(os.sep, ".")[:-3]
                        with open(file_path, 'r', encoding='utf-8') as f:
                            source = f.read()
                        tree = ast.parse(source)
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                func_name = node.name
                                func_code = ast.get_source_segment(source, node)
                                if func_code:
                                    test_code = generate_unit_tests(
                                        func_code, func_name, module_name, framework,
                                        f"Function {func_name} in {module_name}.",
                                        is_method=False
                                    )
                                    if test_code:
                                        test_file = os.path.join(test_output_dir, f"test_{func_name}.py")
                                        with open(test_file, 'w', encoding='utf-8') as f:
                                            f.write(test_code)
                                        logger.info(f"Saved unit tests to {test_file}")

            endpoints = design_data.get('interface_Design', {}).get('api_Specifications', [])
            test_code = generate_integration_tests(app_package, framework, endpoints, project_root)
            if test_code:
                test_file = os.path.join(test_output_dir, "test_integration.py")
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(test_code)
                logger.info(f"Saved integration tests to {test_file}")

            with open(test_flag_file, 'w', encoding='utf-8') as f:
                f.write("Tests generated")
            logger.info(f"Marked tests as generated: {test_flag_file}")

        generate_test_run_script(project_root, venv_python_path)
        run_tests(project_root)

    except Exception as e:
        logger.error(f"Test generation pipeline failed: {e}")
        sys.exit(1)