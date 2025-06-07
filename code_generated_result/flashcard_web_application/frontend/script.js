document.addEventListener('DOMContentLoaded', () => {
    const flashcardContainer = document.getElementById('flashcard-container');
    const createForm = document.getElementById('create-form');
    const searchInput = document.getElementById('search-input');
    const searchResults = document.getElementById('search-results');
    const reviewContainer = document.getElementById('review-container');
    const statisticsContainer = document.getElementById('statistics-container');
    const sidebar = document.getElementById('sidebar');

    let flashcards = [];
    let currentFlashcardIndex = 0;

    // Utility functions (consider moving to utils.js)
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
            flashcards.push(newFlashcard); // Update local flashcards array
            return newFlashcard;
        } catch (error) {
            console.error('Error creating flashcard:', error);
            return null;
        }
    }

    async function createReview(flashcardId, correct) {
        try {
            const response = await fetch('/api/reviews', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ flashcard_id: flashcardId, correct: correct }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const newReview = await response.json();
            return newReview;
        } catch (error) {
            console.error('Error creating review:', error);
            return null;
        }
    }

    async function fetchStatistics() {
        try {
            const response = await fetch('/api/statistics');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const statistics = await response.json();
            return statistics;
        } catch (error) {
            console.error('Error fetching statistics:', error);
            return null;
        }
    }

    function displayFlashcard(flashcard) {
        if (!flashcard) {
            flashcardContainer.innerHTML = '<p>No flashcards available.</p>';
            return;
        }

        flashcardContainer.innerHTML = `
            <div class="flashcard">
                <div class="front">${flashcard.front_text}</div>
                <div class="back" style="display: none;">${flashcard.back_text}</div>
            </div>
            <button id="flip-button">Flip</button>
            <button id="correct-button">Correct</button>
            <button id="incorrect-button">Incorrect</button>
        `;

        const flipButton = document.getElementById('flip-button');
        const correctButton = document.getElementById('correct-button');
        const incorrectButton = document.getElementById('incorrect-button');
        const front = document.querySelector('.front');
        const back = document.querySelector('.back');

        flipButton.addEventListener('click', () => {
            front.style.display = front.style.display === 'none' ? 'block' : 'none';
            back.style.display = back.style.display === 'none' ? 'block' : 'none';
        });

        correctButton.addEventListener('click', async () => {
            await createReview(flashcard.id, true);
            nextFlashcard();
        });

        incorrectButton.addEventListener('click', async () => {
            await createReview(flashcard.id, false);
            nextFlashcard();
        });
    }

    function nextFlashcard() {
        currentFlashcardIndex = (currentFlashcardIndex + 1) % flashcards.length;
        displayFlashcard(flashcards[currentFlashcardIndex]);
    }

    function displaySearchResults(results) {
        searchResults.innerHTML = '';
        if (results.length === 0) {
            searchResults.innerHTML = '<p>No results found.</p>';
            return;
        }

        const list = document.createElement('ul');
        results.forEach(flashcard => {
            const item = document.createElement('li');
            item.textContent = `${flashcard.front_text} - ${flashcard.back_text}`;
            list.appendChild(item);
        });
        searchResults.appendChild(list);
    }

    async function displayStatistics() {
        const stats = await fetchStatistics();
        if (!stats) {
            statisticsContainer.innerHTML = '<p>Could not load statistics.</p>';
            return;
        }

        statisticsContainer.innerHTML = `
            <p>Total cards reviewed: ${stats.total_cards_reviewed || 0}</p>
            <p>Percentage correct: ${stats.percentage_correct ? stats.percentage_correct.toFixed(2) + '%' : '0%'}</p>
        `;
    }

    // Event listeners
    if (createForm) {
        createForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const frontText = document.getElementById('front-text').value;
            const backText = document.getElementById('back-text').value;

            const newFlashcard = await createFlashcard(frontText, backText);
            if (newFlashcard) {
                document.getElementById('front-text').value = '';
                document.getElementById('back-text').value = '';
                alert('Flashcard created!');
            } else {
                alert('Failed to create flashcard.');
            }
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', async (event) => {
            const query = event.target.value;
            const results = await fetchFlashcards(query);
            displaySearchResults(results);
        });
    }

    // Sidebar navigation (basic example)
    if (sidebar) {
        sidebar.addEventListener('click', (event) => {
            if (event.target.tagName === 'A') {
                event.preventDefault();
                const target = event.target.getAttribute('href').substring(1); // Remove '#'
                // Hide all containers
                const containers = document.querySelectorAll('#create-form, #search-container, #review-container, #statistics-container');
                containers.forEach(container => {
                    if (container) {
                        container.style.display = 'none';
                    }
                });

                // Show the target container
                const targetContainer = document.getElementById(target + '-container');
                if (targetContainer) {
                    targetContainer.style.display = 'block';
                }

                if (target === 'review') {
                    startReview();
                } else if (target === 'statistics') {
                    displayStatistics();
                }
            }
        });
    }

    async function startReview() {
        await fetchFlashcards(); // Load flashcards before starting review
        currentFlashcardIndex = 0;
        displayFlashcard(flashcards[currentFlashcardIndex]);
    }

    // Initial load (e.g., start review if on review page)
    if (window.location.hash === '#review') {
        startReview();
    } else if (window.location.hash === '#statistics') {
        displayStatistics();
    } else {
        fetchFlashcards(); // Load flashcards on initial load
    }

    // Preload flashcards (example - can be moved to backend)
    async function preloadFlashcards() {
        const initialFlashcards = [
            { front_text: "नमस्ते", back_text: "Hello" },
            { front_text: "धन्यवाद", back_text: "Thank you" },
            { front_text: "हाँ", back_text: "Yes" },
            { front_text: "नहीं", back_text: "No" },
            { front_text: "अच्छा", back_text: "Good" },
            { front_text: "बुरा", back_text: "Bad" },
            { front_text: "पानी", back_text: "Water" },
            { front_text: "खाना", back_text: "Food" },
            { front_text: "घर", back_text: "Home" },
            { front_text: "दोस्त", back_text: "Friend" }
        ];

        for (const card of initialFlashcards) {
            await createFlashcard(card.front_text, card.back_text);
        }
    }

    // Call preloadFlashcards on initial load (only if no flashcards exist)
    fetchFlashcards().then(existingFlashcards => {
        if (existingFlashcards.length === 0) {
            preloadFlashcards();
        }
    });
});