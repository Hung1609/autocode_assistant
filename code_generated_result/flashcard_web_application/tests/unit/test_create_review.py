import pytest
from unittest.mock import patch
from fastapi import Request, HTTPException, Depends
from backend.routers.reviews import create_review
from sqlalchemy.orm import Session
import backend.models as models
import backend.schemas as schemas

def test_create_review_success(mocker):
    # source_info: backend.routers.reviews.create_review
    review_data = schemas.ReviewCreate(flashcard_id=1, rating=5, comment="Great flashcard!")
    db_mock = mocker.MagicMock(spec=Session)
    db_review_mock = mocker.MagicMock(spec=models.Review)
    
    mocker.patch("backend.routers.reviews.models.Review", return_value=db_review_mock)
    
    result = create_review(review_data, db=db_mock)

    models.Review.assert_called_once_with(**review_data.dict())
    db_mock.add.assert_called_once_with(db_review_mock)
    db_mock.commit.assert_called_once()
    db_mock.refresh.assert_called_once_with(db_review_mock)
    assert result == db_review_mock

def test_create_review_db_error(mocker):
    # source_info: backend.routers.reviews.create_review
    review_data = schemas.ReviewCreate(flashcard_id=1, rating=5, comment="Great flashcard!")
    db_mock = mocker.MagicMock(spec=Session)
    db_mock.add.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        create_review(review_data, db=db_mock)

    assert exc_info.value.status_code == 500
    assert "Database error" in str(exc_info.value.detail)

def test_create_review_invalid_input(mocker):
    # source_info: backend.routers.reviews.create_review
    review_data = schemas.ReviewCreate(flashcard_id=1, rating=5, comment="Great flashcard!")
    db_mock = mocker.MagicMock(spec=Session)
    db_review_mock = mocker.MagicMock(spec=models.Review)
    mocker.patch("backend.routers.reviews.models.Review", return_value=db_review_mock)
    db_mock.commit.side_effect = Exception("Commit Error")
    with pytest.raises(HTTPException) as exc_info:
        create_review(review_data, db=db_mock)

    assert exc_info.value.status_code == 500
    assert "Commit Error" in str(exc_info.value.detail)