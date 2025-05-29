# Flashcard Web Application

## Overview

This is a simple flashcard web application built with:

*   **Backend:** Python, FastAPI
*   **Frontend:** HTML, CSS, JavaScript (Vanilla)
*   **Database:** SQLite

The application allows users to:

*   Create flashcards
*   Search flashcards
*   Review flashcards
*   View review statistics
*   Comes preloaded with ten Hindi-English flashcards.

## Setup

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd flashcard_web_application
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Linux/macOS
    # venv\Scripts\activate  # On Windows
    ```

3.  **Install backend dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the backend:**

    ```bash
    uvicorn backend.main:app --reload --port 8001
    ```

    This will start the FastAPI server on port 8001.  The `--reload` flag enables automatic reloading on code changes.

5.  **Access the application:**

    Open your web browser and navigate to `http://localhost:8001`.

## Project Structure

```
flashcard_web_application/
├── backend/            # Backend application code
│   ├── main.py         # Main FastAPI application file
│   ├── database.py     # Database connection setup
│   ├── models.py       # SQLAlchemy ORM models
│   ├── routers/        # API route definitions
│   │   ├── flashcards.py # Flashcard API endpoints
│   │   └── reviews.py    # Review API endpoints
│   └── schemas.py      # Pydantic schemas for data validation
├── frontend/           # Frontend application code
│   ├── index.html      # Main HTML file
│   ├── style.css       # CSS stylesheet
│   ├── script.js       # JavaScript application logic
│   └── utils.js        # JavaScript utility functions
├── requirements.txt   # Python dependencies
├── README.md          # This file
└── .gitignore         # Git ignore file
```

## API Endpoints

The backend provides the following API endpoints:

*   `POST /api/flashcards`: Create a new flashcard.
*   `GET /api/flashcards`: Retrieve all flashcards (optionally filtered by a search query).
*   `GET /api/flashcards/{flashcard_id}`: Retrieve a specific flashcard by ID.
*   `POST /api/reviews`: Create a new review record for a flashcard.
*   `GET /api/statistics`: Retrieve review statistics.

## Usage

Once the application is running, you can use the web interface to create, search, review, and view statistics for your flashcards. The interface is designed to be intuitive and easy to use.

## Technologies Used

*   **Backend:**
    *   Python
    *   FastAPI
    *   SQLAlchemy
    *   Pydantic
    *   SQLite
*   **Frontend:**
    *   HTML
    *   CSS
    *   JavaScript (Vanilla)

## Contributing

Contributions are welcome! Please submit a pull request with your changes.

## License

[MIT](LICENSE) (Replace with your desired license)