# this class is used to bridge the Google ADK framework with the A2A protocol, allowing agents to communicate and coordinate tasks

import base64
import json
import uuid
from typing import Any, AsyncIterable, Dict, List

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import LlmAgent, Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext
from google.genai import types

class ADKAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain",] # don't get it 
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
