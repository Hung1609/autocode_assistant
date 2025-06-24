import pytest
from unittest.mock import patch
from backend.database import create_db_and_tables
import logging

def test_create_db_and_tables_success(mocker):
    # source_info: backend.database.create_db_and_tables
    mock_base = mocker.MagicMock()
    mock_engine = mocker.MagicMock()

    with patch("backend.database.Base", mock_base), patch("backend.database.engine", mock_engine), patch("backend.database.logger") as mock_logger:
        create_db_and_tables()

        mock_base.metadata.create_all.assert_called_once_with(bind=mock_engine)
        mock_logger.info.assert_any_call("Creating database and tables")
        mock_logger.info.assert_any_call("Database and tables created successfully")