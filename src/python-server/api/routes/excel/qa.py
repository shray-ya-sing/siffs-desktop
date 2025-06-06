from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
from pathlib import Path
import sys
# Add the current directory to Python path
current_dir = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.append(str(current_dir))
# Now import using relative path from python-server
from api.models.excel import QuestionRequest, SearchQARequest
from excel.metadata.excel_metadata_qa import ExcelMetadataQA
import logging
# Get logger instance
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/excel",
    tags=["excel-qa"],
)


#------------------------------------ METADATA ANALYSIS: QA---------------------------------------------

@router.post("/qa/ask")
async def answer_question(request: QuestionRequest):
    """
    Answer a question about Excel metadata using markdown chunks with streaming response.
    """
    try:
        # Validate chunk limit
        if len(request.chunks) > request.chunk_limit:
            request.chunks = request.chunks[:request.chunk_limit]
            logger.warning(f"Truncated chunks from {len(request.chunks)} to {request.chunk_limit}")
        
        qa = ExcelMetadataQA()
        
        async def event_generator():
            try:
                # Convert chunks to search result format expected by LLMQA
                search_results = []
                for i, chunk in enumerate(request.chunks):
                    search_result = {
                        'markdown': chunk.markdown,
                        'score': chunk.score or 1.0,
                        'metadata': chunk.metadata or {},
                        'chunk_index': i
                    }
                    
                    # Add workbook/sheet info if not in metadata
                    if 'workbook' not in search_result['metadata']:
                        search_result['metadata']['workbook'] = 'Unknown'
                    if 'sheet' not in search_result['metadata']:
                        search_result['metadata']['sheet'] = 'Unknown'
                    
                    search_results.append(search_result)
                
                # Get chunk summary for logging
                summary = qa.get_chunk_summary(search_results)
                logger.info(f"Processing {summary['total_chunks']} chunks from {summary['workbooks']}")
                
                # Stream the answer
                stream = await qa.answer_question_from_chunks(
                    search_results=search_results,
                    question=request.question,
                    model=request.model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    include_sources=request.include_chunk_sources,
                    stream=True
                )
                
                # Use the built-in streaming handler from ExcelMetadataQA
                async for chunk in stream:
                    if chunk:
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                        
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Error in answer_question endpoint: {str(e)}")
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
            
    except Exception as e:
        logger.error(f"Error in answer_question endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

#------------------------------------ NON-STREAMING VERSION ------------------------------------

@router.post("/qa/sync")
async def answer_question_sync(request: QuestionRequest):
    """
    Answer a question about Excel metadata using markdown chunks (non-streaming).
    """
    try:
        # Validate chunk limit
        if len(request.chunks) > request.chunk_limit:
            request.chunks = request.chunks[:request.chunk_limit]
        
        qa = ExcelMetadataQA()
        
        # Convert chunks to search result format
        search_results = []
        for i, chunk in enumerate(request.chunks):
            search_results.append({
                'markdown': chunk.markdown,
                'score': chunk.score or 1.0,
                'metadata': chunk.metadata or {},
                'chunk_index': i
            })
        
        # Get answer
        answer = await qa.answer_question_from_chunks(
            search_results=search_results,
            question=request.question,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            include_sources=request.include_chunk_sources,
            stream=False
        )
        
        # Get chunk summary
        summary = qa.get_chunk_summary(search_results)
        
        return {
            "answer": answer,
            "chunks_used": len(request.chunks),
            "question": request.question,
            "chunk_summary": summary
        }
        
    except Exception as e:
        logger.error(f"Error in answer_question_sync endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

#------------------------------------ SEARCH + QA COMBINED ------------------------------------

@router.post("/qa/from-search")
async def answer_from_search(request: SearchQARequest):
    """
    Answer a question directly from search API results.
    """
    try:
        qa = ExcelMetadataQA()
        
        async def event_generator():
            try:
                # Use the convenience method for search responses
                stream = await qa.answer_from_search(
                    search_response=request.search_response,
                    question=request.question,
                    model=request.model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    include_sources=request.include_chunk_sources,
                    stream=True
                )
                
                async for chunk in stream:
                    if chunk:
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                        
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Error in answer_from_search: {str(e)}")
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
            
    except Exception as e:
        logger.error(f"Error in answer_from_search endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

#------------------------------------ CONVERSATION MANAGEMENT ------------------------------------

@router.post("/qa/reset-conversation")
async def reset_conversation():
    """
    Reset the conversation history for a fresh Q&A session.
    """
    try:
        qa = ExcelMetadataQA()
        qa.reset_conversation()
        
        return {
            "status": "success",
            "message": "Conversation history reset successfully"
        }
        
    except Exception as e:
        logger.error(f"Error resetting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/qa/conversation-info")
async def get_conversation_info():
    """
    Get information about the current conversation state.
    """
    try:
        qa = ExcelMetadataQA()
        info = qa.get_conversation_info()
        
        return {
            "status": "success",
            "conversation_info": info
        }
        
    except Exception as e:
        logger.error(f"Error getting conversation info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))