import os
import json
import time
import logging
from google.generativeai import GenerativeModel, configure, types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_CALL_DELAY_SECONDS = 5

try:
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file")
    configure(api_key=api_key)
    logger.info("Gemini API configured successfully for test generator.")
except Exception as e:
    logger.error(f"Failed to configure Gemini API: {e}")
    raise

DEFAULT_MODEL = 'gemini-2.0-flash'
GENERATED_CODE_DIR = "code_generated_result/flashcard_app" # need to be more flexible
FLASK_APP_MODULE_PATH = "app"

def get_function_code(filepath, function_name): # need to improve for more complex cases in the future
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()

        func_lines = []
        in_func = False
        indent_level = 0
        for line in lines:
            stripped_line = line.strip()
            if stripped_line.startswith(f"def {function_name}(") or stripped_line.startswith(f"async def {function_name}("):
                in_func = True
                indent_level = len(line) - len(line.lstrip()) # Indentation of def line
                func_lines.append(line)
            elif in_func:
                current_indent = len(line) - len(line.lstrip())
                if line.strip() == "" or current_indent > indent_level:
                    func_lines.append(line)
                elif current_indent <= indent_level and line.strip() != "":
                    break
        if not func_lines:
            logger.warning(f"Function {function_name} not found in {filepath}")
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
    Module: {full_module_path}

    Function Code:
    ```python
    {function_code}

    Context:
    {context_description}

    Please generate pytest unit tests that cover the following:
    1. Mocking Dependencies: Properly mock all external dependencies. For Flask routes, this typically includes:
    - flask.request (e.g., request.form, request.args, request.json).
    - Database sessions/objects (e.g., db.session.add, db.session.commit, db.session.delete, model query methods like Flashcard.query.get_or_404).
    - Flask utility functions like flask.render_template, flask.redirect, flask.url_for.
    - The Flashcard model constructor or any methods it might call if relevant to the function's logic beyond simple instantiation.
    - Use unittest.mock.patch or pytest fixtures with mocker (from pytest-mock) for mocking. Ensure patches target the correct module where the object is looked up, not where it's defined (e.g., patch '{full_module_path}.request', '{full_module_path}.db', '{full_module_path}.Flashcard').

    2. Test Scenarios:
    - Test the "happy path" where the function behaves as expected with valid inputs.
    - Test edge cases and error conditions (e.g., missing required form data, database errors if applicable, object not found).
    - Verify that mocks for collaborators (like db.session.add, db.session.commit) are called with the expected arguments.
    - Assert the function's return value (e.g., the response from render_template or redirect).

    3. Test Structure:
    - Write clear, well-named test functions (e.g., test_create_card_success, test_create_card_missing_front_content).
    - Use pytest conventions (e.g., test functions prefixed with test_).
    - Ensure necessary imports are included in the test file (e.g., pytest, unittest.mock.patch, the function/module under test, any necessary Flask objects if not fully mocked).
    - If the function is part of a Flask app, the tests might need a Flask test client (app.test_client()) and an application context (app.app_context()), though for pure unit tests with heavy mocking, this might be less critical if all Flask-specific parts are mocked out. Focus on mocking for now.

    Output ONLY the Python code for the test file. Do not include any explanations or markdown formatting around the code block.
    The test code should be runnable and self-contained given the necessary mocks.
    Assume the function under test can be imported from {full_module_path}. 
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
        if generated_text.startswith("```"):
            generated_text = generated_text[len("```"):].strip()
        if generated_text.endswith("```"):
            generated_text = generated_text[:-len("```")].strip()

        logger.info(f"Successfully generated test code for {function_name}.")
        return generated_text
    except types.generation_types.BlockedPromptException as bpe:
        logger.error(f"Prompt was blocked for {function_name}: {bpe}")
        return None
    except types.generation_types.StopCandidateException as sce:
        logger.error(f"Generation stopped unexpectedly for {function_name}: {sce}")
        return None
    except Exception as e:
        logger.error(f"Failed to generate tests for {function_name}: {e}")
        raise

if __name__ == "__main__":
    target_file_path = os.path.join(GENERATED_CODE_DIR, FLASK_APP_MODULE_PATH, "routes.py")
    target_function_name = "create_card"
    # For Flask, often things are imported from the 'app' package.
    target_module_full_path = "app.routes"

    function_code_to_test = get_function_code(target_file_path, target_function_name)
    if function_code_to_test:
        print(f"--- Code for {target_function_name} ---")
        print(function_code_to_test)
        print("-------------------------------------\n")

        # --- Context for the LLM ---
        # This part is crucial. We need to describe how `create_card` works.
        context = f"""The function `{target_function_name}` is a Flask route handler from the module `{target_module_full_path}`.
        It is expected to:
        - Be triggered by a POST request to '/flashcards'.
        - Retrieve 'front_content' and 'back_content' from flask.request.form.
        - If either 'front_content' or 'back_content' is missing, it should call flask.render_template with 'create_edit_card.html' and an error message.
        - If both are present, it should:
            1. Create an instance of the app.models.Flashcard model.
            2. Add this instance to the app.db.session.
            3. Commit the app.db.session.
            4. Return a redirect to the 'index' view using flask.redirect(flask.url_for('index')).

        Key dependencies to mock:
        - flask.request (specifically request.form)
        - app.db.session (methods: add, commit)
        - app.models.Flashcard (the constructor)
        - flask.render_template
        - flask.redirect
        - flask.url_for

        The app object (Flask app instance) and db object (SQLAlchemy instance) are assumed to be initialized in the app package (e.g., in app/__init__.py).
        The Flashcard model is assumed to be defined in app.models.
        When patching, ensure to patch these dependencies where they are looked up within the {target_module_full_path} module.
        For example, patch('{target_module_full_path}.request'), patch('{target_module_full_path}.db'), patch('{target_module_full_path}.Flashcard'), etc.
        """

        generated_test_script = generates_tests_for_function(
            function_code_to_test,
            target_function_name,
            target_module_full_path,
            context
        )

        if generated_test_script:
            print(f"--- Generated Test Script for {target_function_name} ---")
            print(generated_test_script)
            print("-----------------------------------------------------\n")

            # --- Next Step: Save and Run ---
            # We'll do this in the next iteration. For now, just print.
            test_file_name = f"test_{target_function_name}.py"
            test_output_dir = os.path.join(GENERATED_CODE_DIR, "tests") # Or wherever you want tests
            os.makedirs(test_output_dir, exist_ok=True)
            test_file_path = os.path.join(test_output_dir, test_file_name)
            with open(test_file_path, "w", encoding='utf-8') as f:
                f.write(generated_test_script)
            logger.info(f"Saved generated tests to: {test_file_path}")
            logger.info("You can now try to run this test file using pytest:")
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__),'..', '..'))
            path_to_run_pytest_from = os.path.join(project_root, "code_generated_result")
            relative_test_path = os.path.join(os.path.basename(GENERATED_CODE_DIR), "tests", test_file_name)
            logger.info(f"1. Navigate to: cd {path_to_run_pytest_from}")
            logger.info(f"2. Ensure your Flask app's __init__.py (in {GENERATED_CODE_DIR}/app/__init__.py) correctly defines 'app' and 'db'.")
            logger.info(f"3. Run: pytest {relative_test_path}")
        else:
            print(f"Failed to generate tests for {target_function_name}.")
    else:
        print(f"Could not extract function {target_function_name} from {target_file_path}.")
