# file định dạng các tools: create_file, read_file, list_files, create_directory, edit_file

from .config import get_gemini_model
from .prompts import SPECIFICATION_PROMPT

import os
from pathlib import Path
import logging
import json
from .models import SpecificationGenerator
from .utils import (_resolve_and_validate_path, SecurityError,
                   save_data_to_json_file, load_json_file, get_filename)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Khởi tạo generator
def get_spec_generator():
    return SpecificationGenerator()

spec_generator = get_spec_generator()

# Tool tạo file
def create_file(base_dir_str, relative_path_str, content):
    logging.info(f"Attempting to create file '{relative_path_str}' in base directory '{base_dir_str}'")
    try:
        target_path = _resolve_and_validate_path(base_dir_str, relative_path_str)
        target_path.parent.mkdir(parents=True, exist_ok=True) # tạo các thư mục cha nếu chưa tồn tại
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logging.info(f"File created successfully at {target_path}")
        return {"status": "success", "message": f"File '{relative_path_str}' created successfully."}

    except (ValueError, SecurityError) as e: # Lỗi liên quan đến bảo mật
        logging.error(f"Error creating file '{relative_path_str}': {e}")
        return {"status": "error", "message": str(e)}
    except OSError as e: # Lỗi liên quan đến OS
        logging.error(f"OS Error creating file '{relative_path_str}': {e}")
        return {"status": "error", "message": f"Could not create file '{relative_path_str}': {e}"}
    except Exception as e: #  Các lỗi khác
        logging.exception(f"Unexpected error creating file '{relative_path_str}': {e}")
        return {"status": "error", "message": "An unexpected server error occurred."}

# Tool đọc file
def read_file(base_dir_str, relative_path_str):
    logging.info(f"Attempting to read file '{relative_path_str}' in base '{base_dir_str}'")
    try:
        target_path = _resolve_and_validate_path(base_dir_str, relative_path_str)
        if not target_path.is_file():
            logging.warning(f"File not found for reading: {target_path}")
            return {"status": "error", "message": f"File not found: '{relative_path_str}'"}

        content = target_path.read_text(encoding='utf-8')
        logging.info(f"File read successfully: {target_path}")
        return {"status": "success", "content": content}

    except (ValueError, SecurityError) as e:
        logging.error(f"Error reading file '{relative_path_str}': {e}")
        return {"status": "error", "message": str(e)}
    except OSError as e:
        logging.error(f"OS Error reading file '{relative_path_str}': {e}")
        return {"status": "error", "message": f"Could not read file '{relative_path_str}': {e}"}
    except Exception as e:
        logging.exception(f"Unexpected error reading file '{relative_path_str}': {e}")
        return {"status": "error", "message": "An unexpected server error occurred."}

# Tool liệt kê các file
def list_files(base_dir_str, relative_path_str=""):
    logging.info(f"Attempting to list files in '{relative_path_str or '.'}' within base '{base_dir_str}'")
    try:
        target_dir_path = _resolve_and_validate_path(base_dir_str, relative_path_str)
        if not target_dir_path.is_dir():
            logging.warning(f"Directory not found for listing: {target_dir_path}")
            return {"status": "error", "message": f"Directory not found: '{relative_path_str}'"}

        items = []
        for item in target_dir_path.iterdir():
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file"
            })
        logging.info(f"Successfully listed directory contents: {target_dir_path}")
        return {"status": "success", "items": items}

    except (ValueError, SecurityError) as e:
        logging.error(f"Validation/Security Error listing files in '{relative_path_str}': {e}")
        return {"status": "error", "message": str(e)}
    except OSError as e:
        logging.error(f"OS Error listing files in '{relative_path_str}': {e}")
        return {"status": "error", "message": f"Could not list directory '{relative_path_str}': {e}"}
    except Exception as e:
        logging.exception(f"Unexpected error listing files in '{relative_path_str}': {e}")
        return {"status": "error", "message": "An unexpected server error occurred."}

