// Function to fetch data from an API endpoint
async function fetchData(url, options = {}) {
  try {
    const response = await fetch(url, options);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching data:', error);
    throw error; // Re-throw the error to be handled by the caller
  }
}

// Function to create a new flashcard
async function createFlashcard(front_text, back_text) {
  const url = '/api/flashcards';
  const options = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ front_text, back_text }),
  };

  return fetchData(url, options);
}

// Function to get all flashcards (optionally filtered by a query)
async function getFlashcards(query = '') {
  let url = '/api/flashcards';
  if (query) {
    url += `?query=${query}`;
  }
  return fetchData(url);
}

// Function to get a specific flashcard by ID
async function getFlashcard(flashcardId) {
  const url = `/api/flashcards/${flashcardId}`;
  return fetchData(url);
}

// Function to create a new review record
async function createReview(flashcard_id, correct) {
  const url = '/api/reviews';
  const options = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ flashcard_id, correct }),
  };

  return fetchData(url, options);
}

// Function to get review statistics
async function getStatistics() {
  const url = '/api/statistics';
  return fetchData(url);
}

// Function to update the displayed flashcard content
function updateFlashcardDisplay(flashcard, frontElement, backElement) {
    if (flashcard) {
        frontElement.textContent = flashcard.front_text;
        backElement.textContent = flashcard.back_text;
    } else {
        frontElement.textContent = "No flashcards found.";
        backElement.textContent = "";
    }
}

// Function to display an error message
function displayErrorMessage(message, container) {
    const errorElement = document.createElement('p');
    errorElement.className = 'error-message';
    errorElement.textContent = message;
    container.appendChild(errorElement);
}