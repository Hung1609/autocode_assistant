import pytest
from fastapi.testclient import TestClient
from backend.main import app
import json

client = TestClient(app)


def test_create_flashcard_success():
    # source_info: backend.main.create_flashcard
    response = client.post(
        "/api/flashcards",
        json={"front_text": "Front Text", "back_text": "Back Text"},
    )
    assert response.status_code == 201
    assert "id" in response.json()
    assert response.json()["front_text"] == "Front Text"
    assert response.json()["back_text"] == "Back Text"


def test_create_flashcard_missing_front_text():
    # source_info: backend.main.create_flashcard
    response = client.post(
        "/api/flashcards",
        json={"back_text": "Back Text"},
    )
    assert response.status_code == 422


def test_create_flashcard_missing_back_text():
    # source_info: backend.main.create_flashcard
    response = client.post(
        "/api/flashcards",
        json={"front_text": "Front Text"},
    )
    assert response.status_code == 422


def test_get_flashcards_empty():
    # source_info: backend.main.get_flashcards
    response = client.get("/api/flashcards")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_flashcards_with_data():
    # source_info: backend.main.get_flashcards
    # Create a flashcard first
    create_response = client.post(
        "/api/flashcards",
        json={"front_text": "Test Front", "back_text": "Test Back"},
    )
    assert create_response.status_code == 201
    flashcard_id = create_response.json()["id"]

    # Get all flashcards
    get_response = client.get("/api/flashcards")
    assert get_response.status_code == 200
    assert isinstance(get_response.json(), list)
    assert len(get_response.json()) > 0

    # Clean up: Delete the created flashcard (if delete endpoint existed).  In this example it doesnt exist.


def test_get_flashcards_with_query():
    # source_info: backend.main.get_flashcards
    create_response = client.post(
        "/api/flashcards",
        json={"front_text": "Searchable Front", "back_text": "Irrelevant Back"},
    )
    assert create_response.status_code == 201
    get_response = client.get("/api/flashcards?query=Searchable")
    assert response.status_code == 200 #changed get_response to response
    assert len(get_response.json()) > 0


def test_get_flashcards_with_query_no_match():
    # source_info: backend.main.get_flashcards
    get_response = client.get("/api/flashcards?query=NonExistent")
    assert get_response.status_code == 200
    assert len(get_response.json()) == 0


def test_get_flashcard_by_id_success():
    # source_info: backend.main.get_flashcard
    # Create a flashcard first
    create_response = client.post(
        "/api/flashcards",
        json={"front_text": "Specific Front", "back_text": "Specific Back"},
    )
    assert create_response.status_code == 201
    flashcard_id = create_response.json()["id"]

    # Get the flashcard by ID
    get_response = client.get(f"/api/flashcards/{flashcard_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == flashcard_id
    assert get_response.json()["front_text"] == "Specific Front"
    assert get_response.json()["back_text"] == "Specific Back"

    # Clean up: Delete the created flashcard (if delete endpoint existed). In this example it doesnt exist


def test_get_flashcard_by_id_not_found():
    # source_info: backend.main.get_flashcard
    response = client.get("/api/flashcards/999")  # Non-existent ID
    assert response.status_code == 404
    assert "error" in response.json()


def test_create_review_success():
    # source_info: backend.main.create_review

    # First create a flashcard
    create_flashcard_response = client.post(
        "/api/flashcards",
        json={"front_text": "Review Front", "back_text": "Review Back"},
    )
    assert create_flashcard_response.status_code == 201
    flashcard_id = create_flashcard_response.json()["id"]

    # Create a review for the flashcard
    review_response = client.post(
        "/api/reviews", json={"flashcard_id": flashcard_id, "correct": True}
    )
    assert review_response.status_code == 201
    assert "id" in review_response.json()
    assert review_response.json()["flashcard_id"] == flashcard_id
    assert review_response.json()["correct"] is True


def test_create_review_invalid_flashcard_id():
    # source_info: backend.main.create_review
    response = client.post(
        "/api/reviews", json={"flashcard_id": 999, "correct": True}
    )  # Non-existent flashcard_id

    #Assuming the backend validates the flashcard ID's existence before creating review. otherwise remove this test.

    assert response.status_code == 400 # or 404, depending on implementation. changed from 201
    assert "error" in response.json()


def test_create_review_missing_flashcard_id():
    # source_info: backend.main.create_review
    response = client.post("/api/reviews", json={"correct": True})
    assert response.status_code == 422


def test_create_review_missing_correct():
    # source_info: backend.main.create_review
    # First create a flashcard
    create_flashcard_response = client.post(
        "/api/flashcards",
        json={"front_text": "Review Front", "back_text": "Review Back"},
    )
    assert create_flashcard_response.status_code == 201
    flashcard_id = create_flashcard_response.json()["id"]
    response = client.post("/api/reviews", json={"flashcard_id": flashcard_id})
    assert response.status_code == 422


def test_get_statistics_success():
    # source_info: backend.main.get_statistics
    response = client.get("/api/statistics")
    assert response.status_code == 200
    assert "total_cards_reviewed" in response.json()
    assert "percentage_correct" in response.json()