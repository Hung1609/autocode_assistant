import json
import os
import argparse
import logging
import time
import re
from google.generativeai import GenerativeModel, configure
from dotenv import load_dotenv

API_CALL_DELAY_SECONDS = 5
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('codegen.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")
configure(api_key=api_key)
logger.info("Gemini API configured successfully.")

SUPPORTED_MODELS = ['gemini-2.0-flash', 'gemini-1.5-flash']
DEFAULT_MODEL = 'gemini-2.0-flash'
BASE_OUTPUT_DIR = 'code_generated_result'

parser = argparse.ArgumentParser(description="Generate an application from JSON design and specification files.")
parser.add_argument('design_file', help="Path to the JSON design file")
parser.add_argument('spec_file', help="Path to the JSON specification file")
parser.add_argument('--model', default=DEFAULT_MODEL, choices=SUPPORTED_MODELS, help=f"Gemini model to use for code generation (default: {DEFAULT_MODEL}).")


# --- Main functions ---
def  slugify(text):
    text = text.lower()
    text = re.sub(r'\s+', '_', text)
    text = re.sub(r'[^\w_.-]', '', text)
    text = text.strip('_.-')
    return text if text else "unnamed_project"

def validate_json_design(json_data): # Validate the JSON design file against expected structure.
    logger.debug("Validating JSON design file.")
    required_fields = ['system_Architecture', 'data_Design', 'interface_Design', 'folder_Structure', 'dependencies']
    for field in required_fields:
        if field not in json_data:
            logger.error(f"Missing required field: {field}")
            raise ValueError(f"JSON design file must contain '{field}'")

    folder_structure = json_data.get('folder_Structure')
    if not isinstance(folder_structure, dict):
        logger.error("folder_Structure must be a dictionary.")
        raise ValueError("folder_Structure must be a dictionary.")

    root_dir_name = folder_structure.get('root_Project_Directory_Name')
    if not root_dir_name or not isinstance(root_dir_name, str) or not root_dir_name.strip():
        logger.error("folder_Structure must contain a non-empty 'root_Project_Directory_Name' string.")
        raise ValueError("folder_Structure must contain a non-empty 'root_Project_Directory_Name' string.")

    structure_list = folder_structure.get('structure')
    if not isinstance(structure_list, list):
        logger.error("folder_Structure.structure must be a list.")
        raise ValueError("folder_Structure.structure must be a list.")
    
    for i, item in enumerate (structure_list):
        if not isinstance(item, dict):
            logger.error(f"Item at index {i} in folder_Structure.structure is not a dictionary.")
            raise ValueError(f"Item at index {i} in folder_Structure.structure is not a dictionary.")
        if 'path' not in item or not isinstance(item['path'], str) or not item['path'].strip():
            logger.error(f"Item at index {i} in folder_Structure.structure must have a non-empty 'path' string.")
            raise ValueError(f"Item at index {i} in folder_Structure.structure must have a non-empty 'path' string.")
        if 'description' not in item or not isinstance(item['description'], str):
            logger.error(f"Item at index {i} ('{item.get('path')}') in folder_Structure.structure must have a 'description' string.")
            raise ValueError(f"Item at index {i} ('{item.get('path')}') in folder_Structure.structure must have a 'description' string.")
    
    dependencies = json_data.get('dependencies')
    if not isinstance(dependencies, dict):
        logger.error("dependencies must be a dictionary.")
        raise ValueError("dependencies must be a dictionary.")
    if 'backend' not in dependencies or not isinstance(dependencies['backend'], list):
        logger.error("dependencies must contain a 'backend' list.")
        raise ValueError("dependencies must contain a 'backend' list.")
    if 'frontend' not in dependencies or not isinstance(dependencies['frontend'], list):
        logger.error("dependencies must contain a 'frontend' list.")
        raise ValueError("dependencies must contain a 'frontend' list.")
    logger.debug("JSON design validation successful.")

def validate_json_spec(json_data): # Validate the JSON specification file against expected structure.
    logger.debug("Validating JSON specification structure.")
    required_fields = ['project_Overview', 'functional_Requirements', 'technology_Stack', 'data_Storage']
    for field in required_fields:
        if field not in json_data:
            logger.error(f"JSON specification must contain '{field}'.")
            raise ValueError(f"JSON specification must contain '{field}'.")
    project_overview = json_data.get('project_Overview')
    if not isinstance(project_overview, dict) or not project_overview.get('project_Name'):
        logger.error("JSON specification's project_Overview must be a dictionary with a 'project_Name'.")
        raise ValueError("JSON specification's project_Overview must be a dictionary with a 'project_Name'.")
    logger.debug("JSON specification validation successful.")

def parse_json_and_generate_scaffold_plan(json_design, json_spec): # Parse the JSON design file and generate a scaffold plan.
    logger.info("Generating scaffold plan from JSON design file.")
    validate_json_design(json_design)
    validate_json_spec(json_spec)
    
    project_root_name = json_design['folder_Structure']['root_Project_Directory_Name']
    actual_project_root_dir = os.path.join(BASE_OUTPUT_DIR, project_root_name)
    logger.info(f"Target project root directory: {actual_project_root_dir}")
    folder_structure_items = json_design['folder_Structure']['structure']
    directories_to_create = set()
    files_to_create = {}

    for item in folder_structure_items:
        relative_path = item['path'].strip()
        relative_path = relative_path.replace('\\', '/')
        if relative_path.startswith('/'):
            relative_path = relative_path[1:]
            logger.warning(f"Path '{item['path']}' started with '/'. Corrected to '{relative_path}'. Ensure DESIGN_PROMPT output is correct.")
        
        current_path = os.path.join(actual_project_root_dir, relative_path)
        is_directory = 'directory' in item['description'].lower()
        if is_directory:
            directories_to_create.add(current_path)
        else:
            parent_dir = os.path.dirname(current_path)
            if parent_dir and parent_dir != actual_project_root_dir:
                directories_to_create.add(parent_dir)
            files_to_create[current_path] = ""

    # Shell commands (for logging purposes)
    shell_commands_log = [f"mkdir -p \"{d}\"" for d in sorted(list(directories_to_create))] + [f"touch \"{f}\"" for f in files_to_create.keys()]
    result = {
        "project_root_directory": actual_project_root_dir,
        "directories_to_create": sorted(list(directories_to_create)),
        "files_to_create": files_to_create,
        "shell_commands_log": shell_commands_log
    }
    logger.info(f"Scaffold plan generated successfully. Root: {actual_project_root_dir}")
    logger.debug(f"Directories planned: {result['directories_to_create']}")
    logger.debug(f"Files planned: {list(result['files_to_create'].keys())}")
    return result

def create_project_structure(plan): # Create the project structure based on the scaffold plan.
    project_root = plan["project_root_directory"]
    logger.info(f"Creating project structure in {project_root}.")
    os.makedirs(project_root, exist_ok=True)
    logger.info(f"Ensured base project directory exists: {project_root}")
    
    # Create BASE_OUTPUT_DIR if it doesn't exist
    try:
        os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
        logger.info(f"Created output directory: {BASE_OUTPUT_DIR}")
    except OSError as e:
        logger.error(f"Failed to create output directory {BASE_OUTPUT_DIR}: {e}")
        raise
    
    # Create all planned directories
    for directory in plan['directories_to_create']:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")
    # Create empty files
    for file_path in plan["files_to_create"].keys():
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            pass 
        logger.info(f"Created empty file: {file_path}")
    logger.info("Project structure created successfully.")

def generate_code_for_each_file(json_design, json_spec, file_path, project_root_dir, llm_model):
    logger.info(f"Attempting to generate code for file: {file_path}")
    if not all(isinstance(arg, dict) for arg in [json_design, json_spec]):
        raise ValueError("json_design and json_spec must be dictionaries.")
    if not isinstance(file_path, str):
        raise ValueError("file_path must be a string.")

    # Handle dependencies file only for python
    relative_file_path = os.path.relpath(file_path, project_root_dir).replace('\\', '/')
    if relative_file_path == 'requirements.txt':
        logger.info(f"Generating content for backend requirements.txt: {file_path}")
        backend_deps = json_design.get('dependencies', {}).get('backend', [])
        if not backend_deps:
            logger.warning(f"No backend dependencies found in design for {file_path}. File will be empty or have minimal content.")
        return '\n'.join(backend_deps) + '\n'
    
    logger.info(f"Proceeding with LLM generation for: {file_path}")
    project_name = json_spec.get('project_Overview', {}).get('project_Name', 'this application')
    backend_language_framework = f"{json_spec.get('technology_Stack', {}).get('backend', {}).get('language', '')} {json_spec.get('technology_Stack', {}).get('backend', {}).get('framework', '')}".strip()
    frontend_language_framework = f"{json_spec.get('technology_Stack', {}).get('frontend', {}).get('language', '')} {json_spec.get('technology_Stack', {}).get('frontend', {}).get('framework', '')}".strip()
    storage_type = json_design.get('data_Design', {}).get('storage_Type', 'not specified')    

    # NOTE: The file_path passed to prompt is the absolute one.
    prompt = f"""
    Context:
    You are an expert Senior Software Engineer acting as a meticulous code writer for a {project_name} with a {backend_language_framework} backend technology, {frontend_language_framework} frontend technology, and {storage_type} storage type.
    Your task is to generate the complete, syntactically correct code content for the specified file, based on the JSON design file (technical implementation) and JSON specification file (requirements).

    Target File Information:
    - Full Path of the file to generate: `{file_path}`
    - This file is part of the project structure defined in the `folder_Structure` section of the JSON Design. The `folder_Structure.root_Project_Directory_Name` indicates the main project folder. The `folder_Structure.structure` lists all files and directories relative to that root.
    
    INTERNAL THOUGHT PROCESS (Follow these steps to build a comprehensive understanding before writing code):
    1.  **Analyze File Role**: Based on the path `{file_path}` and the JSON Design's `folder_Structure`, determine this file's specific purpose (e.g., API Router, Data Model, Service/Business Logic, UI Component, Configuration, Utility).
    2.  **Identify Key Requirements (from JSON Specification)**:
        *   Which Functional Requirements (FRs) must this file help implement?
        *   Which Non-Functional Requirements (NFRs, e.g., Security, Performance, Usability) must this file adhere to?
    3.  **Map to Design (from JSON Design)**:
        *   Which API endpoints (`interface_Design`) does this file define or call?
        *   Which Data Models (`data_Design`) does this file define or use (CRUD)?
        *   Which Workflows (`workflow_Interaction`) does this file participate in?
    4.  **Plan Implementation & Patterns (Algorithm of Thoughts aspect)**:
        *   What is the high-level structure (Classes, Functions, Imports)?
        *   Based on the file's role and the project's Tech Stack ({backend_language_framework} / {frontend_language_framework}), what standard coding conventions, idioms, and design patterns (e.g., REST conventions, Repository, Service Layer, Error Handling, Async/Await, Component structure) should be applied?
        *   Which specific libraries listed in the `dependencies` section will be needed?

    Instructions for Code Generation:
    1.  **Output Code Only**: Your response MUST be only the raw code for the file. Do NOT include any explanations, comments outside the code, or markdown formatting (like ```language ... ```).
    2.  **Implement Functionality**: Base the code on BOTH the JSON Design and JSON Specification provided below.
        -   **JSON Design (Technical Implementation Details)**:
            -   `system_Architecture`: Overall component layout.
            -   `data_Design.data_Models`: Define database schemas/models, considering the `storage_Type`.
            -   `interface_Design.api_Specifications`: For backend files, implement these API endpoints (routes, controllers, handlers). For frontend files, prepare to call these APIs.
            -   `workflow_Interaction`: Implement the logic described in these user/system flows.
            -   `dependencies`: Utilize libraries listed here where appropriate for the file's purpose.
        -   **JSON Specification (Requirements & Scope)**:
            -   `project_Overview.project_Purpose`, `project_Overview.product_Scope`: Understand the overall goals and boundaries.
            -   `functional_Requirements`: Ensure the code implements the specified features and actions. Pay attention to `acceptance_criteria`.
            -   `non_Functional_Requirements`: Adhere to quality attributes like security (e.g., input validation, auth checks if applicable to the file), usability, performance.
    3.  **Infer Role from Path**: Deduce the file's purpose from its path and the overall project structure (e.g., a backend model, a frontend UI component, a utility script, a configuration file).
    4.  **Completeness**: Generate all necessary imports, class/function definitions, and logic to make the file functional in its context. For UI components, include basic HTML structure and styling if applicable.
    5.  **Placeholder Comments**: If some complex logic is better handled by another file or is too extensive, you MAY include a clear comment like `// TODO: Implement [specific logic] here, interacting with [other component/module]` or `# TODO: ...`. However, strive for complete implementation where feasible.
    6.  **Technology Specifics**: Use idiomatic code and conventions for the specified technologies (e.g., FastAPI/SQLAlchemy for Python backend, React/VanillaJS for frontend).

    Here is the design file in JSON format:
    ```json
    {json.dumps(json_design, indent=2)}
    ```

    Here is the specification file in JSON format:
    ```json
    {json.dumps(json_spec, indent=2)}
    ```

    Now, generate the code for the file: `{file_path}`. Ensure it is complete and ready to be used in the project.
    """

    if API_CALL_DELAY_SECONDS > 0:
        logger.info(f"Waiting for {API_CALL_DELAY_SECONDS} seconds before API call for {os.path.basename(file_path)}...")
        time.sleep(API_CALL_DELAY_SECONDS)

    try:
        logger.info(f"Sending generation request to model {llm_model.model_name} for {os.path.basename(file_path)}.")
        response = llm_model.generate_content(prompt)
        generated_text = ""
        if hasattr(response, 'text'):
            generated_text = response.text
        elif hasattr(response, 'parts') and response.parts:
            generated_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
        else:
            logger.warning(f"Unexpected response structure from LLM for {file_path}. Full response: {response}")
            generated_text = str(response)

        generated_text = response.text.strip()
        if generated_text.startswith("```") and generated_text.endswith("```"):
            lines = generated_text.splitlines()
            if len(lines) > 1:
                if lines[0].startswith("```") and len(lines[0]) > 3:
                    generated_text = "\n".join(lines[1:-1]).strip()
                else:
                    generated_text = "\n".join(lines[1:-1]).strip()
            elif len(lines) == 1 :
                 generated_text = lines[0][3:-3].strip()
        if not generated_text:
            logger.warning(f"LLM returned empty content for {file_path}. The file will be empty.")
        logger.info(f"Code successfully generated by LLM for {os.path.basename(file_path)} ({len(generated_text)} chars).")
        return generated_text
    except Exception as e:
        logger.error(f"LLM API call or response processing failed for {file_path}: {e}")
        logger.debug(f"Prompt (first 500 chars) for {file_path}: {prompt[:500]}")
        raise

def write_code_to_file(file_path, code):
    logger.info(f"Writing code to file: {file_path}")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        logger.info(f"Successfully wrote {len(code)} characters to {file_path}")
    except OSError as e:
        logger.error(f"Failed to write to {file_path}: {e}")
        raise

def run_codegen_pipeline(json_design, json_spec, design_file_path, llm_model_instance): # Run the code generation pipeline: scaffold, create structure, and generate code.
    logger.info(f"Starting code generation pipeline for design file: {design_file_path} using model: {llm_model_instance.model_name}")
    try:
        plan = parse_json_and_generate_scaffold_plan(json_design, json_spec)
        create_project_structure(plan)
        total_files = len(plan["files_to_create"])
        logger.info(f"Attempting to generate code for {total_files} file(s).")
        for i, file_path in enumerate(plan["files_to_create"].keys()):
            code = generate_code_for_each_file(json_design, json_spec, file_path, plan["project_root_directory"], llm_model_instance)
            write_code_to_file(file_path, code)
        logger.info("Code generation pipeline completed.")
    except ValueError as e:
        logger.error(f"Input validation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Code generation pipeline failed: {e}")
        raise

if __name__ == "__main__":
    args = parser.parse_args()
    llm_for_codegen = None

    try:
        logger.info(f"Initializing LLM model for code generation: {args.model}")
        llm_for_codegen = GenerativeModel(args.model)
        logger.info(f"Successfully initialized LLM: {args.model}")

        logger.info(f"Loading design file: {args.design_file}")
        with open(args.design_file, 'r', encoding='utf-8') as f:
            json_design_data = json.load(f)
        
        logger.info(f"Loading specification file: {args.spec_file}")
        with open(args.spec_file, 'r', encoding='utf-8') as f:
            json_spec_data = json.load(f)
        
        # Validate compatibility (check metadata)
        design_meta_ts = json_design_data.get('metadata', {}).get('source_specification_timestamp')
        spec_meta_ts = json_spec_data.get('metadata', {}).get('timestamp')
        if design_meta_ts and spec_meta_ts and design_meta_ts != spec_meta_ts:
            logger.warning(
                f"Timestamp mismatch: Design's source_spec_timestamp ('{design_meta_ts}') "
                f"differs from Spec's timestamp ('{spec_meta_ts}'). Ensure they are compatible."
            )
        elif not design_meta_ts or not spec_meta_ts:
            logger.warning("Metadata timestamps for compatibility check are missing in one or both files.")
        
        run_codegen_pipeline(json_design_data, json_spec_data, args.design_file, llm_for_codegen)
        logger.info("Application generation process finished.")

    except FileNotFoundError as e:
        logger.error(f"Input file not found: {e}")
        print(f"Error: File not found - {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format in one of the input files: {e}")
        print(f"Error: Invalid JSON - {e}")
    except ValueError as e: # Catch validation errors or other ValueErrors
        logger.error(f"Configuration or Data Error: {e}")
        print(f"Error: {e}")
    except SystemExit as e: # Catch critical startup errors
        print(f"System Exit: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True) # exc_info=True logs stack trace
        print(f"An unexpected error occurred. Check codegen.log for details. Error: {e}")

# Run file in C:\Users\Hoang Duy\Documents\Phan Lac Hung\autocode_assistant> python src/module_3/agent.py <design.json> <spec.json> VD: python src/module_3/agent.py src/module_1_vs_2/outputs/task_management_app_20250516.design.json src/module_1_vs_2/outputs/task_management_app_20250516.spec.json