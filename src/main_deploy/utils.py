import os
import json
import logging
from datetime import datetime
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_base_output_dir():
    """Get the absolute path to the outputs directory."""
    current_file_path = os.path.abspath(__file__)
    current_file_dir = os.path.dirname(current_file_path)
    output_dir = os.path.join(current_file_dir, "outputs")
    return output_dir

def get_filename(project_name: str = None, extension: str = "json") -> str:
    """Generate a filename with project name and timestamp."""
    clean_name = (
        "".join(c if c.isalnum() else "_" for c in project_name).lower()
        if project_name
        else "specification"
    )
    timestamp = datetime.now().strftime("%Y%m%d")
    return f"{clean_name}_{timestamp}.{extension}"

def save_data_to_json_file(data: dict, filename: str = None) -> str:
    """Save data to a JSON file in the outputs directory."""
    output_dir = get_base_output_dir()
    if filename is None:
        project_name = data.get("project_Overview", {}).get("project_Name", "unnamed_project")
        filename = get_filename(project_name=project_name)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath

def parse_json_response(response_text: str) -> dict:
    """Parse a JSON response from the model."""
    try:
        if "```json" in response_text:
            json_text = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif response_text.strip().startswith('{') and response_text.strip().endswith('}'):
            json_text = response_text.strip()
        else:
            logger.warning("Response is not a JSON block or object. Attempting direct parse.")
            json_text = response_text
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}\nRaw response: {response_text[:500]}...")
        raise ValueError(f"Failed to parse JSON response: {e}")
    except Exception as e:
        logger.error(f"Unexpected error parsing JSON: {e}\nRaw response: {response_text}")
        raise