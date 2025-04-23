import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [flashcards, setFlashcards] = useState([]);
  const [frontText, setFrontText] = useState('');
  const [backText, setBackText] = useState('');
  const [editingFlashcard, setEditingFlashcard] = useState(null);

  useEffect(() => {
    fetchFlashcards();
  }, []);

  const fetchFlashcards = async () => {
    try {
      const response = await axios.get('/api/flashcards');
      setFlashcards(response.data);
    } catch (error) {
      console.error("Error fetching flashcards:", error);
    }
  };

  const createFlashcard = async () => {
    try {
      await axios.post('/api/flashcards', { front: frontText, back: backText });
      setFrontText('');
      setBackText('');
      fetchFlashcards();
    } catch (error) {
      console.error("Error creating flashcard:", error);
    }
  };

  const handleEdit = (flashcard) => {
    setFrontText(flashcard.front);
    setBackText(flashcard.back);
    setEditingFlashcard(flashcard);
  };

  const updateFlashcard = async () => {
    try {
      await axios.put(`/api/flashcards/${editingFlashcard.id}`, { front: frontText, back: backText });
      setFrontText('');
      setBackText('');
      setEditingFlashcard(null);
      fetchFlashcards();
    } catch (error) {
      console.error("Error updating flashcard:", error);
    }
  };

  const deleteFlashcard = async (id) => {
    try {
      await axios.delete(`/api/flashcards/${id}`);
      fetchFlashcards();
    } catch (error) {
      console.error("Error deleting flashcard:", error);
    }
  };

  return (
    <div>
      <h1>Flashcards</h1>
      <div>
        <input
          type="text"
          placeholder="Front"
          value={frontText}
          onChange={(e) => setFrontText(e.target.value)}
        />
        <input
          type="text"
          placeholder="Back"
          value={backText}
          onChange={(e) => setBackText(e.target.value)}
        />
        {editingFlashcard ? (
          <button onClick={updateFlashcard}>Update</button>
        ) : (
          <button onClick={createFlashcard}>Create</button>
        )}
      </div>
      <ul>
        {flashcards.map((flashcard) => (
          <li key={flashcard.id}>
            <div>Front: {flashcard.front}</div>
            <div>Back: {flashcard.back}</div>
            <button onClick={() => handleEdit(flashcard)}>Edit</button>
            <button onClick={() => deleteFlashcard(flashcard.id)}>Delete</button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;