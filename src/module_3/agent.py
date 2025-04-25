import json
import os
import argparse
import logging
from google.generativeai import GenerativeModel, configure
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('codegen.log'),
        logging.StreamHandler()
    ]
)

# Move API configuration to module level
try:
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file")
    configure(api_key=api_key)
    logger.info("Gemini API configured successfully.")
except Exception as e:
    logger.error(f"Failed to configure Gemini API: {e}")
    raise

# Supported Gemini models
SUPPORTED_MODELS = ['gemini-1.5-pro', 'gemini-1.5-flash']
DEFAULT_MODEL = 'gemini-2.5-pro-exp-03-25'

OUTPUT_DIR = 'code_generated_result'

parser = argparse.ArgumentParser(description="Generate an application from JSON design and specification files.")
parser.add_argument('design_file', help="Path to the JSON design file")
parser.add_argument('spec_file', help="Path to the JSON specification file")

def validate_json_design(json_data):
    """
    Validate the JSON design file against expected structure.

    Args:
        json_data (dict): JSON design file.

    Raises:
        ValueError: If critical fields are missing or invalid.
    """
    required_fields = ['system_Architecture', 'data_Design', 'interface_Design', 'folder_Structure', 'dependencies']
    for field in required_fields:
        if field not in json_data:
            logger.error(f"Missing required field: {field}")
            raise ValueError(f"JSON design file must contain '{field}'")
    
    # Validate folder structure
    folder_structure = json_data.get('folder_Structure', {}).get('structure', [])
    if not isinstance(folder_structure, list):
        logger.error("folder_Structure.structure must be a list")
        raise ValueError("folder_Structure.structure must be a list")
    
    for item in folder_structure:
        if 'path' not in item:
            logger.error("Each folder_Structure item must have a 'path'")
            raise ValueError("Each folder_Structure item must have a 'path'")
    
    # Validate dependencies
    dependencies = json_data.get('dependencies', {})
    if 'backend' not in dependencies or 'frontend' not in dependencies:
        logger.error("dependencies must contain 'backend' and 'frontend'")
        raise ValueError("dependencies must contain 'backend' and 'frontend'")
    
    # Validate dependencies
    dependencies = json_data.get('dependencies', {})
    if 'backend' not in dependencies or 'frontend' not in dependencies:
        logger.error("dependencies must contain 'backend' and 'frontend'")
        raise ValueError("dependencies must contain 'backend' and 'frontend'")

def validate_json_spec(json_data):
    """
    Validate the JSON specification file against expected structure.

    Args:
        json_data (dict): JSON specification file.

    Raises:
        ValueError: If critical fields are missing or invalid.
    """
    required_fields = ['project_Overview', 'functional_Requirements', 'technology_Stack']
    for field in required_fields:
        if field not in json_data:
            logger.error(f"Missing required field in spec: {field}")
            raise ValueError(f"JSON specification must contain '{field}'")

def parse_json_and_generate_scaffold_plan(json_design):
    """
    Parse a JSON design file and generate a scaffold plan.

    Args:
        json_design (dict): JSON design file describing the application structure.

    Returns:
        dict: A plan with shell commands and file paths in the format:
              {"shell": [str], "files": {str: ""}}

    Raises:
        ValueError: If json_design or folder structure is invalid.
    """
    logger.info("Generating scaffold plan from JSON design file.")
    
    # Validate input
    validate_json_design(json_design)
    
    # Extract folder structure
    folder_structure = json_design['folder_Structure']['structure']
    directories = []
    files = {}
    
    for item in folder_structure:
        path = item['path'].lstrip('/')
        # Prepend OUTPUT_DIR to paths
        output_path = os.path.join(OUTPUT_DIR, path)
        if item['description'].lower().find('directory') != -1:
            directories.append(output_path)
        else:
            files[output_path] = ""
    
    # Add dependency files
    files[os.path.join(OUTPUT_DIR, 'backend/requirements.txt')] = ""
    files[os.path.join(OUTPUT_DIR, 'frontend/package.json')] = ""
    
    # Generate shell commands (for logging purposes)
    shell_commands = [f"mkdir {d}" for d in directories] + [f"touch {f}" for f in files.keys()]
    
    result = {
        "shell": shell_commands,
        "files": files
    }
    
    logger.info("Scaffold plan generated successfully.")
    return result

