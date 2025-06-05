from fastapi import APIRouter, HTTPException
from pathlib import Path
import sys
# Add the current directory to Python path
current_dir = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.append(str(current_dir))
# Now import using relative path from python-server
from api.models.excel import QuestionRequest
from excel.metadata.excel_metadata_qa import ExcelMetadataQA
import logging
# Get logger instance
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/excel",
    tags=["excel-qa"],
)


#------------------------------------ METADATA ANALYSIS: QA---------------------------------------------

@router.post("/qa")
async def answer_question(request: QuestionRequest):
    """
    Answer a question about Excel metadata using multiple chunks with streaming response.
    """
    try:
        # Validate chunk limit
        if len(request.chunks) > request.chunk_limit:
            request.chunks = request.chunks[:request.chunk_limit]
            logger.warning(f"Truncated chunks from {len(request.chunks)} to {request.chunk_limit}")
        
        qa = ExcelMetadataQA()
        
        async def event_generator():
            try:
                # Prepare chunks for QA system
                chunk_texts = []
                chunk_contexts = []
                
                for i, chunk in enumerate(request.chunks):
                    chunk_texts.append(chunk.text)
                    
                    # Build context information for each chunk
                    context = {
                        'index': i,
                        'metadata': chunk.metadata or {},
                        'score': chunk.score
                    }
                    chunk_contexts.append(context)
                
                # Stream the answer with rate limiting
                stream = await qa.answer_question_from_chunks(
                    chunk_texts=chunk_texts,
                    chunk_contexts=chunk_contexts,
                    question=request.question,
                    model=request.model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    include_sources=request.include_chunk_sources,
                    stream=True
                )
                
                # Stream the response chunks
                async for response_chunk in stream:
                    if response_chunk:
                        yield f"data: {json.dumps({'chunk': response_chunk})}\n\n"
                
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

#------------------------------------ ALTERNATIVE: NON-STREAMING VERSION ------------------------------------

@router.post("/qa/sync")
async def answer_question_sync(request: QuestionRequest):
    """
    Answer a question about Excel metadata using multiple chunks (non-streaming).
    """
    try:
        # Validate chunk limit
        if len(request.chunks) > request.chunk_limit:
            request.chunks = request.chunks[:request.chunk_limit]
        
        qa = ExcelMetadataQA()
        
        # Prepare chunks
        chunk_texts = [chunk.text for chunk in request.chunks]
        chunk_contexts = [
            {
                'index': i,
                'metadata': chunk.metadata or {},
                'score': chunk.score
            }
            for i, chunk in enumerate(request.chunks)
        ]
        
        # Get answer
        answer = await qa.answer_question_from_chunks(
            chunk_texts=chunk_texts,
            chunk_contexts=chunk_contexts,
            question=request.question,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            include_sources=request.include_chunk_sources,
            stream=False
        )
        
        return {
            "answer": answer,
            "chunks_used": len(request.chunks),
            "question": request.question
        }
        
    except Exception as e:
        logger.error(f"Error in answer_question_sync endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))