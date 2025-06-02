import pytest
import uuid
from unittest.mock import AsyncMock

from fastapi import Request, Response
from backend.main import RequestIDMiddleware

@pytest.fixture
def mock_request():
    mock = AsyncMock(spec=Request)
    return mock

@pytest.fixture
def mock_call_next():
    mock = AsyncMock()
    return mock

@pytest.mark.asyncio
async def test_RequestIDMiddleware_dispatch_success(mock_request, mock_call_next):
    # source_info: backend.main.RequestIDMiddleware.dispatch
    mock_call_next.return_value = Response(status_code=200)
    middleware = RequestIDMiddleware()

    response = await middleware.dispatch(mock_request, mock_call_next)

    assert response.status_code == 200
    mock_call_next.assert_called_once_with(mock_request)

@pytest.mark.asyncio
async def test_RequestIDMiddleware_dispatch_exception(mock_request, mock_call_next):
    # source_info: backend.main.RequestIDMiddleware.dispatch
    mock_call_next.side_effect = Exception("Something went wrong")
    middleware = RequestIDMiddleware()

    with pytest.raises(Exception, match="Something went wrong"):
        await middleware.dispatch(mock_request, mock_call_next)

    mock_call_next.assert_called_once_with(mock_request)