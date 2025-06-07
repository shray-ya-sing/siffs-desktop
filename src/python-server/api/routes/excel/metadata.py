from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pathlib import Path
import sys
# Add the current directory to Python path
current_dir = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.append(str(current_dir))
# Now import using relative path from python-server
from api.models.excel import ExtractMetadataRequest, CompressMetadataRequest, ChunkMetadataRequest, ExtractMetadataChunksRequest, CompressChunksRequest, GenerateMetadataRequest
from excel.metadata.excel_metadata_processor import ExcelMetadataProcessor
from excel.metadata.compression.text_compressor import JsonTextCompressor
from excel.metadata.generation.llm_metadata_generator import LLMMetadataGenerator
from excel.metadata.parsing.llm_metadata_parser import LLMMetadataParser

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
@router.post("/extract-metadata")
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

# ALT: Extract metadata chunks endpoint - returns array of chunk objects
@router.post("/extract-metadata-chunks")
async def extract_metadata_chunks(request: ExtractMetadataChunksRequest):
    """
    Extract metadata from Excel file as an array of chunk objects.
    Each chunk contains metadata for a specific row range.
    """
    logger.info(f"Received request to extract metadata chunks from: {request.filePath}")
    logger.info(f"Chunk configuration: {request.rows_per_chunk} rows per chunk")
    
    try:
        processor = ExcelMetadataProcessor(workbook_path=request.filePath)
        
        
        # Extract chunks only
        chunks = processor._extract_metadata_chunks(
            rows_per_chunk=request.rows_per_chunk,
            max_cols_per_sheet=request.max_cols_per_sheet,
            include_dependencies=request.include_dependencies,
            include_empty_chunks=request.include_empty_chunks
        )
        
        return {
            "status": "success",
            "chunks": chunks,
            "chunkCount": len(chunks)
        }
            
    except Exception as e:
        logger.error(f"Error extracting metadata chunks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

#------------------------------------ METADATA COMPRESSION: SHARED---------------------------------------------
# 2. Compress metadata endpoint - takes JSON metadata, returns markdown
@router.post("/compress-metadata")
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

@router.post("/compress-chunks")
async def compress_chunks(request: CompressChunksRequest):
    """
    Compress an array of chunk metadata objects into natural language text and markdown.
    
    Args:
        request: Contains array of chunk metadata objects
        
    Returns:
        Array of compressed text strings, one per chunk
    """
    logger.info(f"Received request to compress {len(request.chunks)} chunks to text")
    
    try:
        # Validate chunks
        if not request.chunks:
            raise ValueError("No chunks provided")
        
        # Create processor instance for compression
        processor = ExcelMetadataProcessor()
        
        # Set the chunks on the processor
        processor.metadata_chunks = request.chunks
        
        # Configure compressor if custom settings provided
        if request.max_cells_per_chunk or request.max_cell_length:
            processor.text_compressor = JsonTextCompressor(
                max_cells_per_sheet=request.max_cells_per_chunk,
                max_cell_length=request.max_cell_length
            )
        
        # Compress chunks to text
        compressed_texts = processor._compress_chunks_to_text()
        compressed_markdown_texts = processor._compress_chunks_to_markdown()
        
        # Calculate statistics
        total_chars = sum(len(text) for text in compressed_texts)
        avg_chars = total_chars / len(compressed_texts) if compressed_texts else 0
        
        return {
            "status": "success",
            "compressed_texts": compressed_texts,
            "compressed_markdown_texts": compressed_markdown_texts,
            "chunk_count": len(compressed_texts),
            "statistics": {
                "total_characters": total_chars,
                "average_characters_per_chunk": round(avg_chars),
                "chunks_processed": len(request.chunks)
            }
        }
            
    except Exception as e:
        logger.error(f"Error compressing chunks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Alternative endpoint with streaming for large chunk arrays
@router.post("/compress-chunks-stream")
async def compress_chunks_stream(request: CompressChunksRequest):
    """
    Compress chunks with streaming response for large arrays.
    Streams each compressed chunk as it's processed.
    """
    logger.info(f"Received request to stream compress {len(request.chunks)} chunks")
    
    try:
        if not request.chunks:
            raise ValueError("No chunks provided")
        
        async def text_generator():
            try:
                # Start streaming
                yield f"data: {json.dumps({'status': 'started', 'total_chunks': len(request.chunks)})}\n\n"
                
                # Create processor
                processor = ExcelMetadataProcessor()
                
                # Configure compressor
                if request.max_cells_per_chunk or request.max_cell_length:
                    processor.compressor = JsonTextCompressor(
                        max_cells_per_sheet=request.max_cells_per_chunk,
                        max_cell_length=request.max_cell_length
                    )
                
                compressed_texts = []
                
                # Process chunks one by one for streaming
                for i, chunk in enumerate(request.chunks):
                    # Compress single chunk
                    processor.metadata_chunks = [chunk]
                    chunk_texts = processor._compress_chunks_to_text()
                    
                    if chunk_texts:
                        compressed_text = chunk_texts[0]
                        compressed_texts.append(compressed_text)
                        
                        # Stream the compressed chunk
                        chunk_data = {
                            'type': 'compressed_chunk',
                            'index': i,
                            'total': len(request.chunks),
                            'text': compressed_text,
                            'text_length': len(compressed_text)
                        }
                        yield f"data: {json.dumps(chunk_data)}\n\n"
                    
                    # Add delay for large batches
                    if i % 10 == 0 and i > 0:
                        await asyncio.sleep(0.1)
                
                # Send completion with statistics
                total_chars = sum(len(text) for text in compressed_texts)
                completion_data = {
                    'status': 'completed',
                    'total_chunks': len(compressed_texts),
                    'total_characters': total_chars,
                    'average_characters': round(total_chars / len(compressed_texts)) if compressed_texts else 0
                }
                yield f"data: {json.dumps(completion_data)}\n\n"
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Error in chunk compression streaming: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            text_generator(),
            media_type="text/event-stream",
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        logger.error(f"Error in compress chunks streaming endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




#---------------------------------------------CHUNKING: SHARED----------------------
# 3. Chunk metadata endpoint - takes markdown string, returns chunks
@router.post("/chunk-metadata")
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
@router.post("/extract-metadata-legacy")
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

#-------------------------------------------GENERATION-------------------------------------------

# Excel metadata generation endpoint
@router.post("/generate-metadata")
async def generate_metadata(request: GenerateMetadataRequest):
    """
    Generate metadata for Excel using LLM based on user request.
    
    Args:
        request: GenerateMetadataRequest containing:
            - user_request: The user's request for metadata generation
            - model: LLM model to use (default: claude-sonnet-4-20250514)
            - max_tokens: Maximum tokens in response (default: 2000)
            - temperature: Temperature for response generation (default: 0.3)
            - stream: Whether to stream the response (default: False)
    """
    logger.info(f"Received request to generate metadata with model: {request.model}")
    
    try:
        # Initialize the LLM metadata generator
        metadata_generator = LLMMetadataGenerator()
        
        # Generate metadata using the LLM
        result = await metadata_generator.generate_metadata_from_request(
            user_request=request.user_request,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=request.stream
        )
        
        if request.stream:
            # For streaming responses, return the async generator directly
            async def stream_response():
                try:
                    async for chunk in result:
                        yield chunk
                except Exception as e:
                    logger.error(f"Error during streaming: {str(e)}")
                    yield f"Error: {str(e)}"
            
            return StreamingResponse(stream_response(), media_type="text/event-stream")
        else:
            # For non-streaming responses, return a structured response
            return {
                "status": "success",
                "result": result,
                "model": request.model
            }
            
    except Exception as e:
        logger.error(f"Error generating metadata: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate metadata: {str(e)}"
        )



#-------------------------------------------PARSING-------------------------------------------

# Excel metadata parsing endpoint
@router.post("/parse-metadata")
async def parse_metadata(request: dict):
    """
    Parse Excel metadata string into structured format.
    
    Request body:
    {
        "metadata": "worksheet name=\"Sheet1\" | cell=\"A1\" | formula=\"Test\" | bold=true ...",
        "strict": true  # Optional, defaults to True
    }
    """
    logger.info("Received request to parse metadata")
    
    try:
        # Extract and validate request data
        metadata = request.get("metadata")
        strict = request.get("strict", True)  # Default to strict mode
        
        if not metadata or not isinstance(metadata, str):
            raise HTTPException(
                status_code=400,
                detail="Metadata must be a non-empty string"
            )

        # Parse the metadata
        try:
            parsed_data = LLMMetadataParser.parse(metadata, strict=strict)
            
            if not parsed_data:
                logger.warning("No valid metadata could be parsed from the input")
                return {
                    "status": "success",
                    "data": {},
                    "warnings": ["No valid metadata found in input"],
                    "valid": False
                }
                
            return {
                "status": "success",
                "data": parsed_data,
                "valid": True
            }
            
        except ValueError as ve:
            # Handle validation errors from the parser
            logger.warning(f"Validation error parsing metadata: {str(ve)}")
            raise HTTPException(
                status_code=422,  # Unprocessable Entity
                detail={
                    "error": "Metadata validation failed",
                    "message": str(ve),
                    "valid": False
                }
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        # Log the full error for debugging
        logger.error(f"Unexpected error parsing metadata: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred while parsing metadata",
                "valid": False
            }
        )