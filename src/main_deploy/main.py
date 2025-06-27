import logging
import os
import json

# --- Core Modules ---
# These are our own refactored modules that provide configuration and setup.
import config
from utils import save_json_to_file, generate_filename, get_spec_design_output_dir

# --- Agent Classes ---
# These are the refactored agent classes for the pre-coding phases.
from specification_agent import SpecificationAgent
from design_agent import DesignAgent
from coding_agent import LangChainCodingAgent, AgentConfig

# --- Phase-Specific Logic (from refactored standalone scripts) ---
# We import the primary functions from our testing and debugging modules.
from testing_agent import run_test_generation_and_execution
from debug_agent import run_debugging_cycle

# --- Third-Party Libraries ---
import autogen

# Get a logger for this module, which will use the global config.
logger = logging.getLogger(__name__)


def run_autogen_coding_crew(spec_data: dict, design_data: dict) -> str:
    """
    Initializes and runs the AutoGen GroupChat for the code generation phase.
    This function encapsulates the entire multi-agent coding conversation.
    
    Args:
        spec_data: The dictionary containing the project specification.
        design_data: The dictionary containing the system design.

    Returns:
        The absolute path to the generated project's root directory upon success.
    
    Raises:
        ValueError: If the project's root directory name cannot be determined.
    """
    logger.info("🚀 Initializing AutoGen Coding Crew...")

    # Determine the project's output directory from the design data
    project_name_slug = design_data.get('folder_Structure', {}).get('root_Project_Directory_Name')
    if not project_name_slug:
        raise ValueError("Could not determine 'root_Project_Directory_Name' from design data.")
    
    # Construct the absolute path for the generated code
    project_root_path = os.path.abspath(os.path.join(config.BASE_OUTPUT_DIR, project_name_slug))
    logger.info(f"Code will be generated in: {project_root_path}")
    os.makedirs(project_root_path, exist_ok=True)

    # --- Instantiate the LangChainCodingAgent (the "tool" for AutoGen) ---
    # The agent's config is now created from our central config file.
    coding_agent_config = AgentConfig.from_central_config()
    coding_agent_instance = LangChainCodingAgent(coding_agent_config)

    # --- Configure the AutoGen Agents ---
    autogen_llm_config = {
        "config_list": [{
            "model": config.CURRENT_MODELS['coding'],
            "api_key": config.GEMINI_API_KEY,
            "api_type": "google"
        }],
        "temperature": 0.3,
        "timeout": 600,
    }

    project_manager = autogen.AssistantAgent(
        name="ProjectManager",
        system_message="""
        You are a project manager. Your role is to orchestrate the code generation process.
        - Receive the initial task with the design and specification JSON.
        - Delegate the implementation to the Coder by instructing it to call the 'generate_project' function.
        - Once the Coder agent confirms successful generation (by reporting the output of the function), you MUST reply with the word 'TERMINATE'.
        """,
        llm_config=autogen_llm_config,
    )

    coder = autogen.AssistantAgent(
        name="Coder",
        system_message="""
        You are an expert software engineer. You will receive instructions from the ProjectManager.
        - Your main tool is 'generate_project'. When asked to implement the project, you MUST call this function with the provided design and specification data.
        - DO NOT write code directly in the chat.
        - Report the result of the function call back to the ProjectManager.
        """,
        llm_config=autogen_llm_config,
    )

    user_proxy = autogen.UserProxyAgent(
        name="UserProxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5,
        is_termination_msg=lambda x: "TERMINATE" in x.get("content", "").upper(),
        code_execution_config={"work_dir": project_root_path, "use_docker": False},
        function_map={"generate_project": coding_agent_instance.generate_project}
    )

    # --- Start the Conversation ---
    groupchat = autogen.GroupChat(
        agents=[user_proxy, project_manager, coder], messages=[], max_round=15
    )
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=autogen_llm_config)

    initial_message = f"""
    The specification and design phases are complete. Now, we must generate the project code.
    ProjectManager, your task is to instruct the Coder to call the `generate_project` function.
    Do not ask for reviews or other steps. Just call the function.

    Here is the required data:
    --- SPECIFICATION DATA ---
    {json.dumps(spec_data, indent=2)}
    --- DESIGN DATA ---
    {json.dumps(design_data, indent=2)}
    """

    logger.info("Handing off to AutoGen GroupChat for code generation. This may take several minutes...")
    user_proxy.initiate_chat(manager, message=initial_message)
    logger.info("✅ AutoGen Coding Crew has finished.")

    return project_root_path


