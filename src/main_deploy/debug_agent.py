import os
import json
import logging
import time
import re
import subprocess
import ast
import argparse
from langchain.agents import initialize_agent, AgentType
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Tuple, List
import config

logger = logging.getLogger(__name__)

DEFAULT_MODEL = 'gemini-2.0-flash' # gemini-2.5-flash-preview-04-17, gemini-2.0-flash (somehow, gemini-2.5-flash-preview-04-17 doesn't work)
BASE_GENERATED_DIR = os.getenv('BASE_GENERATED_DIR', 'code_generated_result')
OUTPUTS_DIR = os.getenv('OUTPUTS_DIR', r'C:\Users\Hoang Duy\Documents\Phan Lac Hung\autocode_assistant\src\module_1_vs_2\outputs')
# OUTPUTS_DIR = os.getenv('OUTPUTS_DIR', r'C:\Users\ADMIN\Documents\Foxconn\autocode_assistant\src\module_1_vs_2\outputs')
TEST_LOG_FILE = "test_results.log"
DEBUG_LOG_FILE = "debug_results.log"
TEST_HISTORY_LOG_FILE = "test_results_history.log"

# detect the project root, framework and app package
def _detect_project_and_framework_internal(specified_project: Optional[str] = None) -> Tuple[str, str, str]:
    """
    Detects the project root, framework, and app package.
    Improved to find the latest design file for a given project.
    """
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
            # Find the latest .design.json file for the specified project
            design_files = [f for f in os.listdir(OUTPUTS_DIR) if f.startswith(f"{specified_project}_") and f.endswith('.design.json')]
            if design_files:
                design_file_path = os.path.join(OUTPUTS_DIR, max(design_files, key=lambda f: os.path.getmtime(os.path.join(OUTPUTS_DIR, f))))
                logger.info(f"Using specified project folder: {project_name} with design file: {design_file_path}")
            else:
                logger.warning(f"No design file found for specified project '{specified_project}' in {OUTPUTS_DIR}.")
        else:
            logger.warning(f"Specified project '{specified_project}' not found in '{BASE_GENERATED_DIR}'.")

    # Fallback to most recent project if not specified or not found
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

    # Detect app_package and framework from design file
    if design_file_path and os.path.exists(design_file_path):
        try:
            with open(design_file_path, 'r', encoding='utf-8') as f:
                design_data = json.load(f)
            folder_structure = design_data.get('folder_Structure', {}).get('structure', [])
            for item in folder_structure:
                relative_path = item['path'].strip().replace('\\', '/')
                if relative_path.endswith('main.py'):
                    backend_dir = os.path.dirname(relative_path).lstrip('/').lstrip('\\')
                    app_package = backend_dir or "app" # Default to "app" if backend_dir is empty string (e.g., main.py at root)
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
            
    # Fallback to requirements.txt for framework detection if still unknown
    if framework == "unknown":
        requirements_path = os.path.join(project_root, "requirements.txt")
        if os.path.exists(requirements_path):
            with open(requirements_path, 'r', encoding='utf-8') as f:
                reqs = f.read().lower()
                if "fastapi" in reqs:
                    framework = "fastapi"
                    if app_package == "app": # Only override if JSON didn't set it
                        app_package = "backend"
                elif "flask" in reqs:
                    framework = "flask"
                    if app_package == "app": # Only override if JSON didn't set it
                        app_package = "app"
                logger.info(f"Detected framework from requirements.txt: {framework}")

    if framework == "unknown":
        logger.warning("Could not detect framework. Defaulting to FastAPI.")
        framework = "fastapi" # Default to FastAPI (common for generated code)
        # If app_package is still 'app' and framework defaults to FastAPI, it might be better to default app_package to 'backend'
        if app_package == "app":
            app_package = "backend"

    logger.info(f"Final detected project: {os.path.basename(project_root)}, Framework: {framework}, App Package: {app_package}")
    return project_root, framework, app_package

# --- Debugging Agent Tools ---

# Input schema for tools that take no arguments (to avoid Pydantic self-validation issues)
class EmptyInput(BaseModel):
    pass

class ReadSourceCodeInput(BaseModel):
    file_path: str = Field(description="The path to the source code file, relative to the project root.")

class ApplyCodeFixInput(BaseModel):
    file_path: str = Field(description="The path to the source code file, relative to the project root.")
    fixed_full_file_content: str = Field(description="The ENTIRE content of the file after applying the fix. This will overwrite the original file.")

