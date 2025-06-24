import pytest
from unittest.mock import patch, MagicMock
from typing import Optional

from fastapi import Request, HTTPException, Depends
from backend.routers.flashcards import read_flashcards
import backend.models as models


def test_read_flashcards_no_query_success(mocker):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_db = mocker.MagicMock()
    mock_flashcards = [models.Flashcard(front_text="front1", back_text="back1"), models.Flashcard(front_text="front2", back_text="back2")]
    mock_db.query.return_value.all.return_value = mock_flashcards
    mock_get_db = mocker.MagicMock(return_value=mock_db)
    
    result = read_flashcards(db=mock_get_db)

    assert result == mock_flashcards
    mock_db.query.assert_called_once_with(models.Flashcard)
    mock_db.query.return_value.all.assert_called_once()

def test_read_flashcards_with_query_success(mocker):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_db = mocker.MagicMock()
    mock_flashcards = [models.Flashcard(front_text="front1", back_text="back1")]
    mock_db.query.return_value.filter.return_value.all.return_value = mock_flashcards
    mock_get_db = mocker.MagicMock(return_value=mock_db)
    query_string = "front1"
    
    result = read_flashcards(query=query_string, db=mock_get_db)

    assert result == mock_flashcards
    mock_db.query.assert_called_once_with(models.Flashcard)
    mock_db.query.return_value.filter.assert_called()
    mock_db.query.return_value.filter.return_value.all.assert_called_once()

def test_read_flashcards_db_error(mocker):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_db = mocker.MagicMock()
    mock_db.query.side_effect = Exception("Database error")
    mock_get_db = mocker.MagicMock(return_value=mock_db)

    with pytest.raises(HTTPException) as exc_info:
        read_flashcards(db=mock_get_db)

    assert exc_info.value.status_code == 500
    assert "Database error" in str(exc_info.value.detail)

def test_read_flashcards_with_empty_query(mocker):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_db = mocker.MagicMock()
    mock_flashcards = []
    mock_db.query.return_value.all.return_value = mock_flashcards
    mock_get_db = mocker.MagicMock(return_value=mock_db)

    result = read_flashcards(query="", db=mock_get_db)

    assert result == mock_flashcards
    mock_db.query.assert_called_once_with(models.Flashcard)
    mock_db.query.return_value.all.assert_called_once()