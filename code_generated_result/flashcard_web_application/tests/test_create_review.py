import pytest
from unittest.mock import patch
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from backend.routers.reviews import create_review
import backend.schemas as schemas
import backend.models as models
from pytest_mock import MockerFixture


def test_create_review_success(mocker: MockerFixture):
    # source_info: backend.routers.reviews.create_review
    mock_db = mocker.MagicMock(spec=Session)
    review_data = schemas.ReviewCreate(flashcard_id=1, rating=5, comment="Great flashcard!")

    result = create_review(review=review_data, db=mock_db)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()
    assert result is not None
    assert isinstance(result, models.Review)


def test_create_review_database_error(mocker: MockerFixture):
    # source_info: backend.routers.reviews.create_review
    mock_db = mocker.MagicMock(spec=Session)
    mock_db.add.side_effect = Exception("Database error")
    review_data = schemas.ReviewCreate(flashcard_id=1, rating=5, comment="Great flashcard!")

    with pytest.raises(HTTPException) as exc_info:
        create_review(review=review_data, db=mock_db)

    assert exc_info.value.status_code == 500
    assert "Database error" in str(exc_info.value.detail)


def test_create_review_invalid_rating(mocker: MockerFixture):
    # source_info: backend.routers.reviews.create_review
    mock_db = mocker.MagicMock(spec=Session)
    review_data = schemas.ReviewCreate(flashcard_id=1, rating=6, comment="Invalid rating")

    with pytest.raises(Exception) as exc_info:
        create_review(review=review_data, db=mock_db)


def test_create_review_empty_comment(mocker: MockerFixture):
    # source_info: backend.routers.reviews.create_review
    mock_db = mocker.MagicMock(spec=Session)
    review_data = schemas.ReviewCreate(flashcard_id=1, rating=5, comment="")

    result = create_review(review=review_data, db=mock_db)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()
    assert result is not None
    assert isinstance(result, models.Review)