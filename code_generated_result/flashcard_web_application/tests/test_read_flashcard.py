import pytest
from unittest.mock import patch
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from backend.routers.flashcards import read_flashcard
import backend.models as models
from backend.database import get_db

def test_read_flashcard_success(mocker):
    # source_info: backend.routers.flashcards.read_flashcard
    mock_db = mocker.MagicMock(spec=Session)
    mock_flashcard = mocker.MagicMock(spec=models.Flashcard, id=1, front="Front", back="Back")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_flashcard

    result = read_flashcard(flashcard_id=1, db=mock_db)

    assert result == mock_flashcard
    mock_db.query.assert_called_once_with(models.Flashcard)
    mock_db.query.return_value.filter.assert_called_once_with(models.Flashcard.id == 1)
    mock_db.query.return_value.filter.return_value.first.assert_called_once()

def test_read_flashcard_not_found(mocker):
    # source_info: backend.routers.flashcards.read_flashcard
    mock_db = mocker.MagicMock(spec=Session)
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        read_flashcard(flashcard_id=1, db=mock_db)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Flashcard not found"
    mock_db.query.assert_called_once_with(models.Flashcard)
    mock_db.query.return_value.filter.assert_called_once_with(models.Flashcard.id == 1)
    mock_db.query.return_value.filter.return_value.first.assert_called_once()

def test_read_flashcard_db_error(mocker):
    # source_info: backend.routers.flashcards.read_flashcard
    mock_db = mocker.MagicMock(spec=Session)
    mock_db.query.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        read_flashcard(flashcard_id=1, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Failed to read flashcard" in exc_info.value.detail
    mock_db.query.assert_called_once_with(models.Flashcard)

def test_read_flashcard_http_exception_raised(mocker):
    # source_info: backend.routers.flashcards.read_flashcard
    mock_db = mocker.MagicMock(spec=Session)
    mock_db.query.return_value.filter.return_value.first.side_effect = HTTPException(status_code=400, detail="Bad request")

    with pytest.raises(HTTPException) as exc_info:
        read_flashcard(flashcard_id=1, db=mock_db)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Bad request"
    mock_db.query.assert_called_once_with(models.Flashcard)

def test_read_flashcard_integration(mocker):
    # source_info: backend.routers.flashcards.read_flashcard
    mock_db = mocker.MagicMock(spec=Session)
    mock_flashcard = mocker.MagicMock(spec=models.Flashcard, id=1, front="Front", back="Back")

    def mock_get_db():
        try:
            yield mock_db
        finally:
            pass
    
    mock_db.query.return_value.filter.return_value.first.return_value = mock_flashcard

    with patch("backend.routers.flashcards.get_db", side_effect=mock_get_db):
        result = read_flashcard(flashcard_id=1, db=mock_db)

    assert result == mock_flashcard
    mock_db.query.assert_called_once_with(models.Flashcard)
    mock_db.query.return_value.filter.assert_called_once_with(models.Flashcard.id == 1)
    mock_db.query.return_value.filter.return_value.first.assert_called_once()