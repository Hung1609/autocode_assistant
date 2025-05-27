import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.routes import update_task

def test_update_task_success():
    """Test successful update of a task."""
    task_id = 1
    task_update = schemas.TaskUpdate(is_complete=True)
    db_task_mock = MagicMock(spec=models.Task, id=task_id, is_complete=False)
    db_mock = MagicMock(spec=Session)
    db_mock.query.return_value.filter.return_value.first.return_value = db_task_mock

    result = update_task(task_id, task_update, db_mock)

    assert result == db_task_mock
    assert db_task_mock.is_complete == task_update.is_complete
    db_mock.commit.assert_called_once()
    db_mock.refresh.assert_called_once_with(db_task_mock)


def test_update_task_not_found():
    """Test update task when task is not found."""
    task_id = 1
    task_update = schemas.TaskUpdate(is_complete=True)
    db_mock = MagicMock(spec=Session)
    db_mock.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        update_task(task_id, task_update, db_mock)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Task not found"
    db_mock.commit.assert_not_called()


def test_update_task_db_error():
    """Test update task when a database error occurs."""
    task_id = 1
    task_update = schemas.TaskUpdate(is_complete=True)
    db_task_mock = MagicMock(spec=models.Task, id=task_id, is_complete=False)
    db_mock = MagicMock(spec=Session)
    db_mock.query.return_value.filter.return_value.first.return_value = db_task_mock
    db_mock.commit.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        update_task(task_id, task_update, db_mock)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Internal Server Error"
    db_mock.rollback.assert_called_once()
    db_mock.refresh.assert_not_called()


def test_update_task_is_complete_false():
    """Test successful update of a task setting is_complete to False."""
    task_id = 1
    task_update = schemas.TaskUpdate(is_complete=False)
    db_task_mock = MagicMock(spec=models.Task, id=task_id, is_complete=True)
    db_mock = MagicMock(spec=Session)
    db_mock.query.return_value.filter.return_value.first.return_value = db_task_mock

    result = update_task(task_id, task_update, db_mock)

    assert result == db_task_mock
    assert db_task_mock.is_complete == task_update.is_complete
    db_mock.commit.assert_called_once()
    db_mock.refresh.assert_called_once_with(db_task_mock)