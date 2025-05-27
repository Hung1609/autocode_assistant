import pytest
from unittest.mock import patch
from fastapi import Request, HTTPException
from backend.database import get_db

@pytest.fixture
def mock_session():
    """Mocks a database session."""
    class MockSession:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    return MockSession()


def test_get_db_success(mock_session, caplog):
    """Tests the successful execution of get_db."""
    with patch("backend.database.SessionLocal", return_value=mock_session):
        db_generator = get_db()
        db = next(db_generator)

        assert not db.closed
        next(db_generator, None)
        assert db.closed
        assert "Entering get_db" in caplog.text
        assert "Database session closed." in caplog.text
        assert "Exiting get_db" in caplog.text


def test_get_db_exception(mock_session, caplog):
    """Tests if the database session closes even if an exception occurs."""
    class MockSessionException(mock_session):
        def __init__(self):
            super().__init__()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.close()

    with patch("backend.database.SessionLocal", side_effect=Exception("Simulated exception")):
        db_generator = get_db()

        with pytest.raises(Exception, match="Simulated exception"):
            next(db_generator)

        assert "Entering get_db" in caplog.text
        assert "Database session closed." in caplog.text
        assert "Exiting get_db" not in caplog.text