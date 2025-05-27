// Function to fetch flashcards from the backend
async function getFlashcards(query = '') {
    try {
        let url = '/api/flashcards';
        if (query) {
            url += `?query=${query}`;
        }
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const flashcards = await response.json();
        return flashcards;
    } catch (error) {
        console.error('Error fetching flashcards:', error);
        return []; // Return an empty array in case of error
    }
}

// Function to create a flashcard
async function createFlashcard(front_text, back_text) {
    try {
        const response = await fetch('/api/flashcards', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ front_text: front_text, back_text: back_text })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const newFlashcard = await response.json();
        return newFlashcard;
    } catch (error) {
        console.error('Error creating flashcard:', error);
        return null;
    }
}

// Function to submit a review
async function submitReview(flashcard_id, correct) {
    try {
        const response = await fetch('/api/reviews', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ flashcard_id: flashcard_id, correct: correct })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const newReview = await response.json();
        return newReview;
    } catch (error) {
        console.error('Error submitting review:', error);
        return null;
    }
}

// Function to fetch statistics
async function getStatistics() {
    try {
        const response = await fetch('/api/statistics');

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const statistics = await response.json();
        return statistics;
    } catch (error) {
        console.error('Error fetching statistics:', error);
        return null;
    }
}

// Function to display a message in a designated area (e.g., for success/error messages)
function displayMessage(message, type = 'info') {
    const messageArea = document.getElementById('message-area');
    if (!messageArea) {
        console.warn('Message area not found.');
        return;
    }

    messageArea.textContent = message;
    messageArea.className = `message ${type}`; // Use classes for styling based on message type (e.g., success, error)
}

// Function to clear a message in a designated area
function clearMessage() {
    const messageArea = document.getElementById('message-area');
    if (messageArea) {
        messageArea.textContent = '';
        messageArea.className = ''; // Clear any existing classes
    }
}