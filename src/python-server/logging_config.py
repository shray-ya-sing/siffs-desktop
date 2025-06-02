import os
import sys
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    """
    Configure root logger with file and console handlers.
    Should be called once at application startup.
    """
    # Create logs directory in a cross-platform way
    if sys.platform == 'win32':
        # On Windows, use AppData/Roaming/Cori/logs
        log_dir = os.path.join(os.environ.get('APPDATA', ''), 'Cori', 'logs')
    else:
        # On Unix-like systems, use ~/.cori/logs
        log_dir = os.path.join(os.path.expanduser('~'), '.cori', 'logs')
    
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'python.log')

    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure root logger
    root_logger.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return log_file
