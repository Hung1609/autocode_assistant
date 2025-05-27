import os
import json
from datetime import datetime

def get_filename(project_name=None, extension="json"):
    if project_name:
        clean_name = "".join(c if c.isalnum() else "_" for c in project_name).lower()
    else:
        clean_name = "specification"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{clean_name}_{timestamp}.{extension}"

def save_data_to_json_file(data, filename=None, directory="outputs"):
    if filename is None:
        project_name = data.get("project_Overview", {}).get("project_Name", "unnamed_project")
        filename = get_filename(project_name=project_name, extension=filename.split(".")[-1] if filename else "json")
    
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    filepath = os.path.join(directory, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filepath

def load_json_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)