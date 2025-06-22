import os
import sys
from dotenv import load_dotenv, find_dotenv, set_key

# Gets a persisted value from the last run, or returns a default value.
def _get_persistent_value(key: str, default_value: str) -> str:
    load_dotenv()
    return os.getenv(key, default_value)

# Saves a value to the .env file to remember it for subsequent runs.
def _save_persistent_value(key: str, value: str):
    dotenv_path = find_dotenv()
    if not dotenv_path:
        # Create a .env file in the current directory if it doesn't exist.
        dotenv_path = os.path.join(os.getcwd(), '.env')
        open(dotenv_path, 'a').close()

    set_key(dotenv_path, key_to_set=key, value_to_set=value)
    print(f"Configuration updated: Saved {key} to {dotenv_path}")

# Displays a prompt to the user and returns their input or a default value.
def _prompt_user(message: str, default: str) -> str:
    try:
        prompt_message = f"{message} [Default: {default}]: "
        user_input = input(prompt_message).strip()
        return user_input if user_input else default
    except EOFError:
        # Handles cases where the script is run in a non-interactive environment.
        print("Warning: No user input received, using default value.")
        return default

# Defines the root directory to store generated projects.
# It suggests a default based on the last run or the current directory.
def define_project_root() -> str:
    persistence_key = "PERSISTED_BASE_OUTPUT_DIR"
    default_path = _get_persistent_value(
        persistence_key,
        os.path.join(os.getcwd(), 'code_generated_result')
    )

    chosen_path = _prompt_user("Enter the root directory for generated projects", default_path)
    # Expands user-specific paths (like ~) and gets the absolute path.
    final_path = os.path.abspath(os.path.expanduser(chosen_path))

    # Create the directory if it doesn't exist.
    os.makedirs(final_path, exist_ok=True)
    print(f"Project root directory will be: {final_path}")

    # Save the choice for the next run and set the environment variable for the current session.
    _save_persistent_value(persistence_key, final_path)
    os.environ['BASE_OUTPUT_DIR'] = final_path
    
    print("Tip: You can delete the '.env' file to reconfigure from scratch on the next run.")
    return final_path

# Defines the path to the Python executable.
# It suggests the current executable as the default and validates the user's choice.
def define_python_path() -> str:
    persistence_key = "PERSISTED_PYTHON_PATH"
    default_path = _get_persistent_value(persistence_key, sys.executable)
    
    final_path = ""
    while True:
        chosen_path = _prompt_user("Enter the path to the Python executable", default_path)
        final_path = os.path.abspath(os.path.expanduser(chosen_path))

        # Validate if the path is an existing file and looks like a Python executable.
        if os.path.isfile(final_path) and ('python' in final_path.lower() or 'py.exe' in final_path.lower()):
            break  # Exit the loop if the path is valid.
        else:
            print(f"Error: The path '{final_path}' is not a valid Python executable. Please try again.")
            # Suggest the invalid path as the new default to allow for easy editing.
            default_path = final_path
    
    print(f"Python executable path will be: {final_path}")

    # Save the choice for the next run and set the environment variable for the current session.
    _save_persistent_value(persistence_key, final_path)
    os.environ['PYTHON_PATH'] = final_path
    
    print("Tip: You can delete the '.env' file to reconfigure from scratch on the next run.")
    return final_path