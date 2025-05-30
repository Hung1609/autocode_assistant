import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/flashcards",
    tags=["flashcards"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=schemas.Flashcard)
def create_flashcard(flashcard: schemas.FlashcardCreate, db: Session = Depends(get_db)):
    logger.info(f"Entering create_flashcard with args: {flashcard}, kwargs: {{}}")
    try:
        db_flashcard = models.Flashcard(front_text=flashcard.front_text, back_text=flashcard.back_text)
        db.add(db_flashcard)
        db.commit()
        db.refresh(db_flashcard)
        result = db_flashcard
        logger.info(f"Exiting create_flashcard with result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in create_flashcard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create flashcard: {e}")


@router.get("/", response_model=List[schemas.Flashcard])
def read_flashcards(query: Optional[str] = None, db: Session = Depends(get_db)):
    logger.info(f"Entering read_flashcards with args: {query}, kwargs: {{}}")
    try:
        if query:
            flashcards = db.query(models.Flashcard).filter(
                (models.Flashcard.front_text.contains(query)) | (models.Flashcard.back_text.contains(query))
            ).all()
        else:
            flashcards = db.query(models.Flashcard).all()
        logger.info(f"Exiting read_flashcards with result: {flashcards}")
        return flashcards
    except Exception as e:
        logger.error(f"Error in read_flashcards: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to read flashcards: {e}")


@router.get("/{flashcard_id}", response_model=schemas.Flashcard)
def read_flashcard(flashcard_id: int, db: Session = Depends(get_db)):
    logger.info(f"Entering read_flashcard with args: {flashcard_id}, kwargs: {{}}")
    try:
        db_flashcard = db.query(models.Flashcard).filter(models.Flashcard.id == flashcard_id).first()
        if db_flashcard is None:
            raise HTTPException(status_code=404, detail="Flashcard not found")
        logger.info(f"Exiting read_flashcard with result: {db_flashcard}")
        return db_flashcard
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in read_flashcard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to read flashcard: {e}")