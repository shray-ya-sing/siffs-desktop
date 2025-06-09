from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# -------------------------------------------EXTRACT EXCEL METADATA---------------------------------------------------------------------------------------------
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

# -------------------------------------------COMPRESS METADATA---------------------------------------------------------------------------------------------

class CompressMetadataRequest(BaseModel):
    metadata: dict
    display_values: Optional[dict] = {}

class ChunkMetadataRequest(BaseModel):
    markdown: str
    max_tokens: Optional[int] = 18000

class CompressChunksRequest(BaseModel):
    chunks: List[Dict[str, Any]] = Field(..., description="Array of chunk metadata objects")
    max_cells_per_chunk: Optional[int] = Field(default=1000, description="Maximum cells to process per chunk")
    max_cell_length: Optional[int] = Field(default=200, description="Maximum length of cell content")

# -------------------------------------------AUDIT EXCEL---------------------------------------------------------------------------------------------

class AnalyzeMetadataRequest(BaseModel):
    chunks: List[str]  # Changed from metadata to chunks
    model: Optional[str] = "claude-sonnet-4-20250514" # or claude-3-5-haiku-20241022
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = 8000  # Add this line


class ChunkData(BaseModel):
    """Individual chunk with markdown content and metadata."""
    markdown: str = Field(..., description="Markdown formatted chunk content")
    score: Optional[float] = Field(default=1.0, description="Relevance score from search")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Chunk metadata (workbook, sheet, rows, etc.)")

# -------------------------------------------QA EXCEL---------------------------------------------------------------------------------------------

class QuestionRequest(BaseModel):
    """Request model for Excel Q&A with markdown chunks."""
    chunks: List[ChunkData] = Field(..., description="Array of markdown chunks with metadata")
    question: str = Field(..., description="Question to answer based on the chunks")
    model: Optional[str] = Field(default="claude-sonnet-4-20250514", description="LLM model to use")
    temperature: Optional[float] = Field(default=0.3, description="Temperature for response generation")
    max_tokens: Optional[int] = Field(default=2000, description="Maximum tokens in response")
    include_chunk_sources: Optional[bool] = Field(default=True, description="Include source chunk references in answer")
    chunk_limit: Optional[int] = Field(default=10, description="Maximum number of chunks to process")

class SearchQARequest(BaseModel):
    """Request model for Q&A directly from search results."""
    search_response: Dict[str, Any] = Field(..., description="Response from search API")
    question: str = Field(..., description="Question to answer based on search results")
    model: Optional[str] = Field(default="claude-sonnet-4-20250514", description="LLM model to use")
    temperature: Optional[float] = Field(default=0.3, description="Temperature for response generation")
    max_tokens: Optional[int] = Field(default=2000, description="Maximum tokens in response")
    include_chunk_sources: Optional[bool] = Field(default=True, description="Include source chunk references in answer")

#-------------------------------------------CREATE OR EDIT EXCEL-------------------------------------------

class GenerateMetadataRequest(BaseModel):
    """Request model for generating Excel metadata using LLM."""
    user_request: str = Field(..., description="The user's request for metadata generation")
    model: str = Field(default="claude-sonnet-4-20250514", description="LLM model to use for generation")
    max_tokens: int = Field(default=2000, description="Maximum number of tokens in the response")
    temperature: float = Field(default=0.3, description="Temperature parameter for response generation (0.0 to 1.0)")
    stream: bool = Field(default=False, description="Whether to stream the response")

class GenerateEditMetadataRequest(BaseModel):
    user_request: str
    chunks: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of search result chunks with markdown content and metadata"
    )
    chunk_limit: int = Field(
        default=10,
        description="Maximum number of chunks to process (for safety)"
    )
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 2000
    temperature: float = 0.3
    stream: bool = False


class EditExcelRequest(BaseModel):
    file_path: str
    metadata: dict
    visible: bool = False
    version_id: int

class CreateExcelRequest(BaseModel):
    file_path: str
    metadata: dict
    visible: bool = False
    version_id: int = 1

#-------------------------------------------ACCEPT/ REJECT EDITS-------------------------------------------
class EditActionRequest(BaseModel):
    file_path: str
    version_id: int
    sheet_name: Optional[str] = None
    visible: bool = False
