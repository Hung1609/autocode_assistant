import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from backend import models
from backend.routes import read_tasks
from sqlalchemy.orm import Session

def test_read_tasks_success():
    """Test successful retrieval of tasks from the database."""
    mock_db = MagicMock()
    mock_tasks = [MagicMock(id=1, title="Task 1"), MagicMock(id=2, title="Task 2")]
    mock_db.query.return_value.all.return_value = mock_tasks

    result = read_tasks(db=mock_db)

    assert result == mock_tasks
    mock_db.query.assert_called_once_with(models.Task)
    mock_db.query.return_value.all.assert_called_once()


def test_read_tasks_empty_database():
    """Test retrieval of tasks when the database is empty."""
    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = []

    result = read_tasks(db=mock_db)

    assert result == []
    mock_db.query.assert_called_once_with(models.Task)
    mock_db.query.return_value.all.assert_called_once()


def test_read_tasks_database_error():
    """Test handling of database errors during task retrieval."""
    mock_db = MagicMock()
    mock_db.query.return_value.all.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        read_tasks(db=mock_db)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Internal Server Error"
    mock_db.query.assert_called_once_with(models.Task)
    mock_db.query.return_value.all.assert_called_once()