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
    request_id_ctx.set(None)

    result = request_id_filter.filter(record)
    assert result is True
    assert record.request_id is None