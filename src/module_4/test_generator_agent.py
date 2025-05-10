import os
import json
import time
import logging
from google.generativeai import GenerativeModel, configure, types
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_CALL_DELAY_SECONDS = 5

api_key = os.getenv('GEMINI_API_KEY')
configure(api_key=api_key)
logger.info("Gemini API configured successfully for test generator.")

DEFAULT_MODEL = 'gemini-2.0-flash'
GENERATED_APP_ROOT_DIR = "code_generated_result/flashcard_app" # Địa chỉ này nên là dic có chứa app package và file config.py.Ngoài ra, hiện tại đang cố định địa chỉ, cần tích hợp tool để flexible hơn.
FLASK_APP_PACKAGE_NAME = "app"

def ensure_init_py(directory_path): # đảm bảo file __init__.py có trong directory_path
    init_py_path = os.path.join(directory_path, "__init__.py")
    if not os.path.exists(init_py_path):
        with open(init_py_path, 'w', encoding='utf-8') as f:
            f.write("# This file makes this directory a Python package.\n")
            logger.info(f"Created missing __init__.py in {directory_path}")

def get_function_code(filepath, function_name): # need to improve for more complex cases in the future, hiện tại vẫn bị hạn chế nếu làm việc với các file có cấu trúc phức 
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        func_lines = []
        in_func_body = False
        def_indent_level = -1
        paren_level_in_signature = 0

        for line_number, line_content in enumerate(lines):
            stripped_line = line_content.strip()

            if not in_func_body:
                if stripped_line.startswith(f"def {function_name}(") or stripped_line.startswith(f"async def {function_name}("):
                    in_func_body = True
                    def_indent_level = len(line_content) - len(line_content.lstrip()) # Indentation of def line
                    decorator_lines_buffer = []
                    for i in range(line_number -1, -1, -1):
                        prev_line_stripped = lines[i].strip()
                        prev_line_indent = len(lines[i]) - len(lines[i].lstrip())
                        if prev_line_stripped.startswith("@") and prev_line_indent == def_indent_level:
                            decorator_lines_buffer.insert(0, lines[i])
                        elif prev_line_stripped == "" or prev_line_indent < def_indent_level:
                            break
                        else:
                            break
                    func_lines.extend(decorator_lines_buffer)
                    func_lines.append(line_content)
                    paren_level_in_signature == stripped_line.count('(') - stripped_line.count(')')
                    if paren_level_in_signature == 0 and not stripped_line.endswith(':'):
                        if not stripped_line.endswith(":"): # handle case where : is on next line (e.g. due to black formatting)
                            for next_l_idx in range(line_number + 1, len(lines)):
                                if lines[next_l_idx].strip().startswith(":"):
                                    func_lines.append(lines[next_l_idx])
                                    break
                                elif lines[next_l_idx].strip() != "": # some other code
                                    break # Should not happen with valid Python
                            paren_level_in_signature = -1 # Mark signature as complete
                continue

            if in_func_body:
                current_indent = len(line_content) - len(line_content.lstrip())
                # Handle multi-line function signature
                if paren_level_in_signature > 0 or (paren_level_in_signature == 0 and not func_lines[-1].strip().endswith(':')):
                    func_lines.append(line_content)
                    paren_level_in_signature += line_content.strip().count('(') - line_content.strip().count(')')
                    if not line_content.strip().endswith(':') and paren_level_in_signature <= 0: # Signature ended
                         # Check if the colon is on the next line
                        if line_number + 1 < len(lines) and lines[line_number+1].strip().startswith(':'):
                           pass # colon will be appended with next line
                        else: # Should not happen with valid Python if signature truly ended
                            pass # Might need more robust handling or assume valid syntax
                    continue
                
                # body
                if line_content.strip() == "" or current_indent > def_indent_level:
                    func_lines.append(line_content)
                # If indentation is same or less, and it's not an empty line, function has ended
                elif current_indent <= def_indent_level and line_content.strip() != "":
                    break # Function definition ended

        if not func_lines:
            logger.warning(f"Function {function_name} not found or code could not be extracted from {filepath}")
            return None
        return "".join(func_lines)
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        return None
    except Exception as e:
        logger.error(f"Error reading function {function_name} from {filepath}: {e}")
        return None

