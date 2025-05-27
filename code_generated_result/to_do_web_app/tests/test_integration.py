import pytest
from fastapi.testclient import TestClient
from main import app
from typing import Dict, Any

client = TestClient(app)

@pytest.fixture
def valid_flashcard_payload() -> Dict[str, Any]:
    return {
        "question": "What is the capital of France?",
        "answer": "Paris"
    }

@pytest.fixture
def invalid_flashcard_payload() -> Dict[str, Any]:
    return {
        "question": "",
        "answer": ""
    }

def test_create_flashcard_valid(valid_flashcard_payload: Dict[str, Any]) -> None:
    response = client.post("/flashcards", json=valid_flashcard_payload)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["question"] == valid_flashcard_payload["question"]
    assert data["answer"] == valid_flashcard_payload["answer"]


def test_create_flashcard_invalid(invalid_flashcard_payload: Dict[str, Any]) -> None:
    response = client.post("/flashcards", json=invalid_flashcard_payload)
    assert response.status_code == 422


def test_list_flashcards_empty() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_flashcards_populated(valid_flashcard_payload: Dict[str, Any]) -> None:
    # Create a flashcard first
    create_response = client.post("/flashcards", json=valid_flashcard_payload)
    assert create_response.status_code == 200

    # Now list the flashcards
    list_response = client.get("/")
    assert list_response.status_code == 200
    data = list_response.json()
    assert len(data) == 1
    assert "id" in data[0]
    assert data[0]["question"] == valid_flashcard_payload["question"]
    assert data[0]["answer"] == valid_flashcard_payload["answer"]