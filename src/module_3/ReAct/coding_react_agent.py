import json
import os
import logging
from typing import List, Dict, Tuple
from pathlib import Path
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import BaseTool

# Sử dụng đường dẫn tương đối để import
from .react_agent import ReActAgent
from .tools import ReadDesignFileTool, ReadSpecFileTool, ExecuteRunScriptTool, CreateRunScriptTool
from .utils import AgentConfig, ErrorTracker, TechnologyTemplateManager, ProjectStructureTool, FileGeneratorTool, ProjectValidatorTool

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('langchain_coding_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CodingReActAgent:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.template_manager = TechnologyTemplateManager()
        
        self.llm = ChatGoogleGenerativeAI(
            model=config.model_name,
            google_api_key=os.getenv('GEMINI_API_KEY'),
            temperature=0.1
        )
        
    def _setup_tools(self, project_root: str) -> List[BaseTool]:
        # ErrorTracker được tạo ở đây và truyền vào các tool cần nó
        error_tracker = ErrorTracker(project_root)
        
        return [
            ReadDesignFileTool(),
            ReadSpecFileTool(),
            ProjectStructureTool(error_tracker=error_tracker),
            FileGeneratorTool(llm=self.llm, template_manager=self.template_manager, error_tracker=error_tracker, config=self.config),
            ProjectValidatorTool(error_tracker=error_tracker),
            CreateRunScriptTool(template_manager=self.template_manager, config=self.config),
            ExecuteRunScriptTool()        ]
        
    def generate_project(self, design_data: Dict, spec_data: Dict) -> str:
        project_name = design_data.get('folder_Structure', {}).get('root_Project_Directory_Name')
        if not project_name:
            raise ValueError("Missing 'root_Project_Directory_Name' in design file.")
        
        # Validate project name for filesystem compatibility
        if not project_name or any(char in project_name for char in '<>:"|?*'):
            raise ValueError(f"Invalid project name for filesystem: '{project_name}'")

        project_root = Path(self.config.base_output_dir) / project_name
        project_root = project_root.resolve()  # Get absolute path
        logger.info(f"Starting project generation for: {project_name} at {project_root}")

        # Prepare environment for agent
        try:
            project_root.mkdir(parents=True, exist_ok=True)
            design_file_path = project_root / f"{project_name}.design.json"
            spec_file_path = project_root / f"{project_name}.spec.json"
            
            with open(design_file_path, 'w', encoding='utf-8') as f:
                json.dump(design_data, f, indent=2, ensure_ascii=False)
            with open(spec_file_path, 'w', encoding='utf-8') as f:
                json.dump(spec_data, f, indent=2, ensure_ascii=False)
        except (OSError, PermissionError) as e:
            raise RuntimeError(f"Failed to create project files: {e}")
        except (TypeError, ValueError) as e:
            raise RuntimeError(f"Failed to serialize JSON data: {e}")

        # Khởi tạo các tool
        tools = self._setup_tools(project_root)
        
        # Khởi tạo ReActAgent
        react_executor = ReActAgent(
            llm=self.llm,
            tools=tools,
            project_root=project_root,        )
        
        # Nhiệm vụ ban đầu cho agent
        task = f"""
Generate the complete '{project_name}' application following these exact steps:

STEP 1: Read the design file at '{design_file_path}' using read_design_file
STEP 2: Read the spec file at '{spec_file_path}' using read_spec_file  
STEP 3: Create the complete project directory structure using project_structure
STEP 4: Generate ALL files listed in the design structure using file_generator (one call per file)
STEP 5: Validate the completed project using project_validator
STEP 6: Create the run.bat script using create_run_script
STEP 7: Execute the run.bat script using execute_run_script

You must complete ALL steps in order. Do not skip any step.
Each file mentioned in the folder structure must be generated with proper content.
        """
        
        result = react_executor.run(task)
        logger.info(f"Agent finished with result: {result}")
        return result
        
def find_latest_json_files(config: AgentConfig) -> Tuple[str, str]:
    outputs_dir = Path(config.outputs_dir)
    if not outputs_dir.exists():
        raise FileNotFoundError(f"Outputs directory '{outputs_dir}' does not exist")
    
    spec_files = list(outputs_dir.glob('*.spec.json'))
    design_files = list(outputs_dir.glob('*.design.json'))
    
    if not spec_files or not design_files:
        raise FileNotFoundError("No .spec.json or .design.json files found")
    
    latest_spec = max(spec_files, key=lambda p: p.stat().st_mtime)
    latest_design = max(design_files, key=lambda p: p.stat().st_mtime)
    
    logger.info(f"Found latest spec file: {latest_spec}")
    logger.info(f"Found latest design file: {latest_design}")
    return str(latest_design), str(latest_spec)
    
def main():
    try:
        config = AgentConfig.from_env()
        agent = CodingReActAgent(config)
        
        design_file_path, spec_file_path = find_latest_json_files(config)
        
        # Read files with better error handling
        try:
            with open(design_file_path, 'r', encoding='utf-8') as f:
                design_data = json.load(f)
        except (FileNotFoundError, PermissionError) as e:
            raise RuntimeError(f"Cannot read design file '{design_file_path}': {e}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in design file '{design_file_path}': {e}")
            
        try:
            with open(spec_file_path, 'r', encoding='utf-8') as f:
                spec_data = json.load(f)
        except (FileNotFoundError, PermissionError) as e:
            raise RuntimeError(f"Cannot read spec file '{spec_file_path}': {e}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in spec file '{spec_file_path}': {e}")
            
        result = agent.generate_project(design_data, spec_data)
        
        print("\n--- AGENT EXECUTION FINISHED ---")
        print(result)
        
        project_name = design_data.get('folder_Structure', {}).get('root_Project_Directory_Name', 'unknown_project')
        project_root = Path(config.base_output_dir) / project_name
        error_file = project_root / 'errors.json'
        print(f"Check {error_file} for any logged issues during the process.")

    except Exception as e:
        logger.error(f"A critical error occurred in main execution: {e}", exc_info=True)
        print(f"\nFATAL ERROR: {e}")
        
if __name__ == "__main__":
    main()