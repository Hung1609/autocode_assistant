import logging
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func

logger = logging.getLogger(__name__)

DATABASE_URL = "sqlite:///./flashcards.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True)
    front_text = Column(String, nullable=False)
    back_text = Column(String, nullable=False)

    reviews = relationship("Review", back_populates="flashcard")

    def __init__(self, front_text: str, back_text: str):
        self.front_text = front_text
        self.back_text = back_text


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    flashcard_id = Column(Integer, ForeignKey("flashcards.id", ondelete="CASCADE"), nullable=False)
    correct = Column(Boolean, nullable=False)
    review_timestamp = Column(DateTime(timezone=True), server_default=func.now())

    flashcard = relationship("Flashcard", back_populates="reviews")

    def __init__(self, flashcard_id: int, correct: bool):
        self.flashcard_id = flashcard_id
        self.correct = correct


def create_db_and_tables():
    logger.info("Entering create_db_and_tables")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database and tables created successfully.")
    except Exception as e:
        logger.error(f"Error creating database and tables: {e}", exc_info=True)
    finally:
        logger.info("Exiting create_db_and_tables")


def get_db():
    logger.info("Entering get_db")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        logger.info("Exiting get_db")