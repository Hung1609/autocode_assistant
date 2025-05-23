import asyncio
from dotenv import load_dotenv, find_dotenv
from a2a_servers.agent_servers.utils import generate_agent_task_manager, generate_agent_card
from a2a_servers.agents.adk_agent import ADKAgent
from a2a_servers.common.server.server import A2AServer
from a2a_servers.common.types import AgentSkill
from mcp_servers.mcp_tools.mcp_tool_file_system import return_sse_mcp_tools_file_system
from a2a_servers.common.prompt.prompt import SPECIFICATION_PROMPT

load_dotenv(find_dotenv())

async def run_agent():
    AGENT_NAME = "specification_agent"
    AGENT_DESCRIPTION = "An agent that analyzes user requirements and generates structured JSON specifications."
    PORT = 11000
    HOST = "0.0.0.0"
    AGENT_URL = f"http://{HOST}:{PORT}"
    AGENT_VERSION = "1.0.0"
    MODEL = "gemini-2.5-pro-preview-05-06"
    AGENT_SKILLS = [
        AgentSkill(
            id="REQUIREMENTS_AGENT_ANALYSIS",
            name="requirements_analysis",
            description="Analyzes user requirements and generates structured JSON specifications.",
        ),
    ]

    AGENT_CARD = generate_agent_card(
        agent_name=AGENT_NAME,
        agent_description=AGENT_DESCRIPTION,
        agent_url=AGENT_URL,
        agent_version=AGENT_VERSION,
        can_stream=False,
        can_push_notifications=False,
        can_state_transition_history=True,
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=AGENT_SKILLS,
    )

    filesystem_tools, filesystem_exit_stack = await return_sse_mcp_tools_file_system()

    specification_agent = ADKAgent(
        model=MODEL,
        name="specification_agent",
        description="Analyzes user requirements and generates structured JSON specifications.",
        instructions=(
            "You are an expert requirements analyst. Use the following prompt template to analyze the user_provided project description received in the message and generate a structured JSON specification. The user description will be provided in the message's text content. Follow the instructions in the prompt strictly:\n\n"
            f"{SPECIFICATION_PROMPT}"
        ),
        tools=filesystem_tools,
        is_host_agent=False,
    )

    task_manager = generate_agent_task_manager(
        agent=specification_agent,
    )

    server = A2AServer(
        host=HOST,
        port=PORT,
        endpoint="/specification_agent",
        agent_card=AGENT_CARD,
        task_manager=task_manager
    )

    print(f"Starting {AGENT_NAME} A2A Server on {AGENT_URL}")
    await server.astart()

if __name__ == "__main__":
    asyncio.run(
        run_agent()
    )