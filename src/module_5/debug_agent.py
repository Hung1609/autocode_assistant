import os
import json
import logging
import time
import re
import subprocess
import ast
from langchain.agents import initialize_agent, AgentType
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool, StructuredTool
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
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
DEFAULT_MODEL = 'gemini-2.0-flash'
BASE_GENERATED_DIR = os.getenv('BASE_GENERATED_DIR', 'code_generated_result')
# OUTPUTS_DIR = os.getenv('OUTPUTS_DIR', r'C:\Users\Hoang Duy\Documents\Phan Lac Hung\autocode_assistant\src\module_1_vs_2\outputs')
OUTPUTS_DIR = os.getenv('OUTPUTS_DIR', r'C:\Users\ADMIN\Documents\Foxconn\autocode_assistant\src\module_1_vs_2\outputs')
TEST_LOG_FILE = "test_results.log"
DEBUG_LOG_FILE = "debug_results.log"
TEST_HISTORY_LOG_FILE = "test_results_history.log"

# detect the project root, framework and app package
def _detect_project_and_framework_internal(specified_project: Optional[str] = None) -> (str, str, str):
    if not os.path.exists(BASE_GENERATED_DIR):
        logger.error(f"Base directory '{BASE_GENERATED_DIR}' does not exist.")
        raise FileNotFoundError(f"Base directory '{BASE_GENERATED_DIR}' does not exist.")
    
    projects = [d for d in os.listdir(BASE_GENERATED_DIR) if os.path.isdir(os.path.join(BASE_GENERATED_DIR, d))]
    if not projects:
        logger.error(f"No project folders found in '{BASE_GENERATED_DIR}'.")
        raise ValueError("No project folders found.")
    
    project_name = None
    design_file_path = None
    
    if specified_project:
        specified_path = os.path.join(BASE_GENERATED_DIR, specified_project)
        if os.path.isdir(specified_path):
            project_name = specified_project
            # find the latest design file for specified project
            design_files = [f for f in os.listdir(OUTPUTS_DIR) if f.startswith(f"{specified_project}_") and f.endswith('.design.json')]
            if design_files:
                design_file_path = os.path.join(OUTPUTS_DIR, max(design_files, key=lambda f: os.path.getmtime(os.path.join(OUTPUTS_DIR, f))))
                logger.info(f"Using specified project folder: {project_name} with design file: {design_file_path}")
            else:
                logger.warning(f"No design file found for specified project '{specified_project}' in {OUTPUTS_DIR}.")
        else:
            logger.warning(f"Specified project '{specified_project}' not found in '{BASE_GENERATED_DIR}'.")
            
    # Fallback
    if not project_name:
        project_times = [(p, os.path.getctime(os.path.join(BASE_GENERATED_DIR, p))) for p in projects]
        project_name = max(project_times, key=lambda x: x[1])[0]
        # Find the latest .design.json file for the most recent project
        design_files = [f for f in os.listdir(OUTPUTS_DIR) if f.startswith(f"{project_name}_") and f.endswith('.design.json')]
        if design_files:
            design_file_path = os.path.join(OUTPUTS_DIR, max(design_files, key=lambda f: os.path.getmtime(os.path.join(OUTPUTS_DIR, f))))
            logger.info(f"Using most recent project folder: {project_name} with design file: {design_file_path}")
        else:
            logger.warning(f"No design file found for most recent project '{project_name}' in {OUTPUTS_DIR}.")
            
    project_root = os.path.join(BASE_GENERATED_DIR, project_name)
    framework = "unknown"
    app_package = "app"
    
    if design_file_path and os.path.exists(design_file_path):
        try:
            with open(design_file_path, 'r', encoding='utf-8') as f:
                design_data = json.load(f)
            folder_structure = design_data.get('folder_Structure', {}).get('structure',[])
            for item in folder_structure:
                relative_path = item['path'].strip().replace('\\', '/')
                if relative_path.endswith('main.py'): # cần sửa, không phải lúc nào design agent generate ra folder structure cũng có main.py
                    backend_dir = os.path.dirname(relative_path).lstrip('/').lstrip('\\')
                    app_package = backend_dir # bỏ "app" vì nó là giả định, không phải lúc nào cũng có app
                    logger.info(f"Detected app package from JSON design: {app_package}")
                    break
            
            tech_stack = design_data.get('interface_Design', {}).get('technology_Stack', {}).get('backend', {})
            framework_name = tech_stack.get('framework', '').lower()
            if "fastapi" in framework_name:
                framework = "fastapi"
            elif "flask" in framework_name:
                framework = "flask"
            logger.info(f"Detected framework from JSON specification in design file: {framework}")
            
        except Exception as e:
            logger.error(f"Failed to parse design file '{design_file_path}': {e}")
    # Fallback to detect in requirements.txt
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
                logger.info(f"Detected framework from requirements.txt: {framework}")
    
    if framework == "unknown":
        logger.warning("Could not detect framework. Defaulting to FastAPI.")
        framework = "fastapi"
        
    logger.info(f"Final detected project: {os.path.basename(project_root)}, Framework: {framework}, App Package: {app_package}")
    return project_root, framework, app_package

