from datetime import datetime
from abc import ABC, abstractmethod
from typing import Union, AsyncIterable, List
from a2a_servers.common.types import Task
from a2a_servers.common.types import (
    JSONRPCResponse,
    TaskIdParams,
    TaskQueryParams,
    GetTaskRequest,
    TaskNotFoundError,
    SendTaskRequest,
    CancelTaskRequest,
    TaskNotCancelableError,
    SetTaskPushNotificationRequest,
    GetTaskPushNotificationRequest,
    GetTaskResponse,
    CancelTaskResponse,
    SendTaskResponse,
    SetTaskPushNotificationResponse,
    GetTaskPushNotificationResponse,
    PushNotificationNotSupportedError,
    TaskSendParams,
    TaskStatus,
    TaskState,
    TaskResubscriptionRequest,
    SendTaskStreamingRequest,
    SendTaskStreamingResponse,
    Artifact,
    PushNotificationConfig,
    TaskStatusUpdateEvent,
    JSONRPCError,
    TaskPushNotificationConfig,
    InternalError,
)
from a2a_servers.common.server.utils import new_not_implemented_error
import asyncio
import logging

logger = logging.getLogger(__name__)

# this is an abstract(trừu tượng) base class
# cung cấp 1 giao diện thống nhất để quản lý các tác vụ
class TaskManager(ABC):
    @abstractmethod
    async def on_get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        pass

    @abstractmethod
    async def on_cancel_task(self, request: CancelTaskRequest) -> CancelTaskResponse:
        pass

    @abstractmethod
    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        pass

    @abstractmethod
    async def on_send_task_subscribe(
        self, request: SendTaskStreamingRequest
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        pass

    @abstractmethod
    async def on_set_task_push_notification(
        self, request: SetTaskPushNotificationRequest
    ) -> SetTaskPushNotificationResponse:
        pass

    @abstractmethod
    async def on_get_task_push_notification(
        self, request: GetTaskPushNotificationRequest
    ) -> GetTaskPushNotificationResponse:
        pass

    @abstractmethod
    async def on_resubscribe_to_task(
        self, request: TaskResubscriptionRequest
    ) -> Union[AsyncIterable[SendTaskResponse], JSONRPCResponse]:
        pass

# **phù hợp cho các ứng dụng nhỏ hoặc thử nghiệm, lưu trữ dữ liệu trong RAM để xử lý nhanh, mất khi server khởi động lại??? -> need improve**
# triển khai TaskManager với lưu trữ trong bộ nhớ 
class InMemoryTaskManager(TaskManager):
    def __init__(self):
        self.tasks: dict[str, Task] = {}
        self.push_notification_infos: dict[str, PushNotificationConfig] = {}
        self.lock = asyncio.Lock()
        self.task_sse_subscribers: dict[str, List[asyncio.Queue]] = {} # --> hỗ trợ nhiều client đăng ký nhận sự kiện cho cùng 1 task_id
        self.subscriber_lock = asyncio.Lock()

    # Client gọi phương thức tasks/get để lấy trạng thái, lịch sử, hoặc artifact của tác vụ.
    async def on_get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        logger.info(f"Getting task {request.params.id}")
        task_query_params: TaskQueryParams = request.params

        async with self.lock:
            task = self.tasks.get(task_query_params.id)
            if task is None:
                return GetTaskResponse(id=request.id, error=TaskNotFoundError())

            task_result = self.append_task_history(
                task, task_query_params.historyLength
            )

        return GetTaskResponse(id=request.id, result=task_result)

    # Client gọi phương thức tasks/cancel để hủy tác vụ.
    async def on_cancel_task(self, request: CancelTaskRequest) -> CancelTaskResponse:
        logger.info(f"Cancelling task {request.params.id}")
        task_id_params: TaskIdParams = request.params

        async with self.lock:
            task = self.tasks.get(task_id_params.id)
            if task is None:
                return CancelTaskResponse(id=request.id, error=TaskNotFoundError())

        return CancelTaskResponse(id=request.id, error=TaskNotCancelableError())

    @abstractmethod
    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        pass

    @abstractmethod
    async def on_send_task_subscribe(
        self, request: SendTaskStreamingRequest
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        pass
    
    # Lưu cấu hình thông báo đẩy cho một tác vụ.
    # Được gọi bởi on_set_task_push_notification để thiết lập thông báo đẩy.
    async def set_push_notification_info(self, task_id: str, notification_config: PushNotificationConfig):
        async with self.lock:
            task = self.tasks.get(task_id)
            if task is None:
                raise ValueError(f"Task not found for {task_id}")

            self.push_notification_infos[task_id] = notification_config

        return
    
    # Lấy cấu hình thông báo đẩy cho một tác vụ.
    # Được gọi bởi on_get_task_push_notification để lấy thông tin thông báo đẩy.
    async def get_push_notification_info(self, task_id: str) -> PushNotificationConfig:
        async with self.lock:
            task = self.tasks.get(task_id)
            if task is None:
                raise ValueError(f"Task not found for {task_id}")

            return self.push_notification_infos[task_id]
            
        return
    
    # Kiểm tra xem một tác vụ có cấu hình thông báo đẩy không.
    async def has_push_notification_info(self, task_id: str) -> bool:
        async with self.lock:
            return task_id in self.push_notification_infos
            
    # Xử lý yêu cầu thiết lập thông báo đẩy (SetTaskPushNotificationRequest).
    # Client gọi phương thức tasks/pushNotification/set để thiết lập thông báo đẩy.
    async def on_set_task_push_notification(
        self, request: SetTaskPushNotificationRequest
    ) -> SetTaskPushNotificationResponse:
        logger.info(f"Setting task push notification {request.params.id}")
        task_notification_params: TaskPushNotificationConfig = request.params

        try:
            await self.set_push_notification_info(task_notification_params.id, task_notification_params.pushNotificationConfig)
        except Exception as e:
            logger.error(f"Error while setting push notification info: {e}")
            return JSONRPCResponse(
                id=request.id,
                error=InternalError(
                    message="An error occurred while setting push notification info"
                ),
            )
            
        return SetTaskPushNotificationResponse(id=request.id, result=task_notification_params)

    # Xử lý yêu cầu lấy thông tin thông báo đẩy (GetTaskPushNotificationRequest).
    # Client gọi phương thức tasks/pushNotification/get để lấy thông tin thông báo đẩy.
    async def on_get_task_push_notification(
        self, request: GetTaskPushNotificationRequest
    ) -> GetTaskPushNotificationResponse:
        logger.info(f"Getting task push notification {request.params.id}")
        task_params: TaskIdParams = request.params

        try:
            notification_info = await self.get_push_notification_info(task_params.id)
        except Exception as e:
            logger.error(f"Error while getting push notification info: {e}")
            return GetTaskPushNotificationResponse(
                id=request.id,
                error=InternalError(
                    message="An error occurred while getting push notification info"
                ),
            )
        
        return GetTaskPushNotificationResponse(id=request.id, result=TaskPushNotificationConfig(id=task_params.id, pushNotificationConfig=notification_info))

    # Tạo hoặc cập nhật (upsert) một tác vụ trong self.tasks.
    # Được gọi khi xử lý SendTaskRequest để khởi tạo hoặc cập nhật tác vụ.
    async def upsert_task(self, task_send_params: TaskSendParams) -> Task:
        logger.info(f"Upserting task {task_send_params.id}")
        async with self.lock:
            task = self.tasks.get(task_send_params.id)
            if task is None:
                task = Task(
                    id=task_send_params.id,
                    sessionId = task_send_params.sessionId,
                    messages=[task_send_params.message],
                    status=TaskStatus(status=TaskState.SUBMITTED), # fix bug bằng cách tham chiếu đối số với TaskStatus và sửa syntax từ state sang status
                    history=[task_send_params.message],
                )
                self.tasks[task_send_params.id] = task
            else:
                task.history.append(task_send_params.message)

            return task

    # Xử lý yêu cầu đăng ký lại để nhận cập nhật tác vụ.
    # Client gọi phương thức tasks/resubscribe, nhưng chức năng chưa được triển khai.
    async def on_resubscribe_to_task(
        self, request: TaskResubscriptionRequest
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        return new_not_implemented_error(request.id)

    # Cập nhật trạng thái và hiện vật của một tác vụ.
    # Được gọi khi trạng thái tác vụ thay đổi hoặc có hiện vật mới.
    async def update_store(
        self, task_id: str, status: TaskStatus, artifacts: list[Artifact]
    ) -> Task:
        async with self.lock:
            try:
                task = self.tasks[task_id]
            except KeyError:
                logger.error(f"Task {task_id} not found for updating the task")
                raise ValueError(f"Task {task_id} not found")

            task.status = status

            if status.message is not None:
                task.history.append(status.message)

            if artifacts is not None:
                if task.artifacts is None:
                    task.artifacts = []
                task.artifacts.extend(artifacts)

            return task

    # Tạo bản sao của task với lịch sử thông điệp được giới hạn.
    # Được gọi bởi on_get_task để trả về tác vụ với lịch sử giới hạn (historyLength).
    def append_task_history(self, task: Task, historyLength: int | None):
        new_task = task.model_copy()
        if historyLength is not None and historyLength > 0:
            new_task.history = new_task.history[-historyLength:]
        else:
            new_task.history = []

        return new_task        

    # Thiết lập hàng đợi (asyncio.Queue) để gửi sự kiện streaming cho một client.
    # Được gọi khi client đăng ký streaming (qua on_send_task_subscribe hoặc on_resubscribe_to_task).
    async def setup_sse_consumer(self, task_id: str, is_resubscribe: bool = False):
        async with self.subscriber_lock:
            if task_id not in self.task_sse_subscribers:
                if is_resubscribe:
                    raise ValueError("Task not found for resubscription")
                else:
                    self.task_sse_subscribers[task_id] = []

            sse_event_queue = asyncio.Queue(maxsize=0) # <=0 is unlimited
            self.task_sse_subscribers[task_id].append(sse_event_queue)
            return sse_event_queue

    # Thêm sự kiện streaming (task_update_event) vào tất cả hàng đợi của client cho một tác vụ.
    # Được gọi khi có cập nhật trạng thái hoặc hiện vật để gửi đến các client streaming.
    async def enqueue_events_for_sse(self, task_id, task_update_event):
        async with self.subscriber_lock:
            if task_id not in self.task_sse_subscribers:
                return

            current_subscribers = self.task_sse_subscribers[task_id]
            for subscriber in current_subscribers:
                await subscriber.put(task_update_event)

    # Lấy sự kiện từ hàng đợi và trả về dưới dạng AsyncIterable[SendTaskStreamingResponse] cho client streaming.
    # Được gọi bởi on_send_task_subscribe để gửi sự kiện streaming đến client.
    async def dequeue_events_for_sse(
        self, request_id, task_id, sse_event_queue: asyncio.Queue
    ) -> AsyncIterable[SendTaskStreamingResponse] | JSONRPCResponse:
        try:
            while True:                
                event = await sse_event_queue.get()
                if isinstance(event, JSONRPCError):
                    yield SendTaskStreamingResponse(id=request_id, error=event)
                    break
                                                
                yield SendTaskStreamingResponse(id=request_id, result=event)
                if isinstance(event, TaskStatusUpdateEvent) and event.final:
                    break
        finally:
            async with self.subscriber_lock:
                if task_id in self.task_sse_subscribers:
                    self.task_sse_subscribers[task_id].remove(sse_event_queue)