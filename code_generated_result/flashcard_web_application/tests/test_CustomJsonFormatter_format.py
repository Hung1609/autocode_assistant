import pytest
import json
import logging
from unittest import mock
from fastapi import Request, HTTPException, Depends
from backend.main import CustomJsonFormatter

def test_CustomJsonFormatter_format_success(mocker):
    # source_info: backend.main.CustomJsonFormatter.format
    formatter = CustomJsonFormatter()
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='/test/path',
        lineno=10,
        msg='Test message',
        args=(),
        exc_info=None,
        func='test_func'
    )
    mocker.patch.object(formatter, 'formatTime', return_value='2023-10-26T10:00:00')
    
    result = formatter.format(record)
    
    expected_log_record = {
        'timestamp': '2023-10-26T10:00:00',
        'level': 'INFO',
        'logger_name': 'test_logger',
        'message': 'Test message',
        'pathname': '/test/path',
        'funcName': 'test_func',
        'lineno': 10
    }
    assert json.loads(result) == expected_log_record

def test_CustomJsonFormatter_format_with_request_id(mocker):
    # source_info: backend.main.CustomJsonFormatter.format
    formatter = CustomJsonFormatter()
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='/test/path',
        lineno=10,
        msg='Test message',
        args=(),
        exc_info=None,
        func='test_func'
    )
    record.request_id = 'test_request_id'
    mocker.patch.object(formatter, 'formatTime', return_value='2023-10-26T10:00:00')

    result = formatter.format(record)
    
    expected_log_record = {
        'timestamp': '2023-10-26T10:00:00',
        'level': 'INFO',
        'logger_name': 'test_logger',
        'message': 'Test message',
        'pathname': '/test/path',
        'funcName': 'test_func',
        'lineno': 10,
        'request_id': 'test_request_id'
    }
    assert json.loads(result) == expected_log_record

def test_CustomJsonFormatter_format_with_exception(mocker):
    # source_info: backend.main.CustomJsonFormatter.format
    formatter = CustomJsonFormatter()
    record = logging.LogRecord(
        name='test_logger',
        level=logging.ERROR,
        pathname='/test/path',
        lineno=10,
        msg='Test message',
        args=(),
        exc_info=(ValueError, ValueError('Test exception'), None),
        func='test_func'
    )
    mocker.patch.object(formatter, 'formatTime', return_value='2023-10-26T10:00:00')
    mocker.patch.object(formatter, 'formatException', return_value='Test formatted exception')

    result = formatter.format(record)
    
    expected_log_record = {
        'timestamp': '2023-10-26T10:00:00',
        'level': 'ERROR',
        'logger_name': 'test_logger',
        'message': 'Test message',
        'pathname': '/test/path',
        'funcName': 'test_func',
        'lineno': 10,
        'exc_info': 'Test formatted exception'
    }
    assert json.loads(result) == expected_log_record

def test_CustomJsonFormatter_format_empty_message(mocker):
    # source_info: backend.main.CustomJsonFormatter.format
    formatter = CustomJsonFormatter()
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='/test/path',
        lineno=10,
        msg='',
        args=(),
        exc_info=None,
        func='test_func'
    )
    mocker.patch.object(formatter, 'formatTime', return_value='2023-10-26T10:00:00')

    result = formatter.format(record)

    expected_log_record = {
        'timestamp': '2023-10-26T10:00:00',
        'level': 'INFO',
        'logger_name': 'test_logger',
        'message': '',
        'pathname': '/test/path',
        'funcName': 'test_func',
        'lineno': 10
    }
    assert json.loads(result) == expected_log_record

def test_CustomJsonFormatter_format_no_exception_no_request_id(mocker):
    # source_info: backend.main.CustomJsonFormatter.format
    formatter = CustomJsonFormatter()
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='/test/path',
        lineno=10,
        msg='Test message',
        args=(),
        exc_info=None,
        func='test_func'
    )
    mocker.patch.object(formatter, 'formatTime', return_value='2023-10-26T10:00:00')

    result = formatter.format(record)

    expected_log_record = {
        'timestamp': '2023-10-26T10:00:00',
        'level': 'INFO',
        'logger_name': 'test_logger',
        'message': 'Test message',
        'pathname': '/test/path',
        'funcName': 'test_func',
        'lineno': 10
    }
    assert json.loads(result) == expected_log_record