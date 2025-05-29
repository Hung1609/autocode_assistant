import pytest
from unittest.mock import patch
from fastapi import Request, HTTPException, Depends
from backend.routers.flashcards import create_flashcard
from sqlalchemy.orm import Session
from backend import schemas, models

def test_create_flashcard_success(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    mock_db = mocker.MagicMock(spec=Session)
    flashcard_data = schemas.FlashcardCreate(front_text="Front", back_text="Back")
    
    result = create_flashcard(flashcard=flashcard_data, db=mock_db)

    mock_db.add.assert_called()
    mock_db.commit.assert_called()
    mock_db.refresh.assert_called()

    assert result.front_text == "Front"
    assert result.back_text == "Back"

def test_create_flashcard_db_error(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    mock_db = mocker.MagicMock(spec=Session)
    flashcard_data = schemas.FlashcardCreate(front_text="Front", back_text="Back")
    mock_db.add.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        create_flashcard(flashcard=flashcard_data, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Failed to create flashcard" in exc_info.value.detail

def test_create_flashcard_empty_front_text(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    mock_db = mocker.MagicMock(spec=Session)
    flashcard_data = schemas.FlashcardCreate(front_text="", back_text="Back")

    with pytest.raises(HTTPException) as exc_info:
        create_flashcard(flashcard=flashcard_data, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Failed to create flashcard" in exc_info.value.detail
    
def test_create_flashcard_empty_back_text(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    mock_db = mocker.MagicMock(spec=Session)
    flashcard_data = schemas.FlashcardCreate(front_text="Front", back_text="")

    with pytest.raises(HTTPException) as exc_info:
        create_flashcard(flashcard=flashcard_data, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Failed to create flashcard" in exc_info.value.detail