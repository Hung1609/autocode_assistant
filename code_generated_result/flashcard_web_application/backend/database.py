import logging
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func

logger = logging.getLogger(__name__)

DATABASE_URL = "sqlite:///./flashcard.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True)
    front_text = Column(String, nullable=False)
    back_text = Column(String, nullable=False)

    reviews = relationship("Review", back_populates="flashcard")

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    flashcard_id = Column(Integer, ForeignKey("flashcards.id"), nullable=False)
    correct = Column(Boolean, nullable=False)
    review_timestamp = Column(DateTime(timezone=True), server_default=func.now())

    flashcard = relationship("Flashcard", back_populates="reviews")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()