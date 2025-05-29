import pytest
from unittest.mock import AsyncMock, patch
from fastapi import Request, HTTPException, Depends
from backend.main import log_requests
import logging


async def test_log_requests_success(mocker):
    # source_info: backend.main.log_requests
    mock_request = mocker.AsyncMock(spec=Request)
    mock_request.method = "GET"
    mock_request.url.path = "/test"

    mock_call_next = mocker.AsyncMock()
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_call_next.return_value = mock_response

    mock_logger = mocker.patch("backend.main.logger")

    result = await log_requests(mock_request, mock_call_next)

    assert result == mock_response
    mock_logger.info.assert_called()
    assert mock_logger.info.call_count == 2
    assert "Incoming request: GET /test" in str(mock_logger.info.call_args_list[0])
    assert "Outgoing response: 200 for GET /test" in str(mock_logger.info.call_args_list[1])
    mock_call_next.assert_called_once_with(mock_request)


async def test_log_requests_post_request(mocker):
    # source_info: backend.main.log_requests
    mock_request = mocker.AsyncMock(spec=Request)
    mock_request.method = "POST"
    mock_request.url.path = "/items"

    mock_call_next = mocker.AsyncMock()
    mock_response = mocker.Mock()
    mock_response.status_code = 201
    mock_call_next.return_value = mock_response

    mock_logger = mocker.patch("backend.main.logger")

    result = await log_requests(mock_request, mock_call_next)

    assert result == mock_response
    mock_logger.info.assert_called()
    assert mock_logger.info.call_count == 2
    assert "Incoming request: POST /items" in str(mock_logger.info.call_args_list[0])
    assert "Outgoing response: 201 for POST /items" in str(mock_logger.info.call_args_list[1])
    mock_call_next.assert_called_once_with(mock_request)

async def test_log_requests_exception(mocker):
    # source_info: backend.main.log_requests
    mock_request = mocker.AsyncMock(spec=Request)
    mock_request.method = "GET"
    mock_request.url.path = "/error"

    mock_call_next = mocker.AsyncMock()
    mock_call_next.side_effect = Exception("Something went wrong")

    mock_logger = mocker.patch("backend.main.logger")

    with pytest.raises(Exception, match="Something went wrong"):
        await log_requests(mock_request, mock_call_next)

    mock_logger.info.assert_called_once()
    assert "Incoming request: GET /error" in str(mock_logger.info.call_args_list[0])

    mock_call_next.assert_called_once_with(mock_request)