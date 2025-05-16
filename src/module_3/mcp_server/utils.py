import os
import json
from datetime import datetime
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SecurityError(Exception): # class này kế thừa Exception dùng để xử lý các lỗi liên quan đến bảo mật
    pass
    
# Kiểm tra đường dẫn file mà user và LLM đưa vào. Đảm bảo nó ko thoát khỏi thư mục gốc
def _resolve_and_validate_path(base_dir_str, relative_path_str):
    if not base_dir_str or not isinstance(base_dir_str, str):
        raise ValueError("Base directory path must be provided as a non-empty string.")
    if relative_path_str is None or not isinstance(relative_path_str, str):
         relative_path_str = "" 

    try:
        base_dir = Path(base_dir_str).resolve(strict=True) # strict=True đảm bảo base_dir tồn tại
        if not base_dir.is_dir():
             raise ValueError(f"Base directory path '{base_dir_str}' is not a valid directory.")

        # Resolving handles '..' components, symlinks etc.
        absolute_path = (base_dir / relative_path_str).resolve()

        # *** The Core Security Check ***
        # So sánh base_dir với absolute_path xem có khớp không.
        common_path = os.path.commonpath([str(base_dir), str(absolute_path)])

        if common_path != str(base_dir):
            logging.warning(f"Security Violation: Path '{relative_path_str}' resolved to '{absolute_path}', escaping base '{base_dir}'.")
            raise SecurityError(f"Path resolution outside allowed workspace: '{relative_path_str}'")

        return absolute_path

    except FileNotFoundError: # xảy ra khi strict=True mà không tìm thấy base_dir
        logging.error(f"Base directory not found: '{base_dir_str}'")
        raise ValueError(f"Base directory not found: '{base_dir_str}'")
    except SecurityError as se:
        raise se
    except Exception as e:
        # Các lỗi liên quan trong quá trình xử lý đường dẫn
        logging.error(f"Invalid path calculation for base='{base_dir_str}', relative='{relative_path_str}': {e}")
        raise ValueError(f"Invalid path '{relative_path_str}': {e}")

def save_data_to_json_file(data_to_save, base_dir_str, relative_filename):
    logging.info(f"Attempting to save data to '{relative_filename}' within base '{base_dir_str}'")
    try:
        target_path = _resolve_and_validate_path(base_dir_str, relative_filename) #validate target file
        target_path.parent.mkdir(parents=True, exist_ok=True) # create parent directories if they don't exist
        with open(target_path, 'w', encoding = 'utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        logging.info(f"Data saved successfully to '{target_path}'")
        return str(target_path)

    except (ValueError, SecurityError) as e:
        logging.error(f"Validation/Security Error saving data to '{relative_filename}': {e}")
        return {"status": "error", "message": str(e)}
    except OSError as e:
        logging.error(f"OS Error saving data to '{relative_filename}': {e}")
        return {"status": "error", "message": f"Could not save data to '{relative_filename}': {e}"}
    except TypeError as e:
        logging.error(f"Type Error saving JSON (data might not be serializable): {e}")
        return {"status": "error", "message": f"Data could not be serialized to JSON: {e}"}
    except Exception as e:
        logging.exception(f"Unexpected error saving data to '{relative_filename}': {e}")
        return {"status": "error", "message": "An unexpected server error occurred while saving the file."}

# can be removed later or can be used for demo later
def load_json_file(base_dir_str, relative_filepath):
    """Loads JSON data from a file securely within the base directory."""
    logging.info(f"Attempting to load JSON from '{relative_filepath}' within base '{base_dir_str}'")
    try:
        # 1. Validate the path
        target_path = _resolve_and_validate_path(base_dir_str, relative_filepath)

        # 2. Check if file exists (using validated path)
        if not target_path.is_file():
            logging.warning(f"JSON file not found for loading: {target_path}")
            return {"status": "error", "message": f"File not found: '{relative_filepath}'"}

        # 3. Read and parse the file
        with open(target_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logging.info(f"Successfully loaded JSON from: {target_path}")
        # Return the parsed data directly on success
        return data

    except (ValueError, SecurityError) as e:
        logging.error(f"Validation/Security Error loading file '{relative_filepath}': {e}")
        return {"status": "error", "message": str(e)}
    except OSError as e:
        logging.error(f"OS Error loading file '{relative_filepath}': {e}")
        return {"status": "error", "message": f"Could not read file '{relative_filepath}': {e}"}
    except json.JSONDecodeError as e:
         logging.error(f"JSON Decode Error loading file '{relative_filepath}': {e}")
         return {"status": "error", "message": f"Invalid JSON format in file '{relative_filepath}': {e}"}
    except Exception as e:
        logging.exception(f"Unexpected error loading file '{relative_filepath}': {e}")
        return {"status": "error", "message": "An unexpected server error occurred while loading the file."}
