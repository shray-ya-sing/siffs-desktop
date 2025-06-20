import sys
import os
import warnings

# Set environment variable for subprocesses
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

# Suppress transformers warnings
warnings.filterwarnings("ignore", message=".*Config not found for model.*")
warnings.filterwarnings("ignore", message=".*Something went wrong trying to find the model name.*")
warnings.filterwarnings("ignore", message=".*No checkpoint found for.*")


# Set UTF-8 encoding for all outputs
if sys.platform == "win32":
    import codecs
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    if sys.version_info >= (3, 7) and not getattr(sys, 'frozen', False):
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(errors='replace')
            sys.stderr.reconfigure(errors='replace')
    elif not getattr(sys, 'frozen', False):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')



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
import logging
logger = logging.getLogger(__name__)
logger.info("Starting Python server at entry point asgi.py")

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
        # Configure uvicorn logging
        log_config = uvicorn.config.LOGGING_CONFIG
        log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        log_config["formatters"]["access"]["fmt"] = '%(asctime)s - %(client_addr)s - "%(request_line)s" %(status_code)s'
        
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