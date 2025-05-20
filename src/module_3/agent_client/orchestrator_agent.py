import os
import json
import logging
import time
import re 
import agent_core

log_format = '%(asctime)s - %(levelname)s - [Orchestrator] - %(filename)s:%(lineno)d - %(message)s'
logger = logging.getLogger("OrchestratorLogger")
logger.setLevel(logging.INFO)

def slugify(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r'\s+', '_', text)
    text = re.sub(r'[^\w_.-]', '', text)
    text = text.strip('_.-')
    return text if text else "unnamed_project"

# Need to revise 2 classes SpecGenerator and DesignGenerator later
# make sure generate() return JSON string

class SpecGenerator:
    def __init__(self, llm_model_instance=None): 
        self.model = llm_model_instance
        logger.info("SpecGenerator initialized (mock or real).")

    def generate(self, project_description: str) -> str:
        logger.info(f"SpecGenerator: Generating spec for description: '{project_description[:50]}...'")
        project_name_from_desc = slugify(project_description.split(" ")[0]) + "_app"
        if len(project_name_from_desc) > 50: 
            project_name_from_desc = project_name_from_desc[:45] + "_app"

        mock_spec = {
            "project_Overview": {
                "project_Name": project_name_from_desc.replace("_", " ").title(),
                "project_Purpose": f"Purpose of {project_name_from_desc} based on: {project_description}",
                "product_Scope": "Scope to be defined by LLM based on description."
            },
            "functional_Requirements": [{"id": "FR-001", "title": "User Authentication", "description": "Users can register and login.", "priority": "High", "acceptance_criteria": ["User provides valid credentials."]}],
            "non_Functional_Requirements": [{"id": "NFR-001", "category": "Security", "description": "Passwords must be hashed.", "acceptance_criteria": ["Passwords are not stored in plain text."]}],
            "external_Interface_Requirements": {"user_Interfaces": ["Web UI for all user interactions."]},
            "technology_Stack": {"backend": {"language": "Python", "framework": "FastAPI"}, "frontend": {"language": "JavaScript", "framework": "React"}}, # Agent 1 có thể đề xuất
            "data_Storage": {"storage_Type": "SQL", "database_Type": "SQLite", "data_models": [{"entity_name": "User", "key_attributes": ["id", "username", "email", "password_hash"]}]}, # Agent 1 có thể đề xuất
            "assumptions_Made": ["The user has a modern web browser."]
        }
        logger.info(f"SpecGenerator: Mock spec content generated for '{project_name_from_desc}'.")
        return json.dumps(mock_spec, indent=2)
        #** LOGIC**

class DesignGenerator:
    def __init__(self, llm_model_instance=None): 
        self.model = llm_model_instance
        logger.info("DesignGenerator initialized (mock or real).")

    def generate(self, spec_content_string: str) -> str:
        logger.info("DesignGenerator: Generating design based on spec content...")
        try:
            spec_data = json.loads(spec_content_string)
            project_name = spec_data.get("project_Overview", {}).get("project_Name", "UnknownProject")
        except json.JSONDecodeError:
            logger.error("DesignGenerator: Failed to parse spec_content_string.")
            project_name = "UnknownProjectDueToSpecParseError"
        
        project_slug_for_design = slugify(project_name)

        mock_design = {
            "project_Overview": spec_data.get("project_Overview"),
            "system_Architecture": {
                "description": f"Client-Server Architecture for {project_name}", 
                "components": [
                    {"name": "Frontend", "description": "React SPA", "technologies": ["React", "JavaScript"]},
                    {"name": "Backend", "description": "FastAPI API", "technologies": ["Python", "FastAPI"]},
                    {"name": "Database", "description": "SQLite DB", "technologies": ["SQLite"]}
                ]
            },
            "data_Design": spec_data.get("data_Storage"), 
            "interface_Design": {
                "api_Specifications": [
                    {"endpoint": "/auth/register", "method": "POST", "description": "User registration."}
                ], 
                "ui_Interaction_Notes": "User interacts via web forms and buttons."
            },
            "workflow_Interaction": [{"workflow_Name": "User Registration", "description": "User fills form, submits, backend validates and saves."}],
            "folder_Structure": {
                "description": f"Proposed folder structure for {project_name}. All paths are relative to the root_Project_Directory_Name.",
                "root_Project_Directory_Name": project_slug_for_design, # Wichtig!
                "structure": [
                    {"path": "README.md", "description": "Project readme file providing an overview and setup instructions."},
                    {"path": f"{project_slug_for_design}.spec.json", "description": "The specification file for this project."},
                    {"path": f"{project_slug_for_design}.design.json", "description": "This design file."},
                    {"path": "backend", "description": "Backend application source code directory."},
                    {"path": "backend/main.py", "description": "Main FastAPI application file."},
                    {"path": "backend/requirements.txt", "description": "Python backend dependencies file."},
                    {"path": "frontend", "description": "Frontend application source code directory."},
                    {"path": "frontend/src", "description": "Frontend source code (e.g., React components) directory."},
                    {"path": "frontend/src/App.js", "description": "Main frontend application component file."},
                    {"path": "frontend/package.json", "description": "Frontend dependencies and scripts file."}
                ]
            },
            "dependencies": {"backend": ["fastapi", "uvicorn[standard]", "sqlalchemy", "passlib[bcrypt]"], "frontend": ["react", "react-dom", "axios"]}
        }
        logger.info(f"DesignGenerator: Mock design content generated for '{project_name}'.")
        return json.dumps(mock_design, indent=2)

        #**LOGIC**