class DebuggingTools:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.llm_model = ChatGoogleGenerativeAI(model=config.CURRENT_MODELS['debugging'], google_api_key=config.GEMINI_API_KEY)
        
    def get_all_tools(self) -> List[StructuredTool]:
        return [
            StructuredTool.from_function(
                func=self._read_test_results_internal,
                name="read_test_results",
                description="Reads the latest test results log to find the first failed test and extracts relevant information. Returns a JSON string of the first failure or 'No failed tests found.'",
                args_schema=EmptyInput
            ),
            StructuredTool.from_function(
                func=self._read_source_code_internal,
                name="read_source_code",
                description="Reads the entire content of a source code file. Returns the full file content as a string or an error message. Use this before asking to fix code.",
                args_schema=ReadSourceCodeInput
            ),
            StructuredTool.from_function(
                func=self._apply_code_fix_internal,
                name="apply_code_fix",
                description="Applies a code fix by overwriting the specified file with the new full content. Returns 'Code fix applied successfully.' or an error message. You must provide the ENTIRE fixed file content.",
                args_schema=ApplyCodeFixInput
            ),
            StructuredTool.from_function(
                func=self._run_tests_and_get_results,
                name="run_tests_and_get_results",
                description="Runs the project's test suite and returns the result. Returns 'All tests passed.' or a JSON string of the first failure.",
                args_schema=EmptyInput
            )
        ]

        # self.deploy_application_tool = StructuredTool.from_function(
        #     func=self._deploy_application_internal,
        #     name="deploy_application",
        #     description="Deploys the application by running the deploy_app.bat file. Call this only when all tests have passed.",
        #     args_schema=EmptyInput,
        #     return_direct=False
        # )
        
    #Internal helper to parse the test_results.log content.
    def _parse_test_log_file(self, log_file_path: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(log_file_path):
            logger.warning(f"Test log file not found at {log_file_path} for parsing.")
            return None
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Regex to precisely match the "Failure Summary (Mapped)" section generated by test_generator_agent.py
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
                    "source_file_relative": match.group(3).strip(), 
                    "source_function_mapped": match.group(4).strip(),
                    "error_summary_line": match.group(5).strip()
                }
                logger.debug(f"Parsed test failure: {failure}")

                # Record to history log as append
                history_log_path = os.path.join(self.project_root, TEST_HISTORY_LOG_FILE)
                with open(history_log_path, 'a', encoding='utf-8') as f:
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"\n--- Debug Agent Run: {timestamp} ---\n")
                    f.write(f"Parsed Test Failure:\n")
                    for key, value in failure.items():
                        f.write(f"  {key}: {value}\n")
                    f.write("---\n")
                return failure
            
            logger.info(f"No mapped failure summary found in {log_file_path}. Assuming tests passed or format is different.")
            return None # No failures found or parsed
        
        except Exception as e:
            logger.error(f"Failed to parse test results from {log_file_path}: {e}", exc_info=True)
            return None

    # Internal implementation for read_test_results tool
    def _read_test_results_internal(self) -> str:
        log_file_path = os.path.join(self.project_root, TEST_LOG_FILE)
        failure = self._parse_test_log_file(log_file_path)
        return json.dumps(failure) if failure else "No failed tests found."

    # Internal implementation for read_source_code tool
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
            logger.error(f"Error reading source code from {full_file_path}: {e}", exc_info=True)
            return f"Error reading source code: {str(e)} for file {file_path}"

    # Internal implementation for apply_code_fix tool
    def _apply_code_fix_internal(self, file_path: str, fixed_full_file_content: str) -> str:
        full_file_path = os.path.join(self.project_root, file_path.replace('/', os.sep))
        
        if not os.access(full_file_path, os.W_OK):
            logger.error(f"No write permission for {full_file_path}")
            return f"Error: No write permission for {full_file_path}"
        
        try:
            # Basic syntax validation of the fixed code BEFORE writing
            ast.parse(fixed_full_file_content)

            # Create backup by reading current content before overwriting
            with open(full_file_path + '.bak', 'w', encoding='utf-8') as f_bak:
                with open(full_file_path, 'r', encoding='utf-8') as f_orig:
                    f_bak.write(f_orig.read())
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

    # Internal implementation for run_test tool
    def _run_tests_and_get_results(self) -> str:
        """Internal method for run_test tool."""
        bat_file = os.path.join(self.project_root, "run_test.bat")
        test_log_file = os.path.join(self.project_root, TEST_LOG_FILE)

        if not os.path.exists(bat_file):
            logger.error(f"run_test.bat not found at {bat_file}")
            return "Error: run_test.bat not found."
        
        # Pre-cleanup of the log file for this run, in case the bat script fails early
        if os.path.exists(test_log_file):
            try:
                os.remove(test_log_file)
                logger.debug(f"Removed old test log file: {test_log_file}")
            except Exception as e:
                logger.warning(f"Could not remove old test log file {test_log_file}: {e}")

        try:
            # Execute the batch script. It will write pytest output to test_results.log
            result = subprocess.run(
                f'"{bat_file}"',
                shell=True,
                capture_output=True, # Capture output/stderr of the batch script itself (e.g., debug_test_agent.log content)
                text=True,
                cwd=self.project_root,
                check=False # Do not raise CalledProcessError as we handle exit code manually
            )
            
            # Log stdout/stderr of the batch script itself (debug_test_agent.log content will also be here)
            if result.stdout:
                logger.debug(f"run_test.bat stdout (from debug_test_agent.log):\n{result.stdout}")
            if result.stderr:
                logger.error(f"run_test.bat stderr (from debug_test_agent.log):\n{result.stderr}")

            logger.info(f"Pytest run completed. Batch script exit code: {result.returncode}")

            # Check test_results.log for actual failures, as batch script exit code might be 0 even if pytest fails
            # We explicitly call the parsing method here
            failure_info = self._parse_test_log_file(test_log_file) 
            if failure_info:
                return "Tests failed. Check test_results.log for details."
            
            return self._read_test_results_internal()

        except Exception as e:
            logger.error(f"Failed to run tests: {e}", exc_info=True)
            return f"Error running tests: {str(e)}"

