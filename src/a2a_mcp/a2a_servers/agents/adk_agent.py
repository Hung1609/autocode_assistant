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

from a2a_servers.common.a2a_client import A2ACardResolver
from a2a_servers.common.types import AgentCard, TaskSendParams, Message, TextPart, TaskState, Task, Part, DataPart
from a2a_servers.agents.utils.remote_agent_connection import TaskUpdateCallback, RemoteAgentConnections

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
        remote_agent_addresses: list[str] = None, # list of the addresses of the remote agents
        task_callback: TaskUpdateCallback | None = None
    ):
        self.task_callback = task_callback
        if is_host_agent:
            self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
            self.cards: dict[str, AgentCard] = {}
            for address in remote_agent_addresses:
                print(f'loading remote agent {address}')
                card_resolver = A2ACardResolver(address)
                print(f'loaded card resolver for {card_resolver.base_url}')
                card = card_resolver.get_agent_card()
                remote_connection = RemoteAgentConnections(card)
                self.remote_agent_connections[card.name] = remote_connection
                self.cards[card.name] = card
            agent_info = []
            for ra in self.list_remote_agents():
                agent_info.append(json.dumps(ra))
            self.agents = '\n'.join(agent_info)
            tools = tools + [
                self.list_remote_agents,
                self.send_task,
            ]
            instructions = self.root_instruction()
            description = "This agent orchestrates the decomposition of the user request into tasks that can be performed by the child agents."
        self._agent = self._build_agent(
            model=model,
            name=name,
            description=description,
            instructions=instructions,
            tools=tools,
        )
        self._user_id = "remote_agent"
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(), # store artifact
            session_service=InMemorySessionService(), # Session management.
            memory_service=InMemoryMemoryService(), # store state/memory
        )

    # handle request from users, return text response
    # Invokes the agent with the given query and session ID.
    async def invoke(self, query, session_id, task_id=None) -> str: # session_id is used to maintain context
        """
        Invokes the agent with the given query and session ID.
        :param query: The query to send to the agent.
        :param session_id: The session ID to use for the agent.
        :return:  The response from the agent.
        """
        session = self._runner.session_service.get_session(
            app_name=self._agent.name, user_id=self._user_id, session_id=session_id
        ) # take or create a new session with parameters
        content = types.Content(
            role="user", parts=[types.Part.from_text(text=query)]
        ) # create content with role as user and content as query 
        if session is None:
            session = self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state={"taskId": task_id} if task_id else {},
                session_id=session_id,
            )
        events_async = self._runner.run_async(
            session_id=session_id, user_id=session.user_id, new_message=content, state={"taskId": task_id} if task_id else {}
        )
        events = []
        async for event in events_async:
            print(event)
            events.append(event)
        if not events or not events[-1].content or not events[-1].content.parts:
            return ""
        return "\n".join([p.text for p in events[-1].content.parts if p.text]) # return the last event which is events[-1]

    # handle request's streaming, return update in real-time
    async def stream(self, query, session_id) -> AsyncIterable[Dict[str, Any]]:
        """
        Streams the response from the agent for the given query and session ID.
        :param query: The query to send to the agent.
        :param session_id: The session ID to use for the agent.
        :return:  An async iterable of the response from the agent.
        """
        session = self._runner.session_service.get_session(
            app_name=self._agent.name, user_id=self._user_id, session_id=session_id
        )
        content = types.Content(
            role="user", parts=[types.Part.from_text(text=query)]
        )
        if session is None:
            session = self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state={},
                session_id=session_id,
            )
        async for event in self._runner.run_async(
            user_id=self._user_id, session_id=session.id, new_message=content
        ):
            if event.is_final_response():
                response = ""
                if event.content and event.content.parts and event.content.parts[0].text:
                    response = "\n".join([p.text for p in event.content.parts if p.text])
                elif event.content and event.content.parts and any([True for p in event.content.parts if p.function_response]):
                    response = next((p.function_response.model_dump() for p in event.content.parts))
                yield {
                    "is_task_complete": True,
                    "content": response,
                }
            else:
                yield {
                    "is_task_complete": False,
                    "updates": "Processing the request...",
                }

    @staticmethod
    def _build_agent( # Create LlmAgent instance with provided parameters.
            model: str,
            name: str,
            description: str,
            instructions: str,
            tools: List[Any],
    ) -> LlmAgent:
        """
        Builds the LLM agent for the reimbursement agent.

        :param model: The model to use for the agent.
        :param name: The name of the agent.
        :param description: The description of the agent.
        :param instructions: The instructions for the agent.
        :param tools: The tools the agent can use.
        :return: The LLM agent.
        """
        return LlmAgent(
            model=model,
            name=name,
            description=description,
            instruction=instructions,
            tools=tools,
        )

    # Register a new remote agent.
    def register_agent_card(self, card: AgentCard):
        remote_connection = RemoteAgentConnections(card)
        self.remote_agent_connections[card.name] = remote_connection
        self.cards[card.name] = card
        agent_info = []
        for ra in self.list_remote_agents():
            agent_info.append(json.dumps(ra))
        self.agents = '\n'.join(agent_info)

    # instruction about information related to how to use tools from list_remote_agents, create_task and list of remote agents from self.agents
    def root_instruction(self) -> str:
        return f"""You are a expert delegator that can delegate the user request to the appropriate remote agents.
        Discovery:
        - You can use `list_remote_agents` to list the available remote agents you
        can use to delegate the task.

        Execution:
        - For actionable tasks, you can use `create_task` to assign tasks to remote agents to perform.
        Be sure to include the remote agent name when you respond to the user.

        You can use `check_pending_task_states` to check the states of the pending
        tasks.

        Please rely on tools to address the request, don't make up the response. If you are not sure, please ask the user for more details.
        Focus on the most recent parts of the conversation primarily.

        If there is an active agent, send the request to that agent with the update task tool.

        Agents:
        {self.agents}
        """
    # Kiểm tra trạng thái phiên để xác định agent đang hoạt động.
    # Xác định agent nào đang xử lý yêu cầu trong phiên hiện tại.
    def check_state(self, context: ReadonlyContext):
        state = context.state
        if ('session_id' in state and 'session_active' in state and state['session_active'] and 'agent' in state):
            return {"active_agent": f'{state["agent"]}'}
        return {"active_agent": "None"}

    # Thiết lập trạng thái phiên trước khi gọi mô hình LLM.
    # Đảm bảo phiên được kích hoạt trước khi xử lý yêu cầu.
    def before_model_callback(self, callback_context: CallbackContext, llm_request):
        state = callback_context.state
        if 'session_active' not in state or not state['session_active']:
            if 'session_id' not in state:
                state['session_id'] = str(uuid.uuid4())
            state['session_active'] = True

    # Liệt kê các agent từ xa có sẵn.
    # Công cụ cho host agent để khám phá các agent con.
    def list_remote_agents(self): # --> List the available remote agents you can use to delegate the task.
        if not self.remote_agent_connections:
            return []

        remote_agent_info = []
        for card in self.cards.values():
            remote_agent_info.append(
                {"name": card.name, "description": card.description}
            )
        return remote_agent_info

    # Gửi tác vụ đến một remote agent và xử lý phản hồi.
    async def send_task(self, agent_name: str, message: str, tool_context: ToolContext):
        """Sends a task either streaming (if supported) or non-streaming.
        This will send a message to the remote agent named agent_name.
        Args:
          agent_name: The name of the agent to send the task to.
          message: The message to send to the agent for the task.
          tool_context: The tool context this method runs in.
        Yields:
          A dictionary of JSON data.
        """
        if agent_name not in self.remote_agent_connections:
            raise ValueError(f"Agent {agent_name} not found")
        state = tool_context.state
        state['agent'] = agent_name
        card = self.cards[agent_name]
        client = self.remote_agent_connections[agent_name]
        if not client:
            raise ValueError(f"Client not available for {agent_name}")
        if 'task_id' in state:
            taskId = state['task_id']
        else:
            taskId = str(uuid.uuid4())
        sessionId = state.get('session_id', "UKN"+str(uuid.uuid4()))
        task: Task
        messageId = ""
        metadata = {}
        if 'input_message_metadata' in state:
            metadata.update(**state['input_message_metadata'])
            if 'message_id' in state['input_message_metadata']:
                messageId = state['input_message_metadata']['message_id']
        if not messageId:
            messageId = str(uuid.uuid4())
        metadata.update(**{'conversation_id': sessionId, 'message_id': messageId})
        request: TaskSendParams = TaskSendParams(
            id=taskId,
            sessionId=sessionId,
            message=Message(
                role="user",
                parts=[TextPart(text=message)],
                metadata=metadata,
            ),
            acceptedOutputModes=["text", "text/plain", "image/png"],
            # pushNotification=None,
            metadata={'conversation_id': sessionId},
        )
        task = await client.send_task(request, self.task_callback)
        # Assume completion unless a state returns that isn't complete
        state['session_active'] = task.status.status not in [
            TaskState.COMPLETED,
            TaskState.CANCELED,
            TaskState.FAILED,
            TaskState.UNKNOWN,
        ]
        if task.status.status == TaskState.INPUT_REQUIRED:
            # Force user input back
            tool_context.actions.skip_summarization = True
            tool_context.actions.escalate = True
        elif task.status.status == TaskState.CANCELED:
            # Open question, should we return some info for cancellation instead
            raise ValueError(f"Agent {agent_name} task {task.id} is cancelled")
        elif task.status.status == TaskState.FAILED:
            # Raise error for failure
            raise ValueError(f"Agent {agent_name} task {task.id} failed")
        response = []
        if task.status.message:
            # Assume the information is in the task message.
            response.extend(convert_parts(task.status.message.parts, tool_context))
        if task.artifacts:
            for artifact in task.artifacts:
                response.extend(convert_parts(artifact.parts, tool_context))
        return response

# Chuyển đổi các Part (từ A2A) thành định dạng phù hợp, xử lý đặc biệt cho tệp.
# Chuyển đổi kết quả từ A2A (Task.status.message.parts, Task.artifacts.parts) thành định dạng Google ADK.
def convert_parts(parts: list[Part], tool_context: ToolContext):
    rval = []
    for p in parts:
        rval.append(convert_part(p, tool_context))
    return rval

def convert_part(part: Part, tool_context: ToolContext):
    if part.type == "text":
        return part.text
    elif part.type == "data":
        return part.data
    elif part.type == "file":
        # Repackage A2A FilePart to google.genai Blob
        # Currently not considering plain text as files
        file_id = part.file.name
        file_bytes = base64.b64decode(part.file.bytes)
        file_part = types.Part(
            inline_data=types.Blob(
                mime_type=part.file.mimeType,
                data=file_bytes))
        tool_context.save_artifact(file_id, file_part)
        tool_context.actions.skip_summarization = True
        tool_context.actions.escalate = True
        return DataPart(data={"artifact-file-id": file_id})
    return f"Unknown type: {part.type}"