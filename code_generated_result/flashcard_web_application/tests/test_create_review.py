import pytest
from unittest.mock import patch
from fastapi import Request, HTTPException, Depends
from backend.routers.reviews import create_review
import backend.schemas as schemas
import backend.models as models
from sqlalchemy.orm import Session
import logging

def test_create_review_success(mocker):
    # source_info: backend.routers.reviews.create_review
    mock_db = mocker.MagicMock(spec=Session)
    review_create = schemas.ReviewCreate(flashcard_id=1, rating=5, comment="Great flashcard!")
    expected_review = models.Review(flashcard_id=1, rating=5, comment="Great flashcard!")
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None

    result = create_review(review_create, db=mock_db)

    mock_db.add.assert_called()
    mock_db.commit.assert_called()
    mock_db.refresh.assert_called()
    assert result.flashcard_id == expected_review.flashcard_id
    assert result.rating == expected_review.rating
    assert result.comment == expected_review.comment

def test_create_review_db_error(mocker):
    # source_info: backend.routers.reviews.create_review
    mock_db = mocker.MagicMock(spec=Session)
    review_create = schemas.ReviewCreate(flashcard_id=1, rating=5, comment="Great flashcard!")
    mock_db.add.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        create_review(review_create, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Database error" in str(exc_info.value.detail)

def test_create_review_invalid_input(mocker):
    # source_info: backend.routers.reviews.create_review
    mock_db = mocker.MagicMock(spec=Session)
    review_create = schemas.ReviewCreate(flashcard_id=1, rating=6, comment="Great flashcard!")

    with pytest.raises(HTTPException) as exc_info:
        create_review(review_create, db=mock_db)

    assert exc_info.value.status_code == 500

def test_create_review_empty_comment(mocker):
    # source_info: backend.routers.reviews.create_review
    mock_db = mocker.MagicMock(spec=Session)
    review_create = schemas.ReviewCreate(flashcard_id=1, rating=5, comment="")
    expected_review = models.Review(flashcard_id=1, rating=5, comment="")
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None

    result = create_review(review_create, db=mock_db)

    mock_db.add.assert_called()
    mock_db.commit.assert_called()
    mock_db.refresh.assert_called()
    assert result.flashcard_id == expected_review.flashcard_id
    assert result.rating == expected_review.rating
    assert result.comment == expected_review.comment

def test_create_review_no_comment(mocker):
    # source_info: backend.routers.reviews.create_review
    mock_db = mocker.MagicMock(spec=Session)
    review_create = schemas.ReviewCreate(flashcard_id=1, rating=5, comment=None)
    expected_review = models.Review(flashcard_id=1, rating=5, comment=None)
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None

    result = create_review(review_create, db=mock_db)

    mock_db.add.assert_called()
    mock_db.commit.assert_called()
    mock_db.refresh.assert_called()
    assert result.flashcard_id == expected_review.flashcard_id
    assert result.rating == expected_review.rating
    assert result.comment == expected_review.comment

def test_create_review_zero_rating(mocker):
    # source_info: backend.routers.reviews.create_review
    mock_db = mocker.MagicMock(spec=Session)
    review_create = schemas.ReviewCreate(flashcard_id=1, rating=0, comment="Zero rating")
    expected_review = models.Review(flashcard_id=1, rating=0, comment="Zero rating")
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None

    result = create_review(review_create, db=mock_db)

    mock_db.add.assert_called()
    mock_db.commit.assert_called()
    mock_db.refresh.assert_called()
    assert result.flashcard_id == expected_review.flashcard_id
    assert result.rating == expected_review.rating
    assert result.comment == expected_review.comment