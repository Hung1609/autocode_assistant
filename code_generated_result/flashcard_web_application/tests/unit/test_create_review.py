import pytest
from unittest.mock import patch
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from backend.routers.reviews import create_review
import backend.schemas as schemas
import backend.models as models
from pytest_mock import MockerFixture
import logging

def test_create_review_success(mocker: MockerFixture):
    # source_info: backend.routers.reviews.create_review
    review_data = schemas.ReviewCreate(flashcard_id=1, user_id=1, rating=5, comment="Great flashcard!")
    mock_db = mocker.MagicMock(spec=Session)
    mock_db_review = models.Review(**review_data.model_dump())
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None

    mocker.patch('backend.routers.reviews.models.Review', return_value=mock_db_review)

    result = create_review(review_data, db=mock_db)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(mock_db_review)
    assert result == mock_db_review

def test_create_review_db_error(mocker: MockerFixture):
    # source_info: backend.routers.reviews.create_review
    review_data = schemas.ReviewCreate(flashcard_id=1, user_id=1, rating=5, comment="Great flashcard!")
    mock_db = mocker.MagicMock(spec=Session)
    mock_db.add.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        create_review(review_data, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Database error" in str(exc_info.value.detail)

def test_create_review_invalid_review_data(mocker: MockerFixture):
    # source_info: backend.routers.reviews.create_review
    with pytest.raises(TypeError):
        create_review(review="invalid", db=mocker.MagicMock())

def test_create_review_exception_handling(mocker: MockerFixture):
    # source_info: backend.routers.reviews.create_review
    review = schemas.ReviewCreate(flashcard_id=1, user_id=1, rating=5, comment="Test review")
    mock_db = mocker.MagicMock()
    mock_db.add.side_effect = Exception("Simulated database error")

    with pytest.raises(HTTPException) as exc_info:
        create_review(review, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Simulated database error" in str(exc_info.value.detail)

def test_create_review_empty_comment(mocker: MockerFixture):
    # source_info: backend.routers.reviews.create_review
    review_data = schemas.ReviewCreate(flashcard_id=1, user_id=1, rating=5, comment="")
    mock_db = mocker.MagicMock(spec=Session)
    mock_db_review = models.Review(**review_data.model_dump())
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None

    mocker.patch('backend.routers.reviews.models.Review', return_value=mock_db_review)

    result = create_review(review_data, db=mock_db)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(mock_db_review)
    assert result == mock_db_review

def test_create_review_zero_rating(mocker: MockerFixture):
    # source_info: backend.routers.reviews.create_review
    review_data = schemas.ReviewCreate(flashcard_id=1, user_id=1, rating=0, comment="Zero rating")
    mock_db = mocker.MagicMock(spec=Session)
    mock_db_review = models.Review(**review_data.model_dump())
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None

    mocker.patch('backend.routers.reviews.models.Review', return_value=mock_db_review)

    result = create_review(review_data, db=mock_db)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(mock_db_review)
    assert result == mock_db_review