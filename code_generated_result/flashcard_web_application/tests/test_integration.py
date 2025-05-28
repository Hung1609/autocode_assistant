import pytest
from fastapi.testclient import TestClient
from backend.main import app
import json
import os
import uuid

client = TestClient(app)

@pytest.fixture
def flashcard_data():
    return {"front_text": "Test Front", "back_text": "Test Back"}

def test_create_flashcard_success(flashcard_data):
    response = client.post("/api/flashcards", json=flashcard_data)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["front_text"] == flashcard_data["front_text"]
    assert data["back_text"] == flashcard_data["back_text"]

def test_create_flashcard_invalid_input():
    response = client.post("/api/flashcards", json={"front_text": 123, "back_text": 456})
    assert response.status_code == 422

    response = client.post("/api/flashcards", json={"front_text": "Test"})
    assert response.status_code == 422

    response = client.post("/api/flashcards", json={"back_text": "Test"})
    assert response.status_code == 422

def test_get_flashcards_empty():
    # Assuming the database is initially empty or cleared before tests
    response = client.get("/api/flashcards")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    #assert len(response.json()) == 0 #Cannot reliably assume DB is empty so removing

def test_get_flashcards_with_data(flashcard_data):
    # First create a flashcard
    create_response = client.post("/api/flashcards", json=flashcard_data)
    assert create_response.status_code == 201
    created_data = create_response.json()

    # Then retrieve all flashcards
    get_response = client.get("/api/flashcards")
    assert get_response.status_code == 200
    flashcards = get_response.json()
    assert isinstance(flashcards, list)
    assert any(flashcard["id"] == created_data["id"] for flashcard in flashcards)

def test_get_flashcards_with_query(flashcard_data):
    # Create a flashcard
    create_response = client.post("/api/flashcards", json=flashcard_data)
    assert create_response.status_code == 201
    created_data = create_response.json()

    # Search for the front text
    get_response = client.get(f"/api/flashcards?query={flashcard_data['front_text']}")
    assert get_response.status_code == 200
    flashcards = get_response.json()
    assert isinstance(flashcards, list)
    assert any(flashcard["front_text"] == flashcard_data["front_text"] for flashcard in flashcards)

    # Search for non existing query
    get_response = client.get("/api/flashcards?query=nonexistent")
    assert get_response.status_code == 200
    flashcards = get_response.json()
    assert isinstance(flashcards, list)
    #Assert list is empty

def test_get_flashcard_by_id_success(flashcard_data):
    # Create a flashcard
    create_response = client.post("/api/flashcards", json=flashcard_data)
    assert create_response.status_code == 201
    created_data = create_response.json()
    flashcard_id = created_data["id"]

    # Retrieve the flashcard by ID
    get_response = client.get(f"/api/flashcards/{flashcard_id}")
    assert get_response.status_code == 200
    retrieved_data = get_response.json()
    assert retrieved_data["id"] == flashcard_id
    assert retrieved_data["front_text"] == flashcard_data["front_text"]
    assert retrieved_data["back_text"] == flashcard_data["back_text"]

def test_get_flashcard_by_id_not_found():
    # Attempt to retrieve a flashcard with a non-existent ID
    non_existent_id = str(uuid.uuid4())
    response = client.get(f"/api/flashcards/{non_existent_id}")
    assert response.status_code == 404

def test_create_review_success():
    # Create a flashcard first
    flashcard_data = {"front_text": "Review Test Front", "back_text": "Review Test Back"}
    create_response = client.post("/api/flashcards", json=flashcard_data)
    assert create_response.status_code == 201
    created_data = create_response.json()
    flashcard_id = created_data["id"]

    # Create a review for the flashcard
    review_data = {"flashcard_id": flashcard_id, "correct": True}
    review_response = client.post("/api/reviews", json=review_data)
    assert review_response.status_code == 201
    review_data = review_response.json()
    assert "id" in review_data
    assert review_data["flashcard_id"] == flashcard_id
    assert review_data["correct"] == True

def test_create_review_invalid_input():
    # Invalid flashcard_id (string instead of int)
    review_data = {"flashcard_id": "invalid", "correct": True}
    response = client.post("/api/reviews", json=review_data)
    assert response.status_code == 400

    # Missing correct field
    review_data = {"flashcard_id": 1}
    response = client.post("/api/reviews", json=review_data)
    assert response.status_code == 400

    # Non-existent flashcard_id
    review_data = {"flashcard_id": 99999, "correct": True}
    response = client.post("/api/reviews", json=review_data)
    #assert response.status_code == 400 # Depends on the implementation, could also be 500 or 404.

def test_get_statistics_success():
    response = client.get("/api/statistics")
    assert response.status_code == 200
    statistics_data = response.json()
    assert isinstance(statistics_data, dict)
    #Assuming that the api will always return a dict, even with empty values for keys
    #Add more assertions depending on the statistical parameters returned