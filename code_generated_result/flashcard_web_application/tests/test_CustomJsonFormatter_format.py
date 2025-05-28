import pytest
import json
from unittest.mock import MagicMock

from backend.main import CustomJsonFormatter


def test_CustomJsonFormatter_format_success():
    # source_info: backend.main.CustomJsonFormatter.format
    formatter = CustomJsonFormatter()
    record = MagicMock()
    record.levelname = 'INFO'
    record.name = 'test_logger'
    record.getMessage.return_value = 'Test message'
    record.pathname = '/path/to/file.py'
    record.funcName = 'test_function'
    record.lineno = 10
    record.exc_info = None
    formatter.formatTime = MagicMock(return_value='2023-10-27T10:00:00')
    formatter.formatException = MagicMock()

    result = formatter.format(record)
    result_dict = json.loads(result)

    assert result_dict['timestamp'] == '2023-10-27T10:00:00'
    assert result_dict['level'] == 'INFO'
    assert result_dict['logger_name'] == 'test_logger'
    assert result_dict['message'] == 'Test message'
    assert result_dict['pathname'] == '/path/to/file.py'
    assert result_dict['funcName'] == 'test_function'
    assert result_dict['lineno'] == 10
    assert 'exc_info' not in result_dict

def test_CustomJsonFormatter_format_with_request_id():
    # source_info: backend.main.CustomJsonFormatter.format
    formatter = CustomJsonFormatter()
    record = MagicMock()
    record.levelname = 'INFO'
    record.name = 'test_logger'
    record.getMessage.return_value = 'Test message'
    record.pathname = '/path/to/file.py'
    record.funcName = 'test_function'
    record.lineno = 10
    record.request_id = '12345'
    record.exc_info = None

    formatter.formatTime = MagicMock(return_value='2023-10-27T10:00:00')
    formatter.formatException = MagicMock()

    result = formatter.format(record)
    result_dict = json.loads(result)

    assert result_dict['request_id'] == '12345'

def test_CustomJsonFormatter_format_with_exception():
    # source_info: backend.main.CustomJsonFormatter.format
    formatter = CustomJsonFormatter()
    record = MagicMock()
    record.levelname = 'ERROR'
    record.name = 'test_logger'
    record.getMessage.return_value = 'Test message with exception'
    record.pathname = '/path/to/file.py'
    record.funcName = 'test_function'
    record.lineno = 10
    record.exc_info = (ValueError, ValueError("Test Exception"), MagicMock())
    formatter.formatTime = MagicMock(return_value='2023-10-27T10:00:00')
    formatter.formatException = MagicMock(return_value='Formatted Exception')

    result = formatter.format(record)
    result_dict = json.loads(result)

    assert result_dict['exc_info'] == 'Formatted Exception'