#     # Internal implementation for deploy_application tool
#     def _deploy_application_internal(self) -> str:
#         """Internal method for deploy_application tool."""
#         bat_file_path = os.path.join(self.project_root, "deploy_app.bat")
#         bat_content = fr"""@echo off
# setlocal EnableDelayedExpansion

# set "PROJECT_ROOT=%~dp0"
# cd /d "%PROJECT_ROOT%"

# call "%PROJECT_ROOT%venv\Scripts\activate.bat"
# python -m uvicorn {self.app_package}.main:app --host 0.0.0.0 --port 8001
# deactivate
# exit /b 0
# """
#         try:
#             with open(bat_file_path, 'w', encoding='utf-8') as f:
#                 f.write(bat_content)
#             logger.info(f"Created deploy_app.bat at {bat_file_path}")
            
#             subprocess.run(
#                 f'"{bat_file_path}"',
#                 shell=True,
#                 cwd=self.project_root,
#                 check=True
#             )
#             logger.info("Application deployed successfully.")
#             return "Application deployed successfully."
#         except subprocess.CalledProcessError as e:
#             logger.error(f"Failed to deploy application. Exit code: {e.returncode}. Stderr: {e.stderr}", exc_info=True)
#             return f"Error deploying application: {e.stderr}"
#         except Exception as e:
#             logger.error(f"Failed to deploy application: {e}", exc_info=True)
#             return f"Error deploying application: {str(e)}"


