from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
import sys
# Add the current directory to Python path
current_dir = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.append(str(current_dir))
# Now import using relative path from python-server
from vectors.store.embedding_storage import EmbeddingStorage
from api.models.vectors import StoreEmbeddingsRequest, StorePrecomputedEmbeddingsRequest
from vectors.dependencies import get_storage
from vectors.embeddings.chunk_embedder import ChunkEmbedder
import logging
# Get logger instance
logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/vectors/storage",
    tags=["vectors"],
)


@router.post("/embed-and-store-chunks")
async def embed_and_store_chunks(
    request: StoreEmbeddingsRequest,
    storage: EmbeddingStorage = Depends(get_storage)
):
    """
    Embed and store chunks for a workbook.
    """
    logger.info(f"Embedding and storing workbook: {request.workbook_path}")
    
    try:
        # First embed the chunks
        embedder = ChunkEmbedder(model_name=request.embedding_model)
        embeddings, enhanced_chunks = embedder.embed_chunks(request.chunks)
        
        # Store in database
        workbook_id , version_id = storage.add_workbook_embeddings(
            workbook_path=request.workbook_path,
            embeddings=embeddings,
            chunks=enhanced_chunks,
            embedding_model=request.embedding_model,
            create_new_version=request.create_new_version
        )
        
        return {
            "status": "success",
            "workbook_id": workbook_id,
            "version_id": version_id,
            "chunks_stored": len(enhanced_chunks),
            "workbook_path": request.workbook_path
        }
        
    except Exception as e:
        logger.error(f"Error embedding and storing workbook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/store-precomputed-workbook-embeddings")
async def store_workbook_embeddings(
    request: StorePrecomputedEmbeddingsRequest,
    storage: EmbeddingStorage = Depends(get_storage)
):
    """
    Store pre-computed embeddings and chunks for a workbook.
    This endpoint accepts already computed embeddings and stores them directly.
    """
    logger.info(f"Storing pre-computed embeddings for workbook: {request.workbook_path}")
    
    try:
        # Convert embeddings to numpy array
        embeddings = np.array(request.embeddings, dtype=np.float32)
        
        # Store in database
        workbook_id , version_id = storage.add_workbook_embeddings(
            workbook_path=request.workbook_path,
            embeddings=embeddings,
            chunks=request.chunks,
            embedding_model=request.embedding_model,
            create_new_version=request.create_new_version
        )
        
        return {
            "status": "success",
            "workbook_id": workbook_id,
            "version_id": version_id,
            "chunks_stored": len(request.chunks),
            "embedding_dimension": embeddings.shape[1] if len(embeddings) > 0 else 0,
            "workbook_path": request.workbook_path
        }
        
    except Exception as e:
        logger.error(f"Error storing workbook embeddings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list-workbooks")
async def list_workbooks(storage: EmbeddingStorage = Depends(get_storage)):
    """
    List all workbooks in the embedding database.
    """
    try:
        workbooks = storage.list_workbooks()
        
        return {
            "status": "success",
            "workbooks": workbooks,
            "total_count": len(workbooks)
        }
        
    except Exception as e:
        logger.error(f"Error listing workbooks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete-workbook")
async def delete_workbook(
    workbook_path: str,
    storage: EmbeddingStorage = Depends(get_storage)
):
    """
    Delete a workbook and all its embeddings.
    """
    logger.info(f"Deleting workbook: {workbook_path}")
    
    try:
        storage.delete_workbook(workbook_path)
        
        return {
            "status": "success",
            "message": f"Workbook {workbook_path} deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error deleting workbook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
