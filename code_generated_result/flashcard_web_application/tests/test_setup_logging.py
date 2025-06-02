import pytest
import unittest.mock
import logging
import sys
import os
from backend.main import setup_logging
from fastapi import Request, HTTPException, Depends
from pytest_mock import MockerFixture

def test_setup_logging_success(mocker: MockerFixture):
    # source_info: backend.main.setup_logging
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch("os.makedirs")
    mock_rotating_file_handler = mocker.patch("logging.handlers.RotatingFileHandler")
    mock_stream_handler = mocker.patch("logging.StreamHandler")
    mock_basic_config = mocker.patch("logging.basicConfig")
    mock_get_logger = mocker.patch("logging.getLogger")
    mock_add_filter = mocker.patch("logging.Logger.addFilter")
    
    logger = setup_logging()

    assert os.path.exists.call_count == 1
    assert os.makedirs.call_count == 1
    assert mock_rotating_file_handler.call_count == 1
    assert mock_stream_handler.call_count == 1
    assert mock_basic_config.call_count == 1
    assert mock_add_filter.call_count == 1
    assert mock_get_logger.return_value == logger

def test_setup_logging_log_dir_exists(mocker: MockerFixture):
    # source_info: backend.main.setup_logging
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.makedirs")
    mock_rotating_file_handler = mocker.patch("logging.handlers.RotatingFileHandler")
    mock_stream_handler = mocker.patch("logging.StreamHandler")
    mock_basic_config = mocker.patch("logging.basicConfig")
    mock_get_logger = mocker.patch("logging.getLogger")
    mock_add_filter = mocker.patch("logging.Logger.addFilter")

    logger = setup_logging()

    assert os.path.exists.call_count == 1
    assert os.makedirs.call_count == 0
    assert mock_rotating_file_handler.call_count == 1
    assert mock_stream_handler.call_count == 1
    assert mock_basic_config.call_count == 1
    assert mock_add_filter.call_count == 1
    assert mock_get_logger.return_value == logger

def test_setup_logging_has_json_logger_true(mocker: MockerFixture):
    # source_info: backend.main.setup_logging
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch("os.makedirs")
    mock_rotating_file_handler = mocker.patch("logging.handlers.RotatingFileHandler")
    mock_stream_handler = mocker.patch("logging.StreamHandler")
    mock_basic_config = mocker.patch("logging.basicConfig")
    mock_get_logger = mocker.patch("logging.getLogger")
    mock_add_filter = mocker.patch("logging.Logger.addFilter")
    mocker.patch("backend.main.has_json_logger", True)
    mocker.patch("backend.main.jsonlogger.JsonFormatter")

    logger = setup_logging()

    assert os.path.exists.call_count == 1
    assert os.makedirs.call_count == 1
    assert mock_rotating_file_handler.call_count == 1
    assert mock_stream_handler.call_count == 1
    assert mock_basic_config.call_count == 1
    assert mock_add_filter.call_count == 1
    assert mock_get_logger.return_value == logger
    assert backend.main.jsonlogger.JsonFormatter.call_count == 1

def test_setup_logging_has_json_logger_false(mocker: MockerFixture):
    # source_info: backend.main.setup_logging
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch("os.makedirs")
    mock_rotating_file_handler = mocker.patch("logging.handlers.RotatingFileHandler")
    mock_stream_handler = mocker.patch("logging.StreamHandler")
    mock_basic_config = mocker.patch("logging.basicConfig")
    mock_get_logger = mocker.patch("logging.getLogger")
    mock_add_filter = mocker.patch("logging.Logger.addFilter")
    mocker.patch("backend.main.has_json_logger", False)
    mocker.patch("backend.main.CustomJsonFormatter")

    logger = setup_logging()

    assert os.path.exists.call_count == 1
    assert os.makedirs.call_count == 1
    assert mock_rotating_file_handler.call_count == 1
    assert mock_stream_handler.call_count == 1
    assert mock_basic_config.call_count == 1
    assert mock_add_filter.call_count == 1
    assert mock_get_logger.return_value == logger
    assert backend.main.CustomJsonFormatter.call_count == 1