def run_autonomous_software_factory(user_description: str):
    """
    The main orchestration function for the entire multi-agent workflow.
    
    Args:
        user_description: The initial user prompt describing the software to build.
    """
    try:
        logger.info("=================================================")
        logger.info("======= AUTONOMOUS SOFTWARE FACTORY START =======")
        logger.info("=================================================")
        logger.info(f"Received user request: '{user_description[:100]}...'")

        # --- PHASE 1: SPECIFICATION ---
        logger.info("\n----- PHASE 1: GENERATING SPECIFICATION -----")
        spec_agent = SpecificationAgent()
        spec_data = spec_agent.generate_specification(user_description)
        logger.info("✅ Specification generated successfully.")

        # --- PHASE 2: DESIGN ---
        logger.info("\n----- PHASE 2: GENERATING SYSTEM DESIGN -----")
        design_agent = DesignAgent()
        design_data = design_agent.generate_design(spec_data)
        logger.info("✅ System Design generated successfully.")

        # --- PHASE 3: CODING (AUTOGEN) ---
        logger.info("\n----- PHASE 3: GENERATING PROJECT CODE -----")
        project_root_path = run_autogen_coding_crew(spec_data, design_data)
        logger.info(f"✅ Code Generation complete. Project located at: {project_root_path}")

        # --- PHASE 4: TESTING ---
        logger.info("\n----- PHASE 4: GENERATING & RUNNING TESTS -----")
        failed_tests = run_test_generation_and_execution(project_root_path, design_data, spec_data)

        # --- PHASE 5: DEBUGGING (CONDITIONAL) ---
        if failed_tests:
            logger.warning(f"Detected {len(failed_tests)} test failures. Entering debugging phase...")
            logger.info("\n----- PHASE 5: DEBUGGING FAILED TESTS -----")
            debugging_successful = run_debugging_cycle(project_root_path, failed_tests)

            if debugging_successful:
                logger.info("✅ All bugs were successfully fixed by the Debugging Agent!")
            else:
                logger.error("❌ Debugging Agent could not fix all issues after multiple attempts.")
        else:
            logger.info("✅ All tests passed successfully! No debugging needed.")

        logger.info("\n================================================")
        logger.info("======= AUTONOMOUS SOFTWARE FACTORY END ========")
        logger.info("================================================")
        logger.info(f"Final project is located at: {project_root_path}")

    except Exception as e:
        logger.critical(f"A critical error halted the main workflow: {e}", exc_info=True)
        logger.critical("The process has been stopped.")


        
# import os
# import json
# import logging
# import argparse
# from typing import Dict, List
# # Use absolute imports for execution as script
# from .specification_agent import SpecificationAgent
# from .design_agent import DesignAgent
# from .coding_agent import LangChainCodingAgent, AgentConfig
# from .utils import get_filename, get_base_output_dir
# from .setup import get_api_key, configure_genai
# import autogen

# # Configure logging for the orchestrator script
# # This ensures that messages from this script also appear in the console.
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# def check_environment():
#     """Check if the environment is set up correctly."""
#     try:
#         api_key = get_api_key()
#         if not api_key:
#             logger.error("No API key found. Please set the GEMINI_API_KEY environment variable.")
#             return False
#         return True
#     except Exception as e:
#         logger.error(f"Environment setup error: {e}")
#         return False

# def main():
#     """
#     Main function to orchestrate the sequential execution of
#     SpecificationAgent and DesignAgent.
#     """
#     # Parse command line arguments
#     parser = argparse.ArgumentParser(description="Autonomous Software Factory")
#     parser.add_argument("--show-preview", action="store_true", help="Show preview of generated specification and design")
#     args = parser.parse_args()
    
#     logger.info("Starting the autonomous software development orchestrator.")
    
#     # Check environment setup
#     if not check_environment():
#         print("Environment setup error. Please check the logs for more details.")
#         return
    
#     # --- 1. Get user prompt from CMD ---
#     print("\n--- Welcome to the Autonomous Software Factory ---")
#     print("Please provide a detailed description of the web application you want to build.")
#     print("Example: 'I need a simple task management web app with user login, tasks with name/due date, and filter by status. It needs to be accessible from desktop browsers. Basic user login/registration is required. Performance should be reasonably fast.'")
#     user_description = input("\nEnter your project description: \n")

#     if not user_description.strip():
#         print("Project description cannot be empty. Exiting.")
#         logger.warning("Empty user description provided. Exiting.")
#         return

#     try:
#         # --- 2. Initialize Agents ---
#         # Instantiate your agent classes directly.
#         # Their internal LangChain and Gemini model setup happens in their __init__.
#         spec_agent_instance = SpecificationAgent()
#         design_agent_instance = DesignAgent()

#         # --- 3. Execute Specification Generation ---
#         print("\n--- STEP 1: Generating Software Specification ---")
#         logger.info("Calling SpecificationAgent to generate specification...")
        
#         # Directly call the generate_specification method on the instance
#         spec_data = spec_agent_instance.generate_specification(user_description)
        
#         project_name = spec_data.get("project_Overview", {}).get("project_Name", "unnamed_project")
#         spec_filename = get_filename(project_name=project_name, extension="spec.json")
#         spec_filepath = os.path.join(get_base_output_dir(), spec_filename)
#         print(f"Specification for '{project_name}' generated and saved to: {spec_filepath}")
#         logger.info(f"Specification generated and saved: {spec_filepath}")
        
#         # Print preview if requested
#         if args.show_preview:
#             print("\n--- Specification Preview ---")
#             print(json.dumps(spec_data, indent=2)[:1000] + "...") # Print first 1000 chars

