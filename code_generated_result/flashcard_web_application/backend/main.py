import logging
import logging.handlers
import json
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Configure logging
def setup_logger():
    """Sets up logging configuration for the application."""
    log_level = logging.DEBUG
    log_file = "logs/app.log"
    max_bytes = 10 * 1024 * 1024  # 10MB
    backup_count = 5

    # Define a custom JSON formatter
    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            """Formats a log record as a JSON string."""
            log_record = {
                "timestamp": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "logger_name": record.name,
                "message": record.getMessage(),
                "pathname": record.pathname,
                "funcName": record.funcName,
                "lineno": record.lineno,
            }

            # Include exception info if available
            if record.exc_info:
                log_record["exc_info"] = self.formatException(record.exc_info)

            return json.dumps(log_record)

    # Create a rotating file handler
    rotating_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count
    )
    json_formatter = JsonFormatter()
    rotating_handler.setFormatter(json_formatter)

    # Create a stream handler for console output
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    stream_handler.setFormatter(stream_formatter)

    # Configure the root logger
    logging.basicConfig(level=log_level, handlers=[rotating_handler, stream_handler])

setup_logger()

logger = logging.getLogger(__name__)

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from backend.routers import flashcards, reviews

app.include_router(flashcards.router)
app.include_router(reviews.router)

# Mount the frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")