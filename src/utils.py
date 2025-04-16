import os
import json
from datetime import datetime

def get_filename(project_name=None, extension="json"):
    if project_name:
        clean_name = "".join(c if c.isalnum() else "_" for c in project_name).lower()
    else:
        clean_name = "specification"
    timestamp = datetime.now().strftime("%Y%m%d")
    return f"{clean_name}_{timestamp}.{extension}"

def save_data_to_json_file(data, filename=None):
    if filename is None:
        project_name = data.get("project_name", "unnamed_project")
        filename = get_filename(project_name=project_name)
    if not os.path.exists("outputs"):
        os.makedirs("outputs")
    filepath = os.path.join("outputs", filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath

# can be removed later or can be used for demo later
def load_json_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

# can be removed later or can be used for demo later
def get_output_files():
    if not os.path.exists("outputs"):
        return []
    files = [f for f in os.listdir("outputs") if f.endswith('.json')]
    files.sort(key=lambda x: os.path.getmtime(os.path.join("outputs", x)), reverse=True)
    return files