#         # --- 4. Execute Design Generation ---        print("\n--- STEP 2: Generating System Design ---")
#         logger.info("Calling DesignAgent to generate design from specification...")
#         # Directly call the generate_design method on the instance, passing the spec_data
#         design_data = design_agent_instance.generate_design(spec_data)
#         design_filename = get_filename(project_name=project_name, extension="design.json")
#         design_filepath = os.path.join(get_base_output_dir(), design_filename)
#         print(f"Design for '{project_name}' generated and saved to: {design_filepath}")
#         logger.info(f"Design generated and saved: {design_filepath}")
        
#         # Print preview if requested
#         if args.show_preview:
#             print("\n--- Design Preview ---")
#             print(json.dumps(design_data, indent=2)[:1000] + "...") # Print first 1000 chars

#         print("\n--- Orchestration of Specification and Design complete! ---")
#         print("\n--- STEP 3: Entering AutoGen GroupChat for Code Generation ---")
#         coding_config = AgentConfig.from_env()
#         coding_agent_instance = LangChainCodingAgent(coding_config)
#         autogen_llm_config = {
#             "config_list": [
#                 {
#                     "model": coding_config.model_name,
#                     "api_key": os.getenv("GEMINI_API_KEY"),
#                     "api_type": "google"
#                 }
#             ],
#             "temperature": 0.3,
#             "timeout": 600,
#         }
        
#         project_manager = autogen.AssistantAgent(
#             name="ProjectManager",
#             system_message="""
#             You are a project manager. Your role is to orchestrate the code generation process.
#             - Receive the initial task with the design and specification JSON.
#             - Delegate the implementation to the Coder by instructing it to call the 'generate_project' function.
#             - Once the Coder agent confirms successful generation, you must instruct the UserProxy to execute the `run.bat` script to verify the application.
#             - If the execution is successful, your MUST reply with the word 'TERMINATE'.
#             """,
#             llm_config=autogen_llm_config,
#         )
        
#         coder = autogen.AssistantAgent(
#             name="Coder",
#             system_message="""
#             You are an expert software engineer. You will receive instructions from the ProjectManager.
#             - Your main tool is 'generate_project'. When asked to implement the project, call this function with the provided design and specification data.
#             - DO NOT write code directly in the chat.
#             - Report the result of the function call back to the ProjectManager.
#             """,
#             llm_config=autogen_llm_config,
#         )
#         user_proxy = autogen.UserProxyAgent(
#             name="UserProxy",
#             human_input_mode = "NEVER",
#             max_consecutive_auto_reply=30,
#             is_termination_msg=lambda x: "TERMINATE" in x.get("content", "").upper(),
#             code_execution_config={
#                 "work_dir": coding_config.base_output_dir,
#                 "use_docker": False,
#             },
#             function_map={
#                 "generate_project": coding_agent_instance.generate_project,
#             }
#         )
        
#         # GropuChat in AutoGen
#         groupchat = autogen.GroupChat(
#             agents=[user_proxy,project_manager, coder],
#             messages=[],
#             max_round=99
#         )
#         manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=autogen_llm_config)
#         initial_message = f"""
#         The specification and design phases are complete. Now, we need to generate the project code.

#         ProjectManager, please orchestrate this process. Your first step is to instruct the Coder to call the `generate_project` function.

#         Here is the required data:

#         --- SPECIFICATION DATA ---
#         {json.dumps(spec_data, indent=2)}

#         --- DESIGN DATA ---
#         {json.dumps(design_data, indent=2)}
#         """
        
#         print("\n--- Starting AutoGen Conversation... ---")
#         user_proxy.initiate_chat(
#             manager,
#             message=initial_message,
#         )
        
#         print("\n--- AutoGen Conversation Finished. ---")
#         print(f"Check the '{coding_config.base_output_dir}' directory for the generated project.")

#         # --- Next Steps Placeholder ---
#         # At this point, `design_data` holds the detailed design.
#         # This `design_data` would then be passed as input to your
#         # Coding Agent and the subsequent iterative development, testing, and debugging phase.
#         # This is where AutoGen's ConversableAgent, GroupChat, and GroupChatManager
#         # will become the primary orchestration tools, allowing agents to interact dynamically.
#         # We will build this part in the next steps.    
#     except ImportError as e:
#         logger.exception(f"Import error: {e}")
#         print(f"\nImport error occurred: {e}")
#         print("Please make sure all dependencies are installed. Run 'pip install -r requirements.txt'")
#     except ValueError as e:
#         logger.exception(f"Value error: {e}")
#         print(f"\nInput or configuration error: {e}")
#     except (KeyError, TypeError) as e:
#         logger.exception(f"Data structure error: {e}")
#         print(f"\nError in processing data structures: {e}")
#         print("This may be due to unexpected response format from the model.")
#     except Exception as e:
#         logger.exception(f"An error occurred during orchestration: {e}")
#         print(f"\nAn unexpected error occurred: {e}")
#         print("Please check the logs for more details.")

# if __name__ == "__main__":
#     main()