def run_debugging_cycle(project_root: str, initial_failures: List[Dict]) -> bool:
    """
    The main entry point for the debugging phase. It orchestrates the iterative
    fix-and-retest loop using a LangChain agent.

    Args:
        project_root (str): The absolute path to the generated project's root directory.
        initial_failures (list): The list of failed tests from the testing phase.

    Returns:
        bool: True if all bugs were fixed, False otherwise.
    """
    logger.info(f"Starting debugging cycle for project: {project_root}")
    
    # initialize the tools and the Langchain agent
    tools_instance = DebuggingTools(project_root=project_root)
    llm = ChatGoogleGenerativeAI(
        model=config.CURRENT_MODELS['debugging'],
        google_api_key=config.GEMINI_API_KEY,
        temperature=0.2
    )
    
    agent_executor = initialize_agent(
        tools=tools_instance.get_all_tools(),
        llm=llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        max_iterations=15,
        early_stopping_method="force",  # Stop if agent cannot find a valid action
        handle_parsing_errors=True  # Better error handling for LLM output parsing
    )
    
    #start the loop
    max_debug_iterations = 3 
    
    current_debug_history = ""
    
    # Use the first failure from the initial list as the starting point
    current_failure_json = json.dumps(initial_failures[0])
    
    for i in range(max_debug_iterations):
        logger.info(f"\n--- Debug Iteration {i + 1}/{max_debug_iterations} ---")
        
        agent_prompt = f"""
        You are an expert Python debugging agent. Your primary goal is to fix failing tests in a given codebase.
        You operate in a loop: inspect the failure, read the code, propose a fix, apply it, and re-run tests.
        
        Current Failure Details:
        {current_failure_json}
        
        Your Step-by-Step Debugging Process:
        1. Initial Assessment: Start by calling the `read_test_results` tool to get the current status of the tests.
        2. Analyze the Failure: Carefully examine the test failure data above. Understand the source file, function, and error.
        3. Inspect Source Code: Call the `read_source_code` tool with the `source_file_relative` from the failure data to get the full content of the problematic file.
        4. Diagnose and Formulate Fix: Based on the error and the full code, determine the root cause. Generate a complete, corrected version of the entire source file.
        5. Apply Fix: Use the `apply_code_fix` tool. You must provide the `file_path` and the `fixed_full_file_content` (the entire, complete file content).
        6. Verify: After applying the fix, immediately call the `run_tests_and_get_results` tool to see if the fix was successful.
        7. Conclude:
            - If `run_tests_and_get_results` returns "All tests passed.", your job for this bug is done. Respond with the final answer: "TERMINATE - All tests passed."
            - If `run_tests_and_get_results` returns a new failure JSON, the loop will continue. The new failure will be provided in the next iteration.
            
        Previous Debug History (What you tried before):
        {current_debug_history}
        
        Begin the process now. Your first step should be to use `read_source_code` on the file mentioned in the failure data.
        """
        
        try:
            response = agent_executor.invoke({"input": agent_prompt})
            final_answer = response.get("output", "")
            
            if "TERMINATE" in final_answer or "All tests passed" in final_answer:
                logger.info("Agent reports all tests passed. Debugging successful.")
                return True
            
            lastest_results_str = tools_instance._run_tests_and_get_results()
            if "No failed tests found" in lastest_results_str:
                logger.info("Verification shows all tests passed. Debugging successfully.")
                return True
            else:
                current_failure_json = lastest_results_str # update for the next loop
                current_debug_history += f"\n- Iteration {i+1} Result: Fix was not complete. New failure: {current_failure_json}"

        except Exception as e:
            logger.error(f"An error occurred in the agent executor during iteration {i+1}: {e}", exc_info=True)
            current_debug_history += f"\n- Iteration {i+1} Result: Agent loop crashed with an error. Error: {e}"
            time.sleep(config.API_DELAY_SECONDS)
    
    logger.error(f"Reached maximum debug iterations ({max_debug_iterations}). Unable to fix all bugs.")
    return False



# # --- Main Debug Agent Execution ---
# def main():
#     parser = argparse.ArgumentParser(description="Debug Agent using LangChain.")
#     parser.add_argument('--project', type=str, help="Specify project directory name to debug.")
#     args = parser.parse_args()

#     # 1. Detect project and framework details
#     project_root, framework, app_package = _detect_project_and_framework_internal(args.project)

#     # 2. Instantiate DebuggingTools class (this will hold the state for tools)
#     tools_instance = DebuggingTools(project_root, framework, app_package)

#     # 3. Define the Tools that the agent will use
#     # Access the StructuredTool instances directly from the tools_instance
#     tools = [
#         tools_instance.read_test_results_tool,
#         tools_instance.read_source_code_tool,
#         tools_instance.apply_code_fix_tool,
#         tools_instance.run_test_tool,
#         tools_instance.deploy_application_tool
#     ]

#     # 4. Initialize LLM for the Agent
#     llm = ChatGoogleGenerativeAI(model=DEFAULT_MODEL, google_api_key=os.getenv('GEMINI_API_KEY'))

#     # 5. Initialize the Agent
#     agent = initialize_agent(
#         tools,
#         llm,
#         agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
#         verbose=True,
#         max_iterations=15, # Max internal Thought/Action cycles for the agent per run() call
#         early_stopping_method="force", # Stop if agent cannot find a valid action
#         handle_parsing_errors=True # Better error handling for LLM output parsing
#     )

#     # --- Debugging Loop ---
#     max_debug_iterations = 5 # Max attempts to fix the same issue
#     current_debug_history = "" # To pass history to LLM in subsequent attempts

#     logger.info(f"Starting Debug Agent for project: {os.path.basename(project_root)}")

#     for iteration in range(max_debug_iterations):
#         logger.info(f"\n--- Debug Iteration {iteration + 1}/{max_debug_iterations} ---")
        
#         # The main prompt for the agent in each iteration
#         # It's crucial to guide the agent on WHAT to do first (read test results)
#         # and HOW to proceed.
#         agent_master_prompt = f"""
#         You are an expert Python debugging agent. Your primary goal is to fix failing tests in a given codebase.
#         You operate in a loop, fixing one test failure at a time until all tests pass.

