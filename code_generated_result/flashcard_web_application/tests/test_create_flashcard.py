import pytest
from unittest.mock import patch, MagicMock

from fastapi import Request, HTTPException, Depends
from backend.routers.flashcards import create_flashcard
from sqlalchemy.orm import Session

from backend import schemas, models


def test_create_flashcard_success(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    flashcard_data = schemas.FlashcardCreate(question="Test Question", answer="Test Answer")
    db_mock = mocker.MagicMock(spec=Session)
    db_flashcard_mock = mocker.MagicMock(spec=models.Flashcard)
    db_flashcard_mock.question = "Test Question"
    db_flashcard_mock.answer = "Test Answer"
    
    
    result = create_flashcard(flashcard_data, db_mock)
    
    db_mock.add.assert_called_once()
    db_mock.commit.assert_called_once()
    db_mock.refresh.assert_called_once()
    assert result.question == "Test Question"
    assert result.answer == "Test Answer"


def test_create_flashcard_db_error(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    flashcard_data = schemas.FlashcardCreate(question="Test Question", answer="Test Answer")
    db_mock = mocker.MagicMock(spec=Session)
    db_mock.add.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        create_flashcard(flashcard_data, db_mock)

    assert exc_info.value.status_code == 500
    assert "Failed to create flashcard" in str(exc_info.value.detail)
    db_mock.add.assert_called_once()
    db_mock.commit.assert_not_called()
    db_mock.refresh.assert_not_called()


def test_create_flashcard_invalid_input(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    # Simulate an invalid flashcard schema

    flashcard_data = schemas.FlashcardCreate(question="", answer="") # Invalid: empty strings.
    db_mock = mocker.MagicMock(spec=Session)

    with pytest.raises(HTTPException) as exc_info:
         create_flashcard(flashcard_data, db_mock)
    db_mock.add.assert_called_once()
    db_mock.commit.assert_called_once()
    db_mock.refresh.assert_called_once()
    
def test_create_flashcard_sqlalchemy_error(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    flashcard_data = schemas.FlashcardCreate(question="Test Question", answer="Test Answer")
    db_mock = mocker.MagicMock(spec=Session)
    db_mock.commit.side_effect = Exception("SQLAlchemy error")

    with pytest.raises(HTTPException) as exc_info:
        create_flashcard(flashcard_data, db_mock)

    assert exc_info.value.status_code == 500
    assert "Failed to create flashcard" in str(exc_info.value.detail)
    db_mock.add.assert_called_once()
    db_mock.commit.assert_called_once()
    db_mock.refresh.assert_not_called()