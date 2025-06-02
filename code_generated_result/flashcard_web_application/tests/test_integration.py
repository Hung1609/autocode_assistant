import pytest
from fastapi.testclient import TestClient
from backend.main import app
import json
import os
import uuid

client = TestClient(app)


def test_create_flashcard_success():
    # source_info: backend.main.create_flashcard
    payload = {"front_text": "Front Text", "back_text": "Back Text"}
    response = client.post("/api/flashcards", json=payload)
    assert response.status_code == 201
    assert "id" in response.json()
    assert response.json()["front_text"] == "Front Text"
    assert response.json()["back_text"] == "Back Text"


def test_create_flashcard_invalid_input():
    # source_info: backend.main.create_flashcard
    payload = {"front_text": 123, "back_text": 456}
    response = client.post("/api/flashcards", json=payload)
    assert response.status_code == 422


def test_create_flashcard_missing_field():
    # source_info: backend.main.create_flashcard
    payload = {"front_text": "Front Text"}
    response = client.post("/api/flashcards", json=payload)
    assert response.status_code == 422


def test_get_flashcards_empty():
    # source_info: backend.main.get_flashcards
    response = client.get("/api/flashcards")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    # Clear flashcards to ensure the list is truly empty
    flashcards = client.get("/api/flashcards").json()
    for card in flashcards:
        client.delete(f"/api/flashcards/{card['id']}") # Assuming you have a DELETE endpoint
    response = client.get("/api/flashcards")
    assert response.status_code == 200
    assert response.json() == []


def test_get_flashcards_with_data():
    # source_info: backend.main.get_flashcards
    # First, create a flashcard
    payload = {"front_text": "Test Front", "back_text": "Test Back"}
    create_response = client.post("/api/flashcards", json=payload)
    assert create_response.status_code == 201
    flashcard_id = create_response.json()["id"]

    # Then, retrieve the flashcards
    response = client.get("/api/flashcards")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0
    found = False
    for card in response.json():
        if card["id"] == flashcard_id:
            found = True
            break
    assert found

    #Clean up - delete created flashcard. Assuming there is a delete endpoint
    client.delete(f"/api/flashcards/{flashcard_id}")


def test_get_flashcards_with_query():
    # source_info: backend.main.get_flashcards
    # Create two flashcards for testing
    payload1 = {"front_text": "Apple", "back_text": "Fruit"}
    create_response1 = client.post("/api/flashcards", json=payload1)
    assert create_response1.status_code == 201
    flashcard_id1 = create_response1.json()["id"]
    
    payload2 = {"front_text": "Banana", "back_text": "Yellow Fruit"}
    create_response2 = client.post("/api/flashcards", json=payload2)
    assert create_response2.status_code == 201
    flashcard_id2 = create_response2.json()["id"]


    # Search for "Apple"
    response = client.get("/api/flashcards?query=Apple")
    assert response.status_code == 200
    flashcards = response.json()
    assert len(flashcards) > 0
    found_apple = any(card["id"] == flashcard_id1 for card in flashcards)
    assert found_apple

    # Search for "Yellow"
    response = client.get("/api/flashcards?query=Yellow")
    assert response.status_code == 200
    flashcards = response.json()
    assert len(flashcards) > 0
    found_yellow = any(card["id"] == flashcard_id2 for card in flashcards)
    assert found_yellow

    #Clean up created flashcards
    client.delete(f"/api/flashcards/{flashcard_id1}")
    client.delete(f"/api/flashcards/{flashcard_id2}")


def test_get_flashcard_by_id_success():
    # source_info: backend.main.get_flashcard
    # First create a flashcard
    payload = {"front_text": "Specific Front", "back_text": "Specific Back"}
    create_response = client.post("/api/flashcards", json=payload)
    assert create_response.status_code == 201
    flashcard_id = create_response.json()["id"]

    # Then retrieve the specific flashcard by ID
    response = client.get(f"/api/flashcards/{flashcard_id}")
    assert response.status_code == 200
    assert response.json()["id"] == flashcard_id
    assert response.json()["front_text"] == "Specific Front"
    assert response.json()["back_text"] == "Specific Back"

    #Clean up created flashcard
    client.delete(f"/api/flashcards/{flashcard_id}")


def test_get_flashcard_by_id_not_found():
    # source_info: backend.main.get_flashcard
    response = client.get("/api/flashcards/nonexistent_id")
    assert response.status_code == 404


def test_create_review_success():
    # source_info: backend.main.create_review
    # First create a flashcard
    payload_flashcard = {"front_text": "Review Front", "back_text": "Review Back"}
    create_flashcard_response = client.post("/api/flashcards", json=payload_flashcard)
    assert create_flashcard_response.status_code == 201
    flashcard_id = create_flashcard_response.json()["id"]

    # Then create a review for the flashcard
    payload_review = {"flashcard_id": flashcard_id, "correct": True}
    response = client.post("/api/reviews", json=payload_review)
    assert response.status_code == 201
    assert "id" in response.json()
    assert response.json()["flashcard_id"] == flashcard_id
    assert response.json()["correct"] == True

    #Clean up created flashcard
    client.delete(f"/api/flashcards/{flashcard_id}")


def test_create_review_invalid_input():
    # source_info: backend.main.create_review
    payload = {"flashcard_id": "invalid", "correct": "invalid"}
    response = client.post("/api/reviews", json=payload)
    assert response.status_code == 422


def test_create_review_missing_field():
    # source_info: backend.main.create_review
    # First create a flashcard
    payload_flashcard = {"front_text": "Review Front", "back_text": "Review Back"}
    create_flashcard_response = client.post("/api/flashcards", json=payload_flashcard)
    assert create_flashcard_response.status_code == 201
    flashcard_id = create_flashcard_response.json()["id"]

    payload = {"flashcard_id": flashcard_id}
    response = client.post("/api/reviews", json=payload)
    assert response.status_code == 422

    #Clean up created flashcard
    client.delete(f"/api/flashcards/{flashcard_id}")


def test_get_statistics_success():
    # source_info: backend.main.get_statistics
    response = client.get("/api/statistics")
    assert response.status_code == 200
    assert "total_cards_reviewed" in response.json()
    assert "percentage_correct" in response.json()