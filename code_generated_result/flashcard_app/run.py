from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime

app = Flask(__name__)

# Configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flashcards.db'  # Use relative path for simplicity
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable modification tracking
db = SQLAlchemy(app)

# Define the Flashcard model
class Flashcard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    front_content = db.Column(db.Text, nullable=False)
    back_content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Flashcard {self.id}: {self.front_content}>'

# Create the database tables within the app context
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def index():
    flashcards = Flashcard.query.all()
    return render_template('index.html', flashcards=flashcards)

@app.route('/flashcards/new')
def new_card():
    return render_template('create_edit_card.html')

@app.route('/flashcards', methods=['POST'])
def create_card():
    front_content = request.form.get('front_content')
    back_content = request.form.get('back_content')

    if not front_content or not back_content:
        return render_template('create_edit_card.html', error='Both front and back content are required.')

    new_card = Flashcard(front_content=front_content, back_content=back_content)
    db.session.add(new_card)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/flashcards/<int:card_id>/edit')
def edit_card(card_id):
    card = Flashcard.query.get_or_404(card_id)
    return render_template('create_edit_card.html', card=card)

@app.route('/flashcards/<int:card_id>/update', methods=['POST'])
def update_card(card_id):
    card = Flashcard.query.get_or_404(card_id)
    card.front_content = request.form.get('front_content')
    card.back_content = request.form.get('back_content')

    if not card.front_content or not card.back_content:
         return render_template('create_edit_card.html', card=card, error='Both front and back content are required.')

    db.session.commit()
    return redirect(url_for('index'))

@app.route('/flashcards/<int:card_id>/delete', methods=['POST'])
def delete_card(card_id):
    card = Flashcard.query.get_or_404(card_id)
    db.session.delete(card)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)