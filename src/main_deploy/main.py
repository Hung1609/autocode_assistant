import logging
import os
import json
import time
import subprocess
import subprocess

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

try:
    from google.genai.errors import ClientError
except ImportError:
    ClientError = Exception  # Fallback if import fails

# --- Third-Party Libraries ---
import autogen

# Get a logger for this module, which will use the global config.
logger = logging.getLogger(__name__)


def run_autogen_coding_crew(spec_data: dict, design_data: dict) -> str:
    """
    Phase 3: Generate project code with robust rate limiting and retry logic.
    """
    import autogen

    try:
        # Determine project path
        project_name_slug = design_data.get('folder_Structure', {}).get('root_Project_Directory_Name')
        if not project_name_slug:
            project_name = design_data.get("project_name", "unnamed_project")
            project_name_slug = project_name.lower().replace(" ", "_")
        
        project_root_path = os.path.abspath(os.path.join(config.BASE_OUTPUT_DIR, project_name_slug))
        logger.info(f"Code will be generated in: {project_root_path}")
        os.makedirs(project_root_path, exist_ok=True)

        # Initialize the coding agent
        try:
            coding_agent_config = AgentConfig.from_central_config()
            coding_agent_instance = LangChainCodingAgent(coding_agent_config)
        except:
            # Fallback initialization
            coding_agent_instance = LangChainCodingAgent(
                model_name=config.CURRENT_MODELS['coding'],
                config=AgentConfig(),
            )

        # First attempt: Direct code generation with rate limiting
        max_direct_attempts = 3
        for attempt in range(max_direct_attempts):
            try:
                logger.info(f"🔧 Direct attempt {attempt + 1}/{max_direct_attempts}: Generating code...")
                result = coding_agent_instance.generate_project(design_data, spec_data)
                logger.info(f"🎉 Direct code generation successful: {result}")
                
                # Verify files were created
                if verify_code_generation(project_root_path):
                    # Set up project environment (venv, dependencies)
                    logger.info("🔧 Setting up project environment after direct generation...")
                    if not setup_project_environment(project_root_path):
                        logger.warning("⚠️  Environment setup via run.bat failed, trying manual setup...")
                        if not create_venv_manually(project_root_path):
                            logger.warning("⚠️  Failed to create virtual environment manually")
                    
                    return project_root_path
                else:
                    logger.warning(f"⚠️  Direct attempt {attempt + 1}: No files generated")
                    
            except ClientError as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait_time = 60 + (attempt * 30)  # Increasing wait time
                    logger.warning(f"⚠️  Rate limit hit. Waiting {wait_time} seconds...")
                    if attempt < max_direct_attempts - 1:
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error("❌ All direct attempts failed due to rate limits")
                        break
                else:
                    logger.error(f"❌ API error: {e}")
                    break
            except Exception as e:
                logger.error(f"❌ Direct attempt {attempt + 1} failed: {e}")
                if attempt < max_direct_attempts - 1:
                    time.sleep(10)
                    continue
                else:
                    break

        # Second attempt: AutoGen with rate limiting
        logger.info("🔄 Trying AutoGen approach with enhanced rate limiting...")
        
        # Configure AutoGen with conservative settings
        autogen_llm_config = {
            "config_list": [{
                "model": config.CURRENT_MODELS['coding'],
                "api_key": config.GEMINI_API_KEY,
                "api_type": "google"
            }],
            "temperature": 0.3,
            "timeout": 300,
            "request_timeout": 300,
        }

        # Create agents with very clear instructions
        project_manager = autogen.AssistantAgent(
            name="ProjectManager",
            system_message="""You are a project manager. Your ONLY task is to instruct the Coder to call generate_project().
            
            INSTRUCTIONS:
            1. Tell the Coder to call generate_project(design_data, spec_data) immediately
            2. Do NOT ask questions or request clarifications
            3. After the function executes successfully, say "TERMINATE"
            4. If there's a rate limit error, wait 60 seconds and try again
            """,
            llm_config=autogen_llm_config,
        )

        coder = autogen.AssistantAgent(
            name="Coder",
            system_message="""You are a coder. When instructed, call generate_project() function immediately.
            
            CRITICAL:
            - Call generate_project(design_data, spec_data) using the provided data
            - DO NOT write code in chat
            - If rate limited, wait 60 seconds and retry
            - Report success/failure clearly
            """,
            llm_config=autogen_llm_config,
        )

        # Rate-limited function wrapper
        def rate_limited_generate_project(design_data: dict, spec_data: dict) -> str:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"🔧 AutoGen function call attempt {attempt + 1}/{max_retries}...")
                    result = coding_agent_instance.generate_project(design_data, spec_data)
                    logger.info(f"🎉 AutoGen generation successful: {result}")
                    return result
                except ClientError as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        wait_time = 60 + (attempt * 30)
                        logger.warning(f"⚠️  Function call rate limited. Waiting {wait_time}s...")
                        if attempt < max_retries - 1:
                            time.sleep(wait_time)
                            continue
                        else:
                            raise Exception("Rate limit exhausted in function calls")
                    else:
                        raise
                except Exception as e:
                    logger.error(f"❌ Function call error: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(15)
                        continue
                    else:
                        raise

        user_proxy = autogen.UserProxyAgent(
            name="UserProxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=3,  # Keep it short
            is_termination_msg=lambda x: "TERMINATE" in x.get("content", "").upper(),
            code_execution_config={"work_dir": project_root_path, "use_docker": False},
            function_map={"generate_project": rate_limited_generate_project}
        )

        # Start conversation
        groupchat = autogen.GroupChat(
            agents=[user_proxy, project_manager, coder], 
            messages=[], 
            max_round=6  # Keep it minimal
        )
        manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=autogen_llm_config)

        # Clear, direct message
        initial_message = f"""
        IMMEDIATE ACTION REQUIRED:
        
        ProjectManager: Tell Coder to call generate_project() NOW.
        Coder: Call generate_project(design_data, spec_data) immediately.
        
        Data:
        SPEC: {json.dumps(spec_data, indent=1)}
        DESIGN: {json.dumps(design_data, indent=1)}
        
        NO DISCUSSION. EXECUTE NOW.
        """

        logger.info("🚀 Starting AutoGen with rate limiting...")
        
        max_autogen_attempts = 2
        for autogen_attempt in range(max_autogen_attempts):
            try:
                user_proxy.initiate_chat(manager, message=initial_message)
                break  # Success
            except ClientError as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    if autogen_attempt < max_autogen_attempts - 1:
                        logger.warning(f"⚠️  AutoGen rate limited. Waiting 90 seconds...")
                        time.sleep(90)
                        continue
                    else:
                        raise Exception("AutoGen conversation rate limited")
                else:
                    raise

        # Final verification
        if verify_code_generation(project_root_path):
            # Set up project environment (venv, dependencies)
            logger.info("🔧 Setting up project environment...")
            if not setup_project_environment(project_root_path):
                logger.warning("⚠️  Environment setup via run.bat failed, trying manual setup...")
                if not create_venv_manually(project_root_path):
                    logger.error("❌ Failed to create virtual environment")
                    # Don't fail the entire process, just warn
                    logger.warning("⚠️  Continuing without venv - testing phase may fail")
            
            return project_root_path
        else:
            raise Exception("No files were generated despite successful execution")

    except Exception as e:
        logger.error(f"❌ Code generation completely failed: {e}", exc_info=True)
        raise