# Tool tạo đường dẫn thư mục
def create_directory(base_dir_str, relative_path_str):
    logging.info(f"Attempting to create directory '{relative_path_str}' in base '{base_dir_str}'")
    if not relative_path_str: 
         return {"status": "error", "message": "Directory path cannot be empty."}
    try:
        target_path = _resolve_and_validate_path(base_dir_str, relative_path_str)
        target_path.mkdir(parents=True, exist_ok=True)

        logging.info(f"Successfully ensured directory exists: {target_path}")
        return {"status": "success", "message": f"Directory '{relative_path_str}' created or already exists."}

    except (ValueError, SecurityError) as e:
        logging.error(f"Validation/Security Error creating directory '{relative_path_str}': {e}")
        return {"status": "error", "message": str(e)}
    except OSError as e:
        logging.error(f"OS Error creating directory '{relative_path_str}': {e}")
        return {"status": "error", "message": f"Could not create directory '{relative_path_str}': {e}"}
    except Exception as e:
        logging.exception(f"Unexpected error creating directory '{relative_path_str}': {e}")
        return {"status": "error", "message": "An unexpected server error occurred."}

# Tool chỉnh sửa file (tạm thời không cần)
def edit_file(base_dir_str, relative_path_str, changes_description):
    logging.info(f"Attempting to edit file '{relative_path_str}' in base '{base_dir_str}' with changes: '{changes_description[:50]}...'")
    try:
        target_path = _resolve_and_validate_path(base_dir_str, relative_path_str)
        if not target_path.is_file():
            logging.warning(f"File not found for editing: {target_path}")
            return {"status": "error", "message": f"File not found: '{relative_path_str}'"}

        # Đổi toàn bộ content cũ bằng content mới chứ không phải sửa đổi(cần chỉnh sửa thêm)
        new_content = changes_description
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        logging.info(f"Successfully edited (overwritten) file: {target_path}")
        return {"status": "success", "message": f"File '{relative_path_str}' edited successfully."}

    except (ValueError, SecurityError) as e:
        logging.error(f"Validation/Security Error editing file '{relative_path_str}': {e}")
        return {"status": "error", "message": str(e)}
    except OSError as e:
        logging.error(f"OS Error editing file '{relative_path_str}': {e}")
        return {"status": "error", "message": f"Could not edit file '{relative_path_str}': {e}"}
    except Exception as e:
        logging.exception(f"Unexpected error editing file '{relative_path_str}': {e}")
        return {"status": "error", "message": "An unexpected server error occurred."}

