import logging
import os
import config
from datetime import datetime

# Setup Log Dir
log_dir = os.path.join(config.BASE_DIR, "logs")
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, "session.log")

# Configure Singleton Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode='a', encoding='utf-8'),
        logging.StreamHandler() # Also print to console
    ]
)

logger = logging.getLogger("WhisperFlow")

def log(msg, level="info"):
    if level == "info":
        logger.info(msg)
    elif level == "error":
        logger.error(msg)
    elif level == "warning":
        logger.warning(msg)
    elif level == "debug":
        logger.debug(msg)
