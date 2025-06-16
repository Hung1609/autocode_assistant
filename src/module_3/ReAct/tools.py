import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

class ReadFileInput(BaseModel):
    file_path: str = Field(description="Path to the file to read")

class ReadFileTool(BaseTool):
    name: str = "read_file"
    description: str = "Reads the content of a specified file. Use this to get information from design.json or spec.json."
    args_schema: Type[BaseModel] = ReadFileInput
    
    def _run(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return f"Error: File '{file_path}' not found."
        except PermissionError:
            return f"Error: Permission denied accessing '{file_path}'."
        except Exception as e:
            return f"Error reading file '{file_path}': {str(e)}"

class ReadDesignFileTool(ReadFileTool):
    name: str = "read_design_file"
    description: str = "Reads the .design.json file to extract folder structure information."
    
    def _run(self, file_path: str) -> str:
        if not file_path.endswith('.design.json'):
            return "Error: This tool is specifically for .design.json files."
        return super()._run(file_path)

class ReadSpecFileTool(ReadFileTool):
    name: str = "read_spec_file"
    description: str = "Reads the .spec.json file to extract technology stack and file specifications."
    
    def _run(self, file_path: str) -> str:
        if not file_path.endswith('.spec.json'):
            return "Error: This tool is specifically for .spec.json files."
        return super()._run(file_path)
        
class CreateRunScriptInput(BaseModel):
    project_root: str = Field(description="Root directory of the project")
    design_data: Dict = Field(description="Design data from .design.json file")
    spec_data: Dict = Field(description="Specification data from .spec.json file")

class CreateRunScriptTool(BaseTool):
    name: str = "create_run_script"
    description: str = "Creates the run.bat script file in the project root."
    args_schema: Type[BaseModel] = CreateRunScriptInput
    
    # For Pydantic v2 compatibility
    template_manager: Any = None
    config: Any = None
    
    model_config = {"arbitrary_types_allowed": True}
    
    def __init__(self, template_manager: Any = None, config: Any = None, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'template_manager', template_manager)
        object.__setattr__(self, 'config', config)

    def _run(self, project_root: str, design_data: Dict, spec_data: Dict) -> str:
        if not self.template_manager or not self.config:
            return "Error: template_manager and config must be provided during tool initialization."
            
        try:
            tech_stack = spec_data.get('technology_Stack', {}).get('backend', {}).get('framework', 'fastapi')
            
            # Find backend module using cross-platform path handling
            backend_module_path = 'main'
            for item in design_data.get('folder_Structure', {}).get('structure', []):
                if item.get('path', '').endswith('main.py'):
                    # Use Path for cross-platform path handling
                    path_obj = Path(item['path'])
                    path_parts = path_obj.parts
                    if len(path_parts) > 1:
                        # Remove the 'main.py' part and join with dots
                        backend_module_path = '.'.join(path_parts[:-1]) + '.main'
                    else:
                        backend_module_path = 'main'
                    break

            script_content = self.template_manager.get_template(
                tech_stack, 'run_script',
                python_path=self.config.python_path,
                backend_module_path=backend_module_path
            )
            
            script_path = Path(project_root) / 'run.bat'
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            return f"Successfully created run.bat at {script_path}"
        except AttributeError as e:
            return f"Error: Missing required attribute - {e}"
        except Exception as e:
            return f"Error creating run script: {e}"
        
class ExecuteRunScriptInput(BaseModel):
    project_root: str = Field(description="Root directory of the project containing run.bat")

class ExecuteRunScriptTool(BaseTool):
    name: str = "execute_run_script"
    description: str = "Executes the run.bat script in the project root. This should be the last action."
    args_schema: Type[BaseModel] = ExecuteRunScriptInput
    
    def _run(self, project_root: str) -> str:
        script_path = Path(project_root).resolve() / 'run.bat'
        if not script_path.exists():
            return "Error: run.bat not found. Please create it first using 'create_run_script'."
        try:
            result = subprocess.run(
                f'"{script_path}"',
                shell=True,
                check=True,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            output = f"Run script executed successfully. Stdout:\n{result.stdout}"
            if result.stderr:
                output += f"\nStderr:\n{result.stderr}"
            return output
        except subprocess.CalledProcessError as e:
            return f"Run script failed: Exit code: {e.returncode}\nStdout: {e.stdout}\nStderr: {e.stderr}"
        except subprocess.TimeoutExpired:
            return "Run script timed out after 120 seconds."
        except Exception as e:
            return f"Error executing run script: {str(e)}"