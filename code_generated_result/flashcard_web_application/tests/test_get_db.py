import pytest
from unittest.mock import patch, MagicMock
from fastapi import Request, HTTPException, Depends
from backend.database import get_db
import logging

def test_get_db_success(mocker):
    # source_info: backend.database.get_db
    mock_db = MagicMock()
    mock_session_local = mocker.patch("backend.database.SessionLocal", return_value=mock_db)
    mock_logger = mocker.patch("backend.database.logger")

    generator = get_db()
    db = next(generator)

    assert db == mock_db
    mock_session_local.assert_called_once()
    mock_logger.info.assert_called_with("Entering get_db")

    try:
        next(generator)
    except StopIteration:
        pass  # Expected

    mock_db.close.assert_called_once()
    mock_logger.info.assert_called_with("Exiting get_db")