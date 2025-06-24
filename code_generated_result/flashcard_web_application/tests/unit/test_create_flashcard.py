import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

from backend.routers.flashcards import create_flashcard
from backend import schemas
from backend import models


def test_create_flashcard_success(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    flashcard_create = schemas.FlashcardCreate(question="What is FastAPI?", answer="A modern, fast (high-performance), web framework for building APIs with Python 3.7+ based on standard Python type hints.")
    mock_db = MagicMock(spec=Session)
    mock_db_flashcard = models.Flashcard(**flashcard_create.dict())

    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None

    result = create_flashcard(flashcard=flashcard_create, db=mock_db)

    mock_db.add.assert_called()
    mock_db.commit.assert_called()
    mock_db.refresh.assert_called()

    assert result == mock_db_flashcard


def test_create_flashcard_db_error(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    flashcard_create = schemas.FlashcardCreate(question="What is FastAPI?", answer="A modern, fast (high-performance), web framework for building APIs with Python 3.7+ based on standard Python type hints.")
    mock_db = MagicMock(spec=Session)
    mock_db.add.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        create_flashcard(flashcard=flashcard_create, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Database error" in str(exc_info.value.detail)
    mock_db.add.assert_called()
    mock_db.commit.assert_not_called()
    mock_db.refresh.assert_not_called()


def test_create_flashcard_empty_question(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    flashcard_create = schemas.FlashcardCreate(question="", answer="Some answer")
    mock_db = MagicMock(spec=Session)

    with pytest.raises(HTTPException) as exc_info:
        create_flashcard(flashcard=flashcard_create, db=mock_db)

    assert exc_info.value.status_code == 500


def test_create_flashcard_empty_answer(mocker):
    # source_info: backend.routers.flashcards.create_flashcard
    flashcard_create = schemas.FlashcardCreate(question="Some Question", answer="")
    mock_db = MagicMock(spec=Session)

    with pytest.raises(HTTPException) as exc_info:
        create_flashcard(flashcard=flashcard_create, db=mock_db)

    assert exc_info.value.status_code == 500