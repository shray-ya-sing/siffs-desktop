from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# Pydantic models for request/response validation
class ExtractMetadataRequest(BaseModel):
    filePath: str

class ExtractMetadataChunksRequest(BaseModel):
    filePath: str = Field(..., description="Path to the Excel file")
    rows_per_chunk: Optional[int] = Field(default=10, description="Number of rows per chunk")
    max_cols_per_sheet: Optional[int] = Field(default=50, description="Maximum columns to extract per sheet")
    include_dependencies: Optional[bool] = Field(default=True, description="Whether to include dependency analysis")
    include_empty_chunks: Optional[bool] = Field(default=False, description="Whether to include chunks with no data")
    include_summary: Optional[bool] = Field(default=False, description="Whether to include a summary object")

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
    """Request model for Excel Q&A with multiple metadata chunks."""
    chunks: List[str] = Field(..., description="Array of metadata chunks to analyze")
    question: str = Field(..., description="Question to answer based on the chunks")
    model: Optional[str] = Field(default="claude-sonnet-4-20250514", description="LLM model to use")
    temperature: Optional[float] = Field(default=0.3, description="Temperature for response generation")
    max_tokens: Optional[int] = Field(default=2000, description="Maximum tokens in response")
    include_chunk_sources: Optional[bool] = Field(default=True, description="Include source chunk references in answer")
    chunk_limit: Optional[int] = Field(default=10, description="Maximum number of chunks to process")

class CompressChunksRequest(BaseModel):
    chunks: List[Dict[str, Any]] = Field(..., description="Array of chunk metadata objects")
    max_cells_per_chunk: Optional[int] = Field(default=1000, description="Maximum cells to process per chunk")
    max_cell_length: Optional[int] = Field(default=200, description="Maximum length of cell content")
