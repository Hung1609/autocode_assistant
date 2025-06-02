import pytest
from unittest.mock import MagicMock
from backend.main import RequestIDFilter, request_id_ctx

def test_RequestIDFilter_filter_success():
    # source_info: backend.main.RequestIDFilter.filter
    record = MagicMock()
    request_id_ctx.set("test_request_id")
    filter_obj = RequestIDFilter()
    result = filter_obj.filter(record)
    assert result is True
    assert record.request_id == "test_request_id"

def test_RequestIDFilter_filter_no_request_id():
    # source_info: backend.main.RequestIDFilter.filter
    record = MagicMock()
    request_id_ctx.set(None)
    filter_obj = RequestIDFilter()
    result = filter_obj.filter(record)
    assert result is True
    assert record.request_id is None

def test_RequestIDFilter_filter_empty_request_id():
    # source_info: backend.main.RequestIDFilter.filter
    record = MagicMock()
    request_id_ctx.set("")
    filter_obj = RequestIDFilter()
    result = filter_obj.filter(record)
    assert result is True
    assert record.request_id == ""