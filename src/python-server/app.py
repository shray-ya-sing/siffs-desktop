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

# Import routes
from api.routes.health import router as health_router
from api.routes.excel.metadata import router as excel_metadata_router
from api.routes.excel.analysis import router as excel_analysis_router
from api.routes.excel.qa import router as excel_qa_router
from api.routes.vectors.embed import router as vectors_embed_router
from api.routes.vectors.search import router as vectors_search_router
from api.routes.vectors.store import router as vectors_store_router
from api.routes.excel.editing import router as excel_editing_router


# Create FastAPI app
app = FastAPI(title="Cori API")

@app.on_event("startup")
async def startup_event():
    # Print all registered routes
    for route in app.routes:
        print(f"{route.methods} {route.path}")
        
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

# Include routers
app.include_router(health_router)
app.include_router(excel_metadata_router)
app.include_router(excel_analysis_router)
app.include_router(excel_qa_router)
app.include_router(vectors_embed_router)
app.include_router(vectors_search_router)
app.include_router(vectors_store_router)
app.include_router(excel_editing_router)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Log request details
    body = await request.body()
    print(f"\n=== INCOMING REQUEST ===")
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print(f"Headers: {dict(request.headers)}")
    try:
        print(f"Body: {body.decode()}")
    except:
        print("Could not decode body")
    print("=======================\n")
    
    # Reset body for downstream processing
    request._body = body
    
    try:
        response = await call_next(request)
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        raise
    
    print(f"=== RESPONSE: {response.status_code} ===")
    return response

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 3001))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)