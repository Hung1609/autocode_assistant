import pytest
from fastapi.testclient import TestClient
from backend.main import app
import json
import os
import uuid

client = TestClient(app)


def test_create_flashcard_success():
    # source_info: backend.main.create_flashcard
    payload = {"front_text": "Front of card", "back_text": "Back of card"}
    response = client.post("/api/flashcards", json=payload)
    assert response.status_code == 201
    assert "id" in response.json()
    assert response.json()["front_text"] == "Front of card"
    assert response.json()["back_text"] == "Back of card"


def test_create_flashcard_missing_front_text():
    # source_info: backend.main.create_flashcard
    payload = {"back_text": "Back of card"}
    response = client.post("/api/flashcards", json=payload)
    assert response.status_code == 422


def test_create_flashcard_missing_back_text():
    # source_info: backend.main.create_flashcard
    payload = {"front_text": "Front of card"}
    response = client.post("/api/flashcards", json=payload)
    assert response.status_code == 422


def test_get_flashcards_empty():
    # source_info: backend.main.get_flashcards
    response = client.get("/api/flashcards")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_flashcards_with_data():
    # source_info: backend.main.get_flashcards
    # Create a flashcard first
    payload = {"front_text": "Test Front", "back_text": "Test Back"}
    create_response = client.post("/api/flashcards", json=payload)
    assert create_response.status_code == 201

    get_response = client.get("/api/flashcards")
    assert get_response.status_code == 200
    assert isinstance(get_response.json(), list)
    assert len(get_response.json()) >= 1


def test_get_flashcards_with_query():
    # source_info: backend.main.get_flashcards
    # Create a flashcard first
    payload = {"front_text": "Test Front", "back_text": "Test Back"}
    create_response = client.post("/api/flashcards", json=payload)
    assert create_response.status_code == 201

    get_response = client.get("/api/flashcards?query=Front")
    assert get_response.status_code == 200
    assert isinstance(get_response.json(), list)
    assert len(get_response.json()) >= 1


def test_get_flashcard_by_id_success():
    # source_info: backend.main.get_flashcard
    # Create a flashcard first
    payload = {"front_text": "Test Front", "back_text": "Test Back"}
    create_response = client.post("/api/flashcards", json=payload)
    assert create_response.status_code == 201
    flashcard_id = create_response.json()["id"]

    get_response = client.get(f"/api/flashcards/{flashcard_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == flashcard_id


def test_get_flashcard_by_id_not_found():
    # source_info: backend.main.get_flashcard
    flashcard_id = str(uuid.uuid4())
    response = client.get(f"/api/flashcards/{flashcard_id}")
    assert response.status_code == 404


def test_create_review_success():
    # source_info: backend.main.create_review
    # Create a flashcard first
    payload_flashcard = {"front_text": "Test Front", "back_text": "Test Back"}
    create_flashcard_response = client.post("/api/flashcards", json=payload_flashcard)
    assert create_flashcard_response.status_code == 201
    flashcard_id = create_flashcard_response.json()["id"]

    payload_review = {"flashcard_id": flashcard_id, "correct": True}
    review_response = client.post("/api/reviews", json=payload_review)
    assert review_response.status_code == 201
    assert "id" in review_response.json()
    assert review_response.json()["flashcard_id"] == flashcard_id
    assert review_response.json()["correct"] is True


def test_create_review_invalid_flashcard_id():
    # source_info: backend.main.create_review
    payload_review = {"flashcard_id": 9999, "correct": True}  # Assuming ID 9999 doesn't exist
    review_response = client.post("/api/reviews", json=payload_review)
    assert review_response.status_code == 400


def test_create_review_missing_flashcard_id():
    # source_info: backend.main.create_review
    payload_review = {"correct": True}
    review_response = client.post("/api/reviews", json=payload_review)
    assert review_response.status_code == 422


def test_create_review_missing_correct():
    # source_info: backend.main.create_review
    # Create a flashcard first
    payload_flashcard = {"front_text": "Test Front", "back_text": "Test Back"}
    create_flashcard_response = client.post("/api/flashcards", json=payload_flashcard)
    assert create_flashcard_response.status_code == 201
    flashcard_id = create_flashcard_response.json()["id"]
    payload_review = {"flashcard_id": flashcard_id}
    review_response = client.post("/api/reviews", json=payload_review)
    assert review_response.status_code == 422


def test_get_statistics_success():
    # source_info: backend.main.get_statistics
    response = client.get("/api/statistics")
    assert response.status_code == 200
    assert "total_reviewed" in response.json()
    assert "percentage_correct" in response.json()