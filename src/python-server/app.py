import os
import sys
import json
from fastapi.responses import JSONResponse
from fastapi import Request
import shutil
from pathlib import Path
import atexit


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

# Create FastAPI app
app = FastAPI(title="Volute API")

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
            # Remove only the files_mappings.json file, if it exists
            file_mappings_path = cache_dir / "files_mappings.json"
            if file_mappings_path.exists() and file_mappings_path.is_file():
                os.unlink(file_mappings_path)
                logger.info(f"Removed file_mappings.json from {cache_dir}")
            else:
                logger.info(f"files_mappings.json does not exist in {cache_dir}, skipping delete")
        else:
            logger.info(f"Cache directory {cache_dir} does not exist, skipping clear")
    except Exception as e:
        logger.error(f"Error clearing metadata cache: {str(e)}")


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
    from api_key_management.handlers.api_key_handler import api_key_handler
    logger.info("Starting up...APIKeyHandler initialized")

    
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


if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 3001))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)