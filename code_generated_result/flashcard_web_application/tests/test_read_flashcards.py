import pytest
from unittest.mock import patch, MagicMock
from typing import Optional

from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

from backend.routers.flashcards import read_flashcards
from backend import models

def test_read_flashcards_no_query_success(mocker):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_db = mocker.MagicMock(spec=Session)
    mock_flashcards = [models.Flashcard(front_text="Front 1", back_text="Back 1"), models.Flashcard(front_text="Front 2", back_text="Back 2")]
    mock_db.query.return_value.all.return_value = mock_flashcards

    result = read_flashcards(db=mock_db)

    assert result == mock_flashcards
    mock_db.query.assert_called_with(models.Flashcard)
    mock_db.query.return_value.all.assert_called_once()

def test_read_flashcards_with_query_success(mocker):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_db = mocker.MagicMock(spec=Session)
    mock_flashcards = [models.Flashcard(front_text="Front 1", back_text="Back 1")]
    mock_db.query.return_value.filter.return_value.all.return_value = mock_flashcards

    result = read_flashcards(query="Front", db=mock_db)

    assert result == mock_flashcards
    mock_db.query.assert_called_with(models.Flashcard)
    mock_db.query.return_value.filter.assert_called()
    mock_db.query.return_value.filter.return_value.all.assert_called_once()

def test_read_flashcards_db_error(mocker):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_db = mocker.MagicMock(spec=Session)
    mock_db.query.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        read_flashcards(db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Failed to read flashcards" in str(exc_info.value.detail)

def test_read_flashcards_with_empty_query_success(mocker):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_db = mocker.MagicMock(spec=Session)
    mock_flashcards = [models.Flashcard(front_text="Front 1", back_text="Back 1"), models.Flashcard(front_text="Front 2", back_text="Back 2")]
    mock_db.query.return_value.all.return_value = mock_flashcards

    result = read_flashcards(query="", db=mock_db)

    assert result == mock_flashcards
    mock_db.query.assert_called_with(models.Flashcard)
    mock_db.query.return_value.filter.assert_called()
    mock_db.query.return_value.filter.return_value.all.assert_called_once()