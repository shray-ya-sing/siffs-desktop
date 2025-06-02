from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import sys
import asyncio
import logging
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

# Now import using relative path from python-server
from excel.metadata.excel_metadata_processor import ExcelMetadataProcessor
from excel.metadata.excel_metadata_analyzer import ExcelMetadataAnalyzer

# Pydantic models for request/response validation
class ExtractMetadataRequest(BaseModel):
    filePath: str

class AnalyzeMetadataRequest(BaseModel):
    chunks: List[str]  # Changed from metadata to chunks
    model: Optional[str] = "claude-sonnet-4-20250514"
    temperature: Optional[float] = 0.3

# Create FastAPI app
app = FastAPI()

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

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

# Simple health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Python server is running"}

# Example API endpoint
@app.get("/api/example")
async def example_endpoint():
    return {"message": "Hello from FastAPI server!"}

@app.get("/api/test-logging")
async def test_logging():
    # Test logging at different levels
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    return {"message": "Logging test complete"}

# Excel metadata extraction endpoint - now returns chunks
@app.post("/api/excel/extract-metadata")
async def extract_metadata(request: ExtractMetadataRequest):
    logger.info(f"Received request to process: {request.filePath}")
    try:
        processor = ExcelMetadataProcessor(workbook_path=request.filePath)
        
        # Process workbook and get chunks
        result = await processor.process_workbook()
        metadata, markdown, chunks, chunk_info = result
        
        return {
            "status": "success",
            "markdown": markdown,
            "metadata": metadata,
            "chunks": chunks,
            "chunk_info": chunk_info
        }
            
    except Exception as e:
        logger.error(f"Error processing workbook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Analyze chunks with streaming response
@app.post("/api/excel/analyze-chunks")  # Changed endpoint name
async def analyze_chunks(request: AnalyzeMetadataRequest):
    if not request.chunks:
        async def error_stream():
            yield "data: " + json.dumps({'error': 'No chunks provided'}) + "\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )

    analyzer = ExcelMetadataAnalyzer()
    
    async def event_generator():
        try:
            # Process each chunk
            for i, chunk in enumerate(request.chunks):
                # Add chunk header information
                chunk_header = f"\n--- ANALYZING CHUNK {i+1}/{len(request.chunks)} ---\n"
                yield f"data: {json.dumps({'chunk': chunk_header})}\n\n"
                
                # Analyze this chunk
                stream = await analyzer.analyze_metadata(
                    model_metadata=chunk,
                    model=request.model,
                    temperature=request.temperature,
                    stream=True
                )
                
                async for chunk_response in stream:
                    if chunk_response:
                        yield f"data: {json.dumps({'chunk': chunk_response})}\n\n"
                
                # Add separator between chunks
                if i < len(request.chunks) - 1:
                    separator = f"\n\n--- END OF CHUNK {i+1} ---\n\n"
                    yield f"data: {json.dumps({'chunk': separator})}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )



if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 3001))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)