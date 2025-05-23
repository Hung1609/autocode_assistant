import asyncio
from dotenv import load_dotenv, find_dotenv
from a2a_servers.agent_servers.utils import generate_agent_task_manager, generate_agent_card
from a2a_servers.agents.adk_agent import ADKAgent
from a2a_servers.common.server.server import A2AServer
from a2a_servers.common.types import AgentSkill
from mcp_servers.mcp_tools.mcp_tool_file_system import return_sse_mcp_tools_file_system
from a2a_servers.common.prompt.prompt import DESIGN_PROMPT

load_dotenv(find_dotenv())

async def run_agent():
    AGENT_NAME = "design_agent"
    AGENT_DESCRIPTION = "An agent that generates a detailed system design specification from a requirements specification."
    PORT = 10000
    HOST = "0.0.0.0"
    AGENT_URL = f"http://{HOST}:{PORT}"
    AGENT_VERSION = "1.0.0"
    MODEL = "gemini-2.5-pro-preview-05-06"
    AGENT_SKILLS = [
        AgentSkill(
            id="SYSTEM_DESIGN",
            name="system_design",
            description="Generates structured JSON system design specifications from requirements.",
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

    design_agent = ADKAgent(
        model=MODEL,
        name="design_agent",
        description="Generates a detailed system design specification from a requirements specification.",
        instructions=(
            "You are an expert system designer. Use the following prompt template to analyze the JSON requirements specification received in the message and generate a structured JSON system design specification. The JSON specification will be provided in the message's text content. Follow the instructions in the prompt strictly:\n\n"
            f"{DESIGN_PROMPT}"
        ),
        tools=filesystem_tools,
        is_host_agent=False,
    )

    task_manager = generate_agent_task_manager(
        agent=design_agent,
    )

    server = A2AServer(
        host=HOST,
        port=PORT,
        endpoint="/design_agent",
        agent_card=AGENT_CARD,
        task_manager=task_manager
    )

    print(f"Starting {AGENT_NAME} A2A Server on {AGENT_URL}")
    await server.astart()

if __name__ == "__main__":
    asyncio.run(
        run_agent()
    )