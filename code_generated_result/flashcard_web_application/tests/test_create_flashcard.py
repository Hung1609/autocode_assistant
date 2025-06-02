import pytest
from unittest.mock import patch, MagicMock

from fastapi import Request, HTTPException, Depends
from backend.routers.flashcards import create_flashcard
from sqlalchemy.orm import Session
from backend import schemas, models

def test_create_flashcard_success(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    flashcard_create = schemas.FlashcardCreate(front_text="Front", back_text="Back")
    mock_db = MagicMock(spec=Session)
    
    result = create_flashcard(flashcard_create, db=mock_db)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()
    assert result == mock_db.add.return_value
    
def test_create_flashcard_db_error(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    flashcard_create = schemas.FlashcardCreate(front_text="Front", back_text="Back")
    mock_db = MagicMock(spec=Session)
    mock_db.add.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        create_flashcard(flashcard_create, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Failed to create flashcard" in exc_info.value.detail

def test_create_flashcard_empty_front_text(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    flashcard_create = schemas.FlashcardCreate(front_text="", back_text="Back")
    mock_db = MagicMock(spec=Session)
    
    with pytest.raises(HTTPException) as exc_info:
        create_flashcard(flashcard_create, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Failed to create flashcard" in exc_info.value.detail

def test_create_flashcard_empty_back_text(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    flashcard_create = schemas.FlashcardCreate(front_text="Front", back_text="")
    mock_db = MagicMock(spec=Session)

    with pytest.raises(HTTPException) as exc_info:
        create_flashcard(flashcard_create, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Failed to create flashcard" in exc_info.value.detail

def test_create_flashcard_commit_error(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    flashcard_create = schemas.FlashcardCreate(front_text="Front", back_text="Back")
    mock_db = MagicMock(spec=Session)
    mock_db.commit.side_effect = Exception("Commit error")
    
    with pytest.raises(HTTPException) as exc_info:
        create_flashcard(flashcard_create, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Failed to create flashcard" in exc_info.value.detail

def test_create_flashcard_refresh_error(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    flashcard_create = schemas.FlashcardCreate(front_text="Front", back_text="Back")
    mock_db = MagicMock(spec=Session)
    mock_db.refresh.side_effect = Exception("Refresh error")

    with pytest.raises(HTTPException) as exc_info:
        create_flashcard(flashcard_create, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Failed to create flashcard" in exc_info.value.detail