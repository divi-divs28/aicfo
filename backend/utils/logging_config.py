"""
Logging configuration for the application.
Sets up dedicated loggers for chat flow and error tracking.
"""
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent

# Chat flow logger - logs LLM interactions
CHAT_LOG_FILE = ROOT_DIR / 'chat_flow.log'
chat_logger = logging.getLogger('chat_flow')
chat_logger.setLevel(logging.INFO)
chat_file_handler = logging.FileHandler(CHAT_LOG_FILE, encoding='utf-8')
chat_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
chat_logger.addHandler(chat_file_handler)
chat_logger.propagate = False

# Error logger - logs chat-specific errors
ERROR_LOG_FILE = ROOT_DIR / 'chat_error.log'
error_logger = logging.getLogger('chat_error')
error_logger.setLevel(logging.ERROR)
error_file_handler = logging.FileHandler(ERROR_LOG_FILE, encoding='utf-8')
error_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
error_logger.addHandler(error_file_handler)
error_logger.propagate = False

def setup_logging():
    """Initialize logging configuration."""
    # Already configured above, this function can be called to ensure setup
    pass
