# This file initializes the tools for file system operations, including create_file, read_file, list_files, create_directory, edit_file


import os
from pathlib import Path
import logging

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