def create_project_structure(plan):
    """
    Create the project structure programmatically.

    Args:
        plan (dict): Scaffold plan with 'shell' commands and 'files' dictionary.

    Raises:
        OSError: If directory/file creation fails.
    """
    logger.info(f"Creating project structure in {OUTPUT_DIR}.")
    
    # Create OUTPUT_DIR if it doesn't exist
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        logger.info(f"Created output directory: {OUTPUT_DIR}")
    except OSError as e:
        logger.error(f"Failed to create output directory {OUTPUT_DIR}: {e}")
        raise
    
    # Create directories
    directories = set(os.path.dirname(path) for path in plan['files'].keys() if os.path.dirname(path))
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {directory}")
        except OSError as e:
            logger.error(f"Failed to create directory {directory}: {e}")
            raise
    
    # Create empty files
    for file_path in plan['files'].keys():
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                pass  # Create empty file
            logger.info(f"Created file: {file_path}")
        except OSError as e:
            logger.error(f"Failed to create file {file_path}: {e}")
            raise

def generate_code_for_each_file(json_design, json_spec, file_path):
    """
    Generate code content for a specific file based on the JSON design and specification files.

    Args:
        json_design (dict): JSON design file describing the application.
        json_spec (dict): JSON specification file with requirements.
        file_path (str): Path to the file for which to generate code.

    Returns:
        str: Generated code content.

    Raises:
        ValueError: If inputs are invalid.
        Exception: If API call or response parsing fails.
    """
    logger.info(f"Generating code for file: {file_path}")
    
    if not isinstance(json_design, dict) or not isinstance(json_spec, dict) or not isinstance(file_path, str):
        logger.error("Invalid inputs: json_design and json_spec must be dicts, file_path must be str.")
        raise ValueError("json_design and json_spec must be dicts, file_path must be a str.")

    try:
        validate_json_design(json_design)
        validate_json_spec(json_spec)
    except ValueError as e:
         logger.error(f"Invalid JSON structure for {file_path}: {e}")
         raise
    
    if file_path.endswith(os.path.join('backend', 'requirements.txt')): # Use os.path.join for robustness
         logger.info(f"Generating content for requirements.txt: {file_path}")
         dependencies = json_design.get('dependencies', {}).get('backend', [])
         return '\n'.join(dependencies)

    if file_path.endswith(os.path.join('frontend', 'package.json')): # Use os.path.join for robustness
        logger.info(f"Generating content for package.json: {file_path}")
        frontend_deps = json_design.get('dependencies', {}).get('frontend', [])
        project_name = json_spec.get('project_Overview', {}).get('project_Name', 'application')
        package_json = {
            "name": f"{project_name.lower().replace(' ', '-')}-frontend",
            "version": "1.0.0",
            "dependencies": {dep: "latest" for dep in frontend_deps},
            "scripts": {
                "start": "react-scripts start", # Example
                "build": "react-scripts build"  # Example
            }
        }
        return json.dumps(package_json, indent=2)
    
    logger.info(f"Proceeding with LLM generation for: {file_path}")
    model = None
    # Use actual supported models, ensure DEFAULT_MODEL is tried first if valid
    models_to_try = []
    if DEFAULT_MODEL in SUPPORTED_MODELS: # Check if default is supported
         models_to_try.append(DEFAULT_MODEL)
    models_to_try.extend([m for m in SUPPORTED_MODELS if m != DEFAULT_MODEL]) # Add others

    if not models_to_try: # Handle case where DEFAULT_MODEL might be invalid AND SUPPORTED_MODELS is empty
         logger.error("DEFAULT_MODEL is not in SUPPORTED_MODELS and SUPPORTED_MODELS is empty.")
         raise ValueError("No valid models configured for generation.")
    
    for model_name in models_to_try:
        try:
            # Ensure API is configured (might be redundant if module-level worked)
            global api_key # Access the module-level api_key
            if not api_key:
               # This case should ideally be caught by the module-level check, but defense-in-depth
               logger.error("Gemini API key not configured (checked within generate_code_for_each_file).")
               raise ValueError("API key not configured")
            model = GenerativeModel(model_name)
            logger.info(f"Using model: {model_name}")
            break # Stop after successfully initializing a model
        except Exception as e:
            logger.warning(f"Failed to initialize model {model_name}: {e}")

    if model is None:
        logger.error(f"Failed to initialize any supported models: {models_to_try}")
        raise ValueError("No supported Gemini models could be initialized.")

    # Extract dynamic fields for prompt
    project_name = json_spec.get('project_Overview', {}).get('project_Name', 'application')
    backend_framework = json_spec.get('technology_Stack', {}).get('backend', {}).get('framework', 'unknown')
    frontend_framework = json_spec.get('technology_Stack', {}).get('frontend', {}).get('framework', 'unknown')
    storage_type = json_design.get('data_Design', {}).get('storage_Type', 'unknown')    

    prompt = f"""
    You are a code writer for a {project_name} with a {backend_framework} backend, {frontend_framework} frontend, and {storage_type} storage.
    Based on the JSON design file (technical implementation) and JSON specification file (requirements), generate the complete content of the file.

    Requirements:
    - File path: `{file_path}`
    - Only output valid code (no explanation or markdown).
    - Implement functionality based on both files:
      - Design file: Defines system architecture, API endpoints (interface_Design.api_Specifications), data models (data_Design), and workflows (workflow_Interaction).
        - Backend: Implement API endpoints as specified, handling data operations with the given storage type.
        - Frontend: Create components to support user interactions as per workflows and requirements, using the specified storage.
        - Use dependencies from dependencies field.
      - Specification file: Defines functional requirements (functional_Requirements), non-functional requirements (non_Functional_Requirements), and project scope (project_Overview).
        - Functional requirements detail user-facing features and acceptance criteria.
        - Non-functional requirements include constraints like usability, performance, or security.
        - Scope defines what features to include or exclude.
    - Infer the file's role from its path (e.g., backend main file, frontend main component).
    - Ensure code aligns with acceptance criteria and non-functional requirements.

    Here is the design file:
    {json.dumps(json_design, indent=2)}

    Here is the specification file:
    {json.dumps(json_spec, indent=2)}
    """

    try:
        response = model.generate_content(prompt)
        generated_text = response.text.strip()
        # Optional: Strip markdown code fences
        if generated_text.startswith("```") and generated_text.endswith("```"):
             lines = generated_text.splitlines()
             if len(lines) > 1:
                 # Take lines between the first and last line
                 generated_text = "\n".join(lines[1:-1]).strip()
             else: # Handle edge case of ```code``` on one line
                 generated_text = generated_text.strip('`').strip()

        return generated_text
    except Exception as e:
        logger.error(f"Failed to generate code for {file_path}: {e}")
        raise