def verify_code_generation(project_root_path: str) -> bool:
    """Verify that code files were actually generated."""
    if not os.path.exists(project_root_path):
        logger.error(f"❌ Project directory doesn't exist: {project_root_path}")
        return False
    
    project_files = []
    for root, dirs, files in os.walk(project_root_path):
        project_files.extend(files)
    
    if len(project_files) > 0:
        logger.info(f"✅ Verification: Found {len(project_files)} files in project")
        return True
    else:
        logger.error("❌ Verification: No files found in project directory")
        return False
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
        - The function takes two parameters: design_data (dict) and spec_data (dict).
        - Once the Coder agent confirms successful generation (by reporting the output of the function), you MUST reply with the word 'TERMINATE'.
        - If there are any errors, do not terminate - try to resolve them first.
        """,
        llm_config=autogen_llm_config,
    )

    coder = autogen.AssistantAgent(
        name="Coder",
        system_message="""
        You are an expert software engineer. You will receive instructions from the ProjectManager.
        - Your main tool is 'generate_project'. When asked to implement the project, you MUST call this function with the provided design and specification data.
        - The function signature is: generate_project(design_data: dict, spec_data: dict) -> str
        - DO NOT write code directly in the chat.
        - Call the function using the exact design_data and spec_data provided in the conversation.
        - Report the result of the function call back to the ProjectManager.
        - If there are errors, report them clearly to the ProjectManager.
        """,
        llm_config=autogen_llm_config,
    )

    # Create a wrapper function with better error handling and logging
    def wrapped_generate_project(design_data: dict, spec_data: dict) -> str:
        try:
            logger.info("🔧 Starting code generation via AutoGen function call...")
            result = coding_agent_instance.generate_project(design_data, spec_data)
            logger.info(f"🎉 Code generation completed successfully: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ Code generation failed: {e}", exc_info=True)
            raise

    user_proxy = autogen.UserProxyAgent(
        name="UserProxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=10,  # Increased from 5 to allow more conversation
        is_termination_msg=lambda x: "TERMINATE" in x.get("content", "").upper(),
        code_execution_config={"work_dir": project_root_path, "use_docker": False},
        function_map={"generate_project": wrapped_generate_project}
    )

    # --- Start the Conversation ---
    groupchat = autogen.GroupChat(
        agents=[user_proxy, project_manager, coder], messages=[], max_round=30  # Increased from 15
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

    # Verify that code was actually generated
    if os.path.exists(project_root_path):
        # Check if any files were created in the project directory
        project_files = []
        for root, dirs, files in os.walk(project_root_path):
            project_files.extend(files)
        
        if len(project_files) > 0:
            logger.info(f"✅ Verification: Found {len(project_files)} files in generated project")
        else:
            logger.warning("⚠️  Warning: No files found in project directory. Code generation may have failed.")
            # Fallback already attempted in the new implementation
            logger.error("❌ Code generation verification failed")


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


def setup_project_environment(project_root_path: str) -> bool:
    """
    Set up the project environment by creating venv and installing dependencies.
    """
    try:
        logger.info("🔧 Setting up project environment...")
        
        # Check if venv already exists
        venv_path = os.path.join(project_root_path, "venv")
        venv_python = os.path.join(venv_path, "Scripts", "python.exe")
        
        if os.path.exists(venv_python):
            logger.info("✅ Virtual environment already exists")
            return True
            
        logger.info("🚀 Creating virtual environment...")
        
        # Create a setup-only batch script that doesn't start the server
        setup_bat_content = f"""@echo off
