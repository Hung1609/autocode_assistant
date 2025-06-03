import pytest
from unittest.mock import MagicMock

from backend.main import RequestIDFilter

def test_RequestIDFilter_filter_success():
    # source_info: backend.main.RequestIDFilter.filter
    record_mock = MagicMock()
    request_id_ctx_mock = MagicMock()
    request_id_ctx_mock.get.return_value = "test_request_id"

    filter_instance = RequestIDFilter()
    filter_instance.request_id_ctx = request_id_ctx_mock

    result = filter_instance.filter(record_mock)

    assert result is True
    assert record_mock.request_id == "test_request_id"

def test_RequestIDFilter_filter_no_request_id():
    # source_info: backend.main.RequestIDFilter.filter
    record_mock = MagicMock()
    request_id_ctx_mock = MagicMock()
    request_id_ctx_mock.get.return_value = None

    filter_instance = RequestIDFilter()
    filter_instance.request_id_ctx = request_id_ctx_mock

    result = filter_instance.filter(record_mock)

    assert result is True
    assert record_mock.request_id is None