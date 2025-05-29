import pytest
import unittest.mock
import uuid
from fastapi import Request, Response
from backend.main import RequestIDMiddleware
from contextvars import ContextVar


@pytest.fixture
def mock_request():
    mock = unittest.mock.AsyncMock(spec=Request)
    return mock

@pytest.fixture
def mock_call_next():
    mock = unittest.mock.AsyncMock()
    return mock

@pytest.fixture
def request_id_ctx():
    return ContextVar("request_id")


def test_RequestIDMiddleware_dispatch_success(mocker, mock_request, mock_call_next, request_id_ctx):
    # source_info: backend.main.RequestIDMiddleware.dispatch
    middleware = RequestIDMiddleware()
    mock_response = Response(status_code=200)
    mock_call_next.return_value = mock_response

    async def mock_uuid4():
        return uuid.UUID('12345678123456781234567812345678')
    mocker.patch("uuid.uuid4", new_callable=mock_uuid4)
    
    async def run_dispatch():
        return await middleware.dispatch(mock_request, mock_call_next)

    response = pytest. MonkeyPatch().setattr("backend.main.request_id_ctx", request_id_ctx)
    response = pytest. MonkeyPatch().setattr("backend.main.RequestIDMiddleware.dispatch", middleware.dispatch)

    import asyncio
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(middleware.dispatch(mock_request, mock_call_next))

    assert result == mock_response
    mock_call_next.assert_called_once_with(mock_request)
    assert request_id_ctx.get() == '12345678-1234-5678-1234-567812345678'


def test_RequestIDMiddleware_dispatch_exception(mocker, mock_request, mock_call_next, request_id_ctx):
    # source_info: backend.main.RequestIDMiddleware.dispatch
    middleware = RequestIDMiddleware()
    mock_call_next.side_effect = Exception("Something went wrong")

    async def mock_uuid4():
        return uuid.UUID('12345678123456781234567812345678')

    mocker.patch("uuid.uuid4", new_callable=mock_uuid4)

    response = pytest.MonkeyPatch().setattr("backend.main.request_id_ctx", request_id_ctx)
    response = pytest.MonkeyPatch().setattr("backend.main.RequestIDMiddleware.dispatch", middleware.dispatch)

    import asyncio
    loop = asyncio.get_event_loop()

    with pytest.raises(Exception, match="Something went wrong"):
        loop.run_until_complete(middleware.dispatch(mock_request, mock_call_next))

    assert request_id_ctx.get() == None
    mock_call_next.assert_called_once_with(mock_request)