import pytest
from unittest.mock import patch
from fastapi import Request, HTTPException, Depends
from backend.main import health_check
import logging


def test_health_check_success(mocker):
    # source_info: backend.main.health_check
    mock_logger = mocker.patch('backend.main.logger')
    result = health_check()
    assert result == {"status": "ok"}
    mock_logger.info.assert_called_once_with("Health check endpoint hit")