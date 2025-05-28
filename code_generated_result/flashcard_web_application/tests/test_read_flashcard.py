import pytest
from unittest.mock import patch, MagicMock

from fastapi import Request, HTTPException, Depends
from backend.routers.flashcards import read_flashcard
from sqlalchemy.orm import Session

def test_read_flashcard_success(mocker):
    # source_info: backend.routers.flashcards.read_flashcard
    mock_db = mocker.MagicMock()
    mock_flashcard = mocker.MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_flashcard

    result = read_flashcard(flashcard_id=1, db=mock_db)

    assert result == mock_flashcard
    mock_db.query.assert_called_once()
    mock_db.query.return_value.filter.assert_called_once()
    mock_db.query.return_value.filter.return_value.first.assert_called_once()


def test_read_flashcard_not_found(mocker):
    # source_info: backend.routers.flashcards.read_flashcard
    mock_db = mocker.MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        read_flashcard(flashcard_id=1, db=mock_db)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Flashcard not found"
    mock_db.query.assert_called_once()
    mock_db.query.return_value.filter.assert_called_once()
    mock_db.query.return_value.filter.return_value.first.assert_called_once()


def test_read_flashcard_db_error(mocker):
    # source_info: backend.routers.flashcards.read_flashcard
    mock_db = mocker.MagicMock()
    mock_db.query.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        read_flashcard(flashcard_id=1, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Failed to read flashcard" in exc_info.value.detail
    mock_db.query.assert_called_once()


def test_read_flashcard_http_exception_raised(mocker):
    # source_info: backend.routers.flashcards.read_flashcard
    mock_db = mocker.MagicMock()
    mock_db.query.return_value.filter.return_value.first.side_effect = HTTPException(status_code=400, detail="Bad Request")

    with pytest.raises(HTTPException) as exc_info:
        read_flashcard(flashcard_id=1, db=mock_db)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Bad Request"
    mock_db.query.assert_called_once()
    mock_db.query.return_value.filter.assert_called_once()
    mock_db.query.return_value.filter.return_value.first.assert_called_once()