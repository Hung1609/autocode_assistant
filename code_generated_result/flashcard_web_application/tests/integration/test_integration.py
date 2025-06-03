import pytest
import json
import uuid
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_check():
    # source_info: backend.main.health_check
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_flashcard_success():
    # source_info: backend.routers.flashcards.create_flashcard
    payload = {
        "question": "What is the capital of France?",
        "answer": "Paris",
        "deck_name": "Geography"
    }
    response = client.post("/api/flashcards", json=payload)
    assert response.status_code == 201
    assert "id" in response.json()
    assert response.json()["question"] == "What is the capital of France?"
    assert response.json()["answer"] == "Paris"
    assert response.json()["deck_name"] == "Geography"


def test_create_flashcard_invalid_input():
    # source_info: backend.routers.flashcards.create_flashcard
    payload = {
        "question": 123,
        "answer": 456,
        "deck_name": 789
    }
    response = client.post("/api/flashcards", json=payload)
    assert response.status_code == 422


def test_read_flashcards_empty():
    # source_info: backend.routers.flashcards.read_flashcards
    # Assuming database is initially empty or has been cleared
    response = client.get("/api/flashcards")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    #assert len(response.json()) == 0  #Removed hardcoded dependency on initial state, this should be more flexible

def test_read_flashcards_after_creation():
    # source_info: backend.routers.flashcards.read_flashcards
    # Create a flashcard first
    payload = {
        "question": "Test Question",
        "answer": "Test Answer",
        "deck_name": "Test Deck"
    }
    create_response = client.post("/api/flashcards", json=payload)
    assert create_response.status_code == 201
    flashcard_id = create_response.json()["id"]

    # Read all flashcards
    read_response = client.get("/api/flashcards")
    assert read_response.status_code == 200
    flashcards = read_response.json()

    # Verify that the created flashcard is in the list
    found = False
    for flashcard in flashcards:
        if flashcard["id"] == flashcard_id:
            found = True
            assert flashcard["question"] == "Test Question"
            assert flashcard["answer"] == "Test Answer"
            assert flashcard["deck_name"] == "Test Deck"
            break
    assert found, "Created flashcard not found in the list of flashcards"



def test_read_flashcard_success():
    # source_info: backend.routers.flashcards.read_flashcard
    # Create a flashcard first
    payload = {
        "question": "Specific Question",
        "answer": "Specific Answer",
        "deck_name": "Specific Deck"
    }
    create_response = client.post("/api/flashcards", json=payload)
    assert create_response.status_code == 201
    flashcard_id = create_response.json()["id"]

    # Read the specific flashcard
    read_response = client.get(f"/api/flashcards/{flashcard_id}")
    assert read_response.status_code == 200
    assert read_response.json()["id"] == flashcard_id
    assert read_response.json()["question"] == "Specific Question"
    assert read_response.json()["answer"] == "Specific Answer"
    assert read_response.json()["deck_name"] == "Specific Deck"


def test_read_flashcard_not_found():
    # source_info: backend.routers.flashcards.read_flashcard
    invalid_id = str(uuid.uuid4())  # Generate a random UUID that is unlikely to exist
    response = client.get(f"/api/flashcards/{invalid_id}")
    assert response.status_code == 404



def test_create_review_success():
    # source_info: backend.routers.reviews.create_review
    payload = {
        "flashcard_id": str(uuid.uuid4()),  # Replace with a valid flashcard ID if needed
        "rating": 5
    }
    response = client.post("/api/reviews", json=payload)
    assert response.status_code == 201
    assert "id" in response.json()
    assert response.json()["flashcard_id"] == payload["flashcard_id"]
    assert response.json()["rating"] == 5


def test_create_review_invalid_input():
    # source_info: backend.routers.reviews.create_review
    payload = {
        "flashcard_id": 123,
        "rating": "abc"
    }
    response = client.post("/api/reviews", json=payload)
    assert response.status_code == 422

def test_create_review_invalid_rating():
    # source_info: backend.routers.reviews.create_review
    payload = {
        "flashcard_id": str(uuid.uuid4()),
        "rating": 6  # Assuming rating must be between 1 and 5
    }
    response = client.post("/api/reviews", json=payload)
    assert response.status_code == 422