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
    mock_call_next.return_value = mocker.AsyncMock(status_code=200)

    mock_logger = mocker.patch("backend.main.logger")

    response = await log_requests(mock_request, mock_call_next)

    mock_logger.info.assert_called()
    assert response.status_code == 200
    mock_call_next.assert_called_once_with(mock_request)

async def test_log_requests_post_method(mocker):
    # source_info: backend.main.log_requests
    mock_request = mocker.AsyncMock(spec=Request)
    mock_request.method = "POST"
    mock_request.url.path = "/items"

    mock_call_next = mocker.AsyncMock()
    mock_call_next.return_value = mocker.AsyncMock(status_code=201)

    mock_logger = mocker.patch("backend.main.logger")

    response = await log_requests(mock_request, mock_call_next)

    mock_logger.info.assert_called()
    assert response.status_code == 201
    mock_call_next.assert_called_once_with(mock_request)

async def test_log_requests_internal_server_error(mocker):
    # source_info: backend.main.log_requests
    mock_request = mocker.AsyncMock(spec=Request)
    mock_request.method = "GET"
    mock_request.url.path = "/error"

    mock_call_next = mocker.AsyncMock()
    mock_call_next.return_value = mocker.AsyncMock(status_code=500)

    mock_logger = mocker.patch("backend.main.logger")

    response = await log_requests(mock_request, mock_call_next)

    mock_logger.info.assert_called()
    assert response.status_code == 500
    mock_call_next.assert_called_once_with(mock_request)

async def test_log_requests_exception_in_call_next(mocker):
    # source_info: backend.main.log_requests
    mock_request = mocker.AsyncMock(spec=Request)
    mock_request.method = "GET"
    mock_request.url.path = "/exception"

    mock_call_next = mocker.AsyncMock(side_effect=Exception("Something went wrong"))

    mock_logger = mocker.patch("backend.main.logger")

    with pytest.raises(Exception, match="Something went wrong"):
        await log_requests(mock_request, mock_call_next)

    mock_logger.info.assert_called() # called before exception is raised
    mock_call_next.assert_called_once_with(mock_request)