# Tools for debug agent

class DebuggingTools:
    def __init__(self, project_root: str, framework: str, app_package: str):
        self.project_root = project_root
        self.framework = framework
        self.app_package = app_package
        self.llm_model = ChatGoogleGenerativeAI(model=DEFAULT_MODEL, google_api_key=os.getenv('GEMINI_API_KEY'))
        
    def _parse_test_log_file(self, log_file_path: str) -> Optional[Dict[str, Any]]:
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            pattern = re.compile(
                r"Test: (.+?)\n"
                r"Test File Path: (.+?)\n"
                r"Source File: (.+?)\n"
                r"Source Function: (.+?)\n"
                r"Error Line Summary: (.+?)(?=\nTest:|\Z)", re.DOTALL
            )
            match = pattern.search(content)
            
            if match:
                failure = {
                    "test_name": match.group(1).strip(),
                    "test_file_path_full": match.group(2).strip(),
                    "source_file_relative": match.group(3).strip(), # Relative to project root, e.g., 'backend\main.py'
                    "source_function_mapped": match.group(4).strip(), # e.g., 'RequestIDFilter.filter'
                    "error_summary_line": match.group(5).strip()
                }
                logger.debug(f"Parsed test failure: {failure}")
                
                # wtf is this?
                history_log_path = os.path.join(self.project_root, TEST_HISTORY_LOG_FILE)
                with open(history_log_path, 'a', encoding='utf-8') as f:
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"\n--- Debug Agent Run: {timestamp} ---\n")
                    f.write(f"Parsed Test Failure:\n")
                    for key, value in failure.items():
                        f.write(f"  {key}: {value}\n")
                    f.write("---\n")
                return failure
            logger.info(f"No 'Mapped Failure Summary' found in {log_file_path}. All tests might have passed or log format is unexpected.")
            return None
        
        except Exception as e:
            logger.error(f"Failed to parse test results from {log_file_path}: {e}", exc_info=True)
            return None
        
    @Tool(name="read_test_results", description="Reads the latest test results log to find the first failed test and extracts relevant information. Returns a JSON string of the first failure or 'No failed tests found.'")
    
    def read_test_results(self) -> str:
        log_file_path = os.path.join(self.project_root, TEST_LOG_FILE)
        if not os.path.exists(log_file_path):
            logger.warning(f"Test results log not found at {log_file_path}.")
            return "Test results log not found. Please ensure tests have been run."
        
        failure = self._parse_test_log_file(log_file_path)
        if failure:
            return json.dumps(failure)
        
        return "No failed tests found"
        
    class ReadSourceCodeInput(BaseModel):
        file_path: str = Field(description="The path to the source code file, relative to the project root")
           
    @StructuredTool.from_function(
        func=lambda self, file_path: self._read_source_code_internal(file_path),
        name="read_source_code",
        description="Reads the entire content of a source code file. Returns the full file content as a string or an error message. Use this before asking to fix code."
        args_schema=ReadSourceCodeInput,
        return_direct=False
    )
        
    def read_source_code(self, file_path: str) -> str: # Wrapper to call internal method
        return self._read_source_code_internal(file_path)
    
    def _read_source_code_internal(self, file_path: str) -> str:
        full_file_path = os.path.join(self.project_root, file_path.replace('/', os.sep))
        try:
            with open(full_file_path, 'r', encoding='utf-8') as f:
                source_content = f.read()
            # Basic syntax validation
            ast.parse(source_content)
            logger.info(f"Read full content of {full_file_path}")
            return source_content
        except SyntaxError as e:
            logger.error(f"Syntax error in source code file {full_file_path}: {e}")
            return f"Error: Syntax error in file '{file_path}'. Cannot parse. Error: {str(e)}"
        except Exception as e:
            logger.error(f"Error reading source code from {full_file_path}: {e}")
            return f"Error reading source code: {str(e)} for file {file_path}"
    
    class ApplyCodeFixInput(BaseModel):
    file_path: str = Field(description="The path to the source code file, relative to the project root (e.g., 'backend/main.py').")
    fixed_full_file_content: str = Field(description="The ENTIRE content of the file after applying the fix. This will overwrite the original file.")

    @StructuredTool.from_function(
        func=lambda self, file_path, fixed_full_file_content: self._apply_code_fix_internal(file_path, fixed_full_file_content),
        name="apply_code_fix",
        description="Applies a code fix by overwriting the specified file with the new full content. Returns 'Code fix applied successfully.' or an error message. You must provide the ENTIRE fixed file content.",
        args_schema=ApplyCodeFixInput,
        return_direct=False
    )
    def apply_code_fix(self, file_path: str, fixed_full_file_content: str) -> str: # Wrapper to call internal method
        return self._apply_code_fix_internal(file_path, fixed_full_file_content)

    def _apply_code_fix_internal(self, file_path: str, fixed_full_file_content: str) -> str:
        """Internal method to apply code fix by overwriting the file."""
        full_file_path = os.path.join(self.project_root, file_path.replace('/', os.sep))
        
        if not os.access(full_file_path, os.W_OK):
            logger.error(f"No write permission for {full_file_path}")
            return f"Error: No write permission for {full_file_path}"
        
        try:
            # Basic syntax validation of the fixed code BEFORE writing
            ast.parse(fixed_full_file_content)

            # Create backup
            with open(full_file_path + '.bak', 'w', encoding='utf-8') as f:
                # Read current content to backup, not fixed_full_file_content
                with open(full_file_path, 'r', encoding='utf-8') as original_f:
                    f.write(original_f.read())
            logger.info(f"Created backup for {full_file_path} at {full_file_path}.bak")

            # Overwrite the original file with the fixed content
            with open(full_file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_full_file_content)
            logger.info(f"Applied fix to {full_file_path}")
            return "Code fix applied successfully."
        except SyntaxError as e:
            logger.error(f"Error: Fixed code has syntax errors for {full_file_path}: {e}")
            return f"Error applying code fix: Fixed code has syntax errors. Error: {str(e)}"
        except Exception as e:
            logger.error(f"Failed to apply fix to {full_file_path}: {e}", exc_info=True)
            return f"Error applying code fix: {str(e)}"


    @Tool(name="run_tests", description="Runs the project's test suite by executing the run_tests.bat file. Returns 'All tests passed.' or 'Tests failed. Check test_results.log for details.'")
    def run_tests(self) -> str:
        """Runs the tests by executing the run_tests.bat file."""
        bat_file = os.path.join(self.project_root, "run_tests.bat")
        test_log_file = os.path.join(self.project_root, TEST_LOG_FILE)

        if not os.path.exists(bat_file):
            logger.error(f"run_tests.bat not found at {bat_file}")
            return "run_tests.bat not found."
        
        # Pre-cleanup of the log file for this run, in case the bat script fails early
        if os.path.exists(test_log_file):
            try:
                os.remove(test_log_file)
                logger.debug(f"Removed old test log file: {test_log_file}")
            except Exception as e:
                logger.warning(f"Could not remove old test log file {test_log_file}: {e}")

        try:
            result = subprocess.run(
                f'"{bat_file}"',
                shell=True,
                capture_output=True, # Capture output/stderr of the batch script itself (e.g., debug_tests.log content)
                text=True,
                cwd=self.project_root,
                check=False # Do not raise CalledProcessError, we handle exit code manually
            )
            
            # Log stdout/stderr of the batch script itself (debug_tests.log content will also be here)
            if result.stdout:
                logger.debug(f"run_tests.bat stdout (from debug_tests.log):\n{result.stdout}")
            if result.stderr:
                logger.error(f"run_tests.bat stderr (from debug_tests.log):\n{result.stderr}")

            logger.info(f"Pytest run completed. Batch script exit code: {result.returncode}")

            # Check test_results.log for actual failures, as batch script exit code might be 0 even if pytest fails
            failure_info = self._parse_test_log_file(test_log_file)
            if failure_info:
                return "Tests failed. Check test_results.log for details."
            
            return "All tests passed."

        except Exception as e:
            logger.error(f"Failed to run tests: {e}", exc_info=True)
            return f"Error running tests: {str(e)}"

    @Tool(name="deploy_application", description="Deploys the application by running the deploy_app.bat file. Call this only when all tests have passed.")
    def deploy_application(self) -> str:
        """Deploys the application by running the deploy_app.bat file."""
        bat_file_path = os.path.join(self.project_root, "deploy_app.bat")
        bat_content = fr"""@echo off
setlocal EnableDelayedExpansion

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

call "%PROJECT_ROOT%venv\Scripts\activate.bat"
python -m uvicorn {self.app_package}.main:app --host 0.0.0.0 --port 8001
deactivate
exit /b 0
"""
        try:
            with open(bat_file_path, 'w', encoding='utf-8') as f:
                f.write(bat_content)
            logger.info(f"Created deploy_app.bat at {bat_file_path}")
            
            subprocess.run(
                f'"{bat_file_path}"',
                shell=True,
                cwd=self.project_root,
                check=True # Raise CalledProcessError if deployment fails
            )
            logger.info("Application deployed successfully.")
            return "Application deployed successfully."
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to deploy application. Exit code: {e.returncode}. Stderr: {e.stderr}", exc_info=True)
            return f"Error deploying application: {e.stderr}"
        except Exception as e:
            logger.error(f"Failed to deploy application: {e}", exc_info=True)
            return f"Error deploying application: {str(e)}"


