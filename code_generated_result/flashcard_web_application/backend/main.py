import logging
import logging.handlers
import json
import contextvars
import uuid
import sys

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


# Attempt to import python-json-logger, provide fallback if it fails
try:
    from pythonjsonlogger import jsonlogger
    has_json_logger = True
except ImportError:
    has_json_logger = False

# Custom JSON Formatter
class CustomJsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger_name': record.name,
            'message': record.getMessage(),
            'pathname': record.pathname,
            'funcName': record.funcName,
            'lineno': record.lineno
        }

        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id

        if record.exc_info:
            log_record['exc_info'] = self.formatException(record.exc_info)
        return json.dumps(log_record)


# Request ID Context Variable
request_id_ctx = contextvars.ContextVar("request_id")


# Logging Filter to add request_id to each log record
class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_ctx.get()
        return True


# FastAPI Middleware to generate and store Request ID
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        try:
            response: Response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        return response


# Configure Logging
def setup_logging():
    log_dir = "logs"  # Relative to the project root
    import os
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "app.log")
    max_bytes = 10 * 1024 * 1024  # 10MB
    backup_count = 5

    # Configure RotatingFileHandler
    rotating_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf8"
    )

    # Set formatter for RotatingFileHandler
    if has_json_logger:
        formatter = jsonlogger.JsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s %(pathname)s %(funcName)s %(lineno)d')
    else:
        formatter = CustomJsonFormatter()  # Use custom formatter if python-json-logger is not available
    rotating_handler.setFormatter(formatter)

    # Configure StreamHandler (console output)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    stream_handler.setFormatter(stream_formatter)

    # Configure Root Logger
    logging.basicConfig(level=logging.DEBUG, handlers=[rotating_handler, stream_handler])

    # Add Request ID Filter to the root logger
    root_logger = logging.getLogger()
    root_logger.addFilter(RequestIDFilter())

    return logging.getLogger(__name__)


# Initialize FastAPI
app = FastAPI()

# Setup Logging
logger = setup_logging()

# Add Request ID Middleware
app.add_middleware(RequestIDMiddleware)

# Mount Static Files (Frontend)
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Outgoing response: {response.status_code} for {request.method} {request.url.path}")
    return response

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}