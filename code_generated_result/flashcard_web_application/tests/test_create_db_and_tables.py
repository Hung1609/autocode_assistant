import pytest
from unittest.mock import patch
from backend.database import create_db_and_tables
from fastapi import Request, HTTPException, Depends


def test_create_db_and_tables_success(mocker):
    # source_info: backend.database.create_db_and_tables
    mock_base = mocker.patch("backend.database.Base")
    mock_engine = mocker.patch("backend.database.engine")
    mock_logger = mocker.patch("backend.database.logger")

    create_db_and_tables()

    mock_base.metadata.create_all.assert_called_once_with(bind=mock_engine)
    mock_logger.info.assert_any_call("Entering create_db_and_tables")
    mock_logger.info.assert_any_call("Database and tables created successfully.")
    mock_logger.info.assert_any_call("Exiting create_db_and_tables")


def test_create_db_and_tables_exception(mocker):
    # source_info: backend.database.create_db_and_tables
    mock_base = mocker.patch("backend.database.Base")
    mock_engine = mocker.patch("backend.database.engine")
    mock_logger = mocker.patch("backend.database.logger")
    mock_base.metadata.create_all.side_effect = Exception("Test Exception")

    create_db_and_tables()

    mock_logger.info.assert_any_call("Entering create_db_and_tables")
    mock_logger.error.assert_called_once()
    mock_logger.info.assert_any_call("Exiting create_db_and_tables")