from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from sqlalchemy.orm import Session
from backend import models, schemas
from backend.database import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/flashcards", response_model=schemas.Flashcard, status_code=201)
def create_flashcard(flashcard: schemas.FlashcardCreate, db: Session = Depends(get_db)):
    logger.info(f"Entering create_flashcard with args: {flashcard}, kwargs: {{}}")
    try:
        flashcard_data = flashcard.dict()
        db_flashcard = models.Flashcard(**flashcard_data)
        db.add(db_flashcard)
        db.commit()
        db.refresh(db_flashcard)
        result = db_flashcard
        logger.info(f"Exiting create_flashcard with result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in create_flashcard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/flashcards", response_model=List[schemas.Flashcard])
def read_flashcards(query: Optional[str] = None, db: Session = Depends(get_db)):
    logger.info(f"Entering read_flashcards with args: query={query}, kwargs: {{}}")
    try:
        if query:
            flashcards = db.query(models.Flashcard).filter(
                (models.Flashcard.front_text.contains(query)) | (models.Flashcard.back_text.contains(query))
            ).all()
        else:
            flashcards = db.query(models.Flashcard).all()
        result = flashcards
        logger.info(f"Exiting read_flashcards with result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in read_flashcards: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/flashcards/{flashcard_id}", response_model=schemas.Flashcard)
def read_flashcard(flashcard_id: int, db: Session = Depends(get_db)):
    logger.info(f"Entering read_flashcard with args: flashcard_id={flashcard_id}, kwargs: {{}}")
    try:
        db_flashcard = db.query(models.Flashcard).filter(models.Flashcard.id == flashcard_id).first()
        if db_flashcard is None:
            raise HTTPException(status_code=404, detail="Flashcard not found")
        result = db_flashcard
        logger.info(f"Exiting read_flashcard with result: {result}")
        return result
    except HTTPException as http_exception:
        logger.error(f"Error in read_flashcard: {http_exception.detail}", exc_info=True)
        raise http_exception
    except Exception as e:
        logger.error(f"Error in read_flashcard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))