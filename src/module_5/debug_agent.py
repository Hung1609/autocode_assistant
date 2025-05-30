import os
import json
import logging
import time
import re
import subprocess
import ast
from google.generativeai import GenerativeModel, configure
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

API_CALL_DELAY_SECONDS = 5

api_key = os.getenv('GEMINI_API_KEY')
configure(api_key=api_key)
logger.info("Gemini API configured successfully for debug agent.")

DEFAULT_MODEL = 'gemini-2.0-flash'
BASE_GENERATED_DIR = os.getenv('BASE_GENERATED_DIR', 'code_generated_result')
OUTPUTS_DIR = os.getenv('OUTPUTS_DIR', r'C:\Users\Hoang Duy\Documents\Phan Lac Hung\autocode_assistant\src\module_1_vs_2\outputs')
# OUTPUTS_DIR = os.getenv('OUTPUTS_DIR', r'C:\Users\ADMIN\Documents\Foxconn\autocode_assistant\src\module_1_vs_2\outputs')
TEST_LOG_FILE = "test_results.log"
DEBUG_LOG_FILE = "debug_results.log" # Log chi tiết quá trình debug (fix được đề xuất, v.v.)
TEST_HISTORY_LOG_FILE = "test_results_history.log" # Log lịch sử test (được ghi bởi test_generator_agent)

def detect_project_and_framework(specified_project=None):
    if not os.path.exists(BASE_GENERATED_DIR):
        logger.error(f"Base directory '{BASE_GENERATED_DIR}' does not exist.")
        raise FileNotFoundError(f"Base directory '{BASE_GENERATED_DIR}' does not exist.")

    projects = [d for d in os.listdir(BASE_GENERATED_DIR) if os.path.isdir(os.path.join(BASE_GENERATED_DIR, d))]
    if not projects:
        logger.error(f"No project folders found in '{BASE_GENERATED_DIR}'.")
        raise ValueError("No project folders found.")

    project_dir = None
    design_file = None

    if specified_project:
        specified_path = os.path.join(BASE_GENERATED_DIR, specified_project)
        if os.path.isdir(specified_path):
            project_dir = specified_project
            design_files = [f for f in os.listdir(OUTPUTS_DIR) if f.startswith(f"{specified_project}_") and f.endswith('.design.json')]
            if design_files:
                design_file = os.path.join(OUTPUTS_DIR, max(design_files, key=lambda f: os.path.getmtime(os.path.join(OUTPUTS_DIR, f))))
                logger.info(f"Using specified project folder: {project_dir} with design file: {design_file}")
            else:
                logger.warning(f"No design file found for specified project '{specified_project}'.")
        else:
            logger.warning(f"Specified project '{specified_project}' not found in '{BASE_GENERATED_DIR}'.")

    if not project_dir:
        project_times = [(p, os.path.getctime(os.path.join(BASE_GENERATED_DIR, p))) for p in projects]
        project_dir = max(project_times, key=lambda x: x[1])[0]
        design_files = [f for f in os.listdir(OUTPUTS_DIR) if f.startswith(f"{project_dir}_") and f.endswith('.design.json')]
        if design_files:
            design_file = os.path.join(OUTPUTS_DIR, max(design_files, key=lambda f: os.path.getmtime(os.path.join(OUTPUTS_DIR, f))))
            logger.info(f"Using most recent project folder: {project_dir} with design file: {design_file}")
        else:
            logger.warning(f"No design file found for most recent project '{project_dir}'.")

    project_root = os.path.join(BASE_GENERATED_DIR, project_dir)
    framework = "unknown"
    app_package = "app"

    if design_file:
        try:
            with open(design_file, 'r', encoding='utf-8') as f:
                design_data = json.load(f)
            folder_structure = design_data.get('folder_Structure', {}).get('structure', [])
            for item in folder_structure:
                relative_path = item['path'].strip().replace('\\', '/')
                if relative_path.endswith('main.py'):
                    backend_dir = os.path.dirname(relative_path).lstrip('/').lstrip('\\')
                    app_package = backend_dir or "app"
                    logger.info(f"Detected app package from JSON design: {app_package}")
                    break
        except Exception as e:
            logger.error(f"Failed to parse design file '{design_file}': {e}")

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

    logger.info(f"Detected project: {project_dir}, Framework: {framework}, App Package: {app_package}")
    return project_root, framework, app_package

