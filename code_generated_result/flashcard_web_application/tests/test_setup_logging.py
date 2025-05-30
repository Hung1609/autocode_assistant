import pytest
import unittest.mock
import logging
import os
import sys
from fastapi import Request, HTTPException, Depends
from backend.main import setup_logging

def test_setup_logging_success(mocker):
    # source_info: backend.main.setup_logging
    mocker.patch("backend.main.os.path.exists", return_value=True)
    mocker.patch("backend.main.os.makedirs")
    mock_rotating_file_handler = mocker.patch("logging.handlers.RotatingFileHandler")
    mock_stream_handler = mocker.patch("logging.StreamHandler")
    mock_basic_config = mocker.patch("logging.basicConfig")
    mock_get_logger = mocker.patch("logging.getLogger")
    mock_request_id_filter = mocker.patch("backend.main.RequestIDFilter")
    
    logger = setup_logging()
    
    assert mock_rotating_file_handler.call_count == 1
    assert mock_stream_handler.call_count == 1
    assert mock_basic_config.call_count == 1
    mock_get_logger.assert_called_with(__name__)

def test_setup_logging_no_existing_log_dir(mocker):
    # source_info: backend.main.setup_logging
    mocker.patch("backend.main.os.path.exists", return_value=False)
    mocker.patch("backend.main.os.makedirs")
    mock_rotating_file_handler = mocker.patch("logging.handlers.RotatingFileHandler")
    mock_stream_handler = mocker.patch("logging.StreamHandler")
    mock_basic_config = mocker.patch("logging.basicConfig")
    mock_get_logger = mocker.patch("logging.getLogger")
    mock_request_id_filter = mocker.patch("backend.main.RequestIDFilter")

    logger = setup_logging()

    assert mocker.call("logs") in backend.main.os.makedirs.call_args_list
    assert mock_rotating_file_handler.call_count == 1
    assert mock_stream_handler.call_count == 1
    assert mock_basic_config.call_count == 1
    mock_get_logger.assert_called_with(__name__)

def test_setup_logging_json_logger_available(mocker):
    # source_info: backend.main.setup_logging
    mocker.patch("backend.main.os.path.exists", return_value=True)
    mocker.patch("backend.main.os.makedirs")
    mocker.patch("backend.main.has_json_logger", True)
    mock_jsonlogger = mocker.patch("backend.main.jsonlogger.JsonFormatter")
    mock_rotating_file_handler = mocker.patch("logging.handlers.RotatingFileHandler")
    mock_stream_handler = mocker.patch("logging.StreamHandler")
    mock_basic_config = mocker.patch("logging.basicConfig")
    mock_get_logger = mocker.patch("logging.getLogger")
    mock_request_id_filter = mocker.patch("backend.main.RequestIDFilter")
    
    logger = setup_logging()

    assert mock_rotating_file_handler.call_count == 1
    assert mock_stream_handler.call_count == 1
    assert mock_basic_config.call_count == 1
    mock_get_logger.assert_called_with(__name__)
    assert mock_jsonlogger.call_count == 1