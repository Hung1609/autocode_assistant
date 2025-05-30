import pytest
from unittest.mock import patch
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from backend.routers.flashcards import create_flashcard
import backend.schemas as schemas
import backend.models as models


def test_create_flashcard_success(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    flashcard_data = schemas.FlashcardCreate(front_text="Front", back_text="Back")
    mock_db = mocker.MagicMock(spec=Session)
    mock_db_flashcard = models.Flashcard(front_text="Front", back_text="Back")
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None
    
    result = create_flashcard(flashcard_data, db=mock_db)

    mock_db.add.assert_called()
    mock_db.commit.assert_called()
    mock_db.refresh.assert_called()
    assert result.front_text == "Front"
    assert result.back_text == "Back"


def test_create_flashcard_db_error(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    flashcard_data = schemas.FlashcardCreate(front_text="Front", back_text="Back")
    mock_db = mocker.MagicMock(spec=Session)
    mock_db.add.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        create_flashcard(flashcard_data, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Failed to create flashcard" in exc_info.value.detail
    mock_db.add.assert_called()


def test_create_flashcard_empty_front_text(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    flashcard_data = schemas.FlashcardCreate(front_text="", back_text="Back")
    mock_db = mocker.MagicMock(spec=Session)

    with pytest.raises(HTTPException) as exc_info:
        create_flashcard(flashcard_data, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Failed to create flashcard" in exc_info.value.detail
    
def test_create_flashcard_empty_back_text(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    flashcard_data = schemas.FlashcardCreate(front_text="Front", back_text="")
    mock_db = mocker.MagicMock(spec=Session)

    with pytest.raises(HTTPException) as exc_info:
        create_flashcard(flashcard_data, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Failed to create flashcard" in exc_info.value.detail

def test_create_flashcard_long_text(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    long_text = "A" * 2000
    flashcard_data = schemas.FlashcardCreate(front_text=long_text, back_text=long_text)
    mock_db = mocker.MagicMock(spec=Session)

    result = create_flashcard(flashcard_data, db=mock_db)

    assert result.front_text == long_text
    assert result.back_text == long_text