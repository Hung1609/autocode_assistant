
# this class is used to bridge the Google ADK framework with the A2A protocol, allowing agents to communicate and coordinate tasks
class ADKAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain",]
    def __init__(
        self,
        model: str, # model used for the agent
        name: str, # name of the agent
        description: str, # description of the agent
        instructions: str, # instructions for the agent
        tools: list[Any], # tools the agent can use
        is_host_agent: bool = False,
        # is_host_agent=False --> A standalone agent, which acts as a regular ADK agent with its own tools and capabilities.
        # is_host_agent=True --> A host agent, which acts as a coordinator for other agents and can delegate tasks to them
        remote_agent_addresses: list[str] = None, # the addresses of the remote agents
        task_callback: TaskUpdateCallback | None = None,
    ):
