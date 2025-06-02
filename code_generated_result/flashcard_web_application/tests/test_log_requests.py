import pytest
from unittest.mock import AsyncMock
from fastapi import Request, HTTPException, Depends
from backend.main import log_requests
import logging

async def test_log_requests_success(mocker):
    # source_info: backend.main.log_requests
    mock_request = mocker.AsyncMock(spec=Request)
    mock_request.method = "GET"
    mock_request.url.path = "/test"

    mock_call_next = mocker.AsyncMock()
    mock_response = mocker.AsyncMock()
    mock_response.status_code = 200
    mock_call_next.return_value = mock_response

    mock_logger = mocker.patch("backend.main.logger")

    result = await log_requests(mock_request, mock_call_next)

    assert result == mock_response
    mock_logger.info.assert_any_call("Incoming request: GET /test")
    mock_logger.info.assert_any_call("Outgoing response: 200 for GET /test")
    mock_call_next.assert_called_once_with(mock_request)


async def test_log_requests_exception(mocker):
    # source_info: backend.main.log_requests
    mock_request = mocker.AsyncMock(spec=Request)
    mock_request.method = "POST"
    mock_request.url.path = "/error"

    mock_call_next = mocker.AsyncMock()
    mock_call_next.side_effect = HTTPException(status_code=500, detail="Internal Server Error")

    mock_logger = mocker.patch("backend.main.logger")

    with pytest.raises(HTTPException) as exc_info:
        await log_requests(mock_request, mock_call_next)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Internal Server Error"
    mock_logger.info.assert_any_call("Incoming request: POST /error")
    mock_call_next.assert_called_once_with(mock_request)


async def test_log_requests_different_method_and_path(mocker):
    # source_info: backend.main.log_requests
    mock_request = mocker.AsyncMock(spec=Request)
    mock_request.method = "PUT"
    mock_request.url.path = "/update"

    mock_call_next = mocker.AsyncMock()
    mock_response = mocker.AsyncMock()
    mock_response.status_code = 201
    mock_call_next.return_value = mock_response

    mock_logger = mocker.patch("backend.main.logger")

    result = await log_requests(mock_request, mock_call_next)

    assert result == mock_response
    mock_logger.info.assert_any_call("Incoming request: PUT /update")
    mock_logger.info.assert_any_call("Outgoing response: 201 for PUT /update")
    mock_call_next.assert_called_once_with(mock_request)