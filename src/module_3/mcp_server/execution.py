# This file initializes the tools for file system operations, including create_file, read_file, list_files, create_directory, edit_file


import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ERROR_TYPE_SECURITY = "SECURITY_VIOLATION"
ERROR_TYPE_NOT_FOUND = "NOT_FOUND"
ERROR_TYPE_INVALID_INPUT = "INVALID_INPUT"
ERROR_TYPE_OS_ERROR = "OS_ERROR"
ERROR_TYPE_UNEXPECTED = "UNEXPECTED_SERVER_ERROR"

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
        # So sánh base_dir với absolute_path xem có khớp không.
        absolute_path = (base_dir / relative_path_str).resolve()
        common_path = os.path.commonpath([str(base_dir), str(absolute_path)])

        if common_path != str(base_dir):
            raise SecurityError(f"Path resolution outside allowed workspace: '{relative_path_str}'")
        return absolute_path

    except FileNotFoundError: # xảy ra khi strict=True mà không tìm thấy base_dir
        raise ValueError(f"Base directory not found: '{base_dir_str}'")
    except SecurityError as se:
        raise se
    except Exception as e:
        raise ValueError(f"Invalid path '{relative_path_str}': {e}")

# Tool tạo file
def create_file(base_dir_str, relative_path_str, content):
    logger.info(f"Attempting to create file '{relative_path_str}' in base directory '{base_dir_str}'")
    try:
        if relative_path_str == "":
            logger.warning("create_file: File path cannot be empty (attempting to create at workspace root).")
            return {"status": "error", "error_type": ERROR_TYPE_INVALID_INPUT, "message": "File path cannot be empty."}
        target_path = _resolve_and_validate_path(base_dir_str, relative_path_str)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"File created successfully at {target_path}")
        return {"status": "success", "message": f"File '{relative_path_str}' created successfully."}

    except ValueError as e:
        logger.error(f"Input/Validation Error creating file '{relative_path_str}': {e}")
        if "Base directory not found" in str(e) or "is not a valid directory" in str(e):
            return {"status": "error", "error_type": ERROR_TYPE_NOT_FOUND, "message": str(e)}
        return {"status": "error", "error_type": ERROR_TYPE_INVALID_INPUT, "message": str(e)}
    except SecurityError as e:
        logger.error(f"Security Error creating file '{relative_path_str}': {e}")
        return {"status": "error", "error_type": ERROR_TYPE_SECURITY, "message": str(e)}
    except OSError as e:
        logger.error(f"OS Error creating file '{relative_path_str}': {e}")
        return {"status": "error", "error_type": ERROR_TYPE_OS_ERROR, "message": f"Could not create file '{relative_path_str}': {e.strerror}"}
    except Exception as e:
        logger.exception(f"Unexpected error creating file '{relative_path_str}': {e}")
        return {"status": "error", "error_type": ERROR_TYPE_UNEXPECTED, "message": "An unexpected server error occurred."}

# Tool đọc file
def read_file(base_dir_str, relative_path_str):
    logger.info(f"Attempting to read file '{relative_path_str}' in base '{base_dir_str}'")
    try:
        if relative_path_str == "":
            logger.warning("read_file: File path cannot be empty (attempting to read from workspace root).")
            return {"status": "error", "error_type": ERROR_TYPE_INVALID_INPUT, "message": "File path cannot be empty."}
        target_path = _resolve_and_validate_path(base_dir_str, relative_path_str)
        if not target_path.is_file():
            logger.warning(f"File not found for reading: {target_path}")
            return {"status": "error", "error_type": ERROR_TYPE_NOT_FOUND, "message": f"File not found: '{relative_path_str}'"}

        content = target_path.read_text(encoding='utf-8')
        logger.info(f"File read successfully: {target_path}")
        return {"status": "success", "content": content}

    except ValueError as e: 
        logger.error(f"Input/Validation Error reading file '{relative_path_str}': {e}")
        if "Base directory not found" in str(e) or "is not a valid directory" in str(e):
            return {"status": "error", "error_type": ERROR_TYPE_NOT_FOUND, "message": str(e)}
        return {"status": "error", "error_type": ERROR_TYPE_INVALID_INPUT, "message": str(e)}
    except SecurityError as e:
        logger.error(f"Security Error reading file '{relative_path_str}': {e}")
        return {"status": "error", "error_type": ERROR_TYPE_SECURITY, "message": str(e)}
    except OSError as e:
        logger.error(f"OS Error reading file '{relative_path_str}': {e}")
        return {"status": "error", "error_type": ERROR_TYPE_OS_ERROR, "message": f"Could not read file '{relative_path_str}': {e.strerror}"}
    except Exception as e:
        logger.exception(f"Unexpected error reading file '{relative_path_str}': {e}")
        return {"status": "error", "error_type": ERROR_TYPE_UNEXPECTED, "message": "An unexpected server error occurred."}

