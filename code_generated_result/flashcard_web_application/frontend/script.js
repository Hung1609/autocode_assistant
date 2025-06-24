document.addEventListener('DOMContentLoaded', () => {
    const flashcardContainer = document.getElementById('flashcard-container');
    const createForm = document.getElementById('create-form');
    const searchInput = document.getElementById('search-input');
    const reviewButton = document.getElementById('review-button');
    const statisticsButton = document.getElementById('statistics-button');
    const createButton = document.getElementById('create-button');
    const searchButton = document.getElementById('search-button');

    let flashcards = [];
    let currentFlashcardIndex = 0;

    // Function to fetch flashcards from the backend
    async function fetchFlashcards(query = '') {
        try {
            const response = await fetch(`/api/flashcards?query=${query}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            flashcards = await response.json();
            return flashcards;
        } catch (error) {
            console.error('Error fetching flashcards:', error);
            return [];
        }
    }

    // Function to display a flashcard
    function displayFlashcard(index) {
        if (flashcards.length === 0) {
            flashcardContainer.innerHTML = '<p>No flashcards available.</p>';
            return;
        }

        const flashcard = flashcards[index];
        flashcardContainer.innerHTML = `
            <div class="flashcard">
                <div class="front">${flashcard.front_text}</div>
                <div class="back" style="display: none;">${flashcard.back_text}</div>
            </div>
            <p>Card ${index + 1} of ${flashcards.length}</p>
        `;

        const card = flashcardContainer.querySelector('.flashcard');
        card.addEventListener('click', () => {
            const front = card.querySelector('.front');
            const back = card.querySelector('.back');
            if (front.style.display !== 'none') {
                front.style.display = 'none';
                back.style.display = 'block';
            } else {
                front.style.display = 'block';
                back.style.display = 'none';
            }
        });
    }

    // Function to handle creating a new flashcard
    async function createFlashcard(frontText, backText) {
        try {
            const response = await fetch('/api/flashcards', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ front_text: frontText, back_text: backText }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const newFlashcard = await response.json();
            flashcards.push(newFlashcard);
            alert('Flashcard created successfully!');
            return newFlashcard;

        } catch (error) {
            console.error('Error creating flashcard:', error);
            alert('Failed to create flashcard.');
            return null;
        }
    }

    // Event listener for the create form submission
    if (createForm) {
        createForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const frontText = document.getElementById('front-text').value;
            const backText = document.getElementById('back-text').value;

            if (frontText && backText) {
                await createFlashcard(frontText, backText);
                document.getElementById('front-text').value = '';
                document.getElementById('back-text').value = '';
            } else {
                alert('Please fill in both front and back text.');
            }
        });
    }

    // Event listener for the search input
    if (searchInput) {
        searchInput.addEventListener('input', async (event) => {
            const query = event.target.value;
            await fetchFlashcards(query);
            currentFlashcardIndex = 0;
            displayFlashcard(currentFlashcardIndex);
        });
    }

    // Review functionality
    async function startReview() {
        await fetchFlashcards();
        if (flashcards.length > 0) {
            currentFlashcardIndex = 0;
            displayFlashcard(currentFlashcardIndex);
        } else {
            flashcardContainer.innerHTML = '<p>No flashcards to review.</p>';
        }
    }

    // Navigation event listeners (example for arrow keys)
    document.addEventListener('keydown', (event) => {
        if (event.key === 'ArrowRight') {
            if (flashcards.length > 0) {
                currentFlashcardIndex = (currentFlashcardIndex + 1) % flashcards.length;
                displayFlashcard(currentFlashcardIndex);
            }
        } else if (event.key === 'ArrowLeft') {
            if (flashcards.length > 0) {
                currentFlashcardIndex = (currentFlashcardIndex - 1 + flashcards.length) % flashcards.length;
                displayFlashcard(currentFlashcardIndex);
            }
        }
    });

    // Initial fetch and display
    async function initialize() {
        await fetchFlashcards();
        if (flashcards.length > 0) {
            displayFlashcard(currentFlashcardIndex);
        } else {
            flashcardContainer.innerHTML = '<p>No flashcards available. Create some!</p>';
        }
    }

    if (reviewButton) {
        reviewButton.addEventListener('click', startReview);
    }

    if (statisticsButton) {
        statisticsButton.addEventListener('click', () => {
            window.location.href = '/statistics.html';
        });
    }

    if (createButton) {
        createButton.addEventListener('click', () => {
            window.location.href = '/create.html';
        });
    }

    if (searchButton) {
        searchButton.addEventListener('click', () => {
            window.location.href = '/search.html';
        });
    }

    initialize();
});