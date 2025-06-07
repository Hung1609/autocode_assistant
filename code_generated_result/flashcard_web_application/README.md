# Flashcard Web Application

## Overview

This project is a web application for creating, reviewing, and searching flashcards. It's designed to help users learn and memorize information effectively, particularly useful for language learning.

## Features

*   **Create Flashcards:** Users can create new flashcards with a front and back side.
*   **Search Flashcards:** Users can search through their existing flashcards using a search query.
*   **Review Flashcards:** Users can review their flashcards, flipping them to reveal the answer.
*   **View Review Statistics:** Users can view statistics on their flashcard reviews.
*   **Preloaded Flashcards:** The application is preloaded with ten flashcards containing a Hindi word or phrase and its English translation.

## Technology Stack

*   **Backend:**
    *   Language: Python
    *   Framework: FastAPI
    *   Database: SQLite
*   **Frontend:**
    *   Language: HTML, CSS, JavaScript (Vanilla)

## Project Structure

```
flashcard_web_application/
├── README.md
├── requirements.txt
├── .gitignore
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── routers/
│   │   ├── flashcards.py
│   │   └── reviews.py
│   └── schemas.py
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   ├── utils.js
│   └── assets/
└── ...
```

## Setup Instructions

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd flashcard_web_application
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    venv\Scripts\activate  # On Windows
    ```

3.  **Install backend dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the backend:**

    ```bash
    python -m uvicorn backend.main:app --reload --port 8001
    ```

5.  **Access the frontend:**

    Open your web browser and navigate to `http://localhost:8001`.

## API Endpoints

*   `POST /api/flashcards`: Creates a new flashcard.
*   `GET /api/flashcards`: Retrieves all flashcards, optionally filtered by a search query.
*   `GET /api/flashcards/{flashcard_id}`: Retrieves a specific flashcard by ID.
*   `POST /api/reviews`: Creates a new review record for a flashcard.
*   `GET /api/statistics`: Retrieves review statistics.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for any bugs or feature requests.

## License

[MIT](LICENSE)