import logging
import logging.handlers
import json
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Configure logging
def create_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # JSON Formatter
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_record = {
                "timestamp": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "logger_name": record.name,
                "message": record.getMessage(),
                "pathname": record.pathname,
                "funcName": record.funcName,
                "lineno": record.lineno,
            }
            if record.exc_info:
                log_record["exc_info"] = self.formatException(record.exc_info)
            return json.dumps(log_record)

    # Rotating File Handler
    rotating_handler = logging.handlers.RotatingFileHandler(
        "logs/app.log", maxBytes=10*1024*1024, backupCount=5
    )
    json_formatter = JsonFormatter()
    rotating_handler.setFormatter(json_formatter)
    logger.addHandler(rotating_handler)

    # Stream Handler (Console)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)

    return logger

logger = create_logger()

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    logger.info("Health check endpoint hit")
    return {"status": "ok"}

# Mount the frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")