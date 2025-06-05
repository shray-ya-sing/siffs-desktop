from pydantic import BaseModel
from typing import Optional, List, Dict, Any

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

class QuestionRequest(BaseModel):
    metadata: str
    question: str
    model: Optional[str] = "claude-sonnet-4-20250514"
    temperature: Optional[float] = 0.3
    max_tokens: Optional[int] = 2000