#         **Your Debugging Process:**
#         1.  **Initial Assessment:** Start by calling the `read_test_results` tool to get the current status of the tests.
#         2.  **Analyze Test Outcomes:**
#             *   If `read_test_results` returns "No failed tests found.", it means all tests are passing. Your mission is complete. You should **call the `deploy_application` tool** and then provide a final conclusive answer that your task is finished and the application is deployed.
#             *   If `read_test_results` returns a JSON string of a failed test (e.g., {{"test_name": "...", "source_file_relative": "...", "source_function_mapped": "...", "error_summary_line": "..."}}), you must parse this JSON to understand the failure details.
#         3.  **Inspect Source Code:** Use the `read_source_code` tool with the `source_file_relative` from the test failure. This will provide you with the *entire content* of the file where the error occurred.
#         4.  **Diagnose and Fix:**
#             *   Based on the detailed test failure information (test name, source file, source function, error summary) AND the **entire content of the source file you just read**, diagnose the root cause of the bug.
#             *   **Formulate a comprehensive fix:** Your fix must address the issue in the `source_function_mapped` and **any other related parts in the ENTIRE file** (e.g., updating function calls if parameters changed, fixing related logic, adding/removing imports, adjusting class definitions). The fixed code must be syntactically correct Python.
#             *   **Output Format for Proposed Fix:**
#                 Your proposed fix MUST strictly follow this format. Do not add any conversational text or extra markdown outside these markers.
#                 ```json
#                 {{
#                     "explanation": "Brief explanation of the bug's cause and solution.",
#                     "fixed_file_content": "```python\n<ENTIRE_FIXED_FILE_CONTENT_HERE>\n```"
#                 }}
#                 ```
#                 - `explanation`: A concise summary of why the bug occurred and how your fix addresses it.
#                 - `fixed_file_content`: **The complete, entire content of the source file after applying your fix.** This includes all imports, class definitions, functions, and top-level code. Ensure the triple backticks (` ``` `) and `python` language marker are included exactly as shown.
#         5.  **Apply the Fix:** Use the `apply_code_fix` tool with the `source_file_relative` (from the test failure) and the `fixed_full_file_content` (the entire fixed file content you generated).
#         6.  **Verify the Fix:** Immediately after applying the fix, use the `run_test` tool to execute the tests again and check if your fix was successful.
#         7.  **Iterate or Conclude:**
#             *   If `run_test` returns "All tests passed.", then your fix worked. Proceed to call `deploy_application` and state task completion.
#             *   If `run_test` returns "Tests failed.", analyze the new `test_results.log` (by calling `read_test_results` again). Consider the previous debug history (`Previous Debug History` section below) and adjust your strategy for the next attempt.

#         **Important Guidelines:**
#         -   Always provide a well-formed JSON output for your proposed fix.
#         -   Ensure the `fixed_file_content` is valid Python and contains the full file.
#         -   If a tool returns an error (e.g., `Error reading source code`), analyze that error and choose your next action.
#         -   Be systematic. Don't skip steps.

#         **Previous Debug History (from prior iterations on this specific issue):**
#         {current_debug_history}        **Your first step is to call `read_test_results` to understand the current state of tests.**
#         """
        
#         logger.info(f"Agent executing with prompt for iteration {iteration + 1}...")
        
#         try:
#             final_agent_message = agent.invoke(agent_master_prompt)
#             logger.info(f"Agent finished iteration {iteration + 1}. Final message: {final_agent_message}")

#             if "No failed tests found" in final_agent_message or \
#                "Application deployed successfully" in final_agent_message or \
#                "task is complete" in final_agent_message:
#                 logger.info("Agent indicated task completion or deployment. Exiting debug loop.")
#                 break
#             else:
#                 current_debug_history += f"\n--- Iteration {iteration + 1} Outcome Summary ---\n"
#                 current_debug_history += f"Agent's final thought/action for this iteration: {final_agent_message}\n"
#                 current_debug_history += f"Tests likely still failing or unexpected outcome. Agent will analyze in next attempt.\n"

#         except Exception as e:
#             logger.error(f"An unexpected error occurred during agent execution in iteration {iteration + 1}: {e}", exc_info=True)
#             current_debug_history += f"\n--- Iteration {iteration + 1} Error Outcome ---\n"
#             current_debug_history += f"Agent crashed with error: {str(e)}. Attempting to restart loop.\n"

#     if iteration == max_debug_iterations - 1:
#         logger.warning(f"Reached maximum debug iterations ({max_debug_iterations}) without resolving all issues.")
#     else:
#         logger.info("Debugging process completed successfully (or agent indicated completion).")

# if __name__ == "__main__":
#     main()

# to run, type this command: python src\module_5\debug_agent.py  