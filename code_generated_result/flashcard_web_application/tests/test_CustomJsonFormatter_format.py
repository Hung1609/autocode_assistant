import pytest
import unittest.mock
import json
import logging

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
        func='test_func',
        sinfo=None
    )

    formatted_record = json.loads(formatter.format(record))

    assert formatted_record['level'] == 'INFO'
    assert formatted_record['logger_name'] == 'test_logger'
    assert formatted_record['message'] == 'Test message'
    assert formatted_record['pathname'] == 'test_path'
    assert formatted_record['funcName'] == 'test_func'
    assert formatted_record['lineno'] == 10


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
        func='test_func',
        sinfo=None
    )
    record.request_id = 'test_request_id'

    formatted_record = json.loads(formatter.format(record))

    assert formatted_record['request_id'] == 'test_request_id'


def test_CustomJsonFormatter_format_with_exception_info():
    # source_info: backend.main.CustomJsonFormatter.format
    formatter = CustomJsonFormatter()
    record = logging.LogRecord(
        name='test_logger',
        level=logging.ERROR,
        pathname='test_path',
        lineno=10,
        msg='Test message',
        args=(),
        exc_info=(ValueError, ValueError('Test exception'), None),
        func='test_func',
        sinfo=None
    )

    formatted_record = json.loads(formatter.format(record))

    assert 'exc_info' in formatted_record
    assert isinstance(formatted_record['exc_info'], str)


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
        func='test_func',
        sinfo=None
    )

    formatted_record = json.loads(formatter.format(record))

    assert formatted_record['message'] == ''


def test_CustomJsonFormatter_format_none_message():
    # source_info: backend.main.CustomJsonFormatter.format
    formatter = CustomJsonFormatter()
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='test_path',
        lineno=10,
        msg=None,
        args=(),
        exc_info=None,
        func='test_func',
        sinfo=None
    )
    record.getMessage = unittest.mock.MagicMock(return_value='')

    formatted_record = json.loads(formatter.format(record))

    assert formatted_record['message'] == ''