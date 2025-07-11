import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional
import config

logger = logging.getLogger(__name__)

def get_spec_design_output_dir():
    output_dir = config.SPEC_DESIGN_OUTPUT_DIR
    if not output_dir:
        raise ValueError("SPEC_DESIGN_OUTPUT_DIR is not set in the configuration. Please check the .env")

    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        logger.error(f"Could not create spec/design output directory at '{output_dir}': {e}")
        raise
    return output_dir

def generate_filename(project_name: str, extension: str) -> str:
    clean_name = "".join(c if c.isalnum() else "_" for c in project_name).lower()
    timestamp = datetime.now().strftime("%Y%m%d")
    if not extension.startswith('.'):
        extension = '.' + extension
    return f"{clean_name}_{timestamp}{extension}"

def save_json_to_file(data: dict, file_path: str) -> bool:
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Data successfully saved to {file_path}")
        return True
    except (TypeError, OSError) as e:
        logger.error(f"Failed to save JSON to '{file_path}': {e}", exc_info=True)
        return False
    
def parse_json_response(response_text: str) -> dict:
    try:
        if "```json" in response_text:
            # Extract content between ```json and ```
            json_text = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
        # Check if the whole response is a JSON object
        elif response_text.strip().startswith('{') and response_text.strip().endswith('}'):
            json_text = response_text.strip()
        else:
            logger.warning("Response is not a clean JSON block or object. Attempting direct parse.")
            json_text = response_text
            
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}\nRaw response: {response_text[:500]}...")
        raise ValueError(f"Failed to parse JSON response: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while parsing JSON: {e}\nRaw response: {response_text}", exc_info=True)
        raise

def find_latest_json_files(project_name: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Finds the latest design and specification JSON files, optionally for a specific project.

    This function searches in the directory defined by config.SPEC_DESIGN_OUTPUT_DIR.

    Args:
        project_name (Optional[str]): If provided, finds the latest files matching
                                      this project name. If None, finds the overall
                                      latest files in the directory.

    Returns:
        A tuple containing the paths to the (latest_design_file, latest_spec_file).
        Returns (None, None) if files are not found.
    """
    output_dir = Path(config.SPEC_DESIGN_OUTPUT_DIR)
    
    if not output_dir.exists():
        logger.error(f"Spec/Design output directory '{output_dir}' does not exist. Cannot find files.")
        return None, None
    
    if project_name:
        # Sanitize the project name to match the file naming convention
        search_prefix = "".join(c if c.isalnum() else "_" for c in project_name).lower()
        spec_files = list(output_dir.glob(f'{search_prefix}*.spec.json'))
        design_files = list(output_dir.glob(f'{search_prefix}*.design.json'))
    else:
        # Find all spec and design files
        spec_files = list(output_dir.glob('*.spec.json'))
        design_files = list(output_dir.glob('*.design.json'))

    latest_spec_path = None
    latest_design_path = None

    if spec_files:
        latest_spec_path = str(max(spec_files, key=lambda p: p.stat().st_mtime))
        logger.info(f"Found latest spec file: {latest_spec_path}")
    else:
        logger.warning(f"No .spec.json files found for project '{project_name or 'any'}'.")

    if design_files:
        latest_design_path = str(max(design_files, key=lambda p: p.stat().st_mtime))
        logger.info(f"Found latest design file: {latest_design_path}")
    else:
        logger.warning(f"No .design.json files found for project '{project_name or 'any'}'.")

    return latest_design_path, latest_spec_path

# # Get the absolute path to the outputs directory.
# def get_base_output_dir():
#     current_file_path = os.path.abspath(__file__)
#     current_file_dir = os.path.dirname(current_file_path)
#     project_root = os.path.dirname(os.path.dirname(current_file_dir))  # Go up two levels from main_deploy
#     output_dir = os.path.join(project_root, "outputs")
#     return output_dir
# # Generate a filename with project name and timestamp.
# def get_filename(project_name: str = None, extension: str = "json") -> str:
#     clean_name = (
#         "".join(c if c.isalnum() else "_" for c in project_name).lower()
#         if project_name
#         else "specification"
#     )
#     timestamp = datetime.now().strftime("%Y%m%d")
#     return f"{clean_name}_{timestamp}.{extension}"

# def save_data_to_json_file(data: dict, filename: str = None) -> str:
#     output_dir = get_base_output_dir()
#     if filename is None:
#         project_name = data.get("project_Overview", {}).get("project_Name", "unnamed_project")
#         filename = get_filename(project_name=project_name)
#     if not os.path.exists(output_dir):
#         os.makedirs(output_dir)
#     filepath = os.path.join(output_dir, filename)
#     with open(filepath, 'w', encoding='utf-8') as f:
#         json.dump(data, f, ensure_ascii=False, indent=2)
#     return filepath

# #Parse a JSON response from the model.
# def parse_json_response(response_text: str) -> dict:
#     try:
#         if "```json" in response_text:
#             json_text = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
#         elif response_text.strip().startswith('{') and response_text.strip().endswith('}'):
#             json_text = response_text.strip()
#         else:
#             logger.warning("Response is not a JSON block or object. Attempting direct parse.")
#             json_text = response_text
#         return json.loads(json_text)
#     except json.JSONDecodeError as e:
#         logger.error(f"JSON parsing error: {e}\nRaw response: {response_text[:500]}...")
#         raise ValueError(f"Failed to parse JSON response: {e}")
#     except Exception as e:
#         logger.error(f"Unexpected error parsing JSON: {e}\nRaw response: {response_text}")
#         raise