import pytest
from unittest.mock import patch
from fastapi import Request, HTTPException, Depends
from backend.database import get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def test_get_db_success(mocker):
    # source_info: backend.database.get_db
    mock_db = mocker.MagicMock()
    mock_SessionLocal = mocker.MagicMock(return_value=mock_db)
    mocker.patch("backend.database.SessionLocal", mock_SessionLocal)

    generator = get_db()
    db = next(generator)

    assert db == mock_db
    mock_SessionLocal.assert_called_once()
    db.close.assert_not_called()  # close is called in the finally block

    try:
        next(generator)  # Trigger the finally block
    except StopIteration:
        pass  # Expected

    db.close.assert_called_once()

def test_get_db_exception(mocker):
    # source_info: backend.database.get_db
    mock_db = mocker.MagicMock()
    mock_SessionLocal = mocker.MagicMock(return_value=mock_db)
    mocker.patch("backend.database.SessionLocal", mock_SessionLocal)
    mock_db.commit.side_effect = Exception("Simulated error")

    generator = get_db()
    db = next(generator)

    assert db == mock_db
    mock_SessionLocal.assert_called_once()
    db.close.assert_not_called()

    try:
        next(generator)
    except StopIteration:
        pass

    db.close.assert_called_once()