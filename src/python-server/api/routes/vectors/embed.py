from fastapi import APIRouter, HTTPException
from pathlib import Path
import sys
# Add the current directory to Python path
current_dir = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.append(str(current_dir))
# Now import using relative path from python-server
from api.models.vectors import EmbedChunksRequest
from vectors.embeddings.chunk_embedder import ChunkEmbedder
from vectors.dependencies import get_embedder

import logging
# Get logger instance
logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/vectors/embeddings",
    tags=["vectors"],
)

#------------------------------------ EMBEDDING: SHARED---------------------------------------------
@router.post("/embed-chunks")
async def embed_chunks(request: EmbedChunksRequest):
    """
    Embed chunks of text using sentence transformers.
    """
    logger.info(f"Received request to embed {len(request.chunks)} chunks")
    
    try:
        # Get or create embedder with specified model
        embedder = ChunkEmbedder(model_name=request.model_name)
        
        # Embed chunks
        embeddings, enhanced_chunks = embedder.embed_chunks(
            request.chunks,
            normalize_embeddings=request.normalize
        )
        
        # Convert numpy array to list for JSON serialization
        embeddings_list = embeddings.tolist()
        
        return {
            "status": "success",
            "embeddings": embeddings_list,
            "embedding_dimension": embedder.embedding_dimension,
            "model_used": embedder.model_name,
            "chunk_count": len(embeddings_list)
        }
        
    except Exception as e:
        logger.error(f"Error embedding chunks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
