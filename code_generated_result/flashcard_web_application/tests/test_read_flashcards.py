import pytest
from unittest.mock import patch, MagicMock

from fastapi import Request, HTTPException, Depends
from backend.routers.flashcards import read_flashcards
from sqlalchemy.orm import Session


def test_read_flashcards_success_no_query(mocker):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_db = MagicMock()
    mock_flashcards = [MagicMock(), MagicMock()]
    mock_db.query.return_value.all.return_value = mock_flashcards
    mock_get_db = MagicMock(return_value=mock_db)

    result = read_flashcards(db=mock_db)

    assert result == mock_flashcards
    mock_db.query.assert_called_once()
    mock_db.query.return_value.all.assert_called_once()


def test_read_flashcards_success_with_query(mocker):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_db = MagicMock()
    mock_flashcards = [MagicMock(), MagicMock()]
    mock_db.query.return_value.filter.return_value.all.return_value = mock_flashcards
    mock_get_db = MagicMock(return_value=mock_db)
    query_text = "test"

    result = read_flashcards(query=query_text, db=mock_db)

    assert result == mock_flashcards
    mock_db.query.assert_called_once()
    mock_db.query.return_value.filter.assert_called_once()
    mock_db.query.return_value.filter.return_value.all.assert_called_once()


def test_read_flashcards_db_error(mocker):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_db = MagicMock()
    mock_db.query.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        read_flashcards(db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Failed to read flashcards" in str(exc_info.value.detail)
    mock_db.query.assert_called_once()


def test_read_flashcards_empty_result(mocker):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = []

    result = read_flashcards(db=mock_db)

    assert result == []
    mock_db.query.assert_called_once()
    mock_db.query.return_value.all.assert_called_once()