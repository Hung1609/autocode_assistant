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