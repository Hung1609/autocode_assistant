from typing import Any, List
from a2a_servers.common.agent_task_manager import AgentTaskManager
from a2a_servers.common.types import AgentCapabilities, AgentCard, AgentSkill

# Generates an agent card for the Echo Agent
def generate_agent_card(
    agent_name: str,
    agent_description: str,
    agent_url: str, # The URL where the agent is hosted.
    agent_version: str, # The version of the agent.
    can_stream: bool = False, # Whether the agent can stream responses.
    can_push_notifications: bool = False, # Whether the agent can send push notifications.
    can_state_transition_history: bool = True, # Whether the agent can maintain state transition history.
    authentication: str = None, # The authentication method for the agent.
    default_input_modes: List[str] = ["text"], # The default input modes for the agent. Can be "text", "voice", "image"
    default_output_modes: List[str] = ["text"], # The default output modes for the agent.
    skills: List[AgentSkill] = None, # The skills of the agent.
):
    return AgentCard(
        name=agent_name,
        description=agent_description,
        url=agent_url,
        version=agent_version,
        capabilities=AgentCapabilities(
            streaming=can_stream,
            pushNotifications=can_push_notifications,
            stateTransitionHistory=can_state_transition_history,
        ),
        authentication=authentication,
        defaultInputModes=default_input_modes,
        defaultOutputModes=default_output_modes,
        skills=skills,
    )

# Generates an agent task manager for the Echo Agent.
def generate_agent_task_manager(
        agent: Any, # agent instance
):
    return AgentTaskManager(agent)