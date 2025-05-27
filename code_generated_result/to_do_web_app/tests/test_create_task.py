import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from backend import schemas
from backend import models
from backend.routes import create_task


def test_create_task_success(mocker):
    """Test successful task creation."""
    mock_db = MagicMock()
    mock_task_create = schemas.TaskCreate(description="Test Task")
    mock_db_task = models.Task(id=1, description="Test Task")

    # Mock the Task model constructor
    mocker.patch("backend.models.Task", return_value=mock_db_task)

    result = create_task(task=mock_task_create, db=mock_db)

    # Assertions
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(mock_db_task)
    assert result == mock_db_task


def test_create_task_db_error(mocker):
    """Test task creation failure due to database error."""
    mock_db = MagicMock()
    mock_task_create = schemas.TaskCreate(description="Test Task")

    # Mock database commit to raise an exception
    mock_db.commit.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        create_task(task=mock_task_create, db=mock_db)

    # Assertions
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Internal Server Error"
    mock_db.rollback.assert_called_once()


def test_create_task_empty_description(mocker):
    """Test task creation with an empty description."""
    mock_db = MagicMock()
    mock_task_create = schemas.TaskCreate(description="")
    mock_db_task = models.Task(id=1, description="")

    # Mock the Task model constructor
    mocker.patch("backend.models.Task", return_value=mock_db_task)

    result = create_task(task=mock_task_create, db=mock_db)

    # Assertions
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(mock_db_task)
    assert result == mock_db_task