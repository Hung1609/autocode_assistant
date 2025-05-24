import asyncio
import traceback
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from starlette.requests import Request
from a2a_servers.common.types import (
    A2ARequest,
    JSONRPCResponse,
    InvalidRequestError,
    JSONParseError,
    GetTaskRequest,
    CancelTaskRequest,
    SendTaskRequest,
    SetTaskPushNotificationRequest,
    GetTaskPushNotificationRequest,
    InternalError,
    AgentCard,
    TaskResubscriptionRequest,
    SendTaskStreamingRequest,
)
from pydantic import ValidationError
import json
from typing import AsyncIterable, Any
from a2a_servers.common.server.task_manager import TaskManager
import logging

logger = logging.getLogger(__name__)

# To make the agent "connectable", we immplement the A2A server.
# The server is responsible for handling incoming requests from other agents and managing the communication protocol.

# The server is initialized with:

# - Host and port configuration
# - An endpoint for handling requests
# - An agent card describing the agent's capabilities
# - A task manager for handling task execution
class A2AServer:
    def __init__(
        self,
        host="0.0.0.0",
        port=5000,
        endpoint="/",
        agent_card: AgentCard = None,
        task_manager: TaskManager = None,
    ):
        self.host = host
        self.port = port
        self.endpoint = endpoint
        self.agent_card = agent_card
        self.task_manager = task_manager
        self.app = Starlette()
        self.app.add_route(self.endpoint, self._process_request, methods=["POST"])
        self.app.add_route(
            "/.well-known/agent.json", self._get_agent_card, methods=["GET"]
        )

    # this is the original implementation
    # the problem is it block the main thread because:
    # - It couldn't be integrated into an existing async event loop
    # - It made it difficult to coordinate with other async components (like MCP tools)
    def start(self):
        if self.agent_card is None:
            raise ValueError("agent_card is not defined")
        if self.task_manager is None:
            raise ValueError("request_handle is not defined")
        uvicorn.run(self.app, host=self.host, port=self.port)

    # The "astart" method is an upgrade from the original Google implementation which is the "start" method above
    # the advantages of this method:
    # - Creates a Uvicorn server with an async event loop
    # - Starts the server in the background using asyncio.create_task
    # - Waits for the server to be fully started
    # - Handles graceful shutdown on keyboard interrupt
    # - Can be integrated into an existing async application

    # This change was necessary because:

    # - MCP tools are inherently asynchronous
    # - The server needs to be able to run alongside other async components
    # - We need proper control over the server lifecycle
    async def astart(self): # astart means asynchronous startup
        if self.agent_card is None:
            raise ValueError("agent_card is not defined")
        if self.task_manager is None:
            raise ValueError("request_handler is not defined")
        config = uvicorn.Config(self.app, host=self.host, port=self.port, loop="asyncio")
        server = uvicorn.Server(config)

        # start in the background
        server_task = asyncio.create_task(server.serve())

        # wait for startup
        while not server.started:
            await asyncio.sleep(0.5)
        print("Server is up - press Ctrl+C to shut it down manually")

        try:
            await server_task
        except KeyboardInterrupt:
            server.should_exit = True
            await server_task

    def _get_agent_card(self, request: Request) -> JSONResponse:
        return JSONResponse(self.agent_card.model_dump(exclude_none=True))
    
    # The server processes different types of requests:
    # - Task creation and management
    # - Streaming task updates
    # - Push notifications
    # - Task cancellation
    async def _process_request(self, request: Request):
        print("Processing request")
        try:
            body = await request.json()
            json_rpc_request = A2ARequest.validate_python(body)
            if isinstance(json_rpc_request, GetTaskRequest):
                result = await self.task_manager.on_get_task(json_rpc_request)
            elif isinstance(json_rpc_request, SendTaskRequest):
                result = await self.task_manager.on_send_task(json_rpc_request)
            elif isinstance(json_rpc_request, SendTaskStreamingRequest):
                result = await self.task_manager.on_send_task_subscribe(
                    json_rpc_request
                )
            elif isinstance(json_rpc_request, CancelTaskRequest):
                result = await self.task_manager.on_cancel_task(json_rpc_request)
            elif isinstance(json_rpc_request, SetTaskPushNotificationRequest):
                result = await self.task_manager.on_set_task_push_notification(json_rpc_request)
            elif isinstance(json_rpc_request, GetTaskPushNotificationRequest):
                result = await self.task_manager.on_get_task_push_notification(json_rpc_request)
            elif isinstance(json_rpc_request, TaskResubscriptionRequest):
                result = await self.task_manager.on_resubscribe_to_task(
                    json_rpc_request
                )
            else:
                logger.warning(f"Unexpected request type: {type(json_rpc_request)}")
                raise ValueError(f"Unexpected request type: {type(request)}")
            return self._create_response(result)
        
        except Exception as e:
            logger.error(f"traceback --> {traceback.format_exc()}")
            logger.error(f"Error processing request: {e}")
            return self._handle_exception(e)
        
    def _handle_exception(self, e: Exception) -> JSONResponse:
        if isinstance(e, json.decoder.JSONDecodeError):
            json_rpc_error = JSONParseError()
        elif isinstance(e, ValidationError):
            json_rpc_error = InvalidRequestError(data=json.loads(e.json()))
        else:
            logger.error(f"Unhandled exception: {e}")
            json_rpc_error = InternalError()

        response = JSONResponse(content={"id": None, "error": json_rpc_error.model_dump(exclude_none=True)}, status_code=400) #fix bug TypeError: Object of type InvalidRequestError is not JSON serializable bằng cách thêm .model_dump() vào json_rpc_error
        return response
    
    # The server supports two types of responses:
    # - Regular JSON responses for immediate results
    # - Server-Sent Events (SSE) for streaming updates

    # This implementation allows the A2A server to:
    # - Handle multiple concurrent requests
    # - Support streaming responses
    # - Integrate with async components
    # - Provide proper error handling
    # - Support graceful shutdown
    def _create_response(self, result: Any) -> JSONResponse | EventSourceResponse:
        if isinstance(result, AsyncIterable):
            async def event_generator(result) -> AsyncIterable[dict[str, str]]:
                async for item in result:
                    yield {"data": item.model_dump_json(exclude_none=True)}
            return EventSourceResponse(event_generator(result))
        elif isinstance(result, JSONRPCResponse):
            return JSONResponse(result.model_dump(exclude_none=True))
        else:
            logger.error(f"Unexpected result type: {type(result)}")
            raise ValueError(f"Unexpected result type: {type(result)}")