# --- Main Debug Agent Execution ---

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Debug Agent using LangChain.")
    parser.add_argument('--project', type=str, help="Specify project directory name to debug.")
    args = parser.parse_args()

    # 1. Detect project and framework details
    project_root, framework, app_package = _detect_project_and_framework_internal(args.project)

    # 2. Instantiate DebuggingTools class (this will hold the state for tools)
    tools_instance = DebuggingTools(project_root, framework, app_package)

    # 3. Define the Tools that the agent will use
    tools = [
        tools_instance.read_test_results,
        tools_instance.read_source_code, # StructuredTool
        tools_instance.apply_code_fix,   # StructuredTool
        tools_instance.run_tests,
        tools_instance.deploy_application # New tool
    ]

    # 4. Initialize LLM for the Agent
    llm = ChatGoogleGenerativeAI(model=DEFAULT_MODEL, google_api_key=os.getenv('GEMINI_API_KEY'))

    # 5. Initialize the Agent
    # We don't use Memory here directly as the external loop manages iterations and context
    # However, for the LLM to get context across turns, we pass previous outputs in the prompt.
    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION, # Good for structured tool calls and reasoning
        verbose=True, # For detailed logging of agent's thoughts and actions
        max_iterations=10, # Max internal Thought/Action cycles for the agent per run() call
        early_stopping_method="force", # Stop if agent cannot find a valid action
        handle_parsing_errors=True # Better error handling for LLM output parsing
    )

    # --- Debugging Loop ---
    max_debug_iterations = 5 # Max attempts to fix the same issue
    current_debug_history = "" # To pass history to LLM in subsequent attempts

    logger.info(f"Starting Debug Agent for project: {os.path.basename(project_root)}")

    for iteration in range(max_debug_iterations):
        logger.info(f"\n--- Debug Iteration {iteration + 1}/{max_debug_iterations} ---")
        
        # The main prompt for the agent in each iteration
        # It's crucial to guide the agent on WHAT to do first (read test results)
        # and HOW to proceed.
        agent_prompt = f"""
        You are an expert Python debugging agent. Your goal is to fix failing tests in a given codebase.
        You will operate in a loop, fixing one test failure at a time.

        **Current Debug Task:**
        1. **Start by reading the current test results:** Use the `read_test_results` tool. This will tell you if there are any failures.
        2. **Analyze Test Results:**
           - If `read_test_results` returns "No failed tests found.", it means all tests are passing. Your task is complete. You should **call the `deploy_application` tool** and then indicate that your task is finished.
           - If `read_test_results` returns a JSON string of a failed test, carefully parse that JSON to understand the `test_name`, `source_file_relative`, `source_function_mapped`, and `error_summary_line`.
        3. **Read Source Code:** Use the `read_source_code` tool with the `source_file_relative` to get the *entire content* of the file where the error occurred.
        4. **Propose and Apply Fix:**
           - **Analyze the problem:** Based on the failed test information (test name, source file, source function, error summary) AND the *entire content of the source file*.
           - **Formulate a comprehensive fix:** Your goal is to fix the issue in the `source_function_mapped` and any other related parts in the file (e.g., updating function calls if parameters changed, fixing related logic).
           - **Output the ENTIRE fixed file content.**
           - **Call `apply_code_fix`:** Use the `apply_code_fix` tool with the `source_file_relative` and your `fixed_full_file_content`.
        5. **Run Tests Again:** After applying a fix, immediately use the `run_tests` tool to verify if your fix worked.
        6. **Evaluate and Iterate:**
           - If `run_tests` returns "All tests passed.", your fix worked! You should then **call the `deploy_application` tool** and indicate that your task is complete.
           - If `run_tests` returns "Tests failed.", analyze the new `test_results.log` using `read_test_results` again. Consider the previous debug history and adjust your strategy.

        **Important Considerations:**
        - Always act systematically.
        - Ensure your proposed fixed code is syntactically correct Python.
        - The `apply_code_fix` tool expects the *entire file content* as `fixed_full_file_content`. Do not just provide a snippet.
        - If you encounter a problem with a tool (e.g., `read_source_code` returns an error), analyze it and adapt.
        - Be mindful of `max_iterations` for the agent's internal thought process.

        **Previous Debug History (if any):**
        {current_debug_history}

        Begin by calling `read_test_results` to find out what's failing.
        """
        
        logger.info(f"Agent executing with prompt for iteration {iteration + 1}...")
        
        try:
            # The agent.run() call will execute the full debug loop according to its prompt
            # until it hits max_iterations, early_stopping_method, or decides it's done.
            final_agent_message = agent.run(agent_prompt)
            logger.info(f"Agent finished iteration {iteration + 1}. Final message: {final_agent_message}")

            # Here, we check if the agent *explicitly stated* it finished or deployed.
            # Otherwise, we assume it needs another iteration based on the outer loop.
            if "No failed tests found" in final_agent_message or \
               "Application deployed successfully" in final_agent_message or \
               "task is complete" in final_agent_message:
                logger.info("Agent indicated task completion or deployment.")
                break # Exit outer debug loop

            # Update history for the next iteration's prompt
            # Note: This is a simplified way to pass history. LangChain memory management
            # within the agent itself might be more robust for complex interactions.
            # But for explicit prompt history, this works.
            current_debug_history += f"\n--- Iteration {iteration + 1} Outcome ---\n"
            current_debug_history += f"Agent's last message: {final_agent_message}\n"
            current_debug_history += f"Tests still failing or unexpected outcome. Analyzing for next attempt.\n"

        except Exception as e:
            logger.error(f"An unexpected error occurred during agent execution in iteration {iteration + 1}: {e}", exc_info=True)
            current_debug_history += f"\n--- Iteration {iteration + 1} Outcome ---\n"
            current_debug_history += f"Agent crashed with error: {str(e)}. Attempting to restart.\n"
            # In a real system, you might want to break or have more sophisticated error recovery.

    if iteration == max_debug_iterations - 1: # Check if loop completed without breaking
        logger.warning(f"Reached maximum debug iterations ({max_debug_iterations}) without resolving all issues.")
    else:
        logger.info("Debugging process completed successfully (or agent indicated completion).")

if __name__ == "__main__":
    main()
            