# Tool sinh file specification
def execute_generate_specification_json(base_dir_str, project_description, output_filename_base=None):
    """Generates spec JSON, saves it, returns the path."""
    logging.info(f"[EXECUTION] Attempting to generate specification in '{base_dir_str}' based on description: '{project_description[:50]}...'")
    try:
        # --- Get a FRESH model instance HERE ---
        logging.info("[EXECUTION] Getting fresh model instance for this request...")
        fresh_model = get_gemini_model('gemini-2.0-flash') # Use the desired model name
        model_name_used = 'gemini-2.0-flash' # Store for metadata
        logging.info(f"[EXECUTION] Got fresh model: {fresh_model.model_name}")
        # -----------------------------------------

        # --- Use the FRESH model instance ---
        prompt_template_to_use = SPECIFICATION_PROMPT
        full_prompt = prompt_template_to_use.format(user_description=project_description)
        request_options = {"timeout": 180}

        logging.info("[EXECUTION] Calling generate_content with fresh model...")
        response = fresh_model.generate_content( # Call on fresh_model
            full_prompt,
            request_options=request_options
        )
        logging.info("[EXECUTION] Received response from fresh model.")
        # ------------------------------------

        # --- Process the response (borrow parser if needed) ---
        if not response.candidates or not hasattr(response.candidates,'content') or not response.candidates.content.parts:
             finish_reason = response.prompt_feedback.block_reason if hasattr(response, 'prompt_feedback') else 'Unknown'
             error_msg = f"Model response empty or blocked (using fresh model). Finish Reason: {finish_reason}"
             logging.error(error_msg)
             if hasattr(response, 'prompt_feedback') and response.prompt_feedback.safety_ratings:
                  logging.error(f"Safety Ratings: {response.prompt_feedback.safety_ratings}")
             # Return error directly
             return {"status": "error", "message": f"Model did not generate valid content. Reason: {finish_reason}"}

        # Borrow the parser method from the class if needed
        temp_parser = SpecificationGenerator() # Create temporary instance JUST for parser
        spec_data = temp_parser._parse_json_response(response.text)
        # ------------------------------------------------------

        if spec_data is None or not isinstance(spec_data, dict):
            logging.error("Specification generation failed or returned invalid data (after parsing).")
            # Use the parsing error if available from ValueError? No, parser raises now.
            return {"status": "error", "message": "Failed to parse valid specification data from the model's response."}

        # Add Metadata (using model_name_used)
        project_name = output_filename_base or spec_data.get("project_Overview", {}).get("project_Name")
        if "project_Overview" not in spec_data: spec_data["project_Overview"] = {}
        if "project_Name" not in spec_data["project_Overview"]: spec_data["project_Overview"]["project_Name"] = project_name or "unnamed_project"

        spec_data["metadata"] = {
            "generation_step": "specification",
            "timestamp": datetime.now().isoformat(),
            "model_used": model_name_used, # Use the name of the fresh model
            "original_description": project_description
        }

        # --- Save the file ---
        relative_filename = get_filename(project_name=project_name, extension="spec.json")
        save_result = save_data_to_json_file(spec_data, base_dir_str, relative_filename)

        if isinstance(save_result, dict) and save_result.get("status") == "error":
             logging.error(f"Failed to save specification file: {save_result.get('message')}")
             return save_result
        elif isinstance(save_result, str):
             logging.info(f"Successfully generated and saved specification (using fresh model): {save_result}")
             return {"status": "success", "message": f"Specification generated and saved.", "filepath": relative_filename}
        else:
             logging.error(f"Unexpected result from save_data_to_json_file: {save_result}")
             return {"status": "error", "message": "Failed to save specification file due to an internal error."}

    except ValueError as e: # Catch parsing errors, bad input errors, etc.
         logging.error(f"[EXECUTION] ValueError: {e}")
         return {"status": "error", "message": f"Error during specification generation: {e}"}
    except RuntimeError as e: # Catch unexpected model communication errors
         logging.error(f"[EXECUTION] RuntimeError: {e}")
         return {"status": "error", "message": f"Runtime error during model communication: {e}"}
    except (SecurityError) as e: # Catch potential errors from file saving utils
         logging.error(f"[EXECUTION] Security Error saving spec file: {e}")
         return {"status": "error", "message": str(e)}
    except Exception as e: # Catch any other unexpected errors
        logging.exception(f"[EXECUTION] Unexpected error generating specification JSON: {e}")
        return {"status": "error", "message": f"An unexpected server error occurred during specification generation: {e}"}

# Tool sinh file design
def execute_generate_design_json(base_dir_str, spec_file_path):
    logging.info(f"Attempting to generate design in '{base_dir_str}' based on spec file: '{spec_file_path}'")
    try:
        load_result = load_json_file(base_dir_str, spec_file_path)
        if isinstance(load_result, dict) and load_result.get("status") == "error":
            logging.error(f"Failed to load spec file: {load_result.get('message')}")
            return load_result
        elif not isinstance(load_result, dict):
             logging.error(f"Loaded spec data is not a dictionary or load failed. Path: {spec_file_path}")
             return {"status": "error", "message": f"Could not load or parse specification data from '{spec_file_path}'."}

        spec_data = load_result
        design_data = spec_generator.generate_design(spec_data)
        if design_data is None or not isinstance(design_data, dict):
            logging.error("Design generation failed or returned invalid data.")
            return {"status": "error", "message": "Failed to generate valid design data from the model."}
        
        project_name = spec_data.get("project_Overview", {}).get("project_Name")
        relative_filename = get_filename(project_name=project_name, extension="design.json")

        save_result = save_data_to_json_file(design_data, base_dir_str, relative_filename)
        if isinstance(save_result, dict) and save_result.get("status") == "error":
             logging.error(f"Failed to save design file: {save_result.get('message')}")
             return save_result
        elif isinstance(save_result, str): # Assuming returns full path
             logging.info(f"Successfully generated and saved design: {save_result}")
             return {"status": "success", "message": f"Design generated and saved.", "filepath": relative_filename}
        else:
             logging.error(f"Unexpected result from save_data_to_json_file for design: {save_result}")
             return {"status": "error", "message": "Failed to save design file due to an internal error."}
    
    except ValueError as e:
        logging.error(f"Security Error loading/saving design file: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logging.exception(f"Unexpected error generating design JSON: {e}")
        return {"status": "error", "message": f"An unexpected server error occurred during design generation: {e}"}