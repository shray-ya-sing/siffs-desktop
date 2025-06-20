import os
import sys
import json
from fastapi.responses import JSONResponse
from fastapi import Request

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

from pathlib import Path
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

@app.on_event("startup")
async def startup_event():
    from excel.orchestration.excel_orchestrator import ExcelOrchestrator
    logger.info("Starting up...Excel orchestrator initialized")
    from ai_services.orchestration.prebuilt_agent_orchestrator import PrebuiltAgentOrchestrator
    logger.info("Starting up...PrebuiltAgent orchestrator initialized")
    from excel.metadata.extraction.event_handlers.metadata_cache_handler import MetadataCacheHandler
    logger.info("Starting up...MetadataCacheHandler initialized")
    from excel.metadata.extraction.event_handlers.chunk_extractor_handler import ChunkExtractorHandler
    logger.info("Starting up...ChunkExtractorHandler initialized")
    from excel.metadata.compression.event_handlers.markdown_compressor_handler import MarkdownCompressorHandler
    logger.info("Starting up...MarkdownCompressorHandler initialized")
    from excel.metadata.storage.event_handlers.storage_handler import StorageHandler
    logger.info("Starting up...StorageHandler initialized")    
    from vectors.embeddings.event_handler.chunk_embedder_handler import ChunkEmbedderHandler
    logger.info("Starting up...ChunkEmbedderHandler initialized")    
    from vectors.store.event_handlers.embedding_storage_handler import EmbeddingStorageHandler
    logger.info("Starting up...EmbeddingStorageHandler initialized")
    
    
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