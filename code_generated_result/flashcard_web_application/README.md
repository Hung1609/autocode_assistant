# Flashcard Web Application

## Overview

This is a web application for creating, reviewing, and searching flashcards. It is built with a Python FastAPI backend and a Vanilla JavaScript frontend, using an SQLite database for storage.

## Features

*   **Create Flashcards:** Create new flashcards with a front and back side.
*   **Search Flashcards:** Search through existing flashcards using a search query.
*   **Review Flashcards:** Review flashcards, flipping them to reveal the answer.
*   **View Review Statistics:** View statistics on flashcard reviews (number of cards reviewed, percentage correct).
*   **Preloaded Flashcards:** The application is preloaded with ten flashcards containing Hindi words or phrases and their English translations.

## Technologies

*   **Backend:**
    *   Python
    *   FastAPI
    *   SQLAlchemy
    *   SQLite
*   **Frontend:**
    *   HTML
    *   CSS
    *   JavaScript

## Project Structure

```
flashcard_web_application/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── .gitignore                # Git ignore file
├── backend/                  # Backend application
│   ├── main.py               # Main FastAPI application
│   ├── database.py           # Database connection setup
│   ├── models.py             # SQLAlchemy ORM models
│   ├── routers/              # API route definitions
│   │   ├── flashcards.py     # Flashcard API endpoints
│   │   └── reviews.py        # Review API endpoints
│   └── schemas.py            # Pydantic schemas
├── frontend/                 # Frontend application
│   ├── index.html            # Main HTML file
│   ├── style.css             # Main CSS stylesheet
│   ├── script.js             # Main JavaScript file
│   ├── utils.js              # JavaScript utility functions
│   └── assets/               # Static assets (images, fonts)
└── logs/                     # Log files directory
```

## Setup Instructions

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd flashcard_web_application
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Linux/macOS
    venv\Scripts\activate  # On Windows
    ```

3.  **Install backend dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the backend:**

    ```bash
    uvicorn backend.main:app --reload --port 8001
    ```

5.  **Open the frontend in your browser:**

    Navigate to `http://localhost:8001` in your web browser.

## API Endpoints

*   `POST /api/flashcards`: Create a new flashcard.
*   `GET /api/flashcards`: Retrieve all flashcards (optionally filtered by search query).
*   `GET /api/flashcards/{flashcard_id}`: Retrieve a specific flashcard by ID.
*   `POST /api/reviews`: Create a new review record for a flashcard.
*   `GET /api/statistics`: Retrieve review statistics.

## Contributing

Contributions are welcome! Please submit a pull request with your changes.