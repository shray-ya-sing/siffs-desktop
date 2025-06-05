from fastapi import APIRouter, HTTPException
from pathlib import Path
import sys
# Add the current directory to Python path
current_dir = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.append(str(current_dir))
# Now import using relative path from python-server
from api.models.excel import AnalyzeMetadataRequest
from excel.metadata.excel_metadata_processor import ExcelMetadataProcessor
import logging
# Get logger instance
logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/excel",
    tags=["excel-analysis"],
)

#------------------------------------ METADATA ANALYSIS: AUDIT---------------------------------------------
# Analyze chunks with streaming response and rate limiting
@router.post("/api/excel/analyze-chunks")
async def analyze_chunks(request: AnalyzeMetadataRequest):
    if not request.chunks:
        async def error_stream():
            yield "data: " + json.dumps({'error': 'No data provided'}) + "\n\n"
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


            yield f"data: {json.dumps({'chunk': '\nAnalysis complete.'})}\n\n"           
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
@router.post("/api/excel/reset-conversation")
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
@router.get("/api/excel/conversation-info")
async def get_conversation_info():
    """Get current conversation state information"""
    try:
        analyzer = ExcelMetadataAnalyzer()
        info = analyzer.get_conversation_info()
        return info
    except Exception as e:
        logger.error(f"Error getting conversation info: {str(e)}")
        return {"error": str(e)}
