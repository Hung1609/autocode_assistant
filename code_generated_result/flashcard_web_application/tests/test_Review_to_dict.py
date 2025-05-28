import pytest
from unittest.mock import patch
from backend.models import Review
from fastapi import Request, HTTPException, Depends

def test_Review_to_dict_success():
    # source_info: backend.models.Review.to_dict
    review = Review(id=1, flashcard_id=2, correct=True, review_timestamp="2023-10-26T10:00:00")
    expected_dict = {
        'id': 1,
        'flashcard_id': 2,
        'correct': True,
        'review_timestamp': "2023-10-26T10:00:00"
    }
    assert review.to_dict() == expected_dict

def test_Review_to_dict_different_values():
    # source_info: backend.models.Review.to_dict
    review = Review(id=100, flashcard_id=200, correct=False, review_timestamp="2024-01-01T00:00:00")
    expected_dict = {
        'id': 100,
        'flashcard_id': 200,
        'correct': False,
        'review_timestamp': "2024-01-01T00:00:00"
    }
    assert review.to_dict() == expected_dict

def test_Review_to_dict_none_values():
    # source_info: backend.models.Review.to_dict
    review = Review(id=None, flashcard_id=None, correct=None, review_timestamp=None)
    expected_dict = {
        'id': None,
        'flashcard_id': None,
        'correct': None,
        'review_timestamp': None
    }
    assert review.to_dict() == expected_dict