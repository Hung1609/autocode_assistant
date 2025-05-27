import logging
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

logger = logging.getLogger(__name__)

Base = declarative_base()

class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    front_text = Column(String, nullable=False)
    back_text = Column(String, nullable=False)

    reviews = relationship("Review", back_populates="flashcard")

    def __repr__(self):
        return f"<Flashcard(front_text='{self.front_text}', back_text='{self.back_text}')>"

    def __init__(self, front_text, back_text):
        self.front_text = front_text
        self.back_text = back_text

    def to_dict(self):
        return {
            'id': self.id,
            'front_text': self.front_text,
            'back_text': self.back_text
        }

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    flashcard_id = Column(Integer, ForeignKey("flashcards.id"), nullable=False, index=True)
    correct = Column(Boolean, nullable=False)
    review_timestamp = Column(DateTime, server_default=func.now())

    flashcard = relationship("Flashcard", back_populates="reviews")

    def __repr__(self):
        return f"<Review(flashcard_id={self.flashcard_id}, correct={self.correct})>"

    def __init__(self, flashcard_id, correct):
        self.flashcard_id = flashcard_id
        self.correct = correct

    def to_dict(self):
        return {
            'id': self.id,
            'flashcard_id': self.flashcard_id,
            'correct': self.correct,
            'review_timestamp': self.review_timestamp
        }