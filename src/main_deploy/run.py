import sys
import logging
import argparse
import os

# --- Minimal Initial Imports ---
# Only import modules that DO NOT depend on the .env file being complete.
# 'detect_path' is safe because it's what CREATES the .env file.
from detect_path import define_project_root, define_python_path

# We cannot import 'config' here at the top level anymore.

def run_initial_setup():
    """
    Runs an interactive setup wizard for the user to define critical paths.
    This only needs to be run once, as it saves the paths to the .env file.
    """
    print("--- Initial Setup Wizard ---")
    print("Please provide the required paths. These will be saved to your .env file.")
    try:
        # Create a .env file if it doesn't exist, to prevent errors.
        if not os.path.exists('.env'):
            open('.env', 'a').close()
            
        define_project_root()
        define_python_path()
        print("\n✅ Setup complete! You can now run the main application without the --setup flag.")
        print("   If you need to change these paths, just run with --setup again.")
    except (EOFError, KeyboardInterrupt):
        print("\nSetup cancelled by user.")
        sys.exit(0)

def main():
    """
    The main entry point for the Autonomous Software Factory application.
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Autonomous Software Factory - A multi-agent system to generate and test software.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run the interactive setup wizard to configure essential paths."
    )
    parser.add_argument(
        '--description',
        type=str,
        default=None,
        help="A detailed description of the web application to build.\nIf not provided, the script will prompt you for it interactively."
    )
    args = parser.parse_args()

    # --- Handle Setup FIRST ---
    if args.setup:
        run_initial_setup()
        return # Exit after setup

    # --- Run Main Application ---
    # If we are NOT running setup, it's now safe to import our main modules
    # that depend on the .env file.
    try:
        import config
        from main import run_autonomous_software_factory
        from setup import configure_gemini_api

        # Get the logger that was configured in config.py
        logger = logging.getLogger(__name__)

        # 1. Configure the Gemini API (must be done before any agent is created)
        configure_gemini_api()

        # 2. Let the user choose the models for this run
        config.choose_models()

        # 3. Get the user's project description
        user_description = args.description
        if not user_description:
            print("\n--- Welcome to the Autonomous Software Factory ---")
            print("Please provide a detailed description of the application you want to build.")
            print("Example: 'A simple task management web app with user login, tasks with name/due date, and filtering.'")
            try:
                # Use a clear prompt character
                user_description = input("\nEnter your project description:\n> ")
            except (EOFError, KeyboardInterrupt):
                print("\n\nOperation cancelled by user. Exiting.")
                sys.exit(0)

        if not user_description.strip():
            logger.error("Project description cannot be empty. Exiting.")
            sys.exit(1)

        # 4. Kick off the main workflow
        run_autonomous_software_factory(user_description)

    except EnvironmentError as e:
        logger = logging.getLogger(__name__) # Get a basic logger if config failed
        logger.critical(f"A critical configuration error occurred: {e}")
        logger.critical("Please run the setup wizard using: python src/main_deploy/run.py --setup")
        sys.exit(1)
    except ImportError as e:
        # This can happen if the user runs from the wrong directory
        logger = logging.getLogger(__name__)
        logger.critical(f"An import error occurred: {e}. Are you running this command from the project's root directory ('autocode_assistant')?")
        sys.exit(1)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.critical(f"An unexpected fatal error occurred in the application: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()