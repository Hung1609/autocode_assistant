import os
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from .. import config
from .coding_agent_config import AgentConfig
from .error_tracker import ErrorTracker
from .templates import TechnologyTemplateManager
from .tools import ProjectStructureTool, FileGeneratorTool, ProjectValidatorTool

logger = logging.getLogger(__name__)
 
 #The main coding agent responsible for generating a complete software project from design and specification data
class LangChainCodingAgent:
    def __init__(self, agent_config: AgentConfig):
        self.config = agent_config
        self.template_manager = TechnologyTemplateManager()
        self.error_tracker = None  # Initialized per-project in generate_project
        
        logger.info(f"LangChainCodingAgent initialized with model: {self.config.model_name}")
        
        self.llm = ChatGoogleGenerativeAI(
            model=self.config.model_name,
            google_api_key=config.GEMINI_API_KEY,
            temperature=0.1,
            convert_system_message_to_human=True
        )
        self.tools = []

    #Initializes tools for a specific project run.
    def _setup_project_tools(self, project_root: str):
        self.error_tracker = ErrorTracker(project_root)
        self.tools = [
            ProjectStructureTool(self.error_tracker),
            FileGeneratorTool(self.llm, self.template_manager, self.error_tracker, self.config),
            ProjectValidatorTool(self.error_tracker)
        ]
        logger.debug("Coding agent tools initialized for new project.")

    #Generates a complete project from design and specification dictionaries.
    def generate_project(self, design_data: dict, spec_data: dict) -> str:
        project_name = None
        try:
            # 1. Determine project root and initialize tools/error tracker for this run
            project_name = design_data.get('folder_Structure', {}).get('root_Project_Directory_Name')
            if not project_name:
                raise ValueError("Design data is missing 'root_Project_Directory_Name'.")
            
            project_root = os.path.abspath(os.path.join(self.config.base_output_dir, project_name))
            self._setup_project_tools(project_root)
            
            logger.info(f"Starting project generation for: {project_name} at {project_root}")
            
            # 2. Validate JSON inputs
            self._validate_json(design_data, spec_data)
            logger.info("JSON inputs validated successfully.")

            # 3. Create project structure
            structure_result = self._create_project_structure(design_data, project_root)
            logger.info(f"Structure creation result: {structure_result}")
            
            # 4. Generate all project files
            files_result = self._generate_project_files(design_data, spec_data, project_root)
            logger.info(f"File generation result: {files_result}")
            
            # 5. Create the run script to start the application
            self._create_run_script(project_root, spec_data, design_data)
            logger.info(f"Created run script for project '{project_name}'.")
            
            logger.info(f"Project generation completed successfully for: {project_root}")
            
            # This success message is what the AutoGen Coder will report back to the ProjectManager.
            return f"Successfully generated project '{project_name}' at {project_root}. The 'run.bat' script is ready."

        except Exception as e:
            error_project_name = project_name or "unknown_project"
            logger.error(f"Project generation failed for '{error_project_name}': {e}", exc_info=True)
            if self.error_tracker:
                self.error_tracker.add_error("project_generation_fatal", error_project_name, str(e))
            # Re-raise the exception so the orchestrator (AutoGen) knows something went wrong.
            raise

    # --- Helper Methods ---
    # Validate JSON design and specification files
    def _validate_json(self, design_data: dict, spec_data: dict):
        required_design_fields = ['folder_Structure', 'data_Design', 'interface_Design', 'dependencies']
        for field in required_design_fields:
            if field not in design_data:
                self.error_tracker.add_error("validation", "design.json", f"Missing field: {field}")
                raise ValueError(f"JSON design must contain '{field}'")
        
        folder_structure = design_data.get('folder_Structure', {})
        if not folder_structure.get('root_Project_Directory_Name') or not folder_structure.get('structure'):
            self.error_tracker.add_error("validation", "design.json", "Invalid folder_Structure")
            raise ValueError("folder_Structure must contain 'root_Project_Directory_Name' and 'structure'")
        
        required_spec_fields = ['project_Overview', 'functional_Requirements', 'technology_Stack']
        for field in required_spec_fields:
            if field not in spec_data:
                self.error_tracker.add_error("validation", "spec.json", f"Missing field: {field}")
                raise ValueError(f"JSON specification must contain '{field}'")
        
        if not spec_data.get('project_Overview', {}).get('project_Name'):
            self.error_tracker.add_error("validation", "spec.json", "Missing project_Name in project_Overview")
            raise ValueError("project_Overview must contain 'project_Name'")
    
    def _create_project_structure(self, design_data: dict, project_root: str) -> str:
        """Wrapper for ProjectStructureTool"""
        structure_tool = next(t for t in self.tools if isinstance(t, ProjectStructureTool))
        return structure_tool._run(
            project_root,
            design_data['folder_Structure']['structure']
        )
    
    # Wrapper for FileGeneratorTool actions
    def _generate_project_files(self, design_data: dict, spec_data: dict, project_root: str) -> str:
        structure = design_data['folder_Structure']['structure']
        context_for_generation = self._build_context(design_data, spec_data, project_root)
        
        file_generator = next(t for t in self.tools if isinstance(t, FileGeneratorTool))
        generated_files = []
        
        for item in structure:
            if 'directory' not in item.get('description', '').lower():
                # Validate and sanitize the path to prevent directory traversal
                item_path = item['path'].strip('/\\')
                if '..' in item_path or item_path.startswith('/') or item_path.startswith('\\'):
                    logger.warning(f"Skipping potentially unsafe path: {item_path}")
                    continue
                
                file_path = os.path.join(project_root, item_path)
                
                # Ensure the directory exists before creating the file
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                file_context = context_for_generation.copy()
                file_context['file_info'] = item
                
                code = file_generator._run(file_path, file_context, spec_data)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                generated_files.append(file_path)
                
        return f"Generated {len(generated_files)} files"
    
    def _build_context(self, design_data: dict, spec_data: dict, project_root: str) -> dict:
        """Build a comprehensive context dictionary for prompt generation"""
        backend_module_path = 'main'
        frontend_dir_rel = 'frontend'
        css_path_rel_to_frontend = 'style.css'
        js_files_to_link_rel_to_frontend = []
        
        for item in design_data['folder_Structure']['structure']:
            relative_item_path = item['path'].strip('/\\').replace('\\', '/')
            if relative_item_path.endswith('main.py'):
                parts = relative_item_path.split('/')
                backend_module_path = '.'.join(parts[:-1] + ['main']) if len(parts) > 1 else 'main'
            elif relative_item_path.endswith('index.html'):
                frontend_dir_rel = os.path.dirname(relative_item_path) or 'frontend'
            elif relative_item_path.endswith('.css'):
                if relative_item_path.startswith(frontend_dir_rel):
                    css_path_rel_to_frontend = os.path.relpath(relative_item_path, frontend_dir_rel).replace('\\', '/')
                else:
                    css_path_rel_to_frontend = relative_item_path
            elif relative_item_path.endswith('.js') and 'directory' not in item.get('description', '').lower():
                if relative_item_path.startswith(frontend_dir_rel):
                    js_files_to_link_rel_to_frontend.append(os.path.relpath(relative_item_path, frontend_dir_rel).replace('\\', '/'))
                else:
                    js_files_to_link_rel_to_frontend.append(relative_item_path)

        return {
            'tech_stack': spec_data.get('technology_Stack', {}).get('backend', {}).get('framework', 'fastapi'),
            'project_root': project_root,
            'design_data': design_data,
            'backend_module_path': backend_module_path,
            'frontend_dir': frontend_dir_rel,
            'css_path': css_path_rel_to_frontend,
            'js_files_to_link': sorted(list(set(js_files_to_link_rel_to_frontend)))
        }
    
    def _create_run_script(self, project_root: str, spec_data: dict, design_data: dict):
        """Create the run script for the project"""
        tech_stack = spec_data.get('technology_Stack', {}).get('backend', {}).get('framework', 'fastapi')
        backend_module_path = self._find_backend_module(design_data)
        
        script_content = self.template_manager.get_template(
            tech_stack, 'run_script',
            python_path=self.config.python_path,
            backend_module_path=backend_module_path
        )
        
        script_path = os.path.join(project_root, 'run.bat')
        with open(script_path, 'w', encoding='utf-8', newline='\r\n') as f: # Ensure Windows line endings
            f.write(script_content)

    def _find_backend_module(self, design_data: dict) -> str:
        """Find the backend module path from the design structure"""
        structure = design_data['folder_Structure']['structure']
        for item in structure:
            if 'main.py' in item['path']:
                path_parts = item['path'].strip('/\\').replace('\\', '/').split('/')
                # e.g., 'backend/app/main.py' -> 'backend.app.main'
                # Remove the '.py' extension from the last part
                if path_parts[-1].endswith('.py'):
                    path_parts[-1] = path_parts[-1][:-3]  # Remove '.py'
                return '.'.join(path_parts)
        # Fallback if not found
        return 'main'