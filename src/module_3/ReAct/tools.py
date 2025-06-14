from langchain_core.tools import BaseTool
import json
import os
import subprocess
from typing import Dict

class ReadDesignFileTool(BaseTool):
    name: str = "read_design_file"
    description: str = "Reads the .design.json file to extract folder structure information."
    
    def _run(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.dumps(json.load(f))
        except Exception as e:
            return f"Error reading design file: {str(e)}"
        
class ReadSpecFileTool(BaseTool):
    name: str = "read_spec_file"
    description: str = "Reads the .spec.json file to extract technology stack and file specifications."
    
    def _run(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.dumps(json.load(f))
        except Exception as e:
            return f"Error reading spec file: {str(e)}"
        
class ExecuteRunScriptTool(BaseTool):
    name: str = "execute_run_script"
    description: str = "Executes the run.bat script in the project root."
    
    def _run(self, project_root: str) -> str:
        script_path = os.path.abspath(os.path.join(project_root, 'run.bat'))
        try:
            result = subprocess.run(
                f'"{script_path}"',
                shell=True,
                check=True,
                cwd=project_root,
                capture_output=True,
                text=True
            )
            return f"Run script executed: {result.stdout}"
        except subprocess.CalledProcessError as e:
            return f"Run script failed: Exit code: {e.returncode}\nStdout: {e.stdout}\nStderr: {e.stderr}"
        except Exception as e:
            return f"Error executing run script: {str(e)}"