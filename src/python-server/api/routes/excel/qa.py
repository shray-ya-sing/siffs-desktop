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

@router.post("/api/excel/qa")
async def answer_question(request: QuestionRequest):
    """
    Answer a question about Excel metadata with streaming response.
    """
    try:
        qa = ExcelMetadataQA()
        
        async def event_generator():
            try:
                # Stream the answer with rate limiting
                stream = await qa.answer_question(
                    metadata=request.metadata,
                    question=request.question,
                    model=request.model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    stream=True
                )
                
                # Stream the response chunks
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