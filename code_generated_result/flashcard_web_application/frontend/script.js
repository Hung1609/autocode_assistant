document.addEventListener('DOMContentLoaded', () => {
    const flashcardContainer = document.getElementById('flashcard-container');
    const frontTextElement = document.getElementById('front-text');
    const backTextElement = document.getElementById('back-text');
    const flipButton = document.getElementById('flip-button');
    const nextButton = document.getElementById('next-button');
    const createForm = document.getElementById('create-form');
    const searchInput = document.getElementById('search-input');
    const searchResults = document.getElementById('search-results');
    const reviewStats = document.getElementById('review-stats');
    const cardCountElement = document.getElementById('card-count');

    let flashcards = [];
    let currentCardIndex = 0;
    let correctCount = 0;
    let totalReviewed = 0;
    let isFlipped = false;

    // Function to fetch flashcards from the backend
    async function fetchFlashcards(query = '') {
        try {
            let url = '/api/flashcards';
            if (query) {
                url += `?query=${query}`;
            }
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            flashcards = await response.json();
            currentCardIndex = 0;
            updateFlashcardDisplay();
            updateCardCount();
        } catch (error) {
            console.error('Error fetching flashcards:', error);
            flashcardContainer.textContent = 'Failed to load flashcards.';
        }
    }

    // Function to update the flashcard display
    function updateFlashcardDisplay() {
        if (flashcards.length === 0) {
            frontTextElement.textContent = 'No flashcards available. Create some!';
            backTextElement.textContent = '';
            return;
        }

        const card = flashcards[currentCardIndex];
        frontTextElement.textContent = card.front_text;
        backTextElement.textContent = card.back_text;
        isFlipped = false;
        flashcardContainer.classList.remove('flipped');
    }

    // Function to update the card count display
    function updateCardCount() {
        cardCountElement.textContent = `Card ${currentCardIndex + 1} of ${flashcards.length}`;
    }

    // Function to handle flipping the flashcard
    function flipCard() {
        flashcardContainer.classList.toggle('flipped');
        isFlipped = !isFlipped;
    }

    // Function to handle moving to the next flashcard
    async function nextCard(correct) {
        if (flashcards.length === 0) return;

        totalReviewed++;
        if (correct) {
            correctCount++;
        }

        try {
            const card = flashcards[currentCardIndex];
            const response = await fetch('/api/reviews', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    flashcard_id: card.id,
                    correct: correct
                })
            });

            if (!response.ok) {
                console.error('Failed to record review:', response.status);
            }
        } catch (error) {
            console.error('Error recording review:', error);
        }

        currentCardIndex = (currentCardIndex + 1) % flashcards.length;
        updateFlashcardDisplay();
        updateCardCount();
        updateReviewStats();
    }

    // Function to update review statistics
    function updateReviewStats() {
        const percentageCorrect = totalReviewed > 0 ? (correctCount / totalReviewed) * 100 : 0;
        reviewStats.textContent = `Correct: ${percentageCorrect.toFixed(2)}% (${correctCount}/${totalReviewed})`;
    }

    // Event listener for flipping the card
    flipButton.addEventListener('click', flipCard);

    // Event listener for next card (correct)
    document.getElementById('correct-button').addEventListener('click', () => nextCard(true));

    // Event listener for next card (incorrect)
    document.getElementById('incorrect-button').addEventListener('click', () => nextCard(false));


    // Event listener for creating a new flashcard
    createForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const frontText = document.getElementById('front').value;
        const backText = document.getElementById('back').value;

        try {
            const response = await fetch('/api/flashcards', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    front_text: frontText,
                    back_text: backText
                })
            });

            if (response.ok) {
                document.getElementById('front').value = '';
                document.getElementById('back').value = '';
                fetchFlashcards(); // Refresh flashcards after creating
            } else {
                console.error('Failed to create flashcard:', response.status);
                alert('Failed to create flashcard. Please try again.');
            }
        } catch (error) {
            console.error('Error creating flashcard:', error);
            alert('An error occurred while creating the flashcard.');
        }
    });

    // Event listener for real-time search
    searchInput.addEventListener('input', () => {
        const query = searchInput.value.trim();
        fetchFlashcards(query);
    });

    // Initial fetch of flashcards
    fetchFlashcards();
});