class OrchestratorAgent:
    def __init__(self):
        logger.info("OrchestratorAgent initializing...")
        self.spec_generator = SpecGenerator() 
        self.design_generator = DesignGenerator()
        self.current_project_workspace = None 
        self.project_slug = None 
        logger.info("OrchestratorAgent initialized successfully.")

    def _execute_mcp_tool_via_agent_core(self, task_description: str, user_prompt_for_llm: str, is_content_expected_from_tool: bool = False) -> dict:
        if not self.current_project_workspace:
            logger.error("Critical: Project workspace not set. Cannot call agent_core.")
            raise ValueError("Project workspace must be set before calling agent_core.")

        logger.info(f"Orchestrator: Task '{task_description}' - Sending prompt to agent_core.")
        logger.debug(f"Orchestrator: Prompt for agent_core: '{user_prompt_for_llm[:300]}...'")
        
        core_result = agent_core.run_agent_turn(user_prompt_for_llm, self.current_project_workspace)
        logger.debug(f"Orchestrator: Received from agent_core: {core_result}")

        if not isinstance(core_result, dict):
            logger.error(f"Orchestrator: AgentCore did not return a dictionary. Received: {type(core_result)} - {str(core_result)[:200]}")
            raise TypeError("agent_core.run_agent_turn did not return the expected dictionary structure.")

        final_llm_text = core_result.get("final_llm_text_response", "")
        mcp_result = core_result.get("last_tool_mcp_result")
        agent_core_error = core_result.get("error", False)
        agent_core_error_msg = core_result.get("error_message", "")

        if agent_core_error:
            logger.error(f"Orchestrator: Task '{task_description}' - agent_core reported an error: {agent_core_error_msg}")
            return {"status": "error", "message": f"AgentCore Error: {agent_core_error_msg}", "data": None, "llm_response": final_llm_text, "raw_core_result": core_result}

        if mcp_result: # A tool was called and MCP server responded
            logger.info(f"Orchestrator: Task '{task_description}' - MCP Tool '{core_result.get('last_tool_name_called')}' result: Status='{mcp_result.get('status')}'")
            if mcp_result.get("status") == "success":
                tool_data = None
                if is_content_expected_from_tool:
                    tool_data = mcp_result.get("content") # For read_file
                    if tool_data is None and core_result.get('last_tool_name_called') == 'list_files':
                        tool_data = mcp_result.get("items") # For list_files
                    if tool_data is None and is_content_expected_from_tool: # Nếu vẫn None mà lại đang mong đợi content
                         logger.warning(f"Task '{task_description}': Content was expected from tool '{core_result.get('last_tool_name_called')}' but not found in MCP result. MCP Result: {mcp_result}")
                
                return {
                    "status": "success",
                    "message": mcp_result.get("message", final_llm_text or "Tool executed successfully."),
                    "data": tool_data,
                    "llm_response": final_llm_text,
                    "raw_core_result": core_result
                }
            else: # MCP tool execution failed
                error_msg = mcp_result.get("message", "Tool execution failed on MCP server.")
                error_type = mcp_result.get("error_type", "MCP_TOOL_ERROR")
                logger.error(f"Orchestrator: Task '{task_description}' - MCP Tool failed: {error_msg} (Type: {error_type})")
                return {"status": "error", "message": f"MCP Tool Error ({error_type}): {error_msg}", "data": None, "llm_response": final_llm_text, "raw_core_result": core_result}
        
        elif final_llm_text: # No tool was called by LLM, or no MCP result was processed, just LLM text
            logger.info(f"Orchestrator: Task '{task_description}' - LLM_only response: '{final_llm_text[:100]}...'")
            return {
                "status": "success_llm_only", # Indicates LLM provided text, no tool result to check
                "message": "LLM provided a text response.",
                "data": None, # Không có data từ tool
                "llm_response": final_llm_text,
                "raw_core_result": core_result
            }
        else: # Should not happen if agent_core returns error status correctly
            logger.error(f"Orchestrator: Task '{task_description}' - No conclusive result from agent_core (no error, no MCP result, no LLM text).")
            return {"status": "error", "message": "No conclusive result from agent_core.", "data": None, "llm_response": None, "raw_core_result": core_result}


    def run_full_pipeline(self, project_description: str, base_workspace_path: str):
        logger.info(f"===== Orchestrator Pipeline Started for: '{project_description[:50]}...' =====")
        logger.info(f"Base workspace for projects: {base_workspace_path}")

        if not os.path.isdir(base_workspace_path):
            logger.error(f"Base workspace path '{base_workspace_path}' does not exist or is not a directory.")
            raise ValueError(f"Base workspace path '{base_workspace_path}' is invalid.")

        actual_spec_file_path = None
        actual_design_file_path = None
        spec_content_string = None 

        # === STAGE 1: Generate Specification ===
        logger.info("--- STAGE 1: Generating Specification ---")
        try:
            spec_content_string = self.spec_generator.generate(project_description)
            if not spec_content_string:
                logger.error("SpecGenerator returned empty content.")
                raise ValueError("Specification generation failed: empty content from SpecGenerator.")
            
            spec_data = json.loads(spec_content_string) 
            project_name = spec_data.get("project_Overview", {}).get("project_Name")
            if not project_name:
                logger.error("Project name not found in generated specification by SpecGenerator.")
                raise ValueError("Specification generation failed: project_name missing in SpecGenerator output.")
            
            logger.info(f"Generated project name from spec: '{project_name}'")
            self.project_slug = slugify(project_name)
            
            self.current_project_workspace = os.path.join(base_workspace_path, self.project_slug)
            logger.info(f"Project specific workspace (absolute): '{self.current_project_workspace}'")
            # Thư mục này sẽ được tạo bởi tool `create_file` của MCP nếu nó chưa tồn tại,
            # vì `execution.create_file` có `target_path.parent.mkdir(parents=True, exist_ok=True)`

            relative_spec_file_path = f"{self.project_slug}.spec.json"
            logger.info(f"Attempting to save specification to '{relative_spec_file_path}' in workspace.")
            
            prompt_for_saving_spec = (
                f"Nhiệm vụ: Tạo một file mới có tên '{relative_spec_file_path}'.\n"
                f"Nội dung đầy đủ để ghi vào file này là:\n```json\n{spec_content_string}\n```\n"
                "Hãy sử dụng tool 'create_file' để thực hiện việc này. Chỉ gọi tool một lần duy nhất. Xác nhận sau khi hoàn thành."
            )
            save_spec_result = self._execute_mcp_tool_via_agent_core(
                task_description="Save Specification File",
                user_prompt_for_llm=prompt_for_saving_spec
            )

            if save_spec_result.get("status") != "success": # Kiểm tra status tổng thể từ helper
                raise RuntimeError(f"Failed to save specification file: {save_spec_result.get('message')}")

            logger.info(f"Specification file saved successfully: '{relative_spec_file_path}' in '{self.current_project_workspace}'")
            actual_spec_file_path = os.path.join(self.current_project_workspace, relative_spec_file_path)

        except Exception as e:
            logger.error(f"Error during Specification Generation stage: {e}", exc_info=True)
            raise 

        # === STAGE 2: Generate Design ===
        logger.info("--- STAGE 2: Generating Design ---")
        try:
            if not spec_content_string:
                 logger.error("Critical: spec_content_string is not available for Design stage.")
                 raise RuntimeError("Cannot proceed to Design stage: Specification content is missing.")

            design_content_string = self.design_generator.generate(spec_content_string)
            if not design_content_string:
                logger.error("DesignGenerator returned empty content.")
                raise ValueError("Design generation failed: empty content from DesignGenerator.")

            design_data = json.loads(design_content_string)
            design_root_name = design_data.get("folder_Structure", {}).get("root_Project_Directory_Name")
            if design_root_name != self.project_slug:
                logger.warning(f"Design's root_Project_Directory_Name ('{design_root_name}') differs from "
                               f"Orchestrator's project_slug ('{self.project_slug}'). "
                               f"Orchestrator's slug ('{self.project_slug}') will be used for the actual directory structure.")
                # Cập nhật design_data nếu cần thiết để đảm bảo tính nhất quán
                design_data["folder_Structure"]["root_Project_Directory_Name"] = self.project_slug
                design_content_string = json.dumps(design_data, indent=2) # Cập nhật lại chuỗi nếu đã thay đổi

            relative_design_file_path = f"{self.project_slug}.design.json"
            logger.info(f"Attempting to save design to '{relative_design_file_path}' in workspace.")
            
            prompt_for_saving_design = (
                f"Nhiệm vụ: Tạo một file mới có tên '{relative_design_file_path}'.\n"
                f"Nội dung đầy đủ để ghi vào file này là:\n```json\n{design_content_string}\n```\n"
                "Hãy sử dụng tool 'create_file' để thực hiện việc này. Chỉ gọi tool một lần duy nhất. Xác nhận sau khi hoàn thành."
            )
            save_design_result = self._execute_mcp_tool_via_agent_core(
                task_description="Save Design File",
                user_prompt_for_llm=prompt_for_saving_design
            )

            if save_design_result.get("status") != "success":
                raise RuntimeError(f"Failed to save design file: {save_design_result.get('message')}")

            logger.info(f"Design file saved successfully: '{relative_design_file_path}' in '{self.current_project_workspace}'")
            actual_design_file_path = os.path.join(self.current_project_workspace, relative_design_file_path)

        except Exception as e:
            logger.error(f"Error during Design Generation stage: {e}", exc_info=True)
            raise 
            
        logger.info(f"===== Orchestrator: Spec and Design generation complete for project '{self.project_slug}' =====")
        
        # === STAGE 3: Code Generation (Sẽ được thêm ở các bước sau) ===
        logger.info("--- STAGE 3: Code Generation (To be implemented) ---")
        # Placeholder cho các bước tiếp theo:
        # 1. Đọc spec_content_string và design_content_string (hoặc đọc lại từ file nếu muốn)
        #    design_content_string đã có, spec_content_string cũng vậy.
        #
        # 2. Parse design_data['folder_Structure']['structure']
        #
        # 3. Lặp để tạo thư mục bằng tool 'create_directory'
        #    for item in design_data['folder_Structure']['structure']:
        #        if 'directory' in item['description'].lower():
        #            relative_dir_path = item['path']
        #            prompt = f"Tạo thư mục '{relative_dir_path}'. Dùng tool 'create_directory'."
        #            self._execute_mcp_tool_via_agent_core("Create Directory " + relative_dir_path, prompt)
        #
        # 4. Lặp để tạo file rỗng / file phụ thuộc bằng tool 'create_file'
        #    (Xử lý requirements.txt, package.json đặc biệt nếu cần)
        #
        # 5. Lặp qua các file cần gen code:
        #    a. Soạn prompt chi tiết cho LLM để chỉ gen code string (không gọi tool file).
        #       prompt_for_llm_code_gen = "Nhiệm vụ: Tạo nội dung code cho file X... QUAN TRỌNG: Chỉ trả về code string."
        #       core_result_code_string = self._execute_mcp_tool_via_agent_core("Generate Code String for " + file_X, prompt_for_llm_code_gen)
        #       generated_code = core_result_code_string.get("llm_response")
        #    b. Nếu có code string, soạn prompt để agent_core dùng tool 'edit_file' (hoặc create_file) để lưu code.
        #       prompt_to_save = f"Lưu nội dung sau vào file X: \n```\n{generated_code}\n```. Dùng tool 'edit_file'."
        #       self._execute_mcp_tool_via_agent_core("Save Code for " + file_X, prompt_to_save)

        logger.info(f"===== Orchestrator Pipeline Fully Completed for project '{self.project_slug}' (up to Design stage, CodeGen pending) =====")
        return {
            "status": "partial_success", # Vì chưa có Stage 3
            "message": "Specification and Design stages completed. Code generation is pending.",
            "project_workspace": self.current_project_workspace,
            "spec_file_path": actual_spec_file_path,
            "design_file_path": actual_design_file_path,
            "project_slug": self.project_slug
        }

if __name__ == "__main__":
    base_workspace_dir = os.path.join(os.getcwd(), "orchestrator_generated_projects")
    try:
        os.makedirs(base_workspace_dir, exist_ok=True)
        logger.info(f"Base workspace for projects: {base_workspace_dir}")
    except OSError as e:
        logger.error(f"Failed to create base workspace directory '{base_workspace_dir}': {e}")
        exit(1) 

    orchestrator = OrchestratorAgent()
    
    test_project_description_input = "Create a simple Flashcard Web Application. Users can create decks, add flashcards (front and back text) to decks, and review flashcards in a deck. The review mode should show the front, then allow the user to reveal the back."

    try:
        pipeline_run_result = orchestrator.run_full_pipeline(
            project_description=test_project_description_input,
            base_workspace_path=base_workspace_dir
        )
        logger.info(f"Orchestrator pipeline finished with result: {pipeline_run_result}")
    except Exception as e:
        logger.error(f"Orchestrator pipeline failed catastrophically: {e}", exc_info=True)