def generates_tests_for_function(function_code, function_name, full_module_path, context_description):
    if not function_code:
        logger.error("No function code provided to generate_tests_for_function.")
        return None

    try:
        model = GenerativeModel(DEFAULT_MODEL)
        logger.info(f"Using model: {DEFAULT_MODEL} for test generation.")
    except Exception as e:
        logger.warning(f"Failed to initialize model {DEFAULT_MODEL}: {e}")

    prompt = f"""
    You are an expert Python test engineer specializing in the pytest framework and testing Flask applications.
    Your task is to generate comprehensive pytest unit tests for the following Python function.

    Function Name: {function_name}
    Target Module for Imports within test: {full_module_path}(e.g., if function is in 'app.routes', tests will 'from app.routes import function_name')

    Function Code:
    ```python
    {function_code}

    Context and Instructions:
    {context_description}

    Please generate pytest unit tests that cover the following:
    1. Mocking Dependencies: Properly mock all external dependencies. For Flask routes, this typically includes:
    - flask.request (e.g., request.form, request.args, request.json).
    - Database sessions/objects (e.g., db.session.add, db.session.commit, db.session.delete, model query methods like Flashcard.query.get_or_404).
    - Flask utility functions like flask.render_template, flask.redirect, flask.url_for.
    - The Flashcard model constructor or any methods it might call if relevant to the function's logic beyond simple instantiation.
    - Use unittest.mock.patch or pytest fixtures with mocker (from pytest-mock) for mocking. 
    - Crucially, ensure patches target the correct module where the object is looked up by the function under test, not where it's defined (e.g., patch '{full_module_path}.request', '{full_module_path}.db', '{full_module_path}.Flashcard'). For example, if {full_module_path}.py contains from flask import request and uses request, you'd patch {full_module_path}.request. If it uses db.session.add after from . import db (where db is from app/__init__.py), you'd patch {full_module_path}.db.session.add.

    2. Test Scenarios:
    - Test the "happy path" where the function behaves as expected with valid inputs.
    - Test edge cases and error conditions (e.g., missing required form data, database errors if applicable, object not found).
    - Verify that mocks for collaborators (like db.session.add, db.session.commit) are called with the expected arguments.
    - Assert the function's return value (e.g., the response from render_template or redirect).

    3. Test Structure:
    - Write clear, well-named test functions (e.g., test_create_card_success, test_create_card_missing_front_content).
    - Use pytest conventions (e.g., test functions prefixed with test_).
    - Ensure necessary imports are included at the top of the test file (e.g., pytest, unittest.mock.patch, the function/module under test like from {full_module_path} import {function_name}, any necessary Flask objects if not fully mocked).
    - If testing Flask routes, using app.test_request_context() from a pytest fixture providing a Flask app instance is common, especially if url_for or other context-dependent Flask features are involved (even if also mocked).

    Output ONLY the Python code for the test file. Do not include any explanations or markdown formatting around the code block.
    The test code should be runnable using pytest when executed from the root directory of the application being tested (i.e., the directory containing the '{FLASK_APP_PACKAGE_NAME}' package).
    The function under test will be imported as from {full_module_path} import {function_name}.
    """
    logger.info(f"Generating tests for: {function_name} from {full_module_path} ...")
    if API_CALL_DELAY_SECONDS > 0:
        logger.info(f"Waiting for {API_CALL_DELAY_SECONDS} seconds before API call...")
        time.sleep(API_CALL_DELAY_SECONDS)

    try:
        generation_config = types.GenerationConfig(
            temperature= 0.5,
            top_p=0.95,
            max_output_tokens=20000
        )
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
        )

        generated_text = response.text.strip()
         # Basic stripping of markdown, can be improved
        if generated_text.startswith("```python"):
            generated_text = generated_text[len("```python"):].strip()
        elif generated_text.startswith("```"): # Handle generic code block
            generated_text = generated_text[len("```"):].strip()
        if generated_text.endswith("```"):
            generated_text = generated_text[:-len("```")].strip()

        logger.info(f"Successfully generated test code for {function_name}.")
        return generated_text
    except types.generation_types.BlockedPromptException as bpe:
        logger.error(f"Prompt was blocked for {function_name}. Details: {bpe.response.prompt_feedback}")
        for rating in bpe.response.prompt_feedback.safety_ratings:
            logger.error(f"Safety Rating: {rating.category} - {rating.probability}")
        return None
    except types.generation_types.StopCandidateException as sce:
        logger.error(f"Generation stopped unexpectedly for {function_name}: {sce}")
        return None
    except Exception as e:
        logger.error(f"Failed to generate tests for {function_name}: {e}")
        return None