def write_code_to_file(file_path, code):
    """
    Write generated code to a file.

    Args:
        file_path (str): Path to the file.
        code (str): Code content to write.

    Raises:
        OSError: If file writing fails.
    """
    logger.info(f"Writing code to file: {file_path}")
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        logger.info(f"Successfully wrote to {file_path}")
    except OSError as e:
        logger.error(f"Failed to write to {file_path}: {e}")
        raise

def run_codegen_pipeline(json_design, json_spec, design_file_path):
    """
    Run the code generation pipeline: scaffold, create structure, and generate code.

    Args:
        json_design (dict): JSON design file of the application.
        json_spec (dict): JSON specification file with requirements.
        design_file_path (str): Path to the JSON design file (for logging).

    Raises:
        Exception: If any step in the pipeline fails.
    """
    logger.info(f"Starting code generation pipeline for {design_file_path}.")
    try:
        plan = parse_json_and_generate_scaffold_plan(json_design)
        create_project_structure(plan)
        for file_path in plan["files"].keys():
            code = generate_code_for_each_file(json_design, json_spec, file_path)
            write_code_to_file(file_path, code)
        logger.info("Code generation pipeline completed successfully.")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise

if __name__ == "__main__":
    args = parser.parse_args()

    try:
        with open(args.design_file) as f:
            json_design = json.load(f)
        with open(args.spec_file) as f:
            json_spec = json.load(f)
        
        # Validate compatibility (check metadata)
        design_metadata = json_design.get('metadata', {})
        spec_timestamp = json_spec.get('metadata', {}).get('timestamp', '')
        if design_metadata.get('source_specification_timestamp') != spec_timestamp:
            logger.warning("Design file's source specification timestamp does not match spec file timestamp.")
        
        run_codegen_pipeline(json_design, json_spec, args.design_file)
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON file: {e}")
        raise