import os
import logging
import logging.handlers
import sys
import colorama
from dotenv import load_dotenv, find_dotenv

colorama.init(autoreset=True)
class ColorFormatter(logging.Formatter):
    LOG_COLORS = {
            logging.DEBUG: colorama.Fore.CYAN,
            logging.INFO: colorama.Fore.GREEN,
            logging.WARNING: colorama.Fore.YELLOW,
            logging.ERROR: colorama.Fore.RED,
            logging.CRITICAL: colorama.Fore.MAGENTA + colorama.Style.BRIGHT,
    }

    def format(self, record):
        log_message = super().format(record)
        return self.LOG_COLORS.get(record.levelno, colorama.Fore.WHITE) + log_message

def setup_global_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    log_file_path = os.path.join(project_root, 'overall_system.log')

    file_handler = logging.handlers.RotatingFileHandler(log_file_path, maxBytes=3*1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = ColorFormatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger

# Other modules can just call `import logging; logger = logging.getLogger(__name__)`
# and they will automatically use this configuration.
logger = setup_global_logger()

dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
    logger.info(f"Loaded .env file from: {dotenv_path}")
else:
    logger.warning(".env file not found. Relying on environment variables or defaults.")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BASE_OUTPUT_DIR = os.getenv("PERSISTED_BASE_OUTPUT_DIR")
PYTHON_EXECUTABLE = os.getenv("PERSISTED_PYTHON_PATH")

if BASE_OUTPUT_DIR:
    SPEC_DESIGN_OUTPUT_DIR = os.path.join(BASE_OUTPUT_DIR, "spec_vs_design")
else:
    SPEC_DESIGN_OUTPUT_DIR = None

API_DELAY_SECONDS = int(os.getenv("API_DELAY_SECONDS", "5"))
MAX_LLM_RETRIES = int(os.getenv("MAX_LLM_RETRIES", "2"))

DEFAULT_GEMINI_MODEL_FOR_SPEC_DESIGN = os.getenv("SPEC_DESIGN_MODEL", "gemini-2.0-flash")
DEFAULT_GEMINI_MODEL_FOR_CODING = os.getenv("CODING_MODEL", "gemini-2.0-flash")
DEFAULT_GEMINI_MODEL_FOR_TESTING = os.getenv("TESTING_MODEL", "gemini-2.0-flash")
DEFAULT_GEMINI_MODEL_FOR_DEBUGGING = os.getenv("DEBUGGING_MODEL", "gemini-2.0-flash")

CURRENT_MODELS = {
    "spec_design": DEFAULT_GEMINI_MODEL_FOR_SPEC_DESIGN,
    "coding": DEFAULT_GEMINI_MODEL_FOR_CODING,
    "testing": DEFAULT_GEMINI_MODEL_FOR_TESTING,
    "debugging": DEFAULT_GEMINI_MODEL_FOR_DEBUGGING,
}

def choose_models():
    global CURRENT_MODELS
    print("\n--- Model Selection ---")
    print("Choose the Gemini models for this run. Press Enter to use the default.")
    
    options = {
        "1": "gemini-1.5-flash-latest",
        "2": "gemini-1.5-pro-latest"
    }

    default_model_placeholder = "gemini-2.0-flash"

    try:
        print(f"Available Models: 1) {options['1']}, 2) {options['2']}")
        choice = input(f"Select a model for all agents [Default: {default_model_placeholder}]: ").strip()

        chosen_model = options.get(choice, default_model_placeholder)

        if choice == "":
            logger.info("No model selection made. Using predefined default models.")
            return
        
        logger.info(f"User selected model '{chosen_model}' for all agents.")

        for key in CURRENT_MODELS:
            CURRENT_MODELS[key] = chosen_model

    except (EOFError, KeyboardInterrupt):
        logger.warning("\nModel selection skipped. Using default models.")

ESSENTIAL_VARIABLES = {
    "GEMINI_API_KEY": GEMINI_API_KEY,
    "BASE_OUTPUT_DIR": BASE_OUTPUT_DIR,
    "PYTHON_EXECUTABLE": PYTHON_EXECUTABLE,
}

missing_variables = [key for key, value in ESSENTIAL_VARIABLES.items() if not value]

if missing_variables:
    error_message = (
        f"Missing essential configuration variable(s): {', '.join(missing_variables)}. "
        "Please ensure your .env file is correctly set up. You may need to run "
        "a setup script first (like your detect_path.py logic)."
    )
    logger.critical(error_message)
    raise EnvironmentError(error_message)
else:
    logger.info("Essential configurations loaded successfully.")
    logger.info(f"  GEMINI_API_KEY: {'*' * (len(GEMINI_API_KEY) - 4) + GEMINI_API_KEY[-4:]}")
    logger.info(f"  BASE_OUTPUT_DIR: {BASE_OUTPUT_DIR}")
    logger.info(f"  PYTHON_EXECUTABLE: {PYTHON_EXECUTABLE}")
    logger.info(f"  SPEC_DESIGN_OUTPUT_DIR (will be created): {SPEC_DESIGN_OUTPUT_DIR}")
    logger.info(f"  API_DELAY_SECONDS: {API_DELAY_SECONDS}")
    logger.info(f"  MAX_LLM_RETRIES: {MAX_LLM_RETRIES}")
