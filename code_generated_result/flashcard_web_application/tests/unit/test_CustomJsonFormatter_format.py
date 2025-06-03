import pytest
import unittest.mock
import json
from fastapi import Request, HTTPException, Depends
from backend.main import CustomJsonFormatter

def test_CustomJsonFormatter_format_success(mocker):
    # source_info: backend.main.CustomJsonFormatter.format
    formatter = CustomJsonFormatter()
    record = mocker.MagicMock()
    record.levelname = 'INFO'
    record.name = 'test_logger'
    record.getMessage.return_value = 'Test message'
    record.pathname = '/path/to/file.py'
    record.funcName = 'test_function'
    record.lineno = 10
    formatter.formatTime = mocker.MagicMock(return_value='2023-10-26 10:00:00')
    formatter.formatException = mocker.MagicMock(return_value='Exception info')
    record.exc_info = True

    result = formatter.format(record)

    assert json.loads(result) == {
        'timestamp': '2023-10-26 10:00:00',
        'level': 'INFO',
        'logger_name': 'test_logger',
        'message': 'Test message',
        'pathname': '/path/to/file.py',
        'funcName': 'test_function',
        'lineno': 10,
        'exc_info': 'Exception info'
    }
    formatter.formatTime.assert_called_once_with(record, formatter.datefmt)
    formatter.formatException.assert_called_once_with(record.exc_info)


def test_CustomJsonFormatter_format_no_exc_info(mocker):
    # source_info: backend.main.CustomJsonFormatter.format
    formatter = CustomJsonFormatter()
    record = mocker.MagicMock()
    record.levelname = 'WARNING'
    record.name = 'test_logger'
    record.getMessage.return_value = 'Another test message'
    record.pathname = '/another/path/file.py'
    record.funcName = 'another_function'
    record.lineno = 20
    formatter.formatTime = mocker.MagicMock(return_value='2023-10-26 11:00:00')
    record.exc_info = None

    result = formatter.format(record)

    assert json.loads(result) == {
        'timestamp': '2023-10-26 11:00:00',
        'level': 'WARNING',
        'logger_name': 'test_logger',
        'message': 'Another test message',
        'pathname': '/another/path/file.py',
        'funcName': 'another_function',
        'lineno': 20
    }
    formatter.formatTime.assert_called_once_with(record, formatter.datefmt)
    formatter.formatException.assert_not_called()


def test_CustomJsonFormatter_format_with_request_id(mocker):
    # source_info: backend.main.CustomJsonFormatter.format
    formatter = CustomJsonFormatter()
    record = mocker.MagicMock()
    record.levelname = 'ERROR'
    record.name = 'test_logger'
    record.getMessage.return_value = 'Error message'
    record.pathname = '/error/path.py'
    record.funcName = 'error_function'
    record.lineno = 30
    formatter.formatTime = mocker.MagicMock(return_value='2023-10-26 12:00:00')
    record.request_id = '12345'
    record.exc_info = None

    result = formatter.format(record)

    assert json.loads(result) == {
        'timestamp': '2023-10-26 12:00:00',
        'level': 'ERROR',
        'logger_name': 'test_logger',
        'message': 'Error message',
        'pathname': '/error/path.py',
        'funcName': 'error_function',
        'lineno': 30,
        'request_id': '12345'
    }
    formatter.formatTime.assert_called_once_with(record, formatter.datefmt)
    formatter.formatException.assert_not_called()