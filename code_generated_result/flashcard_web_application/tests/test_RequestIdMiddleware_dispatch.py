import pytest
import unittest.mock
import uuid

from fastapi import Request, HTTPException, Depends, Response
from backend.main import RequestIdMiddleware
from contextvars import ContextVar

@pytest.fixture
def mock_request(mocker):
    return mocker.MagicMock(spec=Request)

@pytest.fixture
def mock_call_next(mocker):
    return mocker.AsyncMock()

@pytest.fixture
def request_id_ctx():
    return ContextVar("request_id")

@pytest.mark.asyncio
async def test_RequestIdMiddleware_dispatch_success(mocker, mock_request, mock_call_next, request_id_ctx):
    # source_info: backend.main.RequestIdMiddleware.dispatch
    mock_response = Response(content="OK")
    mock_call_next.return_value = mock_response
    middleware = RequestIdMiddleware()

    response = await middleware.dispatch(mock_request, mock_call_next)

    assert response == mock_response
    mock_call_next.assert_called_once_with(mock_request)
    assert request_id_ctx.get() is None

@pytest.mark.asyncio
async def test_RequestIdMiddleware_dispatch_exception(mocker, mock_request, mock_call_next, request_id_ctx):
    # source_info: backend.main.RequestIdMiddleware.dispatch
    mock_call_next.side_effect = HTTPException(status_code=500, detail="Internal Server Error")
    middleware = RequestIdMiddleware()

    with pytest.raises(HTTPException) as exc_info:
        await middleware.dispatch(mock_request, mock_call_next)

    assert exc_info.value.status_code == 500
    mock_call_next.assert_called_once_with(mock_request)
    assert request_id_ctx.get() is None

@pytest.mark.asyncio
async def test_RequestIdMiddleware_dispatch_uuid_generation(mocker, mock_request, mock_call_next, request_id_ctx):
    # source_info: backend.main.RequestIdMiddleware.dispatch
    mock_response = Response(content="OK")
    mock_call_next.return_value = mock_response
    middleware = RequestIdMiddleware()

    original_uuid4 = uuid.uuid4
    mock_uuid4 = mocker.MagicMock(return_value=uuid.UUID('12345678123456781234567812345678'))
    uuid.uuid4 = mock_uuid4

    try:
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert str(uuid.UUID('12345678-1234-5678-1234-567812345678')) == request_id_ctx.get()
    finally:
        uuid.uuid4 = original_uuid4 # Restore original uuid function
        request_id_ctx.set(None)