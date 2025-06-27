import logging
import os
from typing import Dict, List
from langchain.tools import BaseTool
from langchain_core.messages import HumanMessage
import time
from .templates import TechnologyTemplateManager
from .error_tracker import ErrorTracker
from .coding_agent_config import AgentConfig

logger = logging.getLogger(__name__)

#Tool for generating individual files
class FileGeneratorTool(BaseTool):
    name: str = "file_generator"
    description: str = "Generates code for individual files based on specifications"
    
    def __init__(self, llm, template_manager: TechnologyTemplateManager, error_tracker: ErrorTracker, config: AgentConfig):
        super().__init__()
        self._llm = llm
        self._template_manager = template_manager
        self._error_tracker = error_tracker
        self._config = config
        
    #Generate code for a specific file with retry logic
    def _run(self, file_path: str, context: Dict, requirements: Dict) -> str:
        tech_stack = context.get('tech_stack', 'fastapi')
        project_root = context.get('project_root', '')
        relative_file_path = os.path.relpath(file_path, project_root).replace('\\', '/')
        
        # Handle special files
        if relative_file_path == 'requirements.txt':
            return self._template_manager.get_template(
                tech_stack, 'requirements',
                dependencies=context.get('design_data', {}).get('dependencies', {}).get('backend', [])
            )
        elif relative_file_path == '.env':
            return self._template_manager.get_template(
                tech_stack, 'env_file',
                storage_type=context.get('design_data', {}).get('data_Design', {}).get('storage_Type', 'sqlite')
            )
        
        # Generate code using LLM with retries
        for attempt in range(self._config.max_retries):
            try:
                prompt_template = self._template_manager.get_template(
                    tech_stack, 'prompt_template',
                    file_path=file_path,
                    project_name=requirements.get('project_Overview', {}).get('project_Name', 'this application'),
                    backend_language_framework=f"{requirements.get('technology_Stack', {}).get('backend', {}).get('language', 'Python')} {requirements.get('technology_Stack', {}).get('backend', {}).get('framework', 'FastAPI')}",
                    frontend_language_framework=f"{requirements.get('technology_Stack', {}).get('frontend', {}).get('language', 'HTML/CSS/JS')} {requirements.get('technology_Stack', {}).get('frontend', {}).get('framework', 'Vanilla')}",
                    storage_type=context.get('design_data', {}).get('data_Design', {}).get('storage_Type', 'sqlite'),
                    backend_module_path=context.get('backend_module_path', 'main'),
                    frontend_dir=context.get('frontend_dir', 'frontend'),
                    css_path=context.get('css_path', 'css/style.css'),
                    js_files_to_link=context.get('js_files_to_link', []),
                    json_design=context.get('design_data', {}),
                    json_spec=requirements
                )
                
                response = self._llm.invoke([HumanMessage(content=prompt_template)])
                generated_code = response.content.strip()
                
                # Clean up code blocks
                if generated_code.startswith("```") and generated_code.endswith("```"):
                    lines = generated_code.splitlines()
                    if len(lines) > 2:
                        generated_code = "\n".join(lines[1:-1])
                    else:
                        generated_code = ""
                
                if not generated_code:
                    raise ValueError("LLM returned empty code")
                
                # Basic syntax validation for Python files
                if file_path.endswith('.py'):
                    import ast
                    try:
                        ast.parse(generated_code)
                    except SyntaxError as e:
                        raise ValueError(f"Syntax error in generated Python code: {e}")
                
                return generated_code
                
            except Exception as e:
                self._error_tracker.add_error(
                    "code_generation", file_path, str(e),
                    {"context": context, "requirements": requirements, "attempt": attempt + 1}
                )
                if attempt == self._config.max_retries - 1:
                    return f"# Error generating code: {str(e)}\n# TODO: Fix this file"
                time.sleep(self._config.api_delay_seconds * (2 ** attempt))  # Exponential backoff
        
        return "# Error: Max retries reached"

#Tool for creating project structure
class ProjectStructureTool(BaseTool):
    name: str = "project_structure"
    description: str = "Creates the project directory structure"
    
    def __init__(self, error_tracker: ErrorTracker):
        super().__init__()
        self._error_tracker = error_tracker
    
    #Create project structure
    def _run(self, project_root: str, structure: List[Dict]) -> str:
        try:
            os.makedirs(project_root, exist_ok=True)
            created_items = []
            for item in structure:
                path = os.path.join(project_root, item['path'].strip('/\\'))
                description = item.get('description', '').lower()
                
                # Check if it's a directory based on description or if it ends with '/'
                is_directory = (
                    'directory' in description or 
                    item['path'].rstrip('/\\').endswith('/') or
                    item['path'].rstrip('/\\').endswith('\\') or
                    ('file' not in description and not os.path.splitext(path)[1] and not any(
                        special_file in os.path.basename(path).lower() 
                        for special_file in ['.gitignore', '.env', 'dockerfile', 'makefile', 'readme']
                    ))
                )
                
                if is_directory:
                    os.makedirs(path, exist_ok=True)
                    created_items.append(f"Directory: {path}")
                else:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write("")  # Create empty file
                    created_items.append(f"File: {path}")
            
            # Ensure logs directory
            logs_dir = os.path.join(project_root, 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            created_items.append(f"Directory: {logs_dir}")
            
            return f"Created {len(created_items)} items:\n" + "\n".join(created_items)
            
        except Exception as e:
            self._error_tracker.add_error(
                "structure_creation", project_root, str(e),
                {"structure": structure}
            )
            return f"Error creating structure: {str(e)}"

#Tool for validating generated project
class ProjectValidatorTool(BaseTool):
    name: str = "project_validator"
    description: str = "Validates the generated project for common issues"
    
    def __init__(self, error_tracker: ErrorTracker):
        super().__init__()
        self._error_tracker = error_tracker
    
    #Validate the generated project
    def _run(self, project_root: str, tech_stack: str) -> str:
        issues = []
        
        try:
            # Check for required files
            required_files = ['main.py', 'requirements.txt'] if tech_stack.lower() == 'fastapi' else ['index.js', 'package.json']
            for req_file in required_files:
                if not self._find_file(project_root, req_file):
                    issues.append(f"Missing required file: {req_file}")
            
            # Check for empty files
            for root, _, files in os.walk(project_root):
                for file in files:
                    if file.endswith(('.py', '.js', '.html', '.css')):
                        file_path = os.path.join(root, file)
                        if os.path.getsize(file_path) == 0:
                            issues.append(f"Empty file: {file_path}")
            
            # Check for non-ASCII characters in batch files
            for file in ['run.bat']:
                file_path = os.path.join(project_root, file)
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if any(ord(char) > 127 for char in content):
                            issues.append(f"Non-ASCII characters in {file}")
            
            # Log issues
            for issue in issues:
                self._error_tracker.add_error(
                    "validation", project_root, issue,
                    {"tech_stack": tech_stack}
                )
            
            if issues:
                return f"Found {len(issues)} validation issues:\n" + "\n".join(issues)
            return "Project validation passed successfully"
            
        except Exception as e:
            self._error_tracker.add_error(
                "validation_error", project_root, str(e)
            )
            return f"Validation error: {str(e)}"
    
    #Find if a file exists in the directory tree
    def _find_file(self, root_dir: str, filename: str) -> bool:
        for root, _, files in os.walk(root_dir):
            if filename in files:
                return True
        return False