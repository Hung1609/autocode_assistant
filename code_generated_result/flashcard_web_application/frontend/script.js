document.addEventListener('DOMContentLoaded', () => {
    const flashcardsContainer = document.getElementById('flashcards-container');
    const searchInput = document.getElementById('search-input');
    const createForm = document.getElementById('create-form');
    const reviewCard = document.getElementById('review-card');
    const frontText = document.getElementById('front-text');
    const backText = document.getElementById('back-text');
    const correctCountElement = document.getElementById('correct-count'); // Statistics
    const totalCountElement = document.getElementById('total-count'); // Statistics
    const flipButton = document.getElementById('flip-button');

    let flashcards = [];
    let currentFlashcardIndex = 0;
    let correctCount = 0; // Statistics
    let totalCount = 0; // Statistics
    let isFlipped = false;

    // Helper function to fetch data from the API
    async function fetchData(url, method = 'GET', body = null) {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: body ? JSON.stringify(body) : null,
        };

        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Fetch error:', error);
            return null;
        }
    }

    // Function to render flashcards
    function renderFlashcards(flashcardsToRender) {
        flashcardsContainer.innerHTML = '';
        flashcardsToRender.forEach(flashcard => {
            const cardDiv = document.createElement('div');
            cardDiv.classList.add('flashcard');
            cardDiv.innerHTML = `
                <p>Front: ${flashcard.front_text}</p>
                <p>Back: ${flashcard.back_text}</p>
            `;
            flashcardsContainer.appendChild(cardDiv);
        });
    }

    // Load all flashcards on page load
    async function loadFlashcards() {
        flashcards = await fetchData('/api/flashcards');
        if (flashcards) {
            renderFlashcards(flashcards);
        } else {
            flashcardsContainer.innerHTML = '<p>Failed to load flashcards.</p>';
        }
    }

    // Search functionality
    searchInput.addEventListener('input', async (event) => {
        const query = event.target.value;
        const searchResults = await fetchData(`/api/flashcards?query=${query}`);
        if (searchResults) {
            renderFlashcards(searchResults);
        } else {
            flashcardsContainer.innerHTML = '<p>Failed to load search results.</p>';
        }
    });

    // Create flashcard functionality
    createForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const front = document.getElementById('front').value;
        const back = document.getElementById('back').value;

        const newFlashcard = {
            front_text: front,
            back_text: back,
        };

        const createdFlashcard = await fetchData('/api/flashcards', 'POST', newFlashcard);

        if (createdFlashcard) {
            document.getElementById('front').value = '';
            document.getElementById('back').value = '';
            loadFlashcards(); // Reload flashcards to include the new one
            alert('Flashcard created successfully!');
        } else {
            alert('Failed to create flashcard.');
        }
    });

    // Review functionality
    function showFlashcard() {
        if (flashcards.length === 0) {
            reviewCard.innerHTML = '<p>No flashcards to review.</p>';
            return;
        }

        const flashcard = flashcards[currentFlashcardIndex];
        frontText.textContent = flashcard.front_text;
        backText.textContent = flashcard.textContent = ''; // Initially hidden
        isFlipped = false;
    }

    flipButton.addEventListener('click', () => {
        isFlipped = !isFlipped;
        if (isFlipped) {
            backText.textContent = flashcards[currentFlashcardIndex].back_text;
            frontText.textContent = '';
        } else {
            frontText.textContent = flashcards[currentFlashcardIndex].front_text;
            backText.textContent = '';
        }
    });

    document.addEventListener('keydown', async (event) => {
        if (event.key === 'ArrowRight') {
            if (flashcards.length === 0) return;

            const correct = confirm('Did you get it right?');

            const reviewData = {
                flashcard_id: flashcards[currentFlashcardIndex].id,
                correct: correct,
            };

            const reviewResult = await fetchData('/api/reviews', 'POST', reviewData);

            if (!reviewResult) {
                console.error('Failed to save review data.');
            }

            totalCount++;
            if (correct) {
                correctCount++;
            }
            updateStatisticsDisplay();

            currentFlashcardIndex = (currentFlashcardIndex + 1) % flashcards.length;
            showFlashcard();
        }
    });

    function updateStatisticsDisplay() {
        if (correctCountElement && totalCountElement) {
            correctCountElement.textContent = correctCount;
            totalCountElement.textContent = totalCount;
        }
    }

    async function loadReviewFlashcards() {
        flashcards = await fetchData('/api/flashcards');
        if (flashcards) {
            currentFlashcardIndex = 0;
            correctCount = 0;
            totalCount = 0;
            updateStatisticsDisplay();
            showFlashcard();
        } else {
            reviewCard.innerHTML = '<p>Failed to load flashcards for review.</p>';
        }
    }

    async function loadStatistics() {
        const statistics = await fetchData('/api/statistics');
        if(statistics) {
            correctCount = statistics.correct_count;
            totalCount = statistics.total_count;
            updateStatisticsDisplay();
        } else {
            console.error("Failed to load statistics.");
        }
    }

    // Call loadFlashcards and loadReviewFlashcards on page load to initialize the UI
    if(flashcardsContainer){
        loadFlashcards();
    }

    if(reviewCard){
        loadReviewFlashcards();
    }
    
    if (correctCountElement && totalCountElement) { //If Statistics Page
        loadStatistics();
    }
});