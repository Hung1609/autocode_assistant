import unittest.mock
from fastapi import Request, HTTPException
from backend.main import health_check
import pytest


def test_health_check_success():
    """
    Test the health_check function for a successful response.
    """
    result = health_check()
    assert result == {"status": "ok"}


def test_health_check_logging(caplog):
    """
    Test that the health_check function logs entry and exit messages.
    """
    health_check()
    assert "Entering health_check with args: , kwargs: " in caplog.text
    assert "Exiting health_check with result: {'status': 'ok'}" in caplog.text