if __name__ == "__main__":
    if not os.path.isdir(GENERATED_APP_ROOT_DIR):
        logger.error(f"GENERATED_APP_ROOT_DIR '{GENERATED_APP_ROOT_DIR}' does not exist. Please configure it correctly.")
        exit(1)

    target_file_relative_path = os.path.join(FLASK_APP_PACKAGE_NAME, "routes.py")
    target_function_name = "create_card"
    # For Flask, often things are imported from the 'app' package.
    target_module_import_path = f"{FLASK_APP_PACKAGE_NAME}.routes"

    target_file_full_path = os.path.join(GENERATED_APP_ROOT_DIR, target_file_relative_path)
    if not os.path.isfile(target_file_full_path):
        logger.error(f"Target file for testing '{target_file_full_path}' does not exist.")
        exit(1)

    ensure_init_py(GENERATED_APP_ROOT_DIR)
    ensure_init_py(os.path.join(GENERATED_APP_ROOT_DIR, FLASK_APP_PACKAGE_NAME))

    test_output_dir_name = "tests"
    test_output_full_dir = os.path.join(GENERATED_APP_ROOT_DIR, test_output_dir_name)
    os.makedirs(test_output_full_dir, exist_ok=True)
    ensure_init_py(test_output_full_dir)

    logger.info(f"Attempting to extract code for function '{target_function_name}' from '{target_file_full_path}'...")
    function_code_to_test = get_function_code(target_file_full_path, target_function_name)
    if function_code_to_test:
        logger.info(f"Successfully extracted code for '{target_function_name}'. Length: {len(function_code_to_test)} chars.")
        print(f"--- Code for {target_function_name} ---")
        print(function_code_to_test)
        print("-------------------------------------\n")

        # --- Context for the LLM ---
        # This part is crucial. We need to describe how `create_card` works. Cần cải thiện để ứng với nhiều functions hơn, hiện tại đang modify cho function "create_card"
        context_for_lmm = f"""The function `{target_function_name}` is a Flask route handler from the module `{target_module_import_path}`.
        It is expected to:
        - Be triggered by a POST request to '/flashcards'.
        - Retrieve 'front_content' and 'back_content' from flask.request.form.
        - If either 'front_content' or 'back_content' is missing, it should call flask.render_template with 'create_edit_card.html' and an error message.
        - If both are present, it should:
            1. Create an instance of the {FLASK_APP_PACKAGE_NAME}.models.Flashcard model.
            2. Add this instance to the {FLASK_APP_PACKAGE_NAME}.db.session (assuming db is imported into {target_module_import_path} from {FLASK_APP_PACKAGE_NAME}).
            3. Commit the session.
            4. Return a redirect to the 'index' view using flask.redirect(flask.url_for('index')).

        Key dependencies that will likely need mocking within the {target_module_import_path} module:
        - {target_module_import_path}.request (for request.form)
        - {target_module_import_path}.db.session.add,
        - {target_module_import_path}.db.session.commit,
        - {target_module_import_path}.Flashcard (if from .models import Flashcard or from {FLASK_APP_PACKAGE_NAME}.models import Flashcard is used in routes.py)
        - {target_module_import_path}.render_template
        - {target_module_import_path}.redirect
        - {target_module_import_path}.url_for

        The Flask app object and db (SQLAlchemy instance) are assumed to be initialized in the {FLASK_APP_PACKAGE_NAME} package (e.g., in {FLASK_APP_PACKAGE_NAME}/__init__.py).
        The Flashcard model is assumed to be defined in {FLASK_APP_PACKAGE_NAME}.models.
        When patching, ensure to patch these dependencies where they are looked up within the {target_module_import_path} module.
        For example, patch('{target_module_import_path}.request'), patch('{target_module_import_path}.db'), patch('{target_module_import_path}.Flashcard'), etc.
        """

        generated_test_script_content = generates_tests_for_function(
            function_code_to_test,
            target_function_name,
            target_module_import_path,
            context_for_lmm
        )

        if generated_test_script_content:
            print(f"--- Generated Test Script for {target_function_name} ---")
            print(generated_test_script_content)
            print("-----------------------------------------------------\n")

            # --- Next Step: Save and Run ---
            # We'll do this in the next iteration. For now, just print.
            test_file_name = f"test_{target_function_name}.py"
            test_file_full_path = os.path.join(test_output_full_dir, test_file_name)

            try:
                with open(test_file_full_path, "w", encoding='utf-8') as f:
                    f.write(generated_test_script_content)
                logger.info(f"Successfully saved generated tests to: {test_file_full_path}")

                # --- Log Instructions for Running Pytest ---
                logger.info("---")
                logger.info("INSTRUCTIONS TO RUN THE GENERATED TESTS:")
                logger.info(f"1. Ensure your Flask app's main __init__.py "
                            f"(e.g., in '{os.path.join(GENERATED_APP_ROOT_DIR, FLASK_APP_PACKAGE_NAME, '__init__.py')}') "
                            f"correctly defines the Flask 'app' instance and 'db' object, and imports routes/models.")
                logger.info(f"2. Open your terminal.")
                logger.info(f"3. Navigate to the root directory of the application being tested: "
                            f"cd \"{os.path.abspath(GENERATED_APP_ROOT_DIR)}\"")
                logger.info(f"4. Install test dependencies if you haven't: pip install pytest pytest-mock flask flask_sqlalchemy")
                logger.info(f"5. Run pytest for the specific file: pytest {os.path.join(test_output_dir_name, test_file_name)}")
                logger.info(f"   Or run all tests in the '{test_output_dir_name}' directory: pytest {test_output_dir_name}")
                logger.info(f"   Or simply run all discoverable tests: pytest")
                logger.info("---")

            except OSError as e:
                logger.error(f"Failed to write test file {test_file_full_path}: {e}")
        else:
            logger.error(f"Failed to generate test script content for {target_function_name}.")
    else:
        logger.error(f"Could not extract function code for {target_function_name} from {target_file_full_path}.")