def parse_test_results(log_file):
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        pattern = re.compile(r"Test: (\w+)\nTest File Path: (.+?)\nSource File: (.+?)\nSource Function: (.+?)\nError Line Summary: (.+?)(?=\nTest:|\Z)", re.DOTALL)
        match = pattern.search(content)
        if match:
            failure = {
                "test": match.group(1),
                "test_file_path": match.group(2),
                "source_file": match.group(3),
                "source_function": match.group(4),
                "error_line": match.group(5).strip()
            }
            with open(os.path.join(os.path.dirname(log_file), TEST_HISTORY_LOG_FILE), 'a', encoding='utf-8') as f:
                f.write(f"\n--- Failure ---\n")
                for key, value in failure.items():
                    f.write(f"{key}: {value}\n")
            return [failure]
        logger.info(f"No test failures found in {log_file}")
        return []
    except Exception as e:
        logger.error(f"Failed to parse test results from {log_file}: {e}")
        return []

def get_function_code(filepath, function_name):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
        
        # Handle ClassName.methodName format
        class_name = None
        method_name = function_name
        if '.' in function_name:
            class_name, method_name = function_name.split('.')
        
        for node in ast.walk(tree):
            if class_name:
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    for method in node.body:
                        if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) and method.name == method_name:
                            return ast.get_source_segment(source, method)
            else:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
                    return ast.get_source_segment(source, node)
        
        logger.warning(f"Function or method {function_name} not found in {filepath}")
        return None
    except Exception as e:
        logger.error(f"Error extracting function {function_name} from {filepath}: {e}")
        return None

