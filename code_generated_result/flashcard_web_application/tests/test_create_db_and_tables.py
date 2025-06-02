import pytest
from unittest import mock
from backend.database import create_db_and_tables
from fastapi import Request, HTTPException, Depends
from pytest_mock import MockerFixture
import logging

def test_create_db_and_tables_success(mocker: MockerFixture):
    # source_info: backend.database.create_db_and_tables
    mock_base = mocker.patch("backend.database.Base")
    mock_engine = mocker.patch("backend.database.engine")
    mock_logger = mocker.patch("backend.database.logger")

    create_db_and_tables()

    mock_base.metadata.create_all.assert_called_once_with(bind=mock_engine)
    mock_logger.info.assert_has_calls([
        mock.call("Entering create_db_and_tables"),
        mock.call("Database and tables created successfully."),
        mock.call("Exiting create_db_and_tables")
    ])

def test_create_db_and_tables_error(mocker: MockerFixture):
    # source_info: backend.database.create_db_and_tables
    mock_base = mocker.patch("backend.database.Base")
    mock_engine = mocker.patch("backend.database.engine")
    mock_logger = mocker.patch("backend.database.logger")
    mock_base.metadata.create_all.side_effect = Exception("Test Exception")

    create_db_and_tables()

    mock_base.metadata.create_all.assert_called_once_with(bind=mock_engine)
    mock_logger.info.assert_called_once_with("Entering create_db_and_tables")
    mock_logger.error.assert_called_once()
    mock_logger.info.assert_called_with("Exiting create_db_and_tables")