import logging
from logging import StreamHandler

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

@app.get("/health")
def health_check():
    logger.info("Entering health_check with args: , kwargs: ")
    result = {"status": "ok"}
    logger.info(f"Exiting health_check with result: {result}")
    return result

import backend.routes