setlocal EnableDelayedExpansion

:: Setup project environment without starting server
echo Setting up project environment...

:: Set project root
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

:: Check for Python
"{config.PYTHON_EXECUTABLE}" --version
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python is not installed.
    exit /b 1
)

:: Create virtual environment
echo Creating virtual environment...
"{config.PYTHON_EXECUTABLE}" -m venv "venv"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to create virtual environment.
    exit /b 1
)

:: Activate virtual environment
call "venv\\Scripts\\activate.bat"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to activate virtual environment.
    exit /b 1
)

:: Install dependencies
if exist "requirements.txt" (
    echo Installing dependencies...
    pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to install dependencies.
        exit /b 1
    )
    echo Dependencies installed successfully.
) else (
    echo WARNING: requirements.txt not found.
)

echo Environment setup completed successfully.
exit /b 0
"""
        
        # Write and execute setup script
        setup_bat_path = os.path.join(project_root_path, "setup_env.bat")
        with open(setup_bat_path, 'w', encoding='utf-8') as f:
            f.write(setup_bat_content)
        
        logger.info("🚀 Executing environment setup script...")
        result = subprocess.run(
            f'"{setup_bat_path}"',
            shell=True,
            cwd=project_root_path,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Clean up setup script
        try:
            os.remove(setup_bat_path)
        except:
            pass
        
        if result.returncode == 0:
            logger.info("✅ Environment setup completed successfully")
            logger.debug(f"Setup output: {result.stdout}")
            return True
        else:
            logger.error(f"❌ Environment setup failed: {result.stderr}")
            logger.debug(f"Setup stdout: {result.stdout}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Environment setup timed out")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to setup project environment: {e}")
        return False


def create_venv_manually(project_root_path: str) -> bool:
    """
    Manually create virtual environment if run.bat fails.
    """
    try:
        logger.info("🔧 Manually creating virtual environment...")
        
        # Create virtual environment
        venv_path = os.path.join(project_root_path, "venv")
        result = subprocess.run(
            [config.PYTHON_EXECUTABLE, "-m", "venv", venv_path],
            capture_output=True,
            text=True,
            cwd=project_root_path
        )
        
        if result.returncode != 0:
            logger.error(f"❌ Failed to create venv: {result.stderr}")
            return False
            
        # Install requirements if they exist
        requirements_path = os.path.join(project_root_path, "requirements.txt")
        if os.path.exists(requirements_path):
            venv_pip = os.path.join(venv_path, "Scripts", "pip.exe")
            result = subprocess.run(
                [venv_pip, "install", "-r", requirements_path],
                capture_output=True,
                text=True,
                cwd=project_root_path
            )
            
            if result.returncode == 0:
                logger.info("✅ Dependencies installed successfully")
            else:
                logger.warning(f"⚠️  Failed to install dependencies: {result.stderr}")
        
        # Verify venv creation
        venv_python = os.path.join(venv_path, "Scripts", "python.exe")
        if os.path.exists(venv_python):
            logger.info("✅ Virtual environment created manually")
            return True
        else:
            logger.error("❌ Manual venv creation failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Manual venv creation failed: {e}")
        return False