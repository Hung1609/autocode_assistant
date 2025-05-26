import logging
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Initialize logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database URL
DATABASE_URL = "sqlite:///./todo.db"

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base for declarative models
Base = declarative_base()

# Define the Task model
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    is_complete = Column(Boolean, default=False)

# Function to create the database tables
def create_db_and_tables():
    logger.info("Entering create_db_and_tables")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database and tables created successfully.")
        result = None
    except Exception as e:
        logger.error(f"Error creating database and tables: {e}", exc_info=True)
        raise
    logger.info("Exiting create_db_and_tables")

# Dependency to get the database session
def get_db():
    logger.info("Entering get_db")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        logger.info("Database session closed.")
    logger.info("Exiting get_db")