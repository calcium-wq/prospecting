import logging
from datetime import datetime
from modules.config import ERRORS_LOG

def log_error(component: str, error: Exception, context: str = ""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{ts}] [{component}] {context}: {type(error).__name__}: {error}\n"
    with open(ERRORS_LOG, "a") as f:
        f.write(msg)
    logging.error(msg.strip())

def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    return logging.getLogger(__name__)

logger = setup_logger()
