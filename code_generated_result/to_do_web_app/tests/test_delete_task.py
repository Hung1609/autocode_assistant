import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

from backend import models
from backend.routes import delete_task, get_db


def test_delete_task_success():
    """Test successful deletion of a task."""
    mock_db = MagicMock(spec=Session)
    mock_task = MagicMock(spec=models.Task, id=1)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_task

    delete_task(task_id=1, db=mock_db)

    mock_db.query.assert_called_once()
    mock_db.delete.assert_called_once_with(mock_task)
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()


def test_delete_task_not_found():
    """Test deletion when task is not found."""
    mock_db = MagicMock(spec=Session)
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        delete_task(task_id=1, db=mock_db)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Task not found"
    mock_db.query.assert_called_once()
    mock_db.delete.assert_not_called()
    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_not_called()


def test_delete_task_internal_server_error():
    """Test handling of internal server error during deletion."""
    mock_db = MagicMock(spec=Session)
    mock_task = MagicMock(spec=models.Task, id=1)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_task
    mock_db.delete.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        delete_task(task_id=1, db=mock_db)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Internal Server Error"
    mock_db.query.assert_called_once()
    mock_db.delete.assert_called_once()
    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_called_once()


def test_delete_task_db_dependency():
    """Test the dependency injection for the database session."""

    # Mock the actual database session to avoid real database interaction
    mock_db = MagicMock(spec=Session)

    # Mock the get_db dependency to return our mock_db
    with patch("backend.routes.get_db", return_value=mock_db) as mock_get_db:
        # Call delete_task with a dummy task_id
        try:
            delete_task(task_id=1, db=Depends(get_db))  # type: ignore

        except HTTPException as e:
            # If HTTPException is raised (like Task not found)
            # that is also an allowed path for this test
            if e.status_code == 404:
                pass
            else:
                raise e  # Re-raise any other HTTPException

        except Exception as e:
            # If any other exception occurs (not HTTPException)
            # Then the test case should fail
            raise e

        # Assert that get_db was called
        mock_get_db.assert_called_once()

        # Assert that delete_task uses the db session provided by the dependency
        # Check if query was called on the mock_db session
        mock_db.query.assert_called_once()