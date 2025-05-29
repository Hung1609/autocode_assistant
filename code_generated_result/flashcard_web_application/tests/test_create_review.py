import pytest
from unittest.mock import patch
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from backend.routers.reviews import create_review
import backend.schemas as schemas
import backend.models as models

def test_create_review_success(mocker):
    # source_info: backend.routers.reviews.create_review
    review_data = schemas.ReviewCreate(flashcard_id=1, rating=5, comment="Excellent!")
    mock_db = mocker.MagicMock(spec=Session)
    mock_db_review = models.Review(**review_data.model_dump())

    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None

    result = create_review(review_data, db=mock_db)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(mocker.ANY)  # Ensure refresh is called with some argument.
    assert result is not None
    assert result.flashcard_id == review_data.flashcard_id
    assert result.rating == review_data.rating
    assert result.comment == review_data.comment

def test_create_review_db_error(mocker):
    # source_info: backend.routers.reviews.create_review
    review_data = schemas.ReviewCreate(flashcard_id=1, rating=1, comment="Bad")
    mock_db = mocker.MagicMock(spec=Session)

    mock_db.add.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        create_review(review_data, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Database error" in str(exc_info.value.detail)
    mock_db.add.assert_called_once()
    mock_db.commit.assert_not_called()
    mock_db.refresh.assert_not_called()

def test_create_review_invalid_input(mocker):
    # source_info: backend.routers.reviews.create_review
    # Simulate an error during review creation because of invalid input
    review_data = schemas.ReviewCreate(flashcard_id=None, rating=5, comment="Excellent!")  # flashcard_id is None which is invalid

    mock_db = mocker.MagicMock(spec=Session)

    with pytest.raises(HTTPException) as exc_info:
        create_review(review_data, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Input should be" in str(exc_info.value.detail) # Checking if the validation error message is present.
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()
    mock_db.refresh.assert_not_called()