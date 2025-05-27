import os
import json
from datetime import datetime
import re

def _get_base_output_dir():
    # Lấy đường dẫn tuyệt đối đến file script hiện tại
    current_file_path = os.path.abspath(__file__)
    # Lấy đường dẫn đến thư mục chứa file script đó
    current_file_dir = os.path.dirname(current_file_path)
    # Nối đường dẫn thư mục với tên thư mục 'outputs'
    output_dir = os.path.join(current_file_dir, "outputs")
    return output_dir

def get_filename(project_name=None, extension="json"):
    if project_name:
        clean_name = "".join(c if c.isalnum() else "_" for c in project_name).lower()
    else:
        clean_name = "specification"
    timestamp = datetime.now().strftime("%Y%m%d")
    return f"{clean_name}_{timestamp}.{extension}"

def save_data_to_json_file(data, filename=None):
    output_dir = _get_base_output_dir()
    if filename is None:
        project_name = data.get("project_name", "unnamed_project")
        filename = get_filename(project_name=project_name)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath

# can be removed later or can be used for demo later
def load_json_file(filepath):
    output_dir = _get_base_output_dir()
    filepath = os.path.join(output_dir, filename)
    if not os.path.exists(filepath):
        print(f"Error: File not found at {filepath}")
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

# can be removed later or can be used for demo later
def get_output_files():
    output_dir = _get_base_output_dir()
    if not os.path.exists(output_dir):
        return []
    files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(output_dir, x)), reverse=True)
    return files
