import traceback
from typing import Any, AsyncGenerator, Union
from a2a_servers.common.server import utils
from a2a_servers.common.server.task_manager import InMemoryTaskManager
from a2a_servers.common.types import (
    SendTaskRequest,
    TaskSendParams,
    Message,
    TaskStatus,
    Artifact,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
    TextPart,
    TaskState,
    Task,
    SendTaskResponse,
    InternalError,
    JSONRPCResponse,
    SendTaskStreamingRequest,
    SendTaskStreamingResponse,
)
import json
from typing import AsyncIterable

# Dùng để tích hợp 1 agent cụ thể vào hệ thống quản lý tác vụ, kế thừa mọi thứ từu InMemoryTaskManager
class AgentTaskManager(InMemoryTaskManager):
    def __init__(self, agent: Any):
        super().__init__()
        self.agent = agent

    # Tạo một generator bất đồng bộ để xử lý yêu cầu streaming (SendTaskStreamingRequest), gửi các sự kiện cập nhật trạng thái và hiện vật đến client.
    # Được gọi bởi on_send_task_subscribe để xử lý yêu cầu streaming.
    async def _stream_generator(
        self, request: SendTaskStreamingRequest
    ) -> AsyncGenerator[SendTaskStreamingResponse | JSONRPCResponse, Any]:
        task_send_params: TaskSendParams = request.params
        query = self._get_user_query(task_send_params)
        try:
          async for item in self.agent.stream(query, task_send_params.sessionId):
            is_task_complete = item["is_task_complete"]
            artifacts = None
            if not is_task_complete:
              task_state = TaskState.WORKING
              parts = [{"type": "text", "text": item["updates"]}]
            else:
              if isinstance(item["content"], dict):
                if ("response" in item["content"]
                    and "result" in item["content"]["response"]):
                  data = json.loads(item["content"]["response"]["result"])
                  task_state = TaskState.INPUT_REQUIRED
                else:
                  data = item["content"]
                  task_state = TaskState.COMPLETED
                parts = [{"type": "data", "data": data}]
              else:
                task_state = TaskState.COMPLETED
                parts = [{"type": "text", "text": item["content"]}]
              artifacts = [Artifact(parts=parts, index=0, append=False)]
          message = Message(role="agent", parts=parts)
          task_status = TaskStatus(status=task_state, message=message)
          await self._update_store(task_send_params.id, task_status, artifacts)
          task_update_event = TaskStatusUpdateEvent(
                id=task_send_params.id,
                status=task_status,
                final=False,
            )
          yield SendTaskStreamingResponse(id=request.id, result=task_update_event)
          if artifacts:
            for artifact in artifacts:
              yield SendTaskStreamingResponse(
                  id=request.id,
                  result=TaskArtifactUpdateEvent(
                      id=task_send_params.id,
                      artifact=artifact,
                  )
              )
          if is_task_complete:
            yield SendTaskStreamingResponse(
              id=request.id,
              result=TaskStatusUpdateEvent(
                  id=task_send_params.id,
                  status=TaskStatus(
                      state=task_status.status,
                  ),
                  final=True
              )
            )
        except Exception as e:
            yield JSONRPCResponse(
                id=request.id,
                error=InternalError(
                    message="An error occurred while streaming the response"
                ),
            )

    # Kiểm tra tính tương thích của chế độ đầu ra giữa client và agent.
    # Được gọi bởi on_send_task và on_send_task_subscribe để xác thực yêu cầu trước khi xử lý.
    def _validate_request(
        self, request: Union[SendTaskRequest, SendTaskStreamingRequest]
    ):
        task_send_params: TaskSendParams = request.params
        if not utils.are_modalities_compatible(task_send_params.acceptedOutputModes, self.agent.SUPPORTED_CONTENT_TYPES):
            return utils.new_incompatible_types_error(request.id)
    
    # Xử lý yêu cầu gửi tác vụ đồng bộ (SendTaskRequest), trả về SendTaskResponse.
    # Client gọi phương thức tasks/send để gửi tác vụ và nhận phản hồi ngay lập tức.
    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        error = self._validate_request(request)
        if error:
            return error
        await self.upsert_task(request.params)
        return await self._invoke(request)
    
    # Xử lý yêu cầu gửi tác vụ streaming (SendTaskStreamingRequest), trả về AsyncIterable chứa các sự kiện.
    # Client gọi phương thức tasks/sendSubscribe để nhận cập nhật thời gian thực.
    async def on_send_task_subscribe(
        self, request: SendTaskStreamingRequest
    ) -> AsyncIterable[SendTaskStreamingResponse] | JSONRPCResponse:
        error = self._validate_request(request)
        if error:
            return error
        await self.upsert_task(request.params)
        return self._stream_generator(request)
    
    # Cập nhật trạng thái và hiện vật của một tác vụ trong self.tasks.
    # Được gọi bởi _stream_generator và _invoke để lưu trạng thái và hiện vật.
    async def _update_store(
        self, task_id: str, status: TaskStatus, artifacts: list[Artifact]
    ) -> Task:
        async with self.lock:
            try:
                task = self.tasks[task_id]
            except KeyError:
                raise ValueError(f"Task {task_id} not found")
            task.status = status
            if artifacts is not None:
                if task.artifacts is None:
                    task.artifacts = []
                task.artifacts.extend(artifacts)
            return task

    # Xử lý yêu cầu đồng bộ bằng cách gọi self.agent.invoke.
    # Được gọi bởi on_send_task để xử lý yêu cầu đồng bộ.
    async def _invoke(self, request: SendTaskRequest) -> SendTaskResponse:
        task_send_params: TaskSendParams = request.params
        query = self._get_user_query(task_send_params)
        task_id=task_send_params.id
        try:
            result = await self.agent.invoke(query, task_send_params.sessionId, task_id) # bug bị thiếu param taskID do trong hàm invoke() trong adk_agent.py, state={}.
        except Exception as e:
            raise ValueError(f"Error invoking agent: {e}")
        parts = [{"type": "text", "text": result}]
        task_state = TaskState.INPUT_REQUIRED if "MISSING_INFO:" in result else TaskState.COMPLETED
        task = await self._update_store(
            task_send_params.id,
            TaskStatus(
                status=task_state, message=Message(role="agent", parts=parts)
            ),
            [Artifact(parts=parts)],
        )
        return SendTaskResponse(id=request.id, result=task)

    # Lấy văn bản yêu cầu từ task_send_params.message.parts[0].
    # Được gọi bởi _stream_generator và _invoke để lấy nội dung yêu cầu.
    def _get_user_query(self, task_send_params: TaskSendParams) -> str:
        part = task_send_params.message.parts[0]
        return part.text