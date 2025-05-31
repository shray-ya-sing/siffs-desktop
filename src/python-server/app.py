from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

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
    metadata: str
    model: Optional[str] = "claude-sonnet-4-20250514"
    temperature: Optional[float] = 0.3

# Create FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Python server is running"}

# Example API endpoint
@app.get("/api/example")
async def example_endpoint():
    return {"message": "Hello from FastAPI server!"}

# Excel metadata extraction endpoint
@app.post("/api/excel/extract-metadata")
async def extract_metadata(request: ExtractMetadataRequest):
    try:
        processor = ExcelMetadataProcessor(workbook_path=request.filePath)
        metadata, markdown = processor.process_workbook()
        
        return {
            "status": "success",
            "markdown": markdown,
            "metadata": metadata
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Analyze metadata with streaming response
@app.post("/api/excel/analyze-metadata")
async def analyze_metadata(request: AnalyzeMetadataRequest):
    if not request.metadata:
        async def error_stream():
            yield "data: " + json.dumps({'error': 'No metadata provided'}) + "\n\n"
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
            stream = await analyzer.analyze_metadata(
                model_metadata=request.metadata,
                model=request.model,
                temperature=request.temperature,
                stream=True
            )
            
            async for chunk in stream:
                if chunk:
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
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