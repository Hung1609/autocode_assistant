import pytest
from unittest.mock import patch, MagicMock

from fastapi import Request, HTTPException, Depends
from backend.routers.reviews import create_review
from sqlalchemy.orm import Session
from backend import schemas, models

def test_create_review_success(mocker):
    # source_info: backend.routers.reviews.create_review
    review_data = schemas.ReviewCreate(flashcard_id=1, rating=5, comment="Great flashcard!")
    mock_db = MagicMock(spec=Session)
    mock_db_review = models.Review(**review_data.dict())
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None

    mocker.patch("backend.routers.reviews.models.Review", return_value=mock_db_review)

    result = create_review(review_data, db=mock_db)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(mock_db_review)
    assert result == mock_db_review

def test_create_review_db_error(mocker):
    # source_info: backend.routers.reviews.create_review
    review_data = schemas.ReviewCreate(flashcard_id=1, rating=5, comment="Great flashcard!")
    mock_db = MagicMock(spec=Session)
    mock_db.add.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        create_review(review_data, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Database error" in str(exc_info.value.detail)

def test_create_review_invalid_input(mocker):
    # source_info: backend.routers.reviews.create_review
    review_data = schemas.ReviewCreate(flashcard_id=1, rating=5, comment="Great flashcard!")
    mock_db = MagicMock(spec=Session)

    mocker.patch("backend.routers.reviews.models.Review", side_effect=ValueError("Invalid data"))

    with pytest.raises(HTTPException) as exc_info:
        create_review(review_data, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Invalid data" in str(exc_info.value.detail)

def test_create_review_commit_error(mocker):
    # source_info: backend.routers.reviews.create_review
    review_data = schemas.ReviewCreate(flashcard_id=1, rating=5, comment="Great flashcard!")
    mock_db = MagicMock(spec=Session)
    mock_db.commit.side_effect = Exception("Commit error")
    mock_db_review = models.Review(**review_data.dict())
    mocker.patch("backend.routers.reviews.models.Review", return_value=mock_db_review)

    with pytest.raises(HTTPException) as exc_info:
        create_review(review_data, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Commit error" in str(exc_info.value.detail)

def test_create_review_refresh_error(mocker):
    # source_info: backend.routers.reviews.create_review
    review_data = schemas.ReviewCreate(flashcard_id=1, rating=5, comment="Great flashcard!")
    mock_db = MagicMock(spec=Session)
    mock_db.refresh.side_effect = Exception("Refresh error")
    mock_db_review = models.Review(**review_data.dict())
    mocker.patch("backend.routers.reviews.models.Review", return_value=mock_db_review)

    with pytest.raises(HTTPException) as exc_info:
        create_review(review_data, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Refresh error" in str(exc_info.value.detail)