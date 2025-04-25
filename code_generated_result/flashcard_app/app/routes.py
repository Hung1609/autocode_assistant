from flask import Flask, render_template, request, redirect, url_for
from app import app, db
from app.models import Flashcard

@app.route('/')
@app.route('/flashcards')
def index():
    flashcards = Flashcard.query.all()
    return render_template('index.html', flashcards=flashcards)

@app.route('/flashcards/new', methods=['GET'])
def new_card():
    return render_template('create_edit_card.html')

@app.route('/flashcards', methods=['POST'])
def create_card():
    front_content = request.form.get('front_content')
    back_content = request.form.get('back_content')

    if not front_content or not back_content:
        return render_template('create_edit_card.html', error="Front and back content are required.")

    new_card = Flashcard(front_content=front_content, back_content=back_content)
    db.session.add(new_card)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/flashcards/<int:card_id>/edit', methods=['GET'])
def edit_card(card_id):
    card = Flashcard.query.get_or_404(card_id)
    return render_template('create_edit_card.html', card=card)

@app.route('/flashcards/<int:card_id>/update', methods=['POST'])
def update_card(card_id):
    card = Flashcard.query.get_or_404(card_id)
    card.front_content = request.form.get('front_content')
    card.back_content = request.form.get('back_content')

    if not card.front_content or not card.back_content:
         return render_template('create_edit_card.html', card=card, error="Front and back content are required.")
    
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/flashcards/<int:card_id>/delete', methods=['POST'])
def delete_card(card_id):
    card = Flashcard.query.get_or_404(card_id)
    db.session.delete(card)
    db.session.commit()
    return redirect(url_for('index'))