# Tool liệt kê các file
def list_files(base_dir_str, relative_path_str=""):
    logger.info(f"Attempting to list files in '{relative_path_str or '<root>'}' within base '{base_dir_str}'")
    try:
        target_dir_path = _resolve_and_validate_path(base_dir_str, relative_path_str)
        if not target_dir_path.is_dir():
            logger.warning(f"Directory not found for listing: {target_dir_path}")
            if relative_path_str:
                return {"status": "error", "error_type": ERROR_TYPE_NOT_FOUND, "message": f"Directory not found: '{relative_path_str}'"}
            return {"status": "error", "error_type": ERROR_TYPE_INVALID_INPUT, "message": f"Specified path is not a directory: '{relative_path_str}'"}

        items = []
        for item in target_dir_path.iterdir():
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file"
            })
        logging.info(f"Successfully listed directory contents: {target_dir_path}")
        return {"status": "success", "items": items}

    except ValueError as e:
        logger.error(f"Input/Validation Error listing files in '{relative_path_str}': {e}")
        if "Base directory not found" in str(e) or "is not a valid directory" in str(e):
            return {"status": "error", "error_type": ERROR_TYPE_NOT_FOUND, "message": str(e)}
        return {"status": "error", "error_type": ERROR_TYPE_INVALID_INPUT, "message": str(e)}
    except SecurityError as e:
        logger.error(f"Security Error listing files in '{relative_path_str}': {e}")
        return {"status": "error", "error_type": ERROR_TYPE_SECURITY, "message": str(e)}
    except OSError as e:
        logger.error(f"OS Error listing files in '{relative_path_str}': {e}")
        return {"status": "error", "error_type": ERROR_TYPE_OS_ERROR, "message": f"Could not list directory '{relative_path_str}': {e.strerror}"}
    except Exception as e:
        logger.exception(f"Unexpected error listing files in '{relative_path_str}': {e}")
        return {"status": "error", "error_type": ERROR_TYPE_UNEXPECTED, "message": "An unexpected server error occurred."}

# Tool tạo đường dẫn thư mục
def create_directory(base_dir_str, relative_path_str):
    logger.info(f"Attempting to create directory '{relative_path_str}' in base '{base_dir_str}'")
    if not relative_path_str:
        logger.warning("create_directory: Directory path cannot be empty.")
        return {"status": "error", "error_type": ERROR_TYPE_INVALID_INPUT, "message": "Directory path cannot be empty."}
    try:
        target_path = _resolve_and_validate_path(base_dir_str, relative_path_str)
        target_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Successfully ensured directory exists: {target_path}")
        return {"status": "success", "message": f"Directory '{relative_path_str}' created or already exists."}

    except ValueError as e:
        logger.error(f"Input/Validation Error creating directory '{relative_path_str}': {e}")
        if "Base directory not found" in str(e) or "is not a valid directory" in str(e):
            return {"status": "error", "error_type": ERROR_TYPE_NOT_FOUND, "message": str(e)}
        return {"status": "error", "error_type": ERROR_TYPE_INVALID_INPUT, "message": str(e)}
    except SecurityError as e:
        logger.error(f"Security Error creating directory '{relative_path_str}': {e}")
        return {"status": "error", "error_type": ERROR_TYPE_SECURITY, "message": str(e)}
    except OSError as e:
        logger.error(f"OS Error creating directory '{relative_path_str}': {e}")
        return {"status": "error", "error_type": ERROR_TYPE_OS_ERROR, "message": f"Could not create directory '{relative_path_str}': {e.strerror}"}
    except Exception as e:
        logger.exception(f"Unexpected error creating directory '{relative_path_str}': {e}")
        return {"status": "error", "error_type": ERROR_TYPE_UNEXPECTED, "message": "An unexpected server error occurred."}

# Tool chỉnh sửa file (tạm thời không cần)
def edit_file(base_dir_str, relative_path_str, changes_description):
    logger.info(f"Attempting to edit file '{relative_path_str}' in base '{base_dir_str}'")
    try:
        if relative_path_str == "":
            logger.warning("edit_file: File path cannot be empty.")
            return {"status": "error", "error_type": ERROR_TYPE_INVALID_INPUT, "message": "File path cannot be empty."}
        target_path = _resolve_and_validate_path(base_dir_str, relative_path_str)
        if not target_path.is_file():
            logger.warning(f"File not found for editing: {target_path}")
            return {"status": "error", "error_type": ERROR_TYPE_NOT_FOUND, "message": f"File not found: '{relative_path_str}'"}
        new_content = changes_description
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        logger.info(f"Successfully edited (overwritten) file: {target_path}")
        return {"status": "success", "message": f"File '{relative_path_str}' edited successfully."}

    except ValueError as e:
        logger.error(f"Input/Validation Error editing file '{relative_path_str}': {e}")
        if "Base directory not found" in str(e) or "is not a valid directory" in str(e):
            return {"status": "error", "error_type": ERROR_TYPE_NOT_FOUND, "message": str(e)}
        return {"status": "error", "error_type": ERROR_TYPE_INVALID_INPUT, "message": str(e)}
    except SecurityError as e:
        logger.error(f"Security Error editing file '{relative_path_str}': {e}")
        return {"status": "error", "error_type": ERROR_TYPE_SECURITY, "message": str(e)}
    except OSError as e:
        logger.error(f"OS Error editing file '{relative_path_str}': {e}")
        return {"status": "error", "error_type": ERROR_TYPE_OS_ERROR, "message": f"Could not edit file '{relative_path_str}': {e.strerror}"}
    except Exception as e:
        logger.exception(f"Unexpected error editing file '{relative_path_str}': {e}")
        return {"status": "error", "error_type": ERROR_TYPE_UNEXPECTED, "message": "An unexpected server error occurred."}
