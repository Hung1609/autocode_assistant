import asyncio
from dotenv import load_dotenv, find_dotenv
import os
from a2a_servers.agent_servers.utils import generate_agent_card, generate_agent_task_manager
from a2a_servers.agents.adk_agent import ADKAgent
from a2a_servers.common.server.server import A2AServer
from a2a_servers.common.types import AgentSkill

load_dotenv(find_dotenv()) # for what???

async def run_agent():
    AGENT_NAME = "host_agent"
    AGENT_DESCRIPTION = "An agent orchestrates the decomposition of the user request into tasks that can be performed by the child agents."
    PORT = 12000
    HOST = "0.0.0.0"
    AGENT_URL = f"http://{HOST}:{PORT}"
    AGENT_VERSION = "1.0.0"
    MODEL = "gemini-2.0-flash"
    AGENT_SKILLS = [
        AgentSkill(
            id="COORDINATE_AGENT_TASKS",
            name="coordinate_tasks",
            description="coordinate tasks between agents.",
        ),
    ]

    list_urls = [
        "http://localhost:11000/specification_agent",
        "http://localhost:10000/design_agent"
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

    host_agent = ADKAgent(
        model=MODEL,
        name="host_agent",
        description="coordinate tasks between agents.",
        tools=[],
        instructions="""
            You are a project manager. Your responsibilities are:
            1. Receive the user's request
            2. Analyze the request and break it down into clear, actionable tasks.
            3. Assign each task to the appropriate specialized agent based on their skillset and role.
            4. Manage the workflow by coordinating task execution among agents without asking the user for further clarifications.
            5. Monitor progress, handle dependencies between tasks, and ensure smooth communication between agents.
            6. Handle exceptions or incomplete information by making intelligent decisions

            You act autonomously to ensure efficient task distribution and project completion, simulating how a project manager leads a software development team.
            """,
        is_host_agent=True,
        remote_agent_addresses=list_urls,
    )

    task_manager = generate_agent_task_manager(
        agent=host_agent,
    )

    server = A2AServer(
        host=HOST,
        port=PORT,
        endpoint="/host_agent",
        agent_card=AGENT_CARD,
        task_manager=task_manager
    )

    print(f"Starting {AGENT_NAME} A2A Server on {AGENT_URL}")
    await server.astart()

if __name__ == "__main__":
    asyncio.run(
        run_agent()
    )