import os
import logging
from dotenv import load_dotenv, find_dotenv

config_logger = logging.getLogger(__name__)

dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
    