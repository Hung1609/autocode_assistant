import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, Depends
from backend.routers.flashcards import read_flashcard
from sqlalchemy.orm import Session

def test_read_flashcard_success(mocker):
    # source_info: backend.routers.flashcards.read_flashcard
    mock_db = MagicMock()
    mock_flashcard = MagicMock(id=1, question="Test Question", answer="Test Answer")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_flashcard

    def get_mock_db():
        return mock_db

    result = read_flashcard(flashcard_id=1, db=Depends(get_mock_db))

    assert result == mock_flashcard
    mock_db.query.assert_called_once()
    mock_db.query.return_value.filter.assert_called_once()
    mock_db.query.return_value.filter.return_value.first.assert_called_once()

def test_read_flashcard_not_found(mocker):
    # source_info: backend.routers.flashcards.read_flashcard
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    def get_mock_db():
        return mock_db

    with pytest.raises(HTTPException) as exc_info:
        read_flashcard(flashcard_id=1, db=Depends(get_mock_db))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Flashcard not found"
    mock_db.query.assert_called_once()
    mock_db.query.return_value.filter.assert_called_once()
    mock_db.query.return_value.filter.return_value.first.assert_called_once()

def test_read_flashcard_database_error(mocker):
    # source_info: backend.routers.flashcards.read_flashcard
    mock_db = MagicMock()
    mock_db.query.side_effect = Exception("Database error")

    def get_mock_db():
        return mock_db

    with pytest.raises(HTTPException) as exc_info:
        read_flashcard(flashcard_id=1, db=Depends(get_mock_db))

    assert exc_info.value.status_code == 500
    assert "Failed to read flashcard" in exc_info.value.detail
    mock_db.query.assert_called_once()

def test_read_flashcard_http_exception_re_raised(mocker):
    # source_info: backend.routers.flashcards.read_flashcard
    mock_db = MagicMock()
    mock_db.query.side_effect = HTTPException(status_code=400, detail="Bad Request")

    def get_mock_db():
        return mock_db

    with pytest.raises(HTTPException) as exc_info:
        read_flashcard(flashcard_id=1, db=Depends(get_mock_db))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Bad Request"
    mock_db.query.assert_called_once()