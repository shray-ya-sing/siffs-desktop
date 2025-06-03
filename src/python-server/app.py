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

# Now import using relative path from python-server
from excel.metadata.excel_metadata_processor import ExcelMetadataProcessor
from excel.metadata.excel_metadata_analyzer import ExcelMetadataAnalyzer

# Pydantic models for request/response validation
class ExtractMetadataRequest(BaseModel):
    filePath: str

class AnalyzeMetadataRequest(BaseModel):
    chunks: List[str]  # Changed from metadata to chunks
    model: Optional[str] = "claude-sonnet-4-20250514" # or claude-3-5-haiku-20241022
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = 8000  # Add this line

class CompressMetadataRequest(BaseModel):
    metadata: dict
    display_values: Optional[dict] = {}

class ChunkMetadataRequest(BaseModel):
    markdown: str
    max_tokens: Optional[int] = 18000

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


# 1. Extract metadata endpoint - returns raw JSON metadata
@app.post("/api/excel/extract-metadata")
async def extract_metadata(request: ExtractMetadataRequest):
    logger.info(f"Received request to extract metadata from: {request.filePath}")
    try:
        processor = ExcelMetadataProcessor(workbook_path=request.filePath)
        
        # Step 1: Extract metadata only
        metadata, display_values = processor._extract_metadata(
            max_rows_per_sheet=getattr(request, 'max_rows_per_sheet', 100),
            max_cols_per_sheet=getattr(request, 'max_cols_per_sheet', 50),
            include_display_values=getattr(request, 'include_display_values', False)
        )
        
        return {
            "status": "success",
            "metadata": metadata,
            "display_values": display_values
        }
            
    except Exception as e:
        logger.error(f"Error extracting metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 2. Compress metadata endpoint - takes JSON metadata, returns markdown
@app.post("/api/excel/compress-metadata")
async def compress_metadata(request: dict):
    logger.info("Received request to compress metadata to markdown")
    try:
        # Extract metadata and display_values from request
        metadata = request.get("metadata")
        display_values = request.get("display_values", {})
        
        if not metadata:
            raise ValueError("No metadata provided")
        
        # Create processor instance for compression
        processor = ExcelMetadataProcessor()
        processor.metadata = metadata
        processor.display_values = display_values
        
        # Step 2: Compress to markdown
        markdown = processor._compress_to_markdown()
        
        return {
            "status": "success",
            "markdown": markdown
        }
            
    except Exception as e:
        logger.error(f"Error compressing metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 3. Chunk metadata endpoint - takes markdown string, returns chunks
@app.post("/api/excel/chunk-metadata")
async def chunk_metadata(request: dict):
    logger.info("Received request to chunk markdown content")
    try:
        # Extract markdown from request
        markdown = request.get("markdown")
        max_tokens = request.get("max_tokens", 18000) # 48K for haiku and 18K for sonnet
        
        if not markdown:
            raise ValueError("No markdown content provided")
        
        # Create processor instance for chunking
        processor = ExcelMetadataProcessor()
        processor.max_tokens_per_chunk = max_tokens
        
        # Step 3: Chunk markdown
        chunks, chunk_info = await processor._chunk_markdown(markdown)
        
        return {
            "status": "success",
            "chunks": chunks,
            "chunk_info": chunk_info
        }
            
    except Exception as e:
        logger.error(f"Error chunking metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Excel metadata extraction endpoint - now returns chunks
@app.post("/api/excel/extract-metadata-legacy")
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

# Analyze chunks with streaming response and rate limiting
@app.post("/api/excel/analyze-chunks")
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
            import json
            # Process each chunk
            for i, chunk in enumerate(request.chunks):
                # Add chunk header information
                chunk_header = f"\n--- ANALYZING CHUNK {i+1}/{len(request.chunks)} ---\n"
                logger.info(f"data: {json.dumps({'chunk': chunk_header})}\n\n")
                
                # Get conversation info before processing
                conv_info = analyzer.get_conversation_info()
                if conv_info['conversation_tokens'] > 0:
                    info_msg = f"Conversation context: {conv_info['conversation_tokens']} tokens, {conv_info['message_count']} messages\n"
                    logger.info(f"data: {json.dumps({'info': info_msg})}\n\n")

                # Analyze this chunk with rate limiting and conversation memory
                stream = await analyzer.analyze_metadata(
                    model_metadata=chunk,
                    model=request.model,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    stream=True
                )
                
                # Stream the response (includes rate limit messages and content)
                async for chunk_response in stream:
                    if chunk_response:
                        yield f"data: {json.dumps({'chunk': chunk_response})}\n\n"
                
                # Add separator between chunks
                if i < len(request.chunks) - 1:
                    separator = f"\n\n--- END OF CHUNK {i+1} ---\n\n"
                    logger.info(f"data: {json.dumps({'chunk': separator})}\n\n")
            
            # Final conversation info
            final_info = analyzer.get_conversation_info()
            final_msg = f"\nAnalysis complete. Total conversation: {final_info['conversation_tokens']} tokens, {final_info['message_count']} messages\n"
            logger.info(f"data: {json.dumps({'info': final_msg})}\n\n")
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Error in analyze_chunks endpoint: {str(e)}")
            logger.error(f"data: {json.dumps({'error': str(e)})}\n\n")
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
    
# Optional: Add endpoint to reset conversation if needed
@app.post("/api/excel/reset-conversation")
async def reset_conversation():
    """Reset the conversation history for fresh analysis"""
    try:
        analyzer = ExcelMetadataAnalyzer()
        analyzer.reset_conversation()
        return {"message": "Conversation history reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting conversation: {str(e)}")
        return {"error": str(e)}

# Optional: Add endpoint to get conversation info
@app.get("/api/excel/conversation-info")
async def get_conversation_info():
    """Get current conversation state information"""
    try:
        analyzer = ExcelMetadataAnalyzer()
        info = analyzer.get_conversation_info()
        return info
    except Exception as e:
        logger.error(f"Error getting conversation info: {str(e)}")
        return {"error": str(e)}


if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 3001))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)