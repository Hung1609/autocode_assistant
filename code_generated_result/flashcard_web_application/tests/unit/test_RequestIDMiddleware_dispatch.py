import pytest
from unittest.mock import AsyncMock
from fastapi import Request, Response
from backend.main import RequestIDMiddleware
import uuid
import contextvars

@pytest.fixture
def mock_request():
    return AsyncMock(spec=Request)

@pytest.fixture
def mock_call_next():
    return AsyncMock()

@pytest.fixture
def request_id_middleware():
    return RequestIDMiddleware()

@pytest.fixture(autouse=True)
def reset_request_id_ctx():
    request_id_ctx = contextvars.ContextVar("request_id")
    request_id_ctx.set(None)


async def test_RequestIDMiddleware_dispatch_success(mock_request, mock_call_next, request_id_middleware):
    # source_info: backend.main.RequestIDMiddleware.dispatch
    mock_call_next.return_value = Response(status_code=200)
    response = await request_id_middleware.dispatch(mock_request, mock_call_next)
    assert response.status_code == 200
    mock_call_next.assert_called_once_with(mock_request)


async def test_RequestIDMiddleware_dispatch_exception(mock_request, mock_call_next, request_id_middleware):
    # source_info: backend.main.RequestIDMiddleware.dispatch
    mock_call_next.side_effect = Exception("Test exception")

    with pytest.raises(Exception, match="Test exception"):
        await request_id_middleware.dispatch(mock_request, mock_call_next)
    mock_call_next.assert_called_once_with(mock_request)

async def test_RequestIDMiddleware_dispatch_no_exception(mock_request, mock_call_next, request_id_middleware):
    # source_info: backend.main.RequestIDMiddleware.dispatch
    mock_call_next.return_value = Response(status_code=200)

    response = await request_id_middleware.dispatch(mock_request, mock_call_next)

    assert response.status_code == 200
    mock_call_next.assert_called_once_with(mock_request)

async def test_RequestIDMiddleware_dispatch_request_id_set(mocker, mock_request, mock_call_next, request_id_middleware):
    # source_info: backend.main.RequestIDMiddleware.dispatch
    mock_call_next.return_value = Response(status_code=200)
    request_id_ctx = contextvars.ContextVar("request_id")
    token = request_id_ctx.set(None)

    await request_id_middleware.dispatch(mock_request, mock_call_next)
    assert request_id_ctx.get() is not None
    request_id_ctx.reset(token)

async def test_RequestIDMiddleware_dispatch_request_id_unique(mock_request, mock_call_next, request_id_middleware):
    # source_info: backend.main.RequestIDMiddleware.dispatch
    mock_call_next.return_value = Response(status_code=200)
    
    first_response = await request_id_middleware.dispatch(mock_request, mock_call_next)

    mock_call_next.return_value = Response(status_code=200)
    second_response = await request_id_middleware.dispatch(mock_request, mock_call_next)
    
    request_id_ctx = contextvars.ContextVar("request_id")
    token = request_id_ctx.set(None)
    first_id = str(uuid.uuid4())

    second_id = str(uuid.uuid4())

    assert first_id != second_id
    request_id_ctx.reset(token)