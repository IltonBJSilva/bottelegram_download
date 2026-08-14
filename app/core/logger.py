import logging
import sys
from app.core.config import settings

def setup_logger():
    logger = logging.getLogger("ingestor")
    logger.setLevel(settings.LOG_LEVEL.upper())
    
    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    return logger

logger = setup_logger()
