import pytest
import json
import logging
from unittest import mock
from fastapi import Request, HTTPException, Depends
from backend.main import CustomJsonFormatter

def test_CustomJsonFormatter_format_success():
    # source_info: backend.main.CustomJsonFormatter.format
    formatter = CustomJsonFormatter()
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='test_path',
        lineno=10,
        msg='Test message',
        args=(),
        exc_info=None,
        func='test_function',
        sinfo=None
    )

    formatted_log = formatter.format(record)
    log_dict = json.loads(formatted_log)

    assert 'timestamp' in log_dict
    assert log_dict['level'] == 'INFO'
    assert log_dict['logger_name'] == 'test_logger'
    assert log_dict['message'] == 'Test message'
    assert log_dict['pathname'] == 'test_path'
    assert log_dict['funcName'] == 'test_function'
    assert log_dict['lineno'] == 10

def test_CustomJsonFormatter_format_with_request_id():
    # source_info: backend.main.CustomJsonFormatter.format
    formatter = CustomJsonFormatter()
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='test_path',
        lineno=10,
        msg='Test message',
        args=(),
        exc_info=None,
        func='test_function',
        sinfo=None
    )
    record.request_id = 'test_request_id'

    formatted_log = formatter.format(record)
    log_dict = json.loads(formatted_log)

    assert 'request_id' in log_dict
    assert log_dict['request_id'] == 'test_request_id'

def test_CustomJsonFormatter_format_with_exception():
    # source_info: backend.main.CustomJsonFormatter.format
    formatter = CustomJsonFormatter()
    try:
        raise ValueError('Test exception')
    except ValueError:
        record = logging.LogRecord(
            name='test_logger',
            level=logging.ERROR,
            pathname='test_path',
            lineno=10,
            msg='Test message',
            args=(),
            exc_info=True,
            func='test_function',
            sinfo=None
        )

    formatted_log = formatter.format(record)
    log_dict = json.loads(formatted_log)

    assert 'exc_info' in log_dict
    assert isinstance(log_dict['exc_info'], str)

def test_CustomJsonFormatter_format_empty_message():
    # source_info: backend.main.CustomJsonFormatter.format
    formatter = CustomJsonFormatter()
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='test_path',
        lineno=10,
        msg='',
        args=(),
        exc_info=None,
        func='test_function',
        sinfo=None
    )

    formatted_log = formatter.format(record)
    log_dict = json.loads(formatted_log)

    assert log_dict['message'] == ''

def test_CustomJsonFormatter_format_long_message():
    # source_info: backend.main.CustomJsonFormatter.format
    formatter = CustomJsonFormatter()
    long_message = "A" * 2000
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='test_path',
        lineno=10,
        msg=long_message,
        args=(),
        exc_info=None,
        func='test_function',
        sinfo=None
    )

    formatted_log = formatter.format(record)
    log_dict = json.loads(formatted_log)

    assert log_dict['message'] == long_message