import logging
import logging.handlers
import json
import contextvars
import uuid
import os

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


# Attempt to import python-json-logger and handle ImportError gracefully
try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False

# Define a custom JSON formatter
class CustomJsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger_name': record.name,
            'message': record.getMessage(),
            'pathname': record.pathname,
            'funcName': record.funcName,
            'lineno': record.lineno,
        }

        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id

        if record.exc_info:
            log_record['exc_info'] = self.formatException(record.exc_info)

        return json.dumps(log_record)


# Configure logging
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Instantiate the FastAPI application
app = FastAPI()

# Request ID context
request_id_ctx = contextvars.ContextVar("request_id")


# Request ID Middleware
class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request_id_ctx.set(request_id)
        try:
            response: Response = await call_next(request)
        finally:
            request_id_ctx.reset()
        return response


# Logging Filter to add request_id to log records
class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_ctx.get()
        return True


# Logging Configuration
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
if HAS_JSON_LOGGER:
    try:
        log_formatter_json = jsonlogger.JsonFormatter()
    except Exception as e:
        log_formatter_json = CustomJsonFormatter()
else:
    log_formatter_json = CustomJsonFormatter()

log_handler = logging.handlers.RotatingFileHandler(
    os.path.join(LOG_DIR, "app.log"),
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding="utf8",
)
log_handler.setFormatter(log_formatter_json)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_formatter)

logging.basicConfig(level=logging.DEBUG, handlers=[log_handler, stream_handler])

logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())

# Mount the frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

# Add Request ID Middleware
app.add_middleware(RequestIdMiddleware)

@app.get("/api/healthcheck")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)