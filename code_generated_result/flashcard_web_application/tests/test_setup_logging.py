import pytest
import unittest.mock
import logging
import sys
import os
from backend.main import setup_logging

def test_setup_logging_success(mocker):
    # source_info: backend.main.setup_logging
    mock_os_path_exists = mocker.patch("os.path.exists", return_value=False)
    mock_os_makedirs = mocker.patch("os.makedirs")
    mock_logging_handlers_RotatingFileHandler = mocker.patch("logging.handlers.RotatingFileHandler")
    mock_logging_StreamHandler = mocker.patch("logging.StreamHandler")
    mock_logging_basicConfig = mocker.patch("logging.basicConfig")
    mock_logging_getLogger = mocker.patch("logging.getLogger")
    mock_request_id_filter = mocker.patch("backend.main.RequestIDFilter")

    setup_logging()

    mock_os_path_exists.assert_called_once_with("logs")
    mock_os_makedirs.assert_called_once_with("logs")
    mock_logging_handlers_RotatingFileHandler.assert_called_once()
    mock_logging_StreamHandler.assert_called_once_with(sys.stdout)
    mock_logging_basicConfig.assert_called_once()
    mock_logging_getLogger.assert_called()
    mock_request_id_filter.assert_called()
    
def test_setup_logging_log_dir_exists(mocker):
    # source_info: backend.main.setup_logging
    mock_os_path_exists = mocker.patch("os.path.exists", return_value=True)
    mock_os_makedirs = mocker.patch("os.makedirs")
    mock_logging_handlers_RotatingFileHandler = mocker.patch("logging.handlers.RotatingFileHandler")
    mock_logging_StreamHandler = mocker.patch("logging.StreamHandler")
    mock_logging_basicConfig = mocker.patch("logging.basicConfig")
    mock_logging_getLogger = mocker.patch("logging.getLogger")
    mock_request_id_filter = mocker.patch("backend.main.RequestIDFilter")

    setup_logging()

    mock_os_path_exists.assert_called_once_with("logs")
    mock_os_makedirs.assert_not_called()
    mock_logging_handlers_RotatingFileHandler.assert_called_once()
    mock_logging_StreamHandler.assert_called_once_with(sys.stdout)
    mock_logging_basicConfig.assert_called_once()
    mock_logging_getLogger.assert_called()
    mock_request_id_filter.assert_called()

def test_setup_logging_json_logger_available(mocker):
    # source_info: backend.main.setup_logging
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch("os.makedirs")
    mock_rotating_handler = mocker.patch("logging.handlers.RotatingFileHandler")
    mocker.patch("logging.StreamHandler")
    mocker.patch("logging.basicConfig")
    mock_get_logger = mocker.patch("logging.getLogger")
    mocker.patch("backend.main.RequestIDFilter")
    mocker.patch("backend.main.has_json_logger", return_value=True)
    mock_json_formatter = mocker.patch("backend.main.jsonlogger.JsonFormatter")

    setup_logging()

    mock_json_formatter.assert_called_once()
    mock_rotating_handler.return_value.setFormatter.assert_called_once()
    mock_get_logger.assert_called()