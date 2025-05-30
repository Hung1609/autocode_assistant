import pytest
from unittest.mock import MagicMock
from backend.main import RequestIDFilter
from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id")

def test_RequestIDFilter_filter_success():
    # source_info: backend.main.RequestIDFilter.filter
    record = MagicMock()
    request_id_ctx.set("test_request_id")
    request_id_filter = RequestIDFilter()
    result = request_id_filter.filter(record)
    assert result is True
    assert record.request_id == "test_request_id"

def test_RequestIDFilter_filter_no_request_id():
    # source_info: backend.main.RequestIDFilter.filter
    record = MagicMock()
    request_id_filter = RequestIDFilter()
    result = request_id_filter.filter(record)
    assert result is True
    assert record.request_id is None

def test_RequestIDFilter_filter_empty_request_id():
    # source_info: backend.main.RequestIDFilter.filter
    record = MagicMock()
    request_id_ctx.set("")
    request_id_filter = RequestIDFilter()
    result = request_id_filter.filter(record)
    assert result is True
    assert record.request_id == ""

def test_RequestIDFilter_filter_different_request_ids():
    # source_info: backend.main.RequestIDFilter.filter
    record1 = MagicMock()
    record2 = MagicMock()

    request_id_ctx.set("request_id_1")
    request_id_filter = RequestIDFilter()
    result1 = request_id_filter.filter(record1)
    assert result1 is True
    assert record1.request_id == "request_id_1"

    request_id_ctx.set("request_id_2")
    result2 = request_id_filter.filter(record2)
    assert result2 is True
    assert record2.request_id == "request_id_2"