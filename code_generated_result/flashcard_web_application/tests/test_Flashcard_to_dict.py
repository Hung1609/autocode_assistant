import pytest
from unittest.mock import MagicMock

from backend.models import Flashcard
from fastapi import Request, HTTPException, Depends

def test_Flashcard_to_dict_success():
    # source_info: backend.models.Flashcard.to_dict
    flashcard = Flashcard(id=1, front_text="Front", back_text="Back")
    expected_dict = {'id': 1, 'front_text': 'Front', 'back_text': 'Back'}
    assert flashcard.to_dict() == expected_dict

def test_Flashcard_to_dict_empty_strings():
    # source_info: backend.models.Flashcard.to_dict
    flashcard = Flashcard(id=2, front_text="", back_text="")
    expected_dict = {'id': 2, 'front_text': '', 'back_text': ''}
    assert flashcard.to_dict() == expected_dict

def test_Flashcard_to_dict_none_values():
    # source_info: backend.models.Flashcard.to_dict
    flashcard = Flashcard(id=3, front_text=None, back_text=None)
    expected_dict = {'id': 3, 'front_text': None, 'back_text': None}
    assert flashcard.to_dict() == expected_dict

def test_Flashcard_to_dict_special_characters():
    # source_info: backend.models.Flashcard.to_dict
    flashcard = Flashcard(id=4, front_text="!@#$%^", back_text="&*()")
    expected_dict = {'id': 4, 'front_text': '!@#$%^', 'back_text': '&*()'}
    assert flashcard.to_dict() == expected_dict

def test_Flashcard_to_dict_long_text():
    # source_info: backend.models.Flashcard.to_dict
    long_text = "a" * 200
    flashcard = Flashcard(id=5, front_text=long_text, back_text=long_text)
    expected_dict = {'id': 5, 'front_text': long_text, 'back_text': long_text}
    assert flashcard.to_dict() == expected_dict