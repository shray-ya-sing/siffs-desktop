from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
import sys
# Add the current directory to Python path
current_dir = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.append(str(current_dir))
# Now import using relative path from python-server
from api.models.excel import ExtractMetadataRequest, CompressMetadataRequest, ChunkMetadataRequest
from excel.metadata.excel_metadata_processor import ExcelMetadataProcessor
import logging
# Get logger instance
logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/excel",
    tags=["excel-metadata"],
    responses={404: {"description": "Not found"}},
)

#------------------------------------ METADATA EXTRACTION: SHARED---------------------------------------------
# 1. Extract metadata endpoint - returns raw JSON metadata
@router.post("/api/excel/extract-metadata")
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
@router.post("/api/excel/compress-metadata")
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
@router.post("/api/excel/chunk-metadata")
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
@router.post("/api/excel/extract-metadata-legacy")
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
