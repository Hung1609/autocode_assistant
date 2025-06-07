// Function to fetch data from the backend API
async function fetchData(url, options = {}) {
  try {
    const response = await fetch(url, options);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching data:", error);
    throw error;
  }
}

// Function to create a new flashcard
async function createFlashcard(frontText, backText) {
  const url = '/api/flashcards';
  const options = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ front_text: frontText, back_text: backText }),
  };

  return fetchData(url, options);
}

// Function to get all flashcards (optionally filtered by query)
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
async function createReview(flashcardId, correct) {
  const url = '/api/reviews';
  const options = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ flashcard_id: flashcardId, correct: correct }),
  };

  return fetchData(url, options);
}

// Function to get review statistics
async function getStatistics() {
  const url = '/api/statistics';
  return fetchData(url);
}

// Function to handle errors and display messages to the user
function displayMessage(message, type = 'info') {
  // You can implement a more sophisticated message display system here,
  // such as creating a div element and appending it to the DOM.
  // For now, we'll just use alert.
  alert(message);
}