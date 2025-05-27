import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from backend.database import create_db_and_tables


def test_create_db_and_tables_success():
    """Test successful creation of database and tables."""
    with patch("backend.database.Base.metadata.create_all") as mock_create_all, \
         patch("backend.database.engine"):
        create_db_and_tables()
        mock_create_all.assert_called_once()


def test_create_db_and_tables_exception():
    """Test handling of exception during database/table creation."""
    with patch("backend.database.Base.metadata.create_all") as mock_create_all, \
         patch("backend.database.engine"), \
         pytest.raises(Exception) as exc_info:
        mock_create_all.side_effect = Exception("Simulated database error")
        create_db_and_tables()
    assert str(exc_info.value) == "Simulated database error"


def test_create_db_and_tables_no_engine():
    """Test handling when the engine is not properly initialized."""
    with patch("backend.database.Base.metadata.create_all") as mock_create_all:
        with pytest.raises(Exception):
             create_db_and_tables()