from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import sys
import asyncio
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Import and setup logging configuration
from logging_config import setup_logging

# Configure logging
log_file = setup_logging()
logger = logging.getLogger(__name__)
logger.info(f"Application logging to file: {log_file}")

# Get the project root directory (where .env is located)
project_root = Path(__file__).parent.parent.parent.absolute()

# Load environment variables from the .env file in the root
env_path = project_root / '.env'
load_dotenv(env_path)

# Add the current directory to Python path
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

# Import routes
from api.routes.health import router as health_router
from api.routes.excel.metadata import router as excel_metadata_router
from api.routes.excel.analysis import router as excel_analysis_router
from api.routes.excel.qa import router as excel_qa_router


# Create FastAPI app
app = FastAPI(title="Cori API")

@app.on_event("startup")
async def startup_event():
    # Print all registered routes
    for route in app.routes:
        print(f"{route.methods} {route.path}")

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

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 3001))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)