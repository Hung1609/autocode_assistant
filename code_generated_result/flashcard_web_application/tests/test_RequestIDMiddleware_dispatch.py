import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import Request, Response
from backend.main import RequestIDMiddleware
import uuid

@pytest.fixture
def mock_request():
    return AsyncMock(spec=Request)

@pytest.fixture
def mock_call_next():
    return AsyncMock()

@pytest.fixture
def request_id_middleware():
    return RequestIDMiddleware()

@pytest.mark.asyncio
async def test_RequestIDMiddleware_dispatch_success(request_id_middleware, mock_request, mock_call_next, mocker):
    # source_info: backend.main.RequestIDMiddleware.dispatch
    mock_response = Response(status_code=200)
    mock_call_next.return_value = mock_response
    
    response = await request_id_middleware.dispatch(mock_request, mock_call_next)
    
    mock_call_next.assert_awaited_once_with(mock_request)
    assert isinstance(response, Response)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_RequestIDMiddleware_dispatch_exception(request_id_middleware, mock_request, mock_call_next, mocker):
    # source_info: backend.main.RequestIDMiddleware.dispatch
    mock_call_next.side_effect = Exception("Something went wrong")
    
    with pytest.raises(Exception, match="Something went wrong"):
        await request_id_middleware.dispatch(mock_request, mock_call_next)

@pytest.mark.asyncio
async def test_RequestIDMiddleware_dispatch_reset_called(request_id_middleware, mock_request, mock_call_next, mocker):
    # source_info: backend.main.RequestIDMiddleware.dispatch
    mock_response = Response(status_code=200)
    mock_call_next.return_value = mock_response
    request_id_ctx = mocker.patch("backend.main.request_id_ctx")

    await request_id_middleware.dispatch(mock_request, mock_call_next)

    assert request_id_ctx.set.call_count == 1
    assert request_id_ctx.reset.call_count == 1

@pytest.mark.asyncio
async def test_RequestIDMiddleware_dispatch_valid_request_id(request_id_middleware, mock_request, mock_call_next, mocker):
    # source_info: backend.main.RequestIDMiddleware.dispatch
    mock_response = Response(status_code=200)
    mock_call_next.return_value = mock_response
    uuid4_mock = mocker.patch("backend.main.uuid.uuid4")
    uuid4_mock.return_value = uuid.UUID('12345678123456781234567812345678')

    await request_id_middleware.dispatch(mock_request, mock_call_next)

    assert uuid4_mock.call_count == 1