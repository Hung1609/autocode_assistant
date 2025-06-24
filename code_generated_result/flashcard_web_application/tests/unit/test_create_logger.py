import pytest
import logging
import json
import sys
from unittest import mock
from pytest_mock import MockerFixture

from fastapi import Request, HTTPException, Depends

from backend.main import create_logger


def test_create_logger_success(mocker: MockerFixture):
    # source_info: backend.main.create_logger
    mock_rotating_file_handler = mocker.patch("logging.handlers.RotatingFileHandler")
    mock_stream_handler = mocker.patch("logging.StreamHandler")

    logger = create_logger()

    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 2
    mock_rotating_file_handler.assert_called_once_with("logs/app.log", maxBytes=10*1024*1024, backupCount=5)
    mock_stream_handler.assert_called_once_with(sys.stdout)

def test_JsonFormatter_format(mocker: MockerFixture):
    # source_info: backend.main.create_logger
    from backend.main import create_logger

    logger = create_logger()
    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='test.py',
        lineno=1,
        msg='test message',
        args=(),
        exc_info=None,
        func='test_func'
    )
    
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_record = {
                "timestamp": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "logger_name": record.name,
                "message": record.getMessage(),
                "pathname": record.pathname,
                "funcName": record.funcName,
                "lineno": record.lineno,
            }
            if record.exc_info:
                log_record["exc_info"] = self.formatException(record.exc_info)
            return json.dumps(log_record)

    formatter = JsonFormatter()
    formatted_record = json.loads(formatter.format(record))

    assert formatted_record["level"] == "INFO"
    assert formatted_record["logger_name"] == "test"
    assert formatted_record["message"] == "test message"
    assert formatted_record["pathname"] == "test.py"
    assert formatted_record["funcName"] == "test_func"
    assert formatted_record["lineno"] == 1