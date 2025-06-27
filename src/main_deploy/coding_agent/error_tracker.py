import os
import json
import logging
import time
from typing import List, Dict

logger = logging.getLogger(__name__)

class ErrorTracker:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.errors = []
        self.error_file = os.path.join(project_root, "coder_errors.json")

    def add_error(self, error_type: str, file_path: str, error_message: str, context: dict = None):
        error_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "error_type": error_type,
            "file_path": file_path,
            "error_message": error_message,
            "context": context or {}
        }
        self.errors.append(error_entry)
        self._save_errors()

    def _save_errors(self):
        os.makedirs(os.path.dirname(self.error_file), exist_ok=True)
        try:
            with open(self.error_file, 'w', encoding='utf-8') as f:
                json.dump(self.errors, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save coder errors to {self.error_file}: {e}")
            
    def get_errors(self) -> List[Dict]:
        return self.errors