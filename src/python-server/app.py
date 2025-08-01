import os
import sys
import json
from fastapi.responses import JSONResponse
from fastapi import Request
import shutil
from pathlib import Path
import atexit
from cache_management import initialize_cache_service, shutdown_cache_service


# Set UTF-8 encoding for all outputs
if sys.platform == "win32":
    if sys.version_info >= (3, 7):
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(errors='replace')
            sys.stderr.reconfigure(errors='replace')
    else:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Set environment variable for subprocesses
os.environ['PYTHONIOENCODING'] = 'utf-8'


import logging

# Import and setup logging configuration
from logging_config import setup_logging

# Configure logging
try:
    log_file = setup_logging()
    logger = logging.getLogger(__name__)
    logger.info(f"Application logging to file: {log_file}")
except Exception as e:
    # Fallback basic config if setup fails
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to setup logging: {e}")

try:
    import sentry_sdk
    sentry_sdk.init(
        dsn="https://be283732085f0e4933040ef4af259199@o4509679278686208.ingest.us.sentry.io/4509679595487232",
        traces_sample_rate=1.0,
        send_default_pii=True
    )
except Exception as e:
    logger.error(f"Failed to initialize Sentry: {e}")

from dotenv import load_dotenv

# Get the project root directory (where .env is located)
project_root = Path(__file__).parent.parent.parent.absolute()

# Load environment variables from the .env file in the root
env_path = project_root / '.env'
load_dotenv(env_path)



from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json
from typing import Dict, Any, Optional, List

# Add the current directory to Python path
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

# websocket manager
from api.websocket_manager import manager
from core.events import event_bus
from fastapi import WebSocket, WebSocketDisconnect

# Import routers
from api.routes.cache import router as cache_router

# Create FastAPI app
app = FastAPI(title="Volute API")

# Include routers
app.include_router(cache_router)

def clear_metadata_cache():
    """Clear the metadata cache directory"""
    try:
        cache_dir = Path(__file__).parent / "metadata" / "_cache"
        if cache_dir.exists() and cache_dir.is_dir():
            # Remove all files in the cache directory
            for item in cache_dir.glob('*'):
                if item.is_file():
                    os.unlink(item)
                elif item.is_dir():
                    shutil.rmtree(item)
            logger.info(f"Cleared metadata cache at {cache_dir}")
            cache_dir = Path(__file__).parent / "metadata" / "__cache"
        if cache_dir.exists() and cache_dir.is_dir():
            # Files to preserve during cache clearing
            preserved_files = ["user_api_keys.json", "global_powerpoint_rules.json"]
            
            # Remove all files except preserved ones
            for item in cache_dir.glob('*'):
                if item.is_file() and item.name not in preserved_files:
                    os.unlink(item)
                    logger.info(f"Removed {item.name} from {cache_dir}")
                elif item.is_dir():
                    shutil.rmtree(item)
                    logger.info(f"Removed directory {item.name} from {cache_dir}")
            
            # Log preserved files
            for preserved_file in preserved_files:
                preserved_path = cache_dir / preserved_file
                if preserved_path.exists():
                    logger.info(f"Preserved {preserved_file} in {cache_dir}")
        else:
            logger.info(f"Cache directory {cache_dir} does not exist, skipping clear")
    except Exception as e:
        logger.error(f"Error clearing metadata cache: {str(e)}")

async def periodic_cleanup():
    """Periodic cleanup of old requests"""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            from ai_services.orchestration.cancellation_manager import cancellation_manager
            cleaned_count = cancellation_manager.cleanup_old_requests(max_age_minutes=60)
            if cleaned_count > 0:
                logger.info(f"Periodic cleanup removed {cleaned_count} old requests")
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying


