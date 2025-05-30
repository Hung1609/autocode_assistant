import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, Depends
from backend.routers.flashcards import read_flashcards
from sqlalchemy.orm import Session
from typing import Optional
import logging

# Mocking models and database functions
class MockFlashcard:
    def __init__(self, front_text, back_text):
        self.front_text = front_text
        self.back_text = back_text

    def __repr__(self):
        return f"MockFlashcard(front_text='{self.front_text}', back_text='{self.back_text}')"


@pytest.fixture
def mock_db_session():
    """Mocks the database session."""
    db = MagicMock(spec=Session)
    return db


def test_read_flashcards_success_no_query(mock_db_session):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_flashcards = [MockFlashcard("front1", "back1"), MockFlashcard("front2", "back2")]
    mock_db_session.query().all.return_value = mock_flashcards
    
    result = read_flashcards(query=None, db=mock_db_session)
    
    assert result == mock_flashcards
    mock_db_session.query.assert_called()
    mock_db_session.query().all.assert_called()


def test_read_flashcards_success_with_query(mock_db_session):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_flashcards = [MockFlashcard("front1", "back1"), MockFlashcard("front2", "back2")]
    mock_db_session.query().filter().all.return_value = mock_flashcards
    
    result = read_flashcards(query="front1", db=mock_db_session)
    
    assert result == mock_flashcards
    mock_db_session.query.assert_called()
    mock_db_session.query().filter().all.assert_called()


def test_read_flashcards_no_results(mock_db_session):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_db_session.query().filter().all.return_value = []
    
    result = read_flashcards(query="nonexistent", db=mock_db_session)
    
    assert result == []
    mock_db_session.query.assert_called()
    mock_db_session.query().filter().all.assert_called()


def test_read_flashcards_db_error(mock_db_session):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_db_session.query.side_effect = Exception("Database error")
    
    with pytest.raises(HTTPException) as exc_info:
        read_flashcards(query="some_query", db=mock_db_session)
    
    assert exc_info.value.status_code == 500
    assert "Failed to read flashcards" in exc_info.value.detail
    mock_db_session.query.assert_called()


def test_read_flashcards_empty_query(mock_db_session):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_flashcards = [MockFlashcard("front1", "back1"), MockFlashcard("front2", "back2")]
    mock_db_session.query().all.return_value = mock_flashcards
    
    result = read_flashcards(query="", db=mock_db_session)
    
    assert result == mock_flashcards
    mock_db_session.query.assert_called()
    mock_db_session.query().all.assert_called()


def test_read_flashcards_with_special_characters_in_query(mock_db_session):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_flashcards = [MockFlashcard("front!@#", "back1"), MockFlashcard("front2", "back$^*")]
    mock_db_session.query().filter().all.return_value = mock_flashcards
    
    result = read_flashcards(query="!@#", db=mock_db_session)
    
    assert result == mock_flashcards
    mock_db_session.query.assert_called()
    mock_db_session.query().filter().all.assert_called()

def test_read_flashcards_log_error(mock_db_session, mocker):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_db_session.query.side_effect = Exception("Database error")
    mock_logger = mocker.patch('backend.routers.flashcards.logger')

    with pytest.raises(HTTPException) as exc_info:
        read_flashcards(query="some_query", db=mock_db_session)

    mock_logger.error.assert_called()

def test_read_flashcards_log_info_enter_exit(mock_db_session, mocker):
    # source_info: backend.routers.flashcards.read_flashcards
    mock_flashcards = [MockFlashcard("front1", "back1"), MockFlashcard("front2", "back2")]
    mock_db_session.query().all.return_value = mock_flashcards
    mock_logger = mocker.patch('backend.routers.flashcards.logger')

    read_flashcards(query=None, db=mock_db_session)

    mock_logger.info.assert_called()
    assert mock_logger.info.call_count == 2