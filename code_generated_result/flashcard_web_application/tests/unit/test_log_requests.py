import pytest
from unittest.mock import MagicMock
from fastapi import Request
from backend.main import log_requests
import logging


@pytest.mark.asyncio
async def test_log_requests_success(mocker):
    # source_info: backend.main.log_requests
    mock_request = mocker.AsyncMock(spec=Request)
    mock_request.method = "GET"
    mock_request.url.path = "/test"

    mock_response = MagicMock()
    mock_response.status_code = 200

    async def mock_call_next(request: Request):
        return mock_response

    mock_logger = mocker.patch("backend.main.logger")

    result = await log_requests(mock_request, mock_call_next)

    assert result == mock_response
    mock_logger.info.assert_called()
    assert mock_logger.info.call_count == 2
    mock_logger.info.assert_any_call("Incoming request: GET /test")
    mock_logger.info.assert_any_call("Outgoing response: 200 for GET /test")


@pytest.mark.asyncio
async def test_log_requests_post_method(mocker):
    # source_info: backend.main.log_requests
    mock_request = mocker.AsyncMock(spec=Request)
    mock_request.method = "POST"
    mock_request.url.path = "/items"

    mock_response = MagicMock()
    mock_response.status_code = 201

    async def mock_call_next(request: Request):
        return mock_response

    mock_logger = mocker.patch("backend.main.logger")

    result = await log_requests(mock_request, mock_call_next)

    assert result == mock_response
    mock_logger.info.assert_called()
    assert mock_logger.info.call_count == 2
    mock_logger.info.assert_any_call("Incoming request: POST /items")
    mock_logger.info.assert_any_call("Outgoing response: 201 for POST /items")


@pytest.mark.asyncio
async def test_log_requests_internal_server_error(mocker):
    # source_info: backend.main.log_requests
    mock_request = mocker.AsyncMock(spec=Request)
    mock_request.method = "GET"
    mock_request.url.path = "/error"

    mock_response = MagicMock()
    mock_response.status_code = 500

    async def mock_call_next(request: Request):
        return mock_response

    mock_logger = mocker.patch("backend.main.logger")

    result = await log_requests(mock_request, mock_call_next)

    assert result == mock_response
    mock_logger.info.assert_called()
    assert mock_logger.info.call_count == 2
    mock_logger.info.assert_any_call("Incoming request: GET /error")
    mock_logger.info.assert_any_call("Outgoing response: 500 for GET /error")


@pytest.mark.asyncio
async def test_log_requests_different_path(mocker):
    # source_info: backend.main.log_requests
    mock_request = mocker.AsyncMock(spec=Request)
    mock_request.method = "PUT"
    mock_request.url.path = "/users/123"

    mock_response = MagicMock()
    mock_response.status_code = 204

    async def mock_call_next(request: Request):
        return mock_response

    mock_logger = mocker.patch("backend.main.logger")

    result = await log_requests(mock_request, mock_call_next)

    assert result == mock_response
    mock_logger.info.assert_called()
    assert mock_logger.info.call_count == 2
    mock_logger.info.assert_any_call("Incoming request: PUT /users/123")
    mock_logger.info.assert_any_call("Outgoing response: 204 for PUT /users/123")