@app.on_event("startup")
async def startup_event():
    try:
        clear_metadata_cache()
    except Exception as e:
        logger.error(f"Error clearing metadata cache: {str(e)}")
    from excel.orchestration.excel_orchestrator import ExcelOrchestrator
    logger.info("Starting up...Excel orchestrator initialized")
    from powerpoint.orchestration.powerpoint_orchestrator import PowerPointOrchestrator
    logger.info("Starting up...PowerPoint orchestrator initialized")
    from ai_services.orchestration.supervisor_agent_orchestrator import SupervisorAgentOrchestrator
    logger.info("Starting up...Supervisor orchestrator initialized")
    from excel.metadata.extraction.event_handlers.metadata_cache_handler import MetadataCacheHandler
    logger.info("Starting up...MetadataCacheHandler initialized")
    from excel.metadata.extraction.event_handlers.chunk_extractor_handler import ChunkExtractorHandler
    logger.info("Starting up...ChunkExtractorHandler initialized")
    from powerpoint.metadata.extraction.event_handlers.powerpoint_cache_handler import PowerPointCacheHandler
    logger.info("Starting up...PowerPointCacheHandler initialized")
    from pdf.orchestration.pdf_orchestrator import PDFOrchestrator
    logger.info("Starting up...PDF orchestrator initialized")
    from pdf.content.extraction.event_handlers.pdf_cache_handler import PDFCacheHandler
    logger.info("Starting up...PDFCacheHandler initialized")
    from pdf.content.extraction.event_handlers.pdf_content_handler import PDFContentHandler
    logger.info("Starting up...PDFContentHandler initialized")
    from word.orchestration.word_orchestrator import WordOrchestrator
    logger.info("Starting up...Word orchestrator initialized")
    from word.metadata.extraction.event_handlers.word_cache_handler import WordCacheHandler
    logger.info("Starting up...WordCacheHandler initialized")
    from api_key_management.handlers.api_key_handler import api_key_handler
    logger.info("Starting up...APIKeyHandler initialized")
    from powerpoint.rules.powerpoint_rules_handler import powerpoint_rules_handler
    logger.info("Starting up...PowerPointRulesHandler initialized")
    
    # Initialize cache service
    try:
        server_dir = Path(__file__).parent
        cache_service = initialize_cache_service(server_dir)
        logger.info("Starting up...Cache service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize cache service: {e}")
    
    # Initialize cancellation manager and start cleanup task
    try:
        from ai_services.orchestration.cancellation_manager import cancellation_manager
        asyncio.create_task(periodic_cleanup())
        logger.info("Starting up...Cancellation manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize cancellation manager: {e}")

    
    # Print all registered routes
    for route in app.routes:
        if hasattr(route, 'methods'):
            print(f"HTTP {route.methods} {route.path}")
        else:
            # This is likely a WebSocket route
            print(f"WebSocket {route.path}")
        
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log the full error
    logging.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    # Return a clean error response
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred"}
    )


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add WebSocket endpoint after your existing routers
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str = None):
    """Main WebSocket endpoint"""
    # Accept connection
    client_id = await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive messages
            data = await websocket.receive_json()

            manager.update_last_seen(client_id)

            if data.get("type") == "pong":
                logger.debug(f"Received pong from {client_id}")
                continue

            event_message = {
                "client_id": client_id,
                "message": data
            }
     
            # Emit event for received message
            await event_bus.emit(
                "ws_message_received",
                {
                    "client_id": client_id,
                    "message": data
                }
            )
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        manager.disconnect(client_id)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Log request details
    body = await request.body()
    logger.info(f"\n=== INCOMING REQUEST ===")
    logger.info(f"Method: {request.method}")
    logger.info(f"URL: {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")
    try:
        logger.info(f"Body: {body.decode()}")
    except:
        logger.info("Could not decode body")
    logger.info("=======================\n")
    
    # Reset body for downstream processing
    request._body = body
    
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise
    
    logger.info(f"=== RESPONSE: {response.status_code} ===")
    return response


# Register cleanup function to run on exit
def cleanup_on_exit():
    """Cleanup function to run on application exit"""
    try:
        shutdown_cache_service()
        logger.info("Cache service shut down successfully")
    except Exception as e:
        logger.error(f"Error shutting down cache service: {e}")

atexit.register(cleanup_on_exit)

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 3001))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
