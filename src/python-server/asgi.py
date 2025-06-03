import os
import sys
import logging
from dotenv import load_dotenv
import uvicorn

# Add the current directory to path for PyInstaller
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    application_path = os.path.dirname(sys.executable)
    sys.path.insert(0, application_path)
else:
    # Running in development
    application_path = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, application_path)

# Import and setup logging configuration first
from logging_config import setup_logging

# Configure logging
log_file = setup_logging()
logger = logging.getLogger(__name__)
logger.info(f"ASGI application logging to file: {log_file}")

# In production, load .env from the same directory as the executable
if getattr(sys, 'frozen', False):
    env_path = os.path.join(os.path.dirname(sys.executable), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
else:
    # In development, load from project root
    env_path = os.path.join(os.path.dirname(os.path.dirname(application_path)), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)

# Import app after environment is set up
from app import app

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 5001))
        host = os.environ.get('HOST', '127.0.0.1')
        workers = int(os.environ.get('WORKERS', 1))
        
        logger.info(f"Starting Uvicorn server on {host}:{port} with {workers} workers")
        logger.info(f"Environment: {os.environ.get('ENV', 'production')}")
        
        uvicorn.run(
            "asgi:app",
            host=host,
            port=port,
            workers=workers,
            log_level="info",
            reload=False,
            proxy_headers=True,
            forwarded_allow_ips='*'
        )
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise