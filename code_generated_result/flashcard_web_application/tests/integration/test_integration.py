import pytest
from fastapi.testclient import TestClient
from backend.main import app
import json
import uuid

client = TestClient(app)


def test_health_check_success():
    # source_info: backend.main.health_check
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_flashcard_success():
    # source_info: backend.routers.flashcards.create_flashcard
    payload = {
        "question": "What is FastAPI?",
        "answer": "A modern, fast (high-performance), web framework for building APIs with Python 3.7+ based on standard Python type hints."
    }
    response = client.post("/api/flashcards", json=payload)
    assert response.status_code == 200
    assert "id" in response.json()
    assert response.json()["question"] == payload["question"]
    assert response.json()["answer"] == payload["answer"]


def test_create_flashcard_invalid_input():
    # source_info: backend.routers.flashcards.create_flashcard
    payload = {
        "question": 123,
        "answer": 456
    }
    response = client.post("/api/flashcards", json=payload)
    assert response.status_code == 422


def test_read_flashcards_empty():
    # source_info: backend.routers.flashcards.read_flashcards
    response = client.get("/api/flashcards")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_read_flashcards_success():
    # source_info: backend.routers.flashcards.read_flashcards
    # First create a flashcard
    payload = {
        "question": "What is Python?",
        "answer": "A high-level, general-purpose programming language."
    }
    create_response = client.post("/api/flashcards", json=payload)
    assert create_response.status_code == 200
    flashcard_id = create_response.json()["id"]

    # Then read the flashcards
    response = client.get("/api/flashcards")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert any(flashcard["id"] == flashcard_id for flashcard in response.json())


def test_read_flashcard_success():
    # source_info: backend.routers.flashcards.read_flashcard
    # First create a flashcard
    payload = {
        "question": "What is JavaScript?",
        "answer": "A programming language that enables interactive web pages."
    }
    create_response = client.post("/api/flashcards", json=payload)
    assert create_response.status_code == 200
    flashcard_id = create_response.json()["id"]

    # Then read the flashcard
    response = client.get(f"/api/flashcards/{flashcard_id}")
    assert response.status_code == 200
    assert response.json()["id"] == flashcard_id
    assert response.json()["question"] == payload["question"]
    assert response.json()["answer"] == payload["answer"]


def test_read_flashcard_not_found():
    # source_info: backend.routers.flashcards.read_flashcard
    flashcard_id = str(uuid.uuid4())
    response = client.get(f"/api/flashcards/{flashcard_id}")
    assert response.status_code == 404


def test_create_review_success():
    # source_info: backend.routers.reviews.create_review
    payload = {
        "flashcard_id": str(uuid.uuid4()),  # Using a valid UUID format
        "rating": 5
    }
    response = client.post("/api/reviews", json=payload)
    assert response.status_code == 200
    assert "id" in response.json()
    assert response.json()["flashcard_id"] == payload["flashcard_id"]
    assert response.json()["rating"] == payload["rating"]

def test_create_review_invalid_rating():
    # source_info: backend.routers.reviews.create_review
    payload = {
        "flashcard_id": str(uuid.uuid4()),
        "rating": 6
    }
    response = client.post("/api/reviews", json=payload)
    assert response.status_code == 422

def test_create_review_invalid_flashcard_id():
    # source_info: backend.routers.reviews.create_review
    payload = {
        "flashcard_id": "invalid-uuid",
        "rating": 3
    }
    response = client.post("/api/reviews", json=payload)
    assert response.status_code == 422