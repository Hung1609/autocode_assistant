import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class FlashcardCreate(BaseModel):
    front_text: str
    back_text: str

class Flashcard(BaseModel):
    id: int
    front_text: str
    back_text: str

    class Config:
        orm_mode = True

class ReviewCreate(BaseModel):
    flashcard_id: int
    correct: bool

class Review(BaseModel):
    id: int
    flashcard_id: int
    correct: bool
    review_timestamp: str

    class Config:
        orm_mode = True

class Statistics(BaseModel):
    total_cards_reviewed: int
    percentage_correct: float