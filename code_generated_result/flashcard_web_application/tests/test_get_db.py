import pytest
from unittest.mock import patch
from fastapi import Request, HTTPException, Depends
from backend.database import get_db
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def mock_db_session():
    """
    Mocks the database session for testing.
    """
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()

def test_get_db_success(mocker, mock_db_session):
    # source_info: backend.database.get_db
    logger_mock = mocker.patch("backend.database.logger")
    db_mock = mock_db_session
    generator = get_db()
    db = next(generator)

    assert db is not None
    assert db == db_mock

    try:
        next(generator)  # Exhaust the generator
    except StopIteration:
        pass

    logger_mock.info.assert_called_with("Exiting get_db")

def test_get_db_exception(mocker, mock_db_session):
    # source_info: backend.database.get_db
    logger_mock = mocker.patch("backend.database.logger")

    db_mock = mock_db_session
    generator = get_db()
    db = next(generator)

    assert db is not None
    assert db == db_mock

    try:
        generator.close()
    except Exception as e:
        assert False, f"Unexpected exception: {e}"

    logger_mock.info.assert_called_with("Exiting get_db")