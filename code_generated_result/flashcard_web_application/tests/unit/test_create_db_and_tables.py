import pytest
from unittest.mock import patch
from backend.database import create_db_and_tables
import logging

def test_create_db_and_tables_success(mocker):
    # source_info: backend.database.create_db_and_tables
    mock_base = mocker.MagicMock()
    mock_engine = mocker.MagicMock()

    mocker.patch("backend.database.Base", mock_base)
    mocker.patch("backend.database.engine", mock_engine)
    mock_logger = mocker.spy(logging, 'info')

    create_db_and_tables()

    mock_base.metadata.create_all.assert_called_once_with(bind=mock_engine)
    assert mock_logger.call_count == 3
    assert mock_logger.call_args_list[0][0][0] == "Entering create_db_and_tables"
    assert mock_logger.call_args_list[1][0][0] == "Database and tables created successfully."
    assert mock_logger.call_args_list[2][0][0] == "Exiting create_db_and_tables"


def test_create_db_and_tables_failure(mocker):
    # source_info: backend.database.create_db_and_tables
    mock_base = mocker.MagicMock()
    mock_engine = mocker.MagicMock()
    mock_base.metadata.create_all.side_effect = Exception("Database error")

    mocker.patch("backend.database.Base", mock_base)
    mocker.patch("backend.database.engine", mock_engine)

    mock_logger_info = mocker.spy(logging, 'info')
    mock_logger_error = mocker.spy(logging, 'error')

    create_db_and_tables()

    mock_base.metadata.create_all.assert_called_once_with(bind=mock_engine)

    assert mock_logger_info.call_count == 2
    assert mock_logger_info.call_args_list[0][0][0] == "Entering create_db_and_tables"
    assert mock_logger_info.call_args_list[1][0][0] == "Exiting create_db_and_tables"

    assert mock_logger_error.call_count == 1
    assert "Error creating database and tables" in mock_logger_error.call_args_list[0][0][0]