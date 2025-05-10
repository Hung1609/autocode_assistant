import pytest
from unittest.mock import patch
from app.routes import create_card
from flask import Flask

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_create_card_success(app, client):
    with app.test_request_context('/flashcards', method='POST', data={'front_content': 'Front', 'back_content': 'Back'}):
        with patch('app.routes.request') as mock_request, \
             patch('app.routes.db.session.add') as mock_db_add, \
             patch('app.routes.db.session.commit') as mock_db_commit, \
             patch('app.routes.Flashcard') as mock_flashcard, \
             patch('app.routes.redirect') as mock_redirect, \
             patch('app.routes.url_for') as mock_url_for:

            mock_request.form = {'front_content': 'Front', 'back_content': 'Back'}
            mock_url_for.return_value = '/index'

            response = create_card()

            mock_flashcard.assert_called_once_with(front_content='Front', back_content='Back')
            mock_db_add.assert_called_once()
            mock_db_commit.assert_called_once()
            mock_redirect.assert_called_once_with('/index')
            assert response == mock_redirect.return_value

def test_create_card_missing_front_content(app, client):
    with app.test_request_context('/flashcards', method='POST', data={'back_content': 'Back'}):
        with patch('app.routes.request') as mock_request, \
             patch('app.routes.render_template') as mock_render_template:

            mock_request.form = {'back_content': 'Back'}

            response = create_card()

            mock_render_template.assert_called_once_with('create_edit_card.html', error="Front and back content are required.")
            assert response == mock_render_template.return_value

def test_create_card_missing_back_content(app, client):
    with app.test_request_context('/flashcards', method='POST', data={'front_content': 'Front'}):
        with patch('app.routes.request') as mock_request, \
             patch('app.routes.render_template') as mock_render_template:

            mock_request.form = {'front_content': 'Front'}

            response = create_card()

            mock_render_template.assert_called_once_with('create_edit_card.html', error="Front and back content are required.")
            assert response == mock_render_template.return_value

def test_create_card_empty_form(app, client):
    with app.test_request_context('/flashcards', method='POST', data={}):
        with patch('app.routes.request') as mock_request, \
             patch('app.routes.render_template') as mock_render_template:

            mock_request.form = {}

            response = create_card()

            mock_render_template.assert_called_once_with('create_edit_card.html', error="Front and back content are required.")
            assert response == mock_render_template.return_value