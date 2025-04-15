"""
This module contains utility functions used throughout the application.
"""

import os
import json
from datetime import datetime

def get_timestamp_filename(project_name=None, extension="json"):
    """
    Generate a timestamped filename based on the project name.
    
    Args:
        project_name (str, optional): The name of the project. Defaults to None.
        extension (str, optional): The file extension. Defaults to "json".
        
    Returns:
        str: A timestamped filename.
    """
    if project_name:
        clean_name = "".join(c if c.isalnum() else "_" for c in project_name).lower()
    else:
        clean_name = "specification"
    timestamp = datetime.now().strftime("%Y%m%d")
    return f"{clean_name}_{timestamp}.{extension}"

def save_to_json(data, filename=None):
    """
    Save data to a JSON file.
    
    Args:
        data (dict): The data to save.
        filename (str, optional): The filename to save to. If None, a filename will be generated.
        
    Returns:
        str: The path to the saved file.
    """
    if filename is None:
        project_name = data.get("project_name", "unnamed_project")
        filename = get_timestamp_filename(project_name=project_name)
    
    if not os.path.exists("outputs"):
        os.makedirs("outputs")
    
    filepath = os.path.join("outputs", filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filepath

def load_json_file(filepath):
    """
    Load data from a JSON file.
    
    Args:
        filepath (str): The path to the JSON file.
        
    Returns:
        dict: The loaded data.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_output_files():
    """
    Get a list of all JSON files in the outputs directory.
    
    Returns:
        list: A list of filenames, sorted by modification time (newest first).
    """
    if not os.path.exists("outputs"):
        return []
    
    files = [f for f in os.listdir("outputs") if f.endswith('.json')]
    files.sort(key=lambda x: os.path.getmtime(os.path.join("outputs", x)), reverse=True)
    
    return files
