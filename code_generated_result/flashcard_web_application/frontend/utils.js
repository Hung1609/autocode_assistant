// Function to fetch data from the API
async function fetchData(url, method = 'GET', body = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };

        if (body) {
            options.body = JSON.stringify(body);
        }

        const response = await fetch(url, options);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error("Fetch error:", error);
        throw error; // Re-throw the error for the calling function to handle
    }
}

// Function to create a flashcard
async function createFlashcard(frontText, backText) {
    const url = '/api/flashcards';
    const body = { front_text: frontText, back_text: backText };

    try {
        const newFlashcard = await fetchData(url, 'POST', body);
        return newFlashcard;
    } catch (error) {
        console.error("Error creating flashcard:", error);
        throw error;
    }
}

// Function to get all flashcards (with optional search query)
async function getAllFlashcards(query = '') {
    let url = '/api/flashcards';
    if (query) {
        url += `?query=${query}`;
    }

    try {
        const flashcards = await fetchData(url);
        return flashcards;
    } catch (error) {
        console.error("Error getting flashcards:", error);
        throw error;
    }
}

// Function to get a specific flashcard by ID
async function getFlashcardById(flashcardId) {
    const url = `/api/flashcards/${flashcardId}`;

    try {
        const flashcard = await fetchData(url);
        return flashcard;
    } catch (error) {
        console.error("Error getting flashcard by ID:", error);
        throw error;
    }
}

// Function to create a review record
async function createReview(flashcardId, correct) {
    const url = '/api/reviews';
    const body = { flashcard_id: flashcardId, correct: correct };

    try {
        const newReview = await fetchData(url, 'POST', body);
        return newReview;
    } catch (error) {
        console.error("Error creating review:", error);
        throw error;
    }
}

// Function to get review statistics
async function getStatistics() {
    const url = '/api/statistics';

    try {
        const statistics = await fetchData(url);
        return statistics;
    } catch (error) {
        console.error("Error getting statistics:", error);
        throw error;
    }
}