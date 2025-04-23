import uuid
from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory storage simulating a database.  Replace with a real database in production.
flashcards = {}

@app.route('/api/flashcards', methods=['GET'])
def get_flashcards():
    return jsonify(list(flashcards.values()))

@app.route('/api/flashcards', methods=['POST'])
def create_flashcard():
    data = request.get_json()
    if not data or 'front' not in data or 'back' not in data:
        return jsonify({'error': 'Missing front or back'}), 400
    flashcard_id = str(uuid.uuid4())
    flashcards[flashcard_id] = {'id': flashcard_id, 'front': data['front'], 'back': data['back']}
    return jsonify(flashcards[flashcard_id]), 201

@app.route('/api/flashcards/<flashcard_id>', methods=['PUT'])
def update_flashcard(flashcard_id):
    if flashcard_id not in flashcards:
        return jsonify({'error': 'Flashcard not found'}), 404
    data = request.get_json()
    if not data or 'front' not in data or 'back' not in data:
        return jsonify({'error': 'Missing front or back'}), 400
    flashcards[flashcard_id]['front'] = data['front']
    flashcards[flashcard_id]['back'] = data['back']
    return jsonify(flashcards[flashcard_id])

@app.route('/api/flashcards/<flashcard_id>', methods=['DELETE'])
def delete_flashcard(flashcard_id):
    if flashcard_id not in flashcards:
        return jsonify({'error': 'Flashcard not found'}), 404
    del flashcards[flashcard_id]
    return '', 204

if __name__ == '__main__':
    app.run(debug=True)