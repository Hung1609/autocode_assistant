import logging
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(String, nullable=False)
    is_complete = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Task(id={self.id}, description='{self.description}', is_complete={self.is_complete})>"

if __name__ == "__main__":
    logger.info("Running models.py as main")
    engine = create_engine("sqlite:///./todo.db")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        logger.info("Creating a sample task")
        new_task = Task(description="Sample task", is_complete=False)
        db.add(new_task)
        db.commit()
        logger.info(f"Created task with id: {new_task.id}")

        logger.info("Querying tasks")
        tasks = db.query(Task).all()
        logger.info(f"Found tasks: {tasks}")
    except Exception as e:
        logger.error(f"Error during sample task creation/query: {e}", exc_info=True)
    finally:
        db.close()
        logger.info("Database session closed.")