def apply_fix(filepath, original_code, fixed_code):
    if not os.access(filepath, os.W_OK):
        logger.error(f"No write permission for {filepath}")
        return False

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Validate that original_code appears exactly once
        occurrences = content.count(original_code)
        if occurrences != 1:
            logger.error(f"Original code appears {occurrences} times in {filepath}. Aborting to avoid incorrect replacement.")
            return False
        
        # Parse and replace using AST for precision
        tree = ast.parse(content)
        new_tree = tree  # Placeholder for AST manipulation
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and ast.get_source_segment(content, node) == original_code:
                # Parse fixed_code into AST
                fixed_ast = ast.parse(fixed_code).body[0]
                # Replace node (simplified; actual replacement needs node matching)
                # This is a placeholder; full AST replacement requires a custom visitor
                content = content.replace(original_code, fixed_code)
                break
        
        with open(filepath + '.bak', 'w', encoding='utf-8') as f:
            f.write(content)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Applied fix to {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to apply fix to {filepath}: {e}")
        return False

def generate_bug_fix(test_info, source_code, framework, app_package, debug_history):
    model = GenerativeModel(DEFAULT_MODEL)
    prompt = f"""
    Phân tích lỗi kiểm tra sau:
    Analyze the following error in testing

    Test: {test_info['test']}
    File: {test_info['source_file']}
    Hàm: {test_info['source_function']}
    Lỗi: {test_info['error_line']}

    Mã nguồn:
    ```python
    {source_code}
    ```

    Lịch sử debug trước đó:
    {debug_history}

    Ngữ cảnh:
    - Framework: {framework}
    - Thư mục ứng dụng: {app_package}

    Trả về:
    ```plaintext
    Nguyên nhân: [Giải thích]
    Giải pháp: [Cách sửa]
    Mã đã sửa:
    ```python
    [Mã đã sửa]
    ```
    ```
    """
    time.sleep(API_CALL_DELAY_SECONDS)
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Failed to generate bug fix for {test_info['test']}: {e}")
        return None

def generate_deploy_script(project_root, app_package):
    bat_file_path = os.path.join(project_root, "deploy_app.bat")
    bat_content = fr"""@echo off
setlocal EnableDelayedExpansion

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

call "%PROJECT_ROOT%venv\Scripts\activate.bat"
python -m uvicorn {app_package}.main:app --host 0.0.0.0 --port 8001
deactivate
exit /b 0
"""
    with open(bat_file_path, 'w', encoding='utf-8') as f:
        f.write(bat_content)
    logger.info(f"Created deploy_app.bat at {bat_file_path}")
    return bat_file_path

def deploy_app(project_root, app_package):
    bat_file = generate_deploy_script(project_root, app_package)
    try:
        subprocess.run(
            f'"{bat_file}"',
            shell=True,
            cwd=project_root
        )
        logger.info("Application deployed successfully.")
    except Exception as e:
        logger.error(f"Failed to deploy application: {e}")

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

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Debug generated application tests.")
    parser.add_argument('--project', type=str, help="Specify project directory name.")
    args = parser.parse_args()

    specified_project = os.getenv('DEBUG_PROJECT_DIR', args.project)
    project_root, framework, app_package = detect_project_and_framework(specified_project)

    test_log_file = os.path.join(project_root, TEST_LOG_FILE)
    debug_log_file = os.path.join(project_root, DEBUG_LOG_FILE)

    max_iterations = 100
    iteration = 0
    debug_history = ""

    while iteration < max_iterations:
        logger.info(f"Debug iteration {iteration + 1}/{max_iterations}")
        failures = parse_test_results(test_log_file)
        if not failures:
            logger.info("No test failures found. Deploying application.")
            deploy_app(project_root, app_package)
            break

        failure = failures[0]
        source_path = os.path.join(project_root, failure['source_file'].replace('/', os.sep))
        source_code = get_function_code(source_path, failure['source_function'])
        if not source_code:
            logger.warning(f"Could not extract code for {failure['source_function']} in {source_path}")
            break

        fix_response = generate_bug_fix(failure, source_code, framework, app_package, debug_history)
        if not fix_response:
            logger.warning(f"No fix generated for {failure['test']}")
            break

        try:
            cause = re.search(r"Nguyên nhân:\n(.+?)\nGiải pháp:", fix_response, re.DOTALL).group(1).strip()
            solution = re.search(r"Giải pháp:\n(.+?)\nMã đã sửa:", fix_response, re.DOTALL).group(1).strip()
            fixed_code = re.search(r"```python\n(.+?)\n```", fix_response, re.DOTALL).group(1).strip()
        except AttributeError:
            logger.error(f"Invalid fix response format for {failure['test']}")
            break

        with open(debug_log_file, 'a', encoding='utf-8') as log:
            log.write(f"\n--- Debug Iteration {iteration + 1} ---\n")
            log.write(f"Test: {failure['test']}\n")
            log.write(f"File: {failure['source_file']}\n")
            log.write(f"Function: {failure['source_function']}\n")
            log.write(f"Nguyên nhân: {cause}\n")
            log.write(f"Giải pháp: {solution}\n")
            log.write("Mã đã sửa:\n```python\n{fixed_code}\n```\n")
        
        debug_history += f"\nIteration {iteration + 1}:\nTest: {failure['test']}\nFix Attempt:\n{fixed_code}\nOutcome: Pending\n"

        if apply_fix(source_path, source_code, fixed_code):
            if run_tests(project_root):
                logger.info("Tests passed after fix. Deploying application.")
                deploy_app(project_root, app_package)
                break
            else:
                debug_history = debug_history.replace("Outcome: Pending", "Outcome: Failed")
        else:
            logger.warning("Fix application failed. Continuing to next iteration.")
        
        iteration += 1

    if iteration == max_iterations:
        logger.warning("Reached maximum debug iterations without resolving all issues.")