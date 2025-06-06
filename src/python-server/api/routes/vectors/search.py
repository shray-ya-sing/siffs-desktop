from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
import sys
# Add the current directory to Python path
current_dir = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.append(str(current_dir))
# Now import using relative path from python-server
from api.models.vectors import SearchRequest
from vectors.search.faiss_chunk_retriever import FAISSChunkRetriever
from vectors.dependencies import get_retriever

import logging
# Get logger instance
logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/vectors/search",
    tags=["vectors"],
)

@router.post("/query")
async def search_chunks(
    request: SearchRequest,
    retriever: FAISSChunkRetriever = Depends(get_retriever)
):
    """
    Search for relevant chunks based on a text query.
    """
    logger.info(f"Searching for: '{request.query}' (top_k={request.top_k})")
    
    try:
        # Perform search
        results = retriever.search(
            query=request.query,
            workbook_path=request.workbook_path,
            top_k=request.top_k,
            return_format=request.return_format
        )
        
        return {
            "status": "success",
            "query": request.query,
            "results": results,
            "result_count": len(results),
            "return_format": request.return_format
        }
        
    except Exception as e:
        logger.error(f"Error searching chunks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))