import json
import os
import logging
import subprocess
from datetime import datetime
from typing import Dict, List
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

from src.module_3.ReAct.react_agent import ReActAgent
from src.module_3.ReAct.tools import ReadDesignFileTool, ReadSpecFileTool, ExecuteRunScriptTool
from src.module_3.ReAct.utils import AgentConfig, ErrorTracker, TechnologyTemplateManager, ProjectStructureTool, FileGeneratorTool, ProjectValidatorTool, CodingAgentCallback

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

class LangChainCodingAgent:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.error_tracker = None
        self.template_manager = TechnologyTemplateManager()
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model=config.model_name,
            google_api_key=os.getenv('GEMINI_API_KEY'),
            temperature=0.1
        )
        
    def _setup_tools(self, project_root: str):
        self.error_tracker = ErrorTracker(project_root)
        return [
            ReadDesignFileTool(),
            ReadSpecFileTool(),
            ProjectStructureTool(self.error_tracker),
            FileGeneratorTool(self.llm, self.template_manager, self.error_tracker, self.config),
            ProjectValidatorTool(self.error_tracker),
            ExecuteRunScriptTool()
        ]
        
    def generate_project(self, design_data: Dict, spec_data: Dict) -> str:
        project_name = design_data['folder_Structure']['root_Project_Directory_Name']
        project_root = os.path.abspath(os.path.join(self.config.base_output_dir, project_name))
        logger.info(f"Starting project generation for: {project_name}")

        # Save JSON files to project root for the agent to read
        design_file = os.path.abspath(os.path.join(project_root, 'design.json'))
        spec_file = os.path.abspath(os.path.join(project_root, 'spec.json'))
        os.makedirs(project_root, exist_ok=True)
        with open(design_file, 'w', encoding='utf-8') as f:
            json.dump(design_data, f, indent=2)
        with open(spec_file, 'w', encoding='utf-8') as f:
            json.dump(spec_data, f, indent=2)

        # Initialize custom ReAct agent
        tools = self._setup_tools(project_root)
        agent = ReActAgent(
            llm=self.llm,
            tools=tools,
            project_root=project_root,
            max_iterations=99
        )
        
        task = f"""
        Process the .design.json and .spec.json files to set up a project named '{project_name}'.
        - Read .design.json from '{design_file}' to determine the folder structure.
        - Create the necessary folders.
        - Read .spec.json from '{spec_file}' to determine the files to generate.
        - Generate code for each file.
        - Validate the project structure.
        - Create and execute a run.bat script in '{project_root}'.
        Ensure each step is completed before proceeding to the next.
        """
        
        result = agent.run(task)
        logger.info(f"Project generation result: {result}")
        
        # fallback if not handled by the agent
        if not agent.state["run_script_executed"]:
            self._create_run_script(project_root, spec_data, design_data)
            result += "\n" + self._execute_run_script(project_root)
        
        return result
        
    def _create_run_script(self, project_root: str, spec_data: Dict, design_data: Dict):
        tech_stack = spec_data.get('technology_Stack', {}).get('backend', {}).get('framework', 'fastapi')
        backend_module_path = self._find_backend_module(design_data)
        script_content = self.template_manager.get_template(
            tech_stack, 'run_script',
            python_path=self.config.python_path,
            backend_module_path=backend_module_path
        )
        script_path = os.path.abspath(os.path.join(project_root, 'run.bat'))
        if any(ord(char) > 127 for char in script_content):
            self.error_tracker.add_error("generation", script_path, "Non-ASCII characters in run.bat")
            raise ValueError("Non-ASCII characters in run.bat")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
    def _execute_run_script(self, project_root: str) -> str:
        script_path = os.path.abspath(os.path.join(project_root, 'run.bat'))
        if not os.path.exists(script_path):
            self.error_tracker.add_error("execution", script_path, "Run script not found")
            return "Run script not found"
        try:
            logger.info(f"Executing run script: {script_path} from {project_root}")
            command_string = f'"{script_path}"'
            result = subprocess.run(
                command_string,
                shell=True,
                check=True,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            logger.info(f"Run script executed successfully. Stdout:\n{result.stdout}")
            if result.stderr:
                logger.warning(f"Run script Std_error:\n{result.stderr}")
            return f"Run script executed: {result.stdout}"
        
        except subprocess.CalledProcessError as e:
            error_output = f"Exit code: {e.returncode}\nStdout:\n{e.stdout}\nStderr:\n{e.stderr}"
            self.error_tracker.add_error(
                "execution", script_path, f"Run script failed: {error_output}",
                {"exit_code": e.returncode, "stdout": e.stdout, "stderr": e.stderr}
            )
            logger.error(f"Run script failed: {error_output}")
            return f"Run script failed. Check logs for details: {error_output}"
        
        except subprocess.TimeoutExpired:
            self.error_tracker.add_error("execution", script_path, "Run script timed out")
            logger.error(f"Run script timed out: {script_path}")
            return "Run script timed out"
        
    def _find_backend_module(self, design_data: Dict) -> str:
        structure = design_data['folder_Structure']['structure']
        for item in structure:
            if item['path'].endswith('main.py'):
                path_parts = item['path'].strip('/\\').split('/')
                return '.'.join(path_parts[:-1] + ['main']) if len(path_parts) > 1 else 'main'
        return 'main'
    
    def find_latest_json_files(self) -> tuple[str, str]:
        outputs_dir = Path(self.config.outputs_dir)
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
    """Main function to run the coding agent."""
    try:
        config = AgentConfig.from_env()
        agent = LangChainCodingAgent(config)
        design_file, spec_file = agent.find_latest_json_files()
        with open(design_file, 'r', encoding='utf-8') as f:
            design_data = json.load(f)
        with open(spec_file, 'r', encoding='utf-8') as f:
            spec_data = json.load(f)
        result = agent.generate_project(design_data, spec_data)
        print(result)
        project_name = design_data['folder_Structure']['root_Project_Directory_Name']
        project_root = os.path.join(config.base_output_dir, project_name)
        print(f"Check {os.path.join(project_root, 'errors.json')} for any issues")
    except Exception as e:
        logger.error(f"Main execution failed: {e}", exc_info=True)
        print(f"Error: {e}")
        
if __name__ == "__main__":
    main()