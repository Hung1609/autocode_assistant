import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend import models, schemas
from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/reviews", response_model=schemas.Review, status_code=201)
def create_review(review: schemas.ReviewCreate, db: Session = Depends(get_db)):
    logger.info(f"Entering create_review with args: {review}, kwargs: {{}}")
    try:
        db_review = models.Review(**review.dict())
        db.add(db_review)
        db.commit()
        db.refresh(db_review)
        logger.info(f"Exiting create_review with result: {db_review}")
        return db_review
    except Exception as e:
        logger